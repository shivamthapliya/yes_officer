"""Domain enums. Mirrored 1:1 by native PostgreSQL enum types."""

from enum import StrEnum


class UserRole(StrEnum):
    TEACHER = "TEACHER"
    STUDENT = "STUDENT"


class PollStatus(StrEnum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class ResultsStatus(StrEnum):
    NOT_STARTED = "NOT_STARTED"
    PROCESSING = "PROCESSING"
    PERSISTED = "PERSISTED"
    FAILED = "FAILED"


class AnalysisStatus(StrEnum):
    IDLE = "IDLE"
    LIVE = "LIVE"
    FINALIZING = "FINALIZING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


class BatchStatus(StrEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class BatchTrigger(StrEnum):
    THRESHOLD = "THRESHOLD"
    INTERVAL = "INTERVAL"
    POLL_END = "POLL_END"


class InsightCategory(StrEnum):
    COMMON_DOUBT = "COMMON_DOUBT"
    CONFUSION = "CONFUSION"
    ENGAGEMENT = "ENGAGEMENT"
    MISCONCEPTION = "MISCONCEPTION"
    UNCOUNTED_RESPONSE = "UNCOUNTED_RESPONSE"
    STUDENT_QUESTION = "STUDENT_QUESTION"


TERMINAL_BATCH_STATUSES = (BatchStatus.SUCCEEDED, BatchStatus.FAILED, BatchStatus.CANCELLED)
NON_TERMINAL_BATCH_STATUSES = (BatchStatus.PENDING, BatchStatus.PROCESSING)
