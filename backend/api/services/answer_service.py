"""Official MCQ answer submission. Independent of chat/AI: validated and accepted
atomically in Redis (first valid answer wins), acknowledged with the server
receipt time."""

import uuid

from sqlalchemy.orm import Session

from api.errors.domain_errors import AnswerErrors, PollErrors, RoomErrors
from api.exceptions import create_error
from api.models import User
from api.realtime import events
from api.realtime.events import RoomEvent
from api.realtime.live_state import LiveStateStore
from api.repositories.user_repo import RoomParticipantRepository
from api.schemas.results import AnswerReceipt, AnswerSubmitRequest
from api.services.results_service import ms_to_dt

_REJECTIONS = {
    "closed": AnswerErrors.ANSWER_POLL_CLOSED,
    "expired": AnswerErrors.ANSWER_EXPIRED,
    "not_current": AnswerErrors.ANSWER_NOT_CURRENT,
    "invalid_option": AnswerErrors.ANSWER_INVALID_OPTION,
}


def submit_answer(
    db: Session, live: LiveStateStore, poll_id: uuid.UUID, user: User, request: AnswerSubmitRequest
) -> tuple[AnswerReceipt, list[RoomEvent]]:
    meta = live.get_meta(str(poll_id))
    room_id = meta.get("room_id")
    if not room_id:
        raise create_error(PollErrors.POLL_NOT_ACTIVE)
    if not RoomParticipantRepository.is_member(db, uuid.UUID(room_id), user.id):
        raise create_error(RoomErrors.NOT_ROOM_MEMBER)

    result = live.accept_answer(str(poll_id), str(request.question_id), str(user.id), str(request.option_id))
    if result.outcome in _REJECTIONS:
        raise create_error(_REJECTIONS[result.outcome])

    receipt = AnswerReceipt(
        status=result.outcome,
        question_id=request.question_id,
        option_id=uuid.UUID(result.option_id),
        received_at=ms_to_dt(result.ts_ms),
    )
    progress: list[RoomEvent] = []
    if result.outcome == "accepted" and result.answered_count is not None:
        progress.append(
            events.answer_progress(room_id, str(poll_id), str(request.question_id), result.answered_count, result.option_id)
        )
    return receipt, progress
