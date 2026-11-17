import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class AnswerSubmitRequest(BaseModel):
    question_id: uuid.UUID
    option_id: uuid.UUID


class AnswerReceipt(BaseModel):
    status: str = Field(..., description="accepted | duplicate")
    question_id: uuid.UUID
    option_id: uuid.UUID = Field(..., description="The answer on record (the original one on duplicates)")
    received_at: datetime


class OptionResult(BaseModel):
    option_id: uuid.UUID
    position: int
    label: str
    count: int
    percentage: float
    is_correct: bool


class FirstCorrectStudent(BaseModel):
    student_id: uuid.UUID
    full_name: str
    received_at: datetime


class QuestionResult(BaseModel):
    question_id: uuid.UUID
    position: int
    prompt: str
    correct_option_id: uuid.UUID | None
    answered_count: int
    correct_count: int
    participant_count: int
    options: list[OptionResult]
    first_correct_student: FirstCorrectStudent | None
    kind: str = "verified"


class PollResults(BaseModel):
    poll_id: uuid.UUID
    title: str
    ended_at: datetime | None
    participant_count: int
    questions: list[QuestionResult]


class ReviewOption(BaseModel):
    option_id: uuid.UUID
    position: int
    label: str
    is_correct: bool


class ReviewQuestion(BaseModel):
    question_id: uuid.UUID
    position: int
    prompt: str
    options: list[ReviewOption]
    selected_option_id: uuid.UUID | None
    correct_option_id: uuid.UUID | None
    is_correct: bool | None = Field(None, description="null when unanswered")
    answered_at: datetime | None


class PollReview(BaseModel):
    poll_id: uuid.UUID
    title: str
    room_name: str
    teacher_name: str
    ended_at: datetime | None
    answered_count: int
    correct_count: int
    question_count: int
    questions: list[ReviewQuestion]


class MyPollItem(BaseModel):
    poll_id: uuid.UUID
    title: str
    room_id: uuid.UUID
    room_name: str
    teacher_name: str
    ended_at: datetime | None
    question_count: int
