import re

from pydantic import BaseModel, ConfigDict

WHITESPACE_RUN = re.compile(r"\s+")


def normalize_text(value: str | None) -> str | None:
    """Trim and collapse internal whitespace runs; empty becomes None."""
    if value is None:
        return None
    collapsed = WHITESPACE_RUN.sub(" ", str(value)).strip()
    return collapsed or None


def strip_text(value: str | None) -> str | None:
    """Trim only (keeps line breaks for multi-line prompts); empty becomes None."""
    if value is None:
        return None
    stripped = str(value).strip()
    return stripped or None


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    message: str
