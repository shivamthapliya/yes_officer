import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.common.pagination import Page, PaginationParams
from api.db.session import get_db
from api.dependencies import (
    get_connection_manager,
    get_current_user,
    get_live_state,
    require_student,
    require_teacher,
)
from api.models import User
from api.realtime.connection_manager import ConnectionManager
from api.realtime.live_state import LiveStateStore
from api.schemas.poll import LivePollState
from api.schemas.room import JoinResponse, ParticipantOut, RoomDetail, RoomListItem, RoomUpdateRequest
from api.services import poll_lifecycle_service, room_service

router = APIRouter(prefix="/rooms", tags=["Rooms"])


@router.get("", response_model=Page[RoomListItem], summary="Browse teacher rooms")
def list_rooms(
    search: str | None = Query(None, max_length=120),
    params: PaginationParams = Depends(),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    live: LiveStateStore = Depends(get_live_state),
):
    return room_service.list_rooms(db, live, user, (search or "").strip() or None, params)


@router.get("/mine", response_model=RoomDetail, summary="The teacher's own room")
def my_room(user: User = Depends(require_teacher), db: Session = Depends(get_db), live: LiveStateStore = Depends(get_live_state)):
    return room_service.get_my_room(db, live, user)


@router.patch("/mine", response_model=RoomDetail, summary="Rename the teacher's room")
def update_my_room(
    body: RoomUpdateRequest,
    user: User = Depends(require_teacher),
    db: Session = Depends(get_db),
    live: LiveStateStore = Depends(get_live_state),
):
    return room_service.update_my_room(db, live, user, body)


@router.get("/joined", response_model=list[RoomDetail], summary="Rooms the student has joined")
def joined_rooms(user: User = Depends(require_student), db: Session = Depends(get_db), live: LiveStateStore = Depends(get_live_state)):
    return room_service.list_joined(db, live, user)


@router.get("/{room_id}", response_model=RoomDetail, summary="Room details")
def get_room(
    room_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    live: LiveStateStore = Depends(get_live_state),
):
    return room_service.get_room(db, live, room_id, user)


@router.post("/{room_id}/join", response_model=JoinResponse, summary="Join a room (idempotent)")
def join_room(room_id: uuid.UUID, user: User = Depends(require_student), db: Session = Depends(get_db)):
    return room_service.join_room(db, room_id, user)


@router.get("/{room_id}/participants", response_model=list[ParticipantOut], summary="Students in the room")
def participants(
    room_id: uuid.UUID,
    user: User = Depends(require_teacher),
    db: Session = Depends(get_db),
    manager: ConnectionManager = Depends(get_connection_manager),
):
    return room_service.list_participants(db, manager, room_id, user)


@router.get("/{room_id}/active-poll", response_model=LivePollState | None, summary="The room's live poll, if any")
def active_poll(
    room_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    live: LiveStateStore = Depends(get_live_state),
):
    room_service.ensure_room_access(db, room_service.get_room_or_404(db, room_id), user)
    return poll_lifecycle_service.get_room_active_poll(db, live, room_id, user)
