import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator

from api.config.settings import settings
from api.enums import AnalysisStatus, PollStatus, ResultsStatus
from api.schemas.common import ORMModel, normalize_text, strip_text


class OptionInput(BaseModel):
    label: str = Field(..., min_length=1, max_length=500)
    is_correct: bool = False

    @field_validator("label", mode="before")
    @classmethod
    def _normalize(cls, value):
        return normalize_text(value)


def _validate_option_list(options: list[OptionInput]) -> list[OptionInput]:
    if len(options) > settings.POLL_MAX_OPTIONS:
        raise ValueError(f"A question can have at most {settings.POLL_MAX_OPTIONS} options")
    if sum(o.is_correct for o in options) > 1:
        raise ValueError("Only one option can be marked correct")
    labels = [o.label.casefold() for o in options]
    if len(labels) != len(set(labels)):
        raise ValueError("Option labels must be unique within a question")
    return options


class QuestionInput(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=1000)
    options: list[OptionInput] = Field(default_factory=list)

    @field_validator("prompt", mode="before")
    @classmethod
    def _normalize(cls, value):
        return strip_text(value)

    @field_validator("options")
    @classmethod
    def _options(cls, value: list[OptionInput]) -> list[OptionInput]:
        return _validate_option_list(value)


class QuestionUpdateRequest(BaseModel):
    prompt: str | None = Field(None, min_length=1, max_length=1000)
    options: list[OptionInput] | None = Field(None, description="Replaces all options when provided")

    @field_validator("prompt", mode="before")
    @classmethod
    def _normalize(cls, value):
        return strip_text(value)

    @field_validator("options")
    @classmethod
    def _options(cls, value):
        return None if value is None else _validate_option_list(value)

    @model_validator(mode="after")
    def _not_empty(self):
        if self.prompt is None and self.options is None:
            raise ValueError("Provide prompt and/or options")
        return self


class PollCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    time_limit_seconds: int = Field(
        120, ge=settings.POLL_MIN_TIME_LIMIT_SECONDS, le=settings.POLL_MAX_TIME_LIMIT_SECONDS
    )
    questions: list[QuestionInput] = Field(default_factory=list, max_length=50)

    @field_validator("title", mode="before")
    @classmethod
    def _normalize(cls, value):
        return normalize_text(value)


class PollUpdateRequest(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    time_limit_seconds: int | None = Field(
        None, ge=settings.POLL_MIN_TIME_LIMIT_SECONDS, le=settings.POLL_MAX_TIME_LIMIT_SECONDS
    )

    @field_validator("title", mode="before")
    @classmethod
    def _normalize(cls, value):
        return normalize_text(value)


class QuestionOrderRequest(BaseModel):
    question_ids: list[uuid.UUID] = Field(..., min_length=1, max_length=50)


class OptionOut(ORMModel):
    id: uuid.UUID
    position: int
    label: str
    is_correct: bool


class QuestionOut(ORMModel):
    id: uuid.UUID
    position: int
    prompt: str
    options: list[OptionOut]


class PollSummary(ORMModel):
    id: uuid.UUID
    room_id: uuid.UUID
    title: str
    status: PollStatus
    time_limit_seconds: int
    started_at: datetime | None
    deadline_at: datetime | None
    ended_at: datetime | None
    cancelled_at: datetime | None
    results_status: ResultsStatus
    analysis_status: AnalysisStatus
    insights_version: int
    created_at: datetime
    updated_at: datetime
    question_count: int = 0


class PollDetail(PollSummary):
    questions: list[QuestionOut]


# ----- live (student-safe: never includes correctness) -----
class LiveOptionOut(BaseModel):
    id: uuid.UUID
    position: int
    label: str


class LiveQuestionOut(BaseModel):
    id: uuid.UUID
    position: int
    prompt: str
    options: list[LiveOptionOut]


class LivePollState(BaseModel):
    poll_id: uuid.UUID
    room_id: uuid.UUID
    title: str
    status: PollStatus
    started_at: datetime | None
    deadline_at: datetime | None
    server_time: datetime
    question_count: int
    current_index: int | None
    current_question: LiveQuestionOut | None
    my_answer_option_id: uuid.UUID | None = Field(None, description="Students: your accepted answer")
    answered_count: int | None = Field(None, description="Teachers only")
    participant_count: int | None = Field(None, description="Teachers only")
    option_counts: dict[str, int] | None = Field(None, description="Teachers only: option_id -> live count")
