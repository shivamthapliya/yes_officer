"""Poll results (verified answer statistics) and student history/review.

`compute_poll_results` is the single pure function used both for the live
end-of-poll payload (from the Redis snapshot) and for historical views (from
PostgreSQL), so the two can never disagree.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from api.common.pagination import Page, PaginationParams
from api.enums import PollStatus, ResultsStatus, UserRole
from api.errors.domain_errors import PollErrors
from api.exceptions import create_error
from api.models import Poll, User
from api.realtime.live_state import LiveStateStore
from api.repositories.poll_repo import AnswerRepository, PollParticipantRepository, PollRepository
from api.repositories.user_repo import RoomRepository, UserRepository
from api.schemas.results import (
    FirstCorrectStudent,
    MyPollItem,
    OptionResult,
    PollResults,
    PollReview,
    QuestionResult,
    ReviewOption,
    ReviewQuestion,
)


@dataclass(frozen=True)
class AnswerFact:
    question_id: str
    student_id: str
    option_id: str
    received_at: datetime
    seq: int


def ms_to_dt(ms: int) -> datetime:
    return datetime.fromtimestamp(ms / 1000, tz=UTC)


def question_structure(poll: Poll) -> list[dict[str, Any]]:
    """Serializable question/option structure (with correctness) used for results."""
    return [
        {
            "id": str(q.id),
            "position": q.position,
            "prompt": q.prompt,
            "options": [
                {"id": str(o.id), "position": o.position, "label": o.label, "is_correct": o.is_correct}
                for o in q.options
            ],
        }
        for q in poll.questions
    ]


def compute_poll_results(
    *,
    poll_id: str,
    title: str,
    ended_at: datetime | None,
    questions: list[dict[str, Any]],
    answers: list[AnswerFact],
    participant_ids: set[str],
    names: dict[str, str],
) -> PollResults:
    everyone = set(participant_ids) | {a.student_id for a in answers}
    participant_count = len(everyone)
    by_question: dict[str, list[AnswerFact]] = {}
    for a in answers:
        by_question.setdefault(a.question_id, []).append(a)

    results: list[QuestionResult] = []
    for q in sorted(questions, key=lambda x: x["position"]):
        q_answers = by_question.get(q["id"], [])
        correct = next((o["id"] for o in q["options"] if o["is_correct"]), None)
        answered = len(q_answers)
        counts: dict[str, int] = {}
        for a in q_answers:
            counts[a.option_id] = counts.get(a.option_id, 0) + 1
        correct_answers = sorted((a for a in q_answers if a.option_id == correct), key=lambda a: a.seq)
        first = correct_answers[0] if correct_answers else None
        results.append(
            QuestionResult(
                question_id=q["id"],
                position=q["position"],
                prompt=q["prompt"],
                correct_option_id=correct,
                answered_count=answered,
                correct_count=len(correct_answers),
                participant_count=participant_count,
                options=[
                    OptionResult(
                        option_id=o["id"],
                        position=o["position"],
                        label=o["label"],
                        count=counts.get(o["id"], 0),
                        percentage=round(100.0 * counts.get(o["id"], 0) / answered, 1) if answered else 0.0,
                        is_correct=o["is_correct"],
                    )
                    for o in sorted(q["options"], key=lambda x: x["position"])
                ],
                first_correct_student=(
                    FirstCorrectStudent(
                        student_id=first.student_id,
                        full_name=names.get(first.student_id, "A student"),
                        received_at=first.received_at,
                    )
                    if first
                    else None
                ),
            )
        )
    return PollResults(
        poll_id=poll_id, title=title, ended_at=ended_at, participant_count=participant_count, questions=results
    )


# ---------- reading results ----------
def _results_from_db(db: Session, poll: Poll) -> PollResults:
    answers = [
        AnswerFact(str(a.question_id), str(a.student_id), str(a.selected_option_id), a.received_at, a.accept_seq)
        for a in AnswerRepository.for_poll(db, poll.id)
    ]
    participants = {str(s) for s in PollParticipantRepository.student_ids(db, poll.id)}
    ids = [uuid.UUID(s) for s in participants | {a.student_id for a in answers}]
    names = {str(k): v for k, v in UserRepository.get_names(db, ids).items()}
    return compute_poll_results(
        poll_id=str(poll.id), title=poll.title, ended_at=poll.ended_at,
        questions=question_structure(poll), answers=answers, participant_ids=participants, names=names,
    )


def _snapshot(live: LiveStateStore, poll: Poll) -> dict[str, Any] | None:
    if poll.results_status == ResultsStatus.PERSISTED:
        return None
    return live.get_results(str(poll.id))


def _is_participant(db: Session, live: LiveStateStore, poll: Poll, student_id: uuid.UUID) -> bool:
    if PollParticipantRepository.is_participant(db, poll.id, student_id):
        return True
    snap = _snapshot(live, poll)
    return bool(snap) and str(student_id) in snap.get("participant_ids", [])


def get_results(db: Session, live: LiveStateStore, poll_id: uuid.UUID, user: User) -> PollResults:
    poll = PollRepository.get(db, poll_id, with_questions=True)
    if poll is None:
        raise create_error(PollErrors.POLL_NOT_FOUND)
    room = RoomRepository.get_by_id(db, poll.room_id)
    if user.role == UserRole.TEACHER:
        if room.teacher_id != user.id:
            raise create_error(PollErrors.POLL_NOT_FOUND)
    elif poll.status == PollStatus.COMPLETED and not _is_participant(db, live, poll, user.id):
        raise create_error(PollErrors.NOT_A_PARTICIPANT)
    if poll.status != PollStatus.COMPLETED:
        raise create_error(PollErrors.RESULTS_NOT_AVAILABLE, {"status": poll.status.value})
    snap = _snapshot(live, poll)
    if snap:
        return PollResults.model_validate(snap["results"])
    return _results_from_db(db, poll)


def list_my_polls(db: Session, live: LiveStateStore, user: User, params: PaginationParams) -> Page[MyPollItem]:
    rows, total = PollParticipantRepository.completed_polls_for_student(
        db, user.id, offset=params.offset, limit=params.limit
    )
    if params.page == 1:
        # Polls that just ended are served from the Redis snapshot until persisted.
        listed = {p.id for p, _ in rows}
        for poll, room in PollRepository.unpersisted_completed_in_joined_rooms(db, user.id):
            snap = live.get_results(str(poll.id))
            if poll.id not in listed and snap and str(user.id) in snap.get("participant_ids", []):
                rows.insert(0, (poll, room))
                total += 1
    items = [
        MyPollItem(
            poll_id=poll.id, title=poll.title, room_id=room.id, room_name=room.name,
            teacher_name=room.teacher.full_name, ended_at=poll.ended_at,
            question_count=PollRepository.question_count(db, poll.id),
        )
        for poll, room in rows
    ]
    return Page[MyPollItem].build(items, total, params)


def get_review(db: Session, live: LiveStateStore, poll_id: uuid.UUID, user: User) -> PollReview:
    poll = PollRepository.get(db, poll_id, with_questions=True)
    if poll is None or poll.status != PollStatus.COMPLETED:
        raise create_error(PollErrors.POLL_NOT_FOUND)
    if not _is_participant(db, live, poll, user.id):
        raise create_error(PollErrors.NOT_A_PARTICIPANT)

    mine: dict[str, tuple[str, datetime]] = {}
    snap = _snapshot(live, poll)
    if snap:
        for a in snap.get("answers", []):
            if a["student_id"] == str(user.id):
                mine[a["question_id"]] = (a["option_id"], ms_to_dt(a["ts_ms"]))
    else:
        for a in AnswerRepository.for_student(db, poll.id, user.id):
            mine[str(a.question_id)] = (str(a.selected_option_id), a.received_at)

    questions: list[ReviewQuestion] = []
    correct_total = 0
    for q in poll.questions:
        correct = next((o.id for o in q.options if o.is_correct), None)
        selected = mine.get(str(q.id))
        is_correct = None if selected is None else (correct is not None and selected[0] == str(correct))
        correct_total += bool(is_correct)
        questions.append(
            ReviewQuestion(
                question_id=q.id, position=q.position, prompt=q.prompt,
                options=[ReviewOption(option_id=o.id, position=o.position, label=o.label, is_correct=o.is_correct) for o in q.options],
                selected_option_id=selected[0] if selected else None,
                correct_option_id=correct, is_correct=is_correct,
                answered_at=selected[1] if selected else None,
            )
        )
    room = RoomRepository.get_by_id(db, poll.room_id)
    return PollReview(
        poll_id=poll.id, title=poll.title, room_name=room.name, teacher_name=room.teacher.full_name,
        ended_at=poll.ended_at, answered_count=len(mine), correct_count=correct_total,
        question_count=len(poll.questions), questions=questions,
    )
