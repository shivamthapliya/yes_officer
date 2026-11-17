"""Live poll lifecycle: start → (advance)* → end | cancel, plus live state reads.

PostgreSQL holds the authoritative status (conditional transitions under a row
lock); Redis holds the live state. Events are returned to the caller and
broadcast after the HTTP response.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.config.settings import settings
from api.enums import AnalysisStatus, PollStatus, ResultsStatus, UserRole
from api.errors.domain_errors import PollErrors
from api.exceptions import create_error
from api.models import Poll, PollQuestion, User
from api.realtime import events
from api.realtime.events import RoomEvent
from api.realtime.live_state import LiveStateStore
from api.repositories.ai_repo import BatchRepository
from api.repositories.poll_repo import PollRepository
from api.repositories.user_repo import RoomParticipantRepository, RoomRepository, UserRepository
from api.schemas.poll import LiveOptionOut, LivePollState, LiveQuestionOut
from api.schemas.results import PollResults
from api.services import results_service
from api.services.poll_service import get_owned_poll
from api.services.results_service import AnswerFact, compute_poll_results, ms_to_dt, question_structure
from api.workers import dispatch

logger = logging.getLogger(__name__)


@dataclass
class LifecycleOutcome:
    events: list[RoomEvent] = field(default_factory=list)
    post_actions: list[tuple[Any, tuple]] = field(default_factory=list)  # (callable, args) run after response


def live_question(q: PollQuestion) -> dict[str, Any]:
    """Student-safe question payload: never includes correctness."""
    return LiveQuestionOut(
        id=q.id, position=q.position, prompt=q.prompt,
        options=[LiveOptionOut(id=o.id, position=o.position, label=o.label) for o in q.options],
    ).model_dump(mode="json")


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


def _validate_for_start(poll: Poll) -> None:
    problems: list[str] = []
    if not poll.questions:
        problems.append("Add at least one question")
    for q in poll.questions:
        n = len(q.options)
        if n < settings.POLL_MIN_OPTIONS or n > settings.POLL_MAX_OPTIONS:
            problems.append(f"Question {q.position + 1} needs {settings.POLL_MIN_OPTIONS}–{settings.POLL_MAX_OPTIONS} options")
        if sum(o.is_correct for o in q.options) != 1:
            problems.append(f"Question {q.position + 1} needs exactly one correct option")
    if problems:
        raise create_error(PollErrors.POLL_INVALID_FOR_START, {"problems": problems})


# ---------------------------------------------------------------- start
def start_poll(
    db: Session, live: LiveStateStore, poll_id: uuid.UUID, user: User, connected_student_ids: list[str]
) -> LifecycleOutcome:
    get_owned_poll(db, poll_id, user)
    poll = PollRepository.get_for_update(db, poll_id)
    if poll.status != PollStatus.DRAFT:
        raise create_error(PollErrors.POLL_NOT_DRAFT, {"status": poll.status.value})
    poll = PollRepository.get(db, poll_id, with_questions=True)
    _validate_for_start(poll)

    room_id = str(poll.room_id)
    if live.get_active_poll_id(room_id):
        raise create_error(PollErrors.POLL_ALREADY_ACTIVE)

    started_at = datetime.now(UTC)
    deadline_at = started_at + timedelta(seconds=poll.time_limit_seconds)
    if not PollRepository.transition(
        db, poll.id, PollStatus.DRAFT,
        status=PollStatus.ACTIVE, started_at=started_at, deadline_at=deadline_at,
        analysis_status=AnalysisStatus.LIVE, results_status=ResultsStatus.NOT_STARTED,
    ):
        raise create_error(PollErrors.POLL_NOT_DRAFT)

    first = poll.questions[0]
    question_map = {
        str(q.id): {
            "options": [str(o.id) for o in q.options],
            "correct": next(str(o.id) for o in q.options if o.is_correct),
        }
        for q in poll.questions
    }
    live.init_poll(
        poll_id=str(poll.id), room_id=room_id, deadline_ms=int(deadline_at.timestamp() * 1000),
        question_map=question_map, first_question_id=str(first.id), participant_ids=connected_student_ids,
    )
    try:
        db.flush()  # surfaces the one-active-poll-per-room partial unique index
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        live.discard_poll(str(poll.id), room_id)
        raise create_error(PollErrors.POLL_ALREADY_ACTIVE) from exc
    except Exception:
        db.rollback()
        live.discard_poll(str(poll.id), room_id)
        raise

    poll_payload = {
        "poll_id": str(poll.id), "title": poll.title, "started_at": _iso(started_at),
        "deadline_at": _iso(deadline_at), "time_limit_seconds": poll.time_limit_seconds,
        "question_count": len(poll.questions),
    }
    outcome = LifecycleOutcome(
        events=[
            events.poll_started(room_id, poll_payload),
            events.question_opened(room_id, str(poll.id), 0, live_question(first), _iso(deadline_at)),
        ]
    )
    outcome.post_actions.append((_schedule_auto_end, (str(poll.id), deadline_at)))
    return outcome


def _schedule_auto_end(poll_id: str, deadline_at: datetime) -> None:
    try:
        dispatch.schedule_auto_end(poll_id, deadline_at)
    except Exception:  # noqa: BLE001 - the recovery sweeper also ends overdue polls
        logger.warning("Could not schedule auto-end for poll %s", poll_id, exc_info=True)


# ---------------------------------------------------------------- advance
def next_question(db: Session, live: LiveStateStore, poll_id: uuid.UUID, user: User) -> LifecycleOutcome:
    poll = get_owned_poll(db, poll_id, user, with_questions=True)
    if poll.status != PollStatus.ACTIVE:
        raise create_error(PollErrors.POLL_NOT_ACTIVE)
    meta = live.get_meta(str(poll.id))
    if meta.get("status") != "ACTIVE":
        raise create_error(PollErrors.POLL_NOT_ACTIVE)
    current_id = meta.get("current_question_id")
    ids = [str(q.id) for q in poll.questions]
    index = ids.index(current_id) if current_id in ids else -1
    if index + 1 >= len(ids):
        raise create_error(PollErrors.NO_MORE_QUESTIONS)
    nxt = poll.questions[index + 1]
    result = live.open_question(str(poll.id), current_id, str(nxt.id), index + 1)
    if result == "closed":
        raise create_error(PollErrors.POLL_NOT_ACTIVE)
    if result == "stale":  # a concurrent advance won; report the state as it is now
        return LifecycleOutcome()
    return LifecycleOutcome(
        events=[events.question_opened(str(poll.room_id), str(poll.id), index + 1, live_question(nxt), _iso(poll.deadline_at))]
    )


# ---------------------------------------------------------------- end
def end_poll(
    db: Session, live: LiveStateStore, poll_id: uuid.UUID, user: User | None
) -> tuple[PollResults, LifecycleOutcome]:
    """End by the teacher (user) or by the deadline (user=None, system)."""
    if user is not None:
        get_owned_poll(db, poll_id, user)
    poll = PollRepository.get_for_update(db, poll_id)
    if poll is None:
        raise create_error(PollErrors.POLL_NOT_FOUND)
    if poll.status == PollStatus.COMPLETED:
        db.rollback()
        owner = user or RoomRepository.get_by_id(db, poll.room_id).teacher
        return results_service.get_results(db, live, poll_id, owner), LifecycleOutcome()
    if poll.status != PollStatus.ACTIVE:
        raise create_error(PollErrors.POLL_NOT_ACTIVE, {"status": poll.status.value})

    ended_at = datetime.now(UTC)
    PollRepository.transition(
        db, poll.id, PollStatus.ACTIVE,
        status=PollStatus.COMPLETED, ended_at=ended_at,
        results_status=ResultsStatus.PROCESSING, analysis_status=AnalysisStatus.FINALIZING,
    )
    room_id = str(poll.room_id)
    snapshot = live.close_and_snapshot(str(poll.id), room_id)

    poll = PollRepository.get(db, poll_id, with_questions=True)
    facts = [AnswerFact(a.question_id, a.student_id, a.option_id, ms_to_dt(a.ts_ms), a.seq) for a in snapshot.answers]
    everyone = snapshot.participant_ids | {a.student_id for a in facts}
    names = {str(k): v for k, v in UserRepository.get_names(db, [uuid.UUID(s) for s in everyone]).items()}
    results = compute_poll_results(
        poll_id=str(poll.id), title=poll.title, ended_at=ended_at, questions=question_structure(poll),
        answers=facts, participant_ids=snapshot.participant_ids, names=names,
    )
    correct_by_q = {q.question_id: q.correct_option_id for q in results.questions}
    live.store_results(
        str(poll.id),
        {
            "results": results.model_dump(mode="json"),
            "participant_ids": sorted(everyone),
            "answers": [
                {
                    "question_id": a.question_id, "student_id": a.student_id, "option_id": a.option_id,
                    "ts_ms": a.ts_ms, "seq": a.seq,
                    "is_correct": str(correct_by_q.get(uuid.UUID(a.question_id))) == a.option_id,
                }
                for a in snapshot.answers
            ],
        },
    )
    db.commit()

    outcome = LifecycleOutcome(events=[events.poll_ended(room_id, results.model_dump(mode="json"))])
    outcome.post_actions.append((_publish_persist, (str(poll.id),)))
    return results, outcome


def _publish_persist(poll_id: str) -> None:
    try:
        dispatch.publish_persist(poll_id)
    except Exception:  # noqa: BLE001 - recovery sweeper re-enqueues PROCESSING results
        logger.warning("Could not enqueue persistence for poll %s", poll_id, exc_info=True)


# ---------------------------------------------------------------- cancel
def cancel_poll(db: Session, live: LiveStateStore, poll_id: uuid.UUID, user: User) -> LifecycleOutcome:
    get_owned_poll(db, poll_id, user)
    poll = PollRepository.get_for_update(db, poll_id)
    if poll.status == PollStatus.CANCELLED:
        db.rollback()
        return LifecycleOutcome()  # idempotent
    if poll.status != PollStatus.ACTIVE:
        raise create_error(PollErrors.POLL_NOT_ACTIVE, {"status": poll.status.value})

    now = datetime.now(UTC)
    PollRepository.transition(
        db, poll.id, PollStatus.ACTIVE,
        status=PollStatus.CANCELLED, cancelled_at=now, analysis_status=AnalysisStatus.IDLE,
        results_status=ResultsStatus.NOT_STARTED,
    )
    task_ids = BatchRepository.cancel_open_for_poll(db, poll.id, now)
    PollRepository.delete_subtree_for_cancel(db, poll.id)
    db.commit()

    room_id = str(poll.room_id)
    live.cancel_cleanup(str(poll.id), room_id)
    outcome = LifecycleOutcome(events=[events.poll_cancelled(room_id, str(poll.id))])
    if task_ids:
        outcome.post_actions.append((dispatch.revoke, (task_ids,)))
    return outcome


# ---------------------------------------------------------------- live reads
def _live_state(db: Session, live: LiveStateStore, poll: Poll, user: User) -> LivePollState:
    meta = live.get_meta(str(poll.id)) if poll.status == PollStatus.ACTIVE else {}
    current_id = meta.get("current_question_id")
    current = next((q for q in poll.questions if str(q.id) == current_id), None)
    state = LivePollState(
        poll_id=poll.id, room_id=poll.room_id, title=poll.title, status=poll.status,
        started_at=poll.started_at, deadline_at=poll.deadline_at, server_time=datetime.now(UTC),
        question_count=len(poll.questions),
        current_index=current.position if current else None,
        current_question=LiveQuestionOut.model_validate(live_question(current)) if current else None,
    )
    if current is None:
        return state
    if user.role == UserRole.TEACHER:
        state.answered_count = live.answer_count(str(poll.id), current_id)
        state.participant_count = live.participant_count(str(poll.id))
        state.option_counts = live.option_counts(str(poll.id), current_id)
    else:
        mine = live.get_student_answer(str(poll.id), current_id, str(user.id))
        state.my_answer_option_id = uuid.UUID(mine["option_id"]) if mine else None
    return state


def get_live_state(db: Session, live: LiveStateStore, poll_id: uuid.UUID, user: User) -> LivePollState:
    poll = PollRepository.get(db, poll_id, with_questions=True)
    if poll is None:
        raise create_error(PollErrors.POLL_NOT_FOUND)
    room = RoomRepository.get_by_id(db, poll.room_id)
    if user.role == UserRole.TEACHER:
        if room.teacher_id != user.id:
            raise create_error(PollErrors.POLL_NOT_FOUND)
    elif not RoomParticipantRepository.is_member(db, room.id, user.id) or poll.status == PollStatus.DRAFT:
        raise create_error(PollErrors.POLL_NOT_FOUND)
    return _live_state(db, live, poll, user)


def get_room_active_poll(
    db: Session, live: LiveStateStore, room_id: uuid.UUID, user: User
) -> LivePollState | None:
    poll_id = live.get_active_poll_id(str(room_id))
    if not poll_id:
        return None
    poll = PollRepository.get(db, uuid.UUID(poll_id), with_questions=True)
    if poll is None or poll.status != PollStatus.ACTIVE:
        return None
    return _live_state(db, live, poll, user)
