"""Room WebSocket: ephemeral chat + live poll events.

Inbound:  {"type": "chat", "content": str} | {"type": "ping"}
Outbound: chat, presence, poll_started, question_opened, poll_ended, poll_cancelled,
          answer_progress (teacher), insights_updated (teacher), error, pong
"""

import asyncio
import logging
import time
import uuid
from collections import deque

from anyio import to_thread
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from api.config.settings import settings
from api.db.session import SessionLocal
from api.enums import UserRole
from api.realtime.connection_manager import Connection, ConnectionManager
from api.realtime.live_state import LiveStateStore
from api.repositories.user_repo import RoomParticipantRepository, RoomRepository, UserRepository
from api.services.chat_service import ChatValidationError, build_chat_event, buffer_for_analysis, register_presence

logger = logging.getLogger(__name__)
router = APIRouter()

CLOSE_FORBIDDEN = 4403
CLOSE_UNAUTHORIZED = 4401


def _authorize(token: str | None, room_id: str, jwt_service) -> tuple[str, UserRole, str] | int:
    """Returns (user_id, role, full_name) or a close code. Runs in a worker thread."""
    if not token:
        return CLOSE_UNAUTHORIZED
    payload = jwt_service.decode(token, "access")
    if payload is None:
        return CLOSE_UNAUTHORIZED
    try:
        room_uuid = uuid.UUID(room_id)
        user_uuid = uuid.UUID(payload.sub)
    except ValueError:
        return CLOSE_FORBIDDEN
    with SessionLocal() as db:
        user = UserRepository.get_by_id(db, user_uuid)
        room = RoomRepository.get_by_id(db, room_uuid)
        if user is None or not user.is_active or room is None:
            return CLOSE_FORBIDDEN
        if user.role == UserRole.TEACHER:
            allowed = room.teacher_id == user.id
        else:
            allowed = RoomParticipantRepository.is_member(db, room.id, user.id)
        if not allowed:
            return CLOSE_FORBIDDEN
        return str(user.id), user.role, user.full_name


class _RateLimiter:
    def __init__(self, count: int, window: float):
        self.count, self.window, self.hits = count, window, deque()

    def allow(self) -> bool:
        now = time.monotonic()
        while self.hits and now - self.hits[0] > self.window:
            self.hits.popleft()
        if len(self.hits) >= self.count:
            return False
        self.hits.append(now)
        return True


@router.websocket(f"{settings.API_PREFIX}/ws/rooms/{{room_id}}")
async def room_socket(websocket: WebSocket, room_id: str):
    origin = websocket.headers.get("origin")
    if origin and origin not in settings.CORS_ORIGINS:  # cross-site WebSocket hijacking guard
        await websocket.close(code=CLOSE_FORBIDDEN)
        return

    app = websocket.app
    manager: ConnectionManager = app.state.connection_manager
    live: LiveStateStore = app.state.live_state
    auth = await to_thread.run_sync(
        _authorize, websocket.cookies.get(settings.ACCESS_COOKIE_NAME), room_id, app.state.jwt_service
    )
    if isinstance(auth, int):
        await websocket.close(code=auth)
        return
    user_id, role, full_name = auth

    await websocket.accept()
    conn = Connection(websocket=websocket, user_id=user_id, role=role, full_name=full_name)
    await manager.register(room_id, conn)
    if role == UserRole.STUDENT:
        await to_thread.run_sync(register_presence, live, room_id, user_id)
    await manager.broadcast_presence(room_id)

    limiter = _RateLimiter(settings.CHAT_RATE_LIMIT_COUNT, settings.CHAT_RATE_LIMIT_WINDOW_SECONDS)
    background: set[asyncio.Task] = set()
    try:
        while True:
            message = await websocket.receive_json()
            kind = message.get("type") if isinstance(message, dict) else None
            if kind == "ping":
                await conn.send({"type": "pong"})
                continue
            if kind != "chat":
                await conn.send({"type": "error", "code": "UNKNOWN_MESSAGE", "message": "Unsupported message type"})
                continue
            if not limiter.allow():
                await conn.send({"type": "error", "code": "CHAT_RATE_LIMITED", "message": "You're sending messages too fast"})
                continue
            try:
                event = build_chat_event(
                    author_id=user_id, author_name=full_name, author_role=role, content=message.get("content")
                )
            except ChatValidationError as exc:
                await conn.send({"type": "error", "code": "CHAT_INVALID", "message": str(exc)})
                continue
            await manager.broadcast(room_id, event)  # broadcast first, always
            if role == UserRole.STUDENT:
                task = asyncio.create_task(to_thread.run_sync(buffer_for_analysis, live, room_id, event))
                background.add(task)
                task.add_done_callback(background.discard)
    except WebSocketDisconnect:
        pass
    except Exception:  # noqa: BLE001 - malformed frames etc.
        logger.info("WebSocket error in room %s", room_id, exc_info=True)
    finally:
        await manager.unregister(room_id, conn.id)
        await manager.broadcast_presence(room_id)
