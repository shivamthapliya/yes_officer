"""User, room-membership and refresh-token data access. Repositories flush; services commit."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from api.enums import UserRole
from api.models import RefreshToken, Room, RoomParticipant, User


class UserRepository:
    @staticmethod
    def get_by_id(db: Session, user_id: uuid.UUID) -> User | None:
        return db.get(User, user_id)

    @staticmethod
    def get_by_email(db: Session, email: str) -> User | None:
        return db.scalar(select(User).where(func.lower(User.email) == email.lower()))

    @staticmethod
    def get_names(db: Session, user_ids: list[uuid.UUID]) -> dict[uuid.UUID, str]:
        if not user_ids:
            return {}
        rows = db.execute(select(User.id, User.full_name).where(User.id.in_(user_ids)))
        return {r.id: r.full_name for r in rows}

    @staticmethod
    def create(db: Session, *, email: str, password_hash: str, full_name: str, role: UserRole) -> User:
        user = User(email=email, password_hash=password_hash, full_name=full_name, role=role)
        db.add(user)
        db.flush()
        return user


class RoomRepository:
    @staticmethod
    def provision_for_teacher(db: Session, teacher_id: uuid.UUID, name: str) -> Room:
        """Idempotent: INSERT … ON CONFLICT (teacher_id) DO NOTHING, then select."""
        db.execute(
            insert(Room)
            .values(id=uuid.uuid4(), teacher_id=teacher_id, teacher_role=UserRole.TEACHER, name=name)
            .on_conflict_do_nothing(index_elements=[Room.teacher_id])
        )
        return db.scalars(select(Room).where(Room.teacher_id == teacher_id)).one()

    @staticmethod
    def get_by_id(db: Session, room_id: uuid.UUID) -> Room | None:
        return db.get(Room, room_id)

    @staticmethod
    def get_by_teacher(db: Session, teacher_id: uuid.UUID) -> Room | None:
        return db.scalar(select(Room).where(Room.teacher_id == teacher_id))

    @staticmethod
    def list_rooms(db: Session, *, search: str | None, offset: int, limit: int) -> tuple[list[tuple[Room, int]], int]:
        counts = (
            select(RoomParticipant.room_id, func.count().label("n"))
            .group_by(RoomParticipant.room_id)
            .subquery()
        )
        base = select(Room, func.coalesce(counts.c.n, 0)).join(User, User.id == Room.teacher_id).outerjoin(
            counts, counts.c.room_id == Room.id
        ).where(User.is_active.is_(True))
        if search:
            like = f"%{search}%"
            base = base.where(Room.name.ilike(like) | User.full_name.ilike(like))
        total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
        rows = db.execute(base.order_by(Room.name, Room.id).offset(offset).limit(limit)).all()
        return [(r[0], int(r[1])) for r in rows], int(total)

    @staticmethod
    def participant_count(db: Session, room_id: uuid.UUID) -> int:
        return db.scalar(select(func.count()).where(RoomParticipant.room_id == room_id)) or 0


class RoomParticipantRepository:
    @staticmethod
    def get(db: Session, room_id: uuid.UUID, student_id: uuid.UUID) -> RoomParticipant | None:
        return db.scalar(
            select(RoomParticipant).where(
                RoomParticipant.room_id == room_id, RoomParticipant.student_id == student_id
            )
        )

    @staticmethod
    def is_member(db: Session, room_id: uuid.UUID, student_id: uuid.UUID) -> bool:
        return (
            db.scalar(
                select(RoomParticipant.id).where(
                    RoomParticipant.room_id == room_id, RoomParticipant.student_id == student_id
                )
            )
            is not None
        )

    @staticmethod
    def add(db: Session, room_id: uuid.UUID, student_id: uuid.UUID) -> bool:
        """Returns True when a new membership row was created."""
        result = db.execute(
            insert(RoomParticipant)
            .values(id=uuid.uuid4(), room_id=room_id, student_id=student_id, student_role=UserRole.STUDENT)
            .on_conflict_do_nothing(index_elements=[RoomParticipant.room_id, RoomParticipant.student_id])
        )
        return bool(result.rowcount)

    @staticmethod
    def joined_room_ids(db: Session, student_id: uuid.UUID) -> set[uuid.UUID]:
        return set(db.scalars(select(RoomParticipant.room_id).where(RoomParticipant.student_id == student_id)))

    @staticmethod
    def list_for_room(db: Session, room_id: uuid.UUID) -> list[RoomParticipant]:
        return list(
            db.scalars(
                select(RoomParticipant)
                .where(RoomParticipant.room_id == room_id)
                .order_by(RoomParticipant.joined_at)
            )
        )


class RefreshTokenRepository:
    @staticmethod
    def create(db: Session, *, user_id: uuid.UUID, jti: uuid.UUID, expires_at: datetime) -> None:
        db.add(RefreshToken(user_id=user_id, jti=jti, expires_at=expires_at))
        db.flush()

    @staticmethod
    def revoke_if_active(db: Session, jti: uuid.UUID) -> bool:
        """Atomically revoke a live token. False if unknown, revoked, or expired."""
        now = datetime.now(UTC)
        result = db.execute(
            update(RefreshToken)
            .where(RefreshToken.jti == jti, RefreshToken.revoked_at.is_(None), RefreshToken.expires_at > now)
            .values(revoked_at=now)
        )
        return bool(result.rowcount)
