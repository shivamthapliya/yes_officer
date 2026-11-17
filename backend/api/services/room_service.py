import uuid

from sqlalchemy.orm import Session

from api.common.pagination import Page, PaginationParams
from api.enums import UserRole
from api.errors.domain_errors import AuthErrors, RoomErrors
from api.exceptions import create_error
from api.models import Room, User
from api.realtime.connection_manager import ConnectionManager
from api.realtime.live_state import LiveStateStore
from api.repositories.user_repo import RoomParticipantRepository, RoomRepository
from api.schemas.room import JoinResponse, ParticipantOut, RoomDetail, RoomListItem, RoomUpdateRequest


def get_room_or_404(db: Session, room_id: uuid.UUID) -> Room:
    room = RoomRepository.get_by_id(db, room_id)
    if room is None:
        raise create_error(RoomErrors.ROOM_NOT_FOUND)
    return room


def get_owned_room(db: Session, room_id: uuid.UUID, user: User) -> Room:
    room = get_room_or_404(db, room_id)
    if room.teacher_id != user.id:
        raise create_error(RoomErrors.NOT_ROOM_OWNER)
    return room


def ensure_room_access(db: Session, room: Room, user: User) -> None:
    """Owner teacher or joined student; everyone else is refused."""
    if user.role == UserRole.TEACHER:
        if room.teacher_id != user.id:
            raise create_error(RoomErrors.NOT_ROOM_OWNER)
    elif not RoomParticipantRepository.is_member(db, room.id, user.id):
        raise create_error(RoomErrors.NOT_ROOM_MEMBER)


def _detail(db: Session, live: LiveStateStore, room: Room, user: User, count: int | None = None) -> RoomDetail:
    is_joined = user.role == UserRole.STUDENT and RoomParticipantRepository.is_member(db, room.id, user.id)
    return RoomDetail(
        id=room.id,
        name=room.name,
        teacher_name=room.teacher.full_name,
        teacher_id=room.teacher_id,
        participant_count=RoomRepository.participant_count(db, room.id) if count is None else count,
        is_joined=is_joined,
        is_owner=room.teacher_id == user.id,
        has_active_poll=live.get_active_poll_id(str(room.id)) is not None,
        created_at=room.created_at,
    )


def list_rooms(
    db: Session, live: LiveStateStore, user: User, search: str | None, params: PaginationParams
) -> Page[RoomListItem]:
    rows, total = RoomRepository.list_rooms(db, search=search, offset=params.offset, limit=params.limit)
    joined = RoomParticipantRepository.joined_room_ids(db, user.id) if user.role == UserRole.STUDENT else set()
    items = [
        RoomListItem(
            id=room.id,
            name=room.name,
            teacher_name=room.teacher.full_name,
            participant_count=count,
            is_joined=room.id in joined,
            has_active_poll=live.get_active_poll_id(str(room.id)) is not None,
        )
        for room, count in rows
    ]
    return Page[RoomListItem].build(items, total, params)


def get_room(db: Session, live: LiveStateStore, room_id: uuid.UUID, user: User) -> RoomDetail:
    return _detail(db, live, get_room_or_404(db, room_id), user)


def get_my_room(db: Session, live: LiveStateStore, user: User) -> RoomDetail:
    if user.role != UserRole.TEACHER:
        raise create_error(AuthErrors.INVALID_ROLE)
    room = RoomRepository.get_by_teacher(db, user.id)
    if room is None:  # self-heal: provisioning is idempotent
        room = RoomRepository.provision_for_teacher(db, user.id, f"{user.full_name}'s Room"[:120])
        db.commit()
    return _detail(db, live, room, user)


def update_my_room(db: Session, live: LiveStateStore, user: User, request: RoomUpdateRequest) -> RoomDetail:
    if user.role != UserRole.TEACHER:
        raise create_error(AuthErrors.INVALID_ROLE)
    room = RoomRepository.get_by_teacher(db, user.id)
    if room is None:
        raise create_error(RoomErrors.ROOM_NOT_FOUND)
    room.name = request.name
    db.commit()
    return _detail(db, live, room, user)


def join_room(db: Session, room_id: uuid.UUID, user: User) -> JoinResponse:
    get_room_or_404(db, room_id)
    created = RoomParticipantRepository.add(db, room_id, user.id)
    db.commit()
    membership = RoomParticipantRepository.get(db, room_id, user.id)
    return JoinResponse(room_id=room_id, joined_at=membership.joined_at, already_member=not created)


def list_joined(db: Session, live: LiveStateStore, user: User) -> list[RoomDetail]:
    room_ids = RoomParticipantRepository.joined_room_ids(db, user.id)
    rooms = [RoomRepository.get_by_id(db, rid) for rid in room_ids]
    details = [_detail(db, live, r, user) for r in rooms if r is not None]
    return sorted(details, key=lambda d: d.name.casefold())


def list_participants(
    db: Session, manager: ConnectionManager, room_id: uuid.UUID, user: User
) -> list[ParticipantOut]:
    room = get_owned_room(db, room_id, user)
    online = {u["id"] for u in manager.online_users(str(room.id))}
    return [
        ParticipantOut(
            student_id=p.student_id,
            full_name=p.student.full_name,
            joined_at=p.joined_at,
            is_online=str(p.student_id) in online,
        )
        for p in RoomParticipantRepository.list_for_room(db, room.id)
    ]
