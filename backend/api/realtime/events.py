"""WebSocket event shapes. Services return `RoomEvent`s; routers deliver them after
the response (FastAPI BackgroundTasks), so broadcasting never delays the caller."""

from dataclasses import dataclass
from typing import Any

from api.enums import UserRole


@dataclass(frozen=True)
class RoomEvent:
    room_id: str
    payload: dict[str, Any]
    role: UserRole | None = None  # None = everyone in the room


def poll_started(room_id: str, poll: dict[str, Any]) -> RoomEvent:
    return RoomEvent(room_id, {"type": "poll_started", "poll": poll})


def question_opened(room_id: str, poll_id: str, index: int, question: dict[str, Any], deadline_at: str) -> RoomEvent:
    return RoomEvent(
        room_id,
        {"type": "question_opened", "poll_id": poll_id, "index": index, "question": question, "deadline_at": deadline_at},
    )


def poll_ended(room_id: str, results: dict[str, Any]) -> RoomEvent:
    return RoomEvent(room_id, {"type": "poll_ended", "poll_id": results["poll_id"], "results": results})


def poll_cancelled(room_id: str, poll_id: str) -> RoomEvent:
    return RoomEvent(room_id, {"type": "poll_cancelled", "poll_id": poll_id})


def answer_progress(
    room_id: str, poll_id: str, question_id: str, answered_count: int, option_id: str
) -> RoomEvent:
    return RoomEvent(
        room_id,
        {
            "type": "answer_progress", "poll_id": poll_id, "question_id": question_id,
            "answered_count": answered_count, "option_id": option_id,
        },
        role=UserRole.TEACHER,
    )


def insights_updated(room_id: str, poll_id: str, question_id: str | None, version: int) -> RoomEvent:
    return RoomEvent(
        room_id,
        {"type": "insights_updated", "poll_id": poll_id, "question_id": question_id, "version": version},
        role=UserRole.TEACHER,
    )
