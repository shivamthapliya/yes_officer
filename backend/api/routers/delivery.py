"""Schedule WebSocket broadcasts and post-commit actions to run after the response."""

from collections.abc import Iterable

from fastapi import BackgroundTasks

from api.realtime.connection_manager import ConnectionManager
from api.realtime.events import RoomEvent
from api.services.poll_lifecycle_service import LifecycleOutcome


def schedule_events(background: BackgroundTasks, manager: ConnectionManager, room_events: Iterable[RoomEvent]) -> None:
    for e in room_events:
        background.add_task(manager.broadcast, e.room_id, e.payload, role=e.role)


def schedule_outcome(background: BackgroundTasks, manager: ConnectionManager, outcome: LifecycleOutcome) -> None:
    schedule_events(background, manager, outcome.events)
    for fn, args in outcome.post_actions:
        background.add_task(fn, *args)
