import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from api.enums import UserRole
from api.schemas.common import ORMModel, normalize_text


class RegisterRequest(BaseModel):
    email: EmailStr = Field(..., max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=1, max_length=120)
    role: UserRole
    room_name: str | None = Field(None, max_length=120, description="Teachers only; defaults from the name")

    @field_validator("full_name", "room_name", mode="before")
    @classmethod
    def _normalize(cls, value):
        return normalize_text(value)

    @field_validator("email")
    @classmethod
    def _lower_email(cls, value: str) -> str:
        return value.strip().lower()


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., max_length=255)
    password: str = Field(..., min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def _lower_email(cls, value: str) -> str:
        return value.strip().lower()


class UserOut(ORMModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: UserRole
    created_at: datetime


class RoomBrief(ORMModel):
    id: uuid.UUID
    name: str


class AuthResponse(BaseModel):
    user: UserOut
    room: RoomBrief | None = Field(None, description="The teacher's own room; null for students")
