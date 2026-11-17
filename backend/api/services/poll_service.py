"""Draft poll management: polls, questions and options are editable only in DRAFT."""

import uuid

from sqlalchemy.orm import Session

from api.common.pagination import Page, PaginationParams
from api.enums import PollStatus
from api.errors.domain_errors import PollErrors, RoomErrors
from api.exceptions import create_error
from api.models import Poll, PollQuestion, User
from api.repositories.poll_repo import PollRepository, QuestionRepository
from api.repositories.user_repo import RoomRepository
from api.schemas.poll import (
    PollCreateRequest,
    PollDetail,
    PollSummary,
    PollUpdateRequest,
    QuestionInput,
    QuestionOrderRequest,
    QuestionOut,
    QuestionUpdateRequest,
)
from api.services.room_service import get_owned_room


def get_owned_poll(db: Session, poll_id: uuid.UUID, user: User, *, with_questions: bool = False) -> Poll:
    poll = PollRepository.get(db, poll_id, with_questions=with_questions)
    if poll is None:
        raise create_error(PollErrors.POLL_NOT_FOUND)
    room = RoomRepository.get_by_id(db, poll.room_id)
    if room is None or room.teacher_id != user.id:
        # Do not reveal other teachers' polls.
        raise create_error(PollErrors.POLL_NOT_FOUND)
    return poll


def _require_draft(poll: Poll) -> None:
    if poll.status != PollStatus.DRAFT:
        raise create_error(PollErrors.POLL_NOT_DRAFT, {"status": poll.status.value})


def _get_owned_question(db: Session, question_id: uuid.UUID, user: User) -> tuple[PollQuestion, Poll]:
    question = QuestionRepository.get(db, question_id)
    if question is None:
        raise create_error(PollErrors.QUESTION_NOT_FOUND)
    poll = get_owned_poll(db, question.poll_id, user)
    return question, poll


def to_summary(poll: Poll, question_count: int) -> PollSummary:
    return PollSummary.model_validate(poll).model_copy(update={"question_count": question_count})


def to_detail(db: Session, poll_id: uuid.UUID) -> PollDetail:
    db.expire_all()
    poll = PollRepository.get(db, poll_id, with_questions=True)
    summary = to_summary(poll, len(poll.questions)).model_dump()
    return PollDetail(**summary, questions=[QuestionOut.model_validate(q) for q in poll.questions])


def list_polls(
    db: Session, room_id: uuid.UUID, user: User, status: PollStatus | None, params: PaginationParams
) -> Page[PollSummary]:
    get_owned_room(db, room_id, user)
    rows, total = PollRepository.list_for_room(db, room_id, status=status, offset=params.offset, limit=params.limit)
    return Page[PollSummary].build([to_summary(p, n) for p, n in rows], total, params)


def create_poll(db: Session, room_id: uuid.UUID, user: User, request: PollCreateRequest) -> PollDetail:
    room = get_owned_room(db, room_id, user)
    if room is None:
        raise create_error(RoomErrors.ROOM_NOT_FOUND)
    poll = PollRepository.create(
        db, room_id=room.id, title=request.title, time_limit_seconds=request.time_limit_seconds
    )
    for position, q in enumerate(request.questions):
        QuestionRepository.add(
            db, poll_id=poll.id, position=position, prompt=q.prompt,
            options=[(o.label, o.is_correct) for o in q.options],
        )
    db.commit()
    return to_detail(db, poll.id)


def get_poll(db: Session, poll_id: uuid.UUID, user: User) -> PollDetail:
    get_owned_poll(db, poll_id, user)
    return to_detail(db, poll_id)


def update_poll(db: Session, poll_id: uuid.UUID, user: User, request: PollUpdateRequest) -> PollDetail:
    poll = get_owned_poll(db, poll_id, user)
    _require_draft(poll)
    if request.title is not None:
        poll.title = request.title
    if request.time_limit_seconds is not None:
        poll.time_limit_seconds = request.time_limit_seconds
    db.commit()
    return to_detail(db, poll.id)


def delete_poll(db: Session, poll_id: uuid.UUID, user: User) -> None:
    poll = get_owned_poll(db, poll_id, user)
    _require_draft(poll)
    PollRepository.delete(db, poll)
    db.commit()


def add_question(db: Session, poll_id: uuid.UUID, user: User, request: QuestionInput) -> PollDetail:
    poll = get_owned_poll(db, poll_id, user)
    _require_draft(poll)
    PollRepository.get_for_update(db, poll.id)  # serialize concurrent position allocation
    QuestionRepository.add(
        db, poll_id=poll.id, position=QuestionRepository.next_position(db, poll.id), prompt=request.prompt,
        options=[(o.label, o.is_correct) for o in request.options],
    )
    db.commit()
    return to_detail(db, poll.id)


def update_question(db: Session, question_id: uuid.UUID, user: User, request: QuestionUpdateRequest) -> PollDetail:
    question, poll = _get_owned_question(db, question_id, user)
    _require_draft(poll)
    if request.prompt is not None:
        question.prompt = request.prompt
    if request.options is not None:
        QuestionRepository.replace_options(db, question, [(o.label, o.is_correct) for o in request.options])
    db.commit()
    return to_detail(db, poll.id)


def delete_question(db: Session, question_id: uuid.UUID, user: User) -> PollDetail:
    question, poll = _get_owned_question(db, question_id, user)
    _require_draft(poll)
    db.delete(question)
    db.flush()
    QuestionRepository.compact_positions(db, poll.id)
    db.commit()
    return to_detail(db, poll.id)


def reorder_questions(db: Session, poll_id: uuid.UUID, user: User, request: QuestionOrderRequest) -> PollDetail:
    poll = get_owned_poll(db, poll_id, user)
    _require_draft(poll)
    existing = QuestionRepository.list_ids(db, poll.id)
    if len(request.question_ids) != len(existing) or set(request.question_ids) != set(existing):
        raise create_error(PollErrors.INVALID_QUESTION_ORDER)
    QuestionRepository.set_positions(db, request.question_ids)
    db.commit()
    return to_detail(db, poll.id)
