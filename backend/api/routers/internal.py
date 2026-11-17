"""Worker → API callbacks. Celery runs in separate processes that cannot reach the
in-memory WebSocket connections, so workers POST here (shared-secret header)."""

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from api.db.session import get_db
from api.dependencies import get_connection_manager, get_live_state, verify_internal_secret
from api.errors.domain_errors import PollErrors
from api.exceptions import AppException, create_error
from api.realtime import events
from api.realtime.connection_manager import ConnectionManager
from api.realtime.live_state import LiveStateStore
from api.repositories.poll_repo import PollRepository
from api.routers.delivery import schedule_events, schedule_outcome
from api.schemas.common import MessageResponse
from api.schemas.insights import InsightsUpdatedEvent
from api.services import poll_lifecycle_service

router = APIRouter(prefix="/internal", tags=["Internal"], dependencies=[Depends(verify_internal_secret)], include_in_schema=False)


@router.post("/events/insights-updated", response_model=MessageResponse)
def insights_updated(
    body: InsightsUpdatedEvent,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    manager: ConnectionManager = Depends(get_connection_manager),
):
    poll = PollRepository.get(db, body.poll_id)
    if poll is None:
        raise create_error(PollErrors.POLL_NOT_FOUND)
    schedule_events(
        background, manager,
        [events.insights_updated(str(poll.room_id), str(poll.id), str(body.question_id) if body.question_id else None, body.version)],
    )
    return MessageResponse(message="queued")


@router.post("/polls/{poll_id}/auto-end", response_model=MessageResponse)
def auto_end(
    poll_id: uuid.UUID,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    live: LiveStateStore = Depends(get_live_state),
    manager: ConnectionManager = Depends(get_connection_manager),
):
    """No-op unless the poll is still ACTIVE and its deadline has passed."""
    poll = PollRepository.get(db, poll_id)
    if poll is None or poll.status.value != "ACTIVE":
        return MessageResponse(message="not active")
    from datetime import UTC, datetime

    if poll.deadline_at and poll.deadline_at > datetime.now(UTC):
        return MessageResponse(message="not due")
    try:
        _, outcome = poll_lifecycle_service.end_poll(db, live, poll_id, None)
    except AppException as exc:
        if exc.definition is PollErrors.POLL_NOT_ACTIVE:
            return MessageResponse(message="not active")
        raise
    schedule_outcome(background, manager, outcome)
    return MessageResponse(message="ended")
