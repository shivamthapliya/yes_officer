"""Ephemeral room chat. Messages are broadcast first; buffering for AI analysis is a
fire-and-forget side path that only runs for student messages during an active
poll. Nothing is ever written to PostgreSQL."""

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from api.config.settings import settings
from api.db.session import SessionLocal
from api.enums import UserRole
from api.realtime.live_state import LiveStateStore, now_ms
from api.services.batch_dispatch_service import dispatch_threshold

logger = logging.getLogger(__name__)


class ChatValidationError(ValueError):
    pass


def build_chat_event(*, author_id: str, author_name: str, author_role: UserRole, content: Any) -> dict[str, Any]:
    if not isinstance(content, str):
        raise ChatValidationError("Message must be text")
    text = content.strip()
    if not text:
        raise ChatValidationError("Message is empty")
    if len(text) > settings.CHAT_MAX_LENGTH:
        raise ChatValidationError(f"Message exceeds {settings.CHAT_MAX_LENGTH} characters")
    return {
        "type": "chat",
        "id": str(uuid.uuid4()),
        "author_id": author_id,
        "author_name": author_name,
        "author_role": author_role.value,
        "content": text,
        "sent_at": datetime.now(UTC).isoformat(),
    }


def buffer_for_analysis(live: LiveStateStore, room_id: str, event: dict[str, Any]) -> None:
    """Append a student message to the active poll's AI buffer (if any).

    Runs off the event loop. Redis or Celery failures are logged and never affect
    chat delivery, which has already happened.
    """
    try:
        poll_id = live.get_active_poll_id(room_id)
        if not poll_id:
            return
        question_id = live.get_meta(poll_id).get("current_question_id")
        length = live.buffer_chat(
            poll_id,
            {
                "msg_id": event["id"],
                "student_id": event["author_id"],
                "question_id": question_id,
                "received_ms": now_ms(),
                "content": event["content"],
            },
        )
        if length >= settings.CHAT_BATCH_SIZE:
            with SessionLocal() as db:
                dispatch_threshold(db, live, poll_id)
    except Exception:  # noqa: BLE001
        logger.warning("Chat buffering failed for room %s", room_id, exc_info=True)


def register_presence(live: LiveStateStore, room_id: str, student_id: str) -> None:
    """A student connected while a poll is active counts as a participant."""
    try:
        poll_id = live.get_active_poll_id(room_id)
        if poll_id and live.get_meta(poll_id).get("status") == "ACTIVE":
            live.add_participant(poll_id, student_id)
    except Exception:  # noqa: BLE001
        logger.warning("Could not register participant in room %s", room_id, exc_info=True)
