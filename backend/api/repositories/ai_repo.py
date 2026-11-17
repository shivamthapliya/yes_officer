"""AI batch and insight data access."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from api.enums import NON_TERMINAL_BATCH_STATUSES, BatchStatus, BatchTrigger
from api.models import AIAnalysisBatch, AIInsight, User
from api.models.base import NIL_UUID_SQL


class BatchRepository:
    @staticmethod
    def create_if_missing(
        db: Session,
        *,
        batch_id: uuid.UUID,
        poll_id: uuid.UUID,
        question_id: uuid.UUID | None,
        trigger: BatchTrigger,
        message_count: int,
        claimed_at: datetime,
    ) -> None:
        db.execute(
            insert(AIAnalysisBatch)
            .values(
                id=batch_id, poll_id=poll_id, question_id=question_id, trigger=trigger,
                message_count=message_count, claimed_at=claimed_at, celery_task_id=str(batch_id),
            )
            .on_conflict_do_nothing(index_elements=[AIAnalysisBatch.id])
        )

    @staticmethod
    def get(db: Session, batch_id: uuid.UUID) -> AIAnalysisBatch | None:
        return db.get(AIAnalysisBatch, batch_id)

    @staticmethod
    def mark_processing(db: Session, batch_id: uuid.UUID, now: datetime) -> bool:
        result = db.execute(
            update(AIAnalysisBatch)
            .where(AIAnalysisBatch.id == batch_id, AIAnalysisBatch.status.in_(NON_TERMINAL_BATCH_STATUSES))
            .values(
                status=BatchStatus.PROCESSING,
                attempt_count=AIAnalysisBatch.attempt_count + 1,
                started_at=func.coalesce(AIAnalysisBatch.started_at, now),
            )
        )
        return bool(result.rowcount)

    @staticmethod
    def claim_success(db: Session, batch_id: uuid.UUID, raw_output: dict, now: datetime) -> bool:
        """Conditional SUCCEEDED transition — the exactly-once merge gate."""
        row = db.execute(
            update(AIAnalysisBatch)
            .where(AIAnalysisBatch.id == batch_id, AIAnalysisBatch.status.in_(NON_TERMINAL_BATCH_STATUSES))
            .values(status=BatchStatus.SUCCEEDED, raw_output=raw_output, completed_at=now, last_error=None)
            .returning(AIAnalysisBatch.id)
        ).first()
        return row is not None

    @staticmethod
    def mark_terminal(db: Session, batch_id: uuid.UUID, status: BatchStatus, error: str | None, now: datetime) -> None:
        db.execute(
            update(AIAnalysisBatch)
            .where(AIAnalysisBatch.id == batch_id, AIAnalysisBatch.status.in_(NON_TERMINAL_BATCH_STATUSES))
            .values(status=status, last_error=(error or None) and error[:1000], completed_at=now)
        )

    @staticmethod
    def record_error(db: Session, batch_id: uuid.UUID, error: str) -> None:
        db.execute(update(AIAnalysisBatch).where(AIAnalysisBatch.id == batch_id).values(last_error=error[:1000]))

    @staticmethod
    def cancel_open_for_poll(db: Session, poll_id: uuid.UUID, now: datetime) -> list[str]:
        rows = db.execute(
            update(AIAnalysisBatch)
            .where(AIAnalysisBatch.poll_id == poll_id, AIAnalysisBatch.status.in_(NON_TERMINAL_BATCH_STATUSES))
            .values(status=BatchStatus.CANCELLED, completed_at=now)
            .returning(AIAnalysisBatch.celery_task_id)
        ).all()
        return [r[0] for r in rows if r[0]]

    @staticmethod
    def open_count(db: Session, poll_id: uuid.UUID) -> int:
        return db.scalar(
            select(func.count()).where(
                AIAnalysisBatch.poll_id == poll_id, AIAnalysisBatch.status.in_(NON_TERMINAL_BATCH_STATUSES)
            )
        ) or 0

    @staticmethod
    def stale_processing(db: Session, updated_before: datetime) -> list[AIAnalysisBatch]:
        return list(
            db.scalars(
                select(AIAnalysisBatch).where(
                    AIAnalysisBatch.status == BatchStatus.PROCESSING, AIAnalysisBatch.updated_at < updated_before
                )
            )
        )


_UPSERT_INSIGHT = text(
    f"""
    INSERT INTO ai_insights (
        poll_id, question_id, student_id, category, topic_label, normalized_topic_key, summary,
        referenced_option_id, confidence, support_count, first_observed_at, last_observed_at,
        updated_in_version
    ) VALUES (
        :poll_id, :question_id, :student_id, CAST(:category AS insight_category), :topic_label,
        :normalized_topic_key, :summary, :referenced_option_id, :confidence, :support_count,
        :observed_at, :observed_at, :version
    )
    ON CONFLICT (
        poll_id, COALESCE(question_id, {NIL_UUID_SQL}), COALESCE(student_id, {NIL_UUID_SQL}),
        category, normalized_topic_key
    ) WHERE normalized_topic_key IS NOT NULL
    DO UPDATE SET
        topic_label = EXCLUDED.topic_label,
        summary = EXCLUDED.summary,
        referenced_option_id = COALESCE(EXCLUDED.referenced_option_id, ai_insights.referenced_option_id),
        confidence = GREATEST(COALESCE(ai_insights.confidence, 0), COALESCE(EXCLUDED.confidence, 0)),
        support_count = ai_insights.support_count + EXCLUDED.support_count,
        last_observed_at = EXCLUDED.last_observed_at,
        updated_in_version = EXCLUDED.updated_in_version,
        updated_at = now()
    """
)


class InsightRepository:
    @staticmethod
    def merge(
        db: Session,
        *,
        poll_id: uuid.UUID,
        question_id: uuid.UUID | None,
        student_id: uuid.UUID | None,
        category: str,
        topic_label: str,
        normalized_topic_key: str | None,
        summary: str,
        referenced_option_id: uuid.UUID | None,
        confidence: Decimal | None,
        support_count: int,
        observed_at: datetime,
        version: int,
    ) -> None:
        db.execute(
            _UPSERT_INSIGHT,
            {
                "poll_id": poll_id, "question_id": question_id, "student_id": student_id,
                "category": category, "topic_label": topic_label,
                "normalized_topic_key": normalized_topic_key, "summary": summary,
                "referenced_option_id": referenced_option_id, "confidence": confidence,
                "support_count": support_count, "observed_at": observed_at, "version": version,
            },
        )

    @staticmethod
    def list_for_poll(
        db: Session, poll_id: uuid.UUID, *, question_id: uuid.UUID | None = None, student_id: uuid.UUID | None = None
    ) -> list[tuple[AIInsight, str | None]]:
        stmt = (
            select(AIInsight, User.full_name)
            .outerjoin(User, User.id == AIInsight.student_id)
            .where(AIInsight.poll_id == poll_id)
        )
        if question_id is not None:
            stmt = stmt.where(AIInsight.question_id == question_id)
        if student_id is not None:
            stmt = stmt.where(AIInsight.student_id == student_id)
        stmt = stmt.order_by(AIInsight.support_count.desc(), AIInsight.last_observed_at.desc())
        return [(r[0], r[1]) for r in db.execute(stmt).all()]
