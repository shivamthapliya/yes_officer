"""In-process WebSocket connection registry and room broadcast.

Scale-out note: with more than one FastAPI instance, this in-memory broadcast only
reaches sockets connected to the instance that handles the event. The future
design is to publish every room event to Redis Pub/Sub (channel `room:{id}`) and
have each instance relay to its local sockets; the internal worker callback would
become a publish too. That is deliberately out of scope for now.
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any

from fastapi import WebSocket

from api.config.settings import settings
from api.enums import UserRole

logger = logging.getLogger(__name__)


@dataclass(eq=False)
class Connection:
    websocket: WebSocket
    user_id: str
    role: UserRole
    full_name: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex)

    async def send(self, event: dict[str, Any]) -> None:
        await self.websocket.send_json(event)


class ConnectionManager:
    def __init__(self, send_timeout: float | None = None):
        self._rooms: dict[str, dict[str, Connection]] = {}
        self._lock = asyncio.Lock()
        self._send_timeout = send_timeout or settings.WS_SEND_TIMEOUT_SECONDS

    async def register(self, room_id: str, conn: Connection) -> None:
        async with self._lock:
            self._rooms.setdefault(room_id, {})[conn.id] = conn

    async def unregister(self, room_id: str, conn_id: str) -> None:
        async with self._lock:
            room = self._rooms.get(room_id)
            if room is not None:
                room.pop(conn_id, None)
                if not room:
                    self._rooms.pop(room_id, None)

    def snapshot(self, room_id: str) -> list[Connection]:
        return list(self._rooms.get(room_id, {}).values())

    def online_users(self, room_id: str) -> list[dict[str, str]]:
        seen: dict[str, dict[str, str]] = {}
        for c in self.snapshot(room_id):
            seen.setdefault(c.user_id, {"id": c.user_id, "full_name": c.full_name, "role": c.role.value})
        return list(seen.values())

    def connected_student_ids(self, room_id: str) -> list[str]:
        return sorted({c.user_id for c in self.snapshot(room_id) if c.role == UserRole.STUDENT})

    async def broadcast(
        self, room_id: str, event: dict[str, Any], *, role: UserRole | None = None
    ) -> None:
        """Send to every connection in the room (optionally only one role).

        Sends run concurrently with a per-send timeout; any connection that errors
        or times out is pruned so one dead client never blocks the others.
        """
        targets = [c for c in self.snapshot(room_id) if role is None or c.role == role]
        if not targets:
            return
        results = await asyncio.gather(
            *(asyncio.wait_for(c.send(event), timeout=self._send_timeout) for c in targets),
            return_exceptions=True,
        )
        for conn, result in zip(targets, results, strict=True):
            if isinstance(result, BaseException):
                logger.info("Pruning websocket %s in room %s: %r", conn.id, room_id, result)
                await self.unregister(room_id, conn.id)
                try:
                    await conn.websocket.close(code=1011)
                except Exception:  # noqa: BLE001 - socket is already broken
                    pass

    async def broadcast_presence(self, room_id: str) -> None:
        await self.broadcast(room_id, {"type": "presence", "users": self.online_users(room_id)})
