import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.enums import UserRole
from api.models.base import Base, TimestampMixin, pg_enum, uuid_pk

user_role_enum = pg_enum(UserRole, "user_role")


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = uuid_pk()
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    role: Mapped[UserRole] = mapped_column(user_role_enum, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))

    __table_args__ = (
        UniqueConstraint("id", "role", name="uq_users_id_role"),
        Index("uq_users_email_lower", func.lower(email), unique=True),
    )


class Room(TimestampMixin, Base):
    __tablename__ = "rooms"

    id: Mapped[uuid.UUID] = uuid_pk()
    teacher_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True)
    teacher_role: Mapped[UserRole] = mapped_column(
        user_role_enum, nullable=False, server_default=UserRole.TEACHER.value
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)

    teacher: Mapped[User] = relationship(foreign_keys=[teacher_id], lazy="joined")

    __table_args__ = (
        CheckConstraint("teacher_role = 'TEACHER'", name="teacher_role_is_teacher"),
        ForeignKeyConstraint(
            ["teacher_id", "teacher_role"], ["users.id", "users.role"], name="fk_rooms_teacher_role"
        ),
    )


class RoomParticipant(Base):
    __tablename__ = "room_participants"

    id: Mapped[uuid.UUID] = uuid_pk()
    room_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rooms.id", ondelete="RESTRICT"), nullable=False
    )
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    student_role: Mapped[UserRole] = mapped_column(
        user_role_enum, nullable=False, server_default=UserRole.STUDENT.value
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    student: Mapped[User] = relationship(foreign_keys=[student_id], lazy="joined")

    __table_args__ = (
        CheckConstraint("student_role = 'STUDENT'", name="student_role_is_student"),
        ForeignKeyConstraint(
            ["student_id", "student_role"],
            ["users.id", "users.role"],
            name="fk_room_participants_student_role",
        ),
        UniqueConstraint("room_id", "student_id", name="uq_room_participants_room_student"),
        Index("ix_room_participants_student_id", "student_id"),
    )


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    jti: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
