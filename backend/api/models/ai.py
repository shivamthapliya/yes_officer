import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from api.enums import BatchStatus, BatchTrigger, InsightCategory
from api.models.base import NIL_UUID_SQL, Base, TimestampMixin, pg_enum


class AIAnalysisBatch(TimestampMixin, Base):
    __tablename__ = "ai_analysis_batches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    poll_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("polls.id", ondelete="CASCADE"), nullable=False
    )
    question_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("poll_questions.id", ondelete="SET NULL")
    )
    status: Mapped[BatchStatus] = mapped_column(
        pg_enum(BatchStatus, "batch_status"), nullable=False, server_default=BatchStatus.PENDING.value
    )
    trigger: Mapped[BatchTrigger] = mapped_column(pg_enum(BatchTrigger, "batch_trigger"), nullable=False)
    message_count: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    attempt_count: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")
    celery_task_id: Mapped[str | None] = mapped_column(String(155))
    last_error: Mapped[str | None] = mapped_column(String(1000))
    raw_output: Mapped[dict | None] = mapped_column(JSONB)
    claimed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint("message_count BETWEEN 1 AND 50", name="message_count_range"),
        Index("ix_ai_analysis_batches_poll_status", "poll_id", "status"),
        Index("ix_ai_analysis_batches_status_updated", "status", "updated_at"),
    )


class AIInsight(TimestampMixin, Base):
    __tablename__ = "ai_insights"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    poll_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("polls.id", ondelete="CASCADE"), nullable=False
    )
    question_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("poll_questions.id", ondelete="CASCADE")
    )
    student_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    category: Mapped[InsightCategory] = mapped_column(
        pg_enum(InsightCategory, "insight_category"), nullable=False
    )
    topic_label: Mapped[str] = mapped_column(String(200), nullable=False)
    normalized_topic_key: Mapped[str | None] = mapped_column(String(200))
    summary: Mapped[str] = mapped_column(String(2000), nullable=False)
    referenced_option_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("question_options.id", ondelete="SET NULL")
    )
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))
    support_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    first_observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_in_version: Mapped[int] = mapped_column(BigInteger, nullable=False)

    __table_args__ = (
        CheckConstraint("confidence IS NULL OR (confidence >= 0 AND confidence <= 1)", name="confidence_range"),
        Index(
            "uq_ai_insights_dedup",
            "poll_id",
            text(f"COALESCE(question_id, {NIL_UUID_SQL})"),
            text(f"COALESCE(student_id, {NIL_UUID_SQL})"),
            "category",
            "normalized_topic_key",
            unique=True,
            postgresql_where=text("normalized_topic_key IS NOT NULL"),
        ),
        Index("ix_ai_insights_poll_question_category", "poll_id", "question_id", "category"),
        Index("ix_ai_insights_poll_student", "poll_id", "student_id"),
    )
