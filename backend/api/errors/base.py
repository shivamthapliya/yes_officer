from dataclasses import dataclass


@dataclass(frozen=True)
class ErrorDefinition:
    """Immutable error with status code, error code, and message."""

    status_code: int
    error_code: str
    message: str

    def __str__(self) -> str:
        return f"{self.error_code}: {self.message}"


class CommonErrors:
    VALIDATION_ERROR = ErrorDefinition(422, "VALIDATION_ERROR", "Request validation failed")
    INTERNAL_ERROR = ErrorDefinition(500, "INTERNAL_ERROR", "An unexpected error occurred")
    RATE_LIMITED = ErrorDefinition(429, "RATE_LIMITED", "Too many requests, slow down")
    FORBIDDEN_INTERNAL = ErrorDefinition(403, "FORBIDDEN_INTERNAL", "Invalid internal credentials")
    LIVE_STATE_UNAVAILABLE = ErrorDefinition(
        503, "LIVE_STATE_UNAVAILABLE", "Live poll state is temporarily unavailable"
    )
