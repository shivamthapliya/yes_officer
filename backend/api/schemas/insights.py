import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from api.enums import AnalysisStatus, InsightCategory


class InsightOut(BaseModel):
    id: uuid.UUID
    question_id: uuid.UUID | None
    student_id: uuid.UUID | None
    student_name: str | None
    category: InsightCategory
    topic_label: str
    summary: str
    referenced_option_id: uuid.UUID | None
    confidence: float | None
    support_count: int
    first_observed_at: datetime
    last_observed_at: datetime
    updated_in_version: int
    kind: str = Field("ai_inference", description="AI output is always an inference, never a verified fact")


class InsightsResponse(BaseModel):
    poll_id: uuid.UUID
    question_id: uuid.UUID | None
    version: int
    analysis_status: AnalysisStatus
    insights: list[InsightOut]


class InsightsUpdatedEvent(BaseModel):
    poll_id: uuid.UUID
    question_id: uuid.UUID | None = None
    version: int
