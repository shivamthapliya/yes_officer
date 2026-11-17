import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    PrimaryKeyConstraint,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.enums import AnalysisStatus, PollStatus, ResultsStatus
from api.models.base import Base, TimestampMixin, pg_enum, uuid_pk


class Poll(TimestampMixin, Base):
    __tablename__ = "polls"

    id: Mapped[uuid.UUID] = uuid_pk()
    room_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rooms.id", ondelete="RESTRICT"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[PollStatus] = mapped_column(
        pg_enum(PollStatus, "poll_status"), nullable=False, server_default=PollStatus.DRAFT.value
    )
    time_limit_seconds: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="120")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    results_status: Mapped[ResultsStatus] = mapped_column(
        pg_enum(ResultsStatus, "results_status"),
        nullable=False,
        server_default=ResultsStatus.NOT_STARTED.value,
    )
    analysis_status: Mapped[AnalysisStatus] = mapped_column(
        pg_enum(AnalysisStatus, "analysis_status"),
        nullable=False,
        server_default=AnalysisStatus.IDLE.value,
    )
    insights_version: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0")

    questions: Mapped[list["PollQuestion"]] = relationship(
        back_populates="poll",
        order_by="PollQuestion.position",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        CheckConstraint("time_limit_seconds BETWEEN 10 AND 300", name="time_limit_range"),
        CheckConstraint("status <> 'DRAFT' OR started_at IS NULL", name="draft_not_started"),
        CheckConstraint(
            "status NOT IN ('ACTIVE','COMPLETED') OR (started_at IS NOT NULL AND deadline_at IS NOT NULL)",
            name="started_has_times",
        ),
        CheckConstraint("status <> 'COMPLETED' OR ended_at IS NOT NULL", name="completed_has_end"),
        CheckConstraint("status <> 'CANCELLED' OR cancelled_at IS NOT NULL", name="cancelled_has_time"),
        Index(
            "uq_polls_one_active_per_room",
            "room_id",
            unique=True,
            postgresql_where=text("status = 'ACTIVE'"),
        ),
        Index("ix_polls_room_status", "room_id", "status"),
        Index("ix_polls_room_created", "room_id", text("created_at DESC")),
    )


class PollQuestion(TimestampMixin, Base):
    __tablename__ = "poll_questions"

    id: Mapped[uuid.UUID] = uuid_pk()
    poll_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("polls.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)

    poll: Mapped[Poll] = relationship(back_populates="questions")
    options: Mapped[list["QuestionOption"]] = relationship(
        back_populates="question",
        order_by="QuestionOption.position",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        CheckConstraint("position >= 0", name="position_non_negative"),
        CheckConstraint("char_length(prompt) BETWEEN 1 AND 1000", name="prompt_length"),
        UniqueConstraint(
            "poll_id", "position", name="uq_poll_questions_poll_position",
            deferrable=True, initially="DEFERRED",
        ),
        UniqueConstraint("id", "poll_id", name="uq_poll_questions_id_poll"),
    )


class QuestionOption(Base):
    __tablename__ = "question_options"

    id: Mapped[uuid.UUID] = uuid_pk()
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("poll_questions.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    label: Mapped[str] = mapped_column(String(500), nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))

    question: Mapped[PollQuestion] = relationship(back_populates="options")

    __table_args__ = (
        CheckConstraint("position >= 0", name="position_non_negative"),
        UniqueConstraint(
            "question_id", "position", name="uq_question_options_question_position",
            deferrable=True, initially="DEFERRED",
        ),
        UniqueConstraint("id", "question_id", name="uq_question_options_id_question"),
        Index(
            "uq_question_options_one_correct",
            "question_id",
            unique=True,
            postgresql_where=text("is_correct"),
        ),
    )


class StudentAnswer(Base):
    __tablename__ = "student_answers"

    id: Mapped[uuid.UUID] = uuid_pk()
    poll_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    question_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    selected_option_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accept_seq: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["question_id", "poll_id"],
            ["poll_questions.id", "poll_questions.poll_id"],
            ondelete="CASCADE",
            name="fk_student_answers_question_poll",
        ),
        ForeignKeyConstraint(
            ["selected_option_id", "question_id"],
            ["question_options.id", "question_options.question_id"],
            ondelete="CASCADE",
            name="fk_student_answers_option_question",
        ),
        UniqueConstraint("poll_id", "question_id", "student_id", name="uq_student_answers_first_wins"),
        UniqueConstraint("poll_id", "accept_seq", name="uq_student_answers_poll_seq"),
        Index("ix_student_answers_poll_student", "poll_id", "student_id"),
        Index("ix_student_answers_distribution", "poll_id", "question_id", "selected_option_id"),
    )


class PollParticipant(Base):
    __tablename__ = "poll_participants"

    poll_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("polls.id", ondelete="CASCADE"), nullable=False
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )

    __table_args__ = (
        PrimaryKeyConstraint("poll_id", "student_id", name="pk_poll_participants"),
        Index("ix_poll_participants_student_id", "student_id"),
    )
