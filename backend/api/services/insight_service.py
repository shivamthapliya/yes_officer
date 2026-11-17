import uuid

from sqlalchemy.orm import Session

from api.models import AIInsight, User
from api.repositories.ai_repo import InsightRepository
from api.schemas.insights import InsightOut, InsightsResponse
from api.services.poll_service import get_owned_poll


def _out(insight: AIInsight, student_name: str | None) -> InsightOut:
    return InsightOut(
        id=insight.id,
        question_id=insight.question_id,
        student_id=insight.student_id,
        student_name=student_name,
        category=insight.category,
        topic_label=insight.topic_label,
        summary=insight.summary,
        referenced_option_id=insight.referenced_option_id,
        confidence=float(insight.confidence) if insight.confidence is not None else None,
        support_count=insight.support_count,
        first_observed_at=insight.first_observed_at,
        last_observed_at=insight.last_observed_at,
        updated_in_version=insight.updated_in_version,
    )


def get_insights(db: Session, poll_id: uuid.UUID, user: User, question_id: uuid.UUID | None) -> InsightsResponse:
    poll = get_owned_poll(db, poll_id, user)
    rows = InsightRepository.list_for_poll(db, poll.id, question_id=question_id)
    return InsightsResponse(
        poll_id=poll.id, question_id=question_id, version=poll.insights_version,
        analysis_status=poll.analysis_status, insights=[_out(i, n) for i, n in rows],
    )


def get_student_insights(db: Session, poll_id: uuid.UUID, student_id: uuid.UUID, user: User) -> InsightsResponse:
    poll = get_owned_poll(db, poll_id, user)
    rows = InsightRepository.list_for_poll(db, poll.id, student_id=student_id)
    return InsightsResponse(
        poll_id=poll.id, question_id=None, version=poll.insights_version,
        analysis_status=poll.analysis_status, insights=[_out(i, n) for i, n in rows],
    )
