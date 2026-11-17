import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from api.schemas.common import normalize_text


class RoomListItem(BaseModel):
    id: uuid.UUID
    name: str
    teacher_name: str
    participant_count: int
    is_joined: bool
    has_active_poll: bool


class RoomDetail(RoomListItem):
    teacher_id: uuid.UUID
    created_at: datetime
    is_owner: bool


class RoomUpdateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)

    @field_validator("name", mode="before")
    @classmethod
    def _normalize(cls, value):
        return normalize_text(value)


class ParticipantOut(BaseModel):
    student_id: uuid.UUID
    full_name: str
    joined_at: datetime
    is_online: bool


class JoinResponse(BaseModel):
    room_id: uuid.UUID
    joined_at: datetime
    already_member: bool
