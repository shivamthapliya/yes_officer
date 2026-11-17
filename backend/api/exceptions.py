"""Application exception type, `create_error` factory, and global handlers."""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from api.errors.base import CommonErrors, ErrorDefinition

logger = logging.getLogger(__name__)


class AppException(Exception):
    def __init__(self, definition: ErrorDefinition, details: dict[str, Any] | None = None):
        super().__init__(str(definition))
        self.definition = definition
        self.details = details or {}

    def to_payload(self) -> dict[str, Any]:
        return {
            "status_code": self.definition.status_code,
            "error_code": self.definition.error_code,
            "message": self.definition.message,
            "details": self.details,
        }


def create_error(definition: ErrorDefinition, details: dict[str, Any] | None = None) -> AppException:
    return AppException(definition, details)


def _payload(definition: ErrorDefinition, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return AppException(definition, details).to_payload()


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def _app_exception(_: Request, exc: AppException):
        return JSONResponse(status_code=exc.definition.status_code, content=exc.to_payload())

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        errors = [
            {"field": ".".join(str(p) for p in e["loc"] if p != "body"), "reason": e["msg"]}
            for e in exc.errors()
        ]
        return JSONResponse(
            status_code=422, content=_payload(CommonErrors.VALIDATION_ERROR, {"errors": errors})
        )

    @app.exception_handler(RateLimitExceeded)
    async def _rate_limited(_: Request, exc: RateLimitExceeded):
        return JSONResponse(
            status_code=429, content=_payload(CommonErrors.RATE_LIMITED, {"limit": str(exc.detail)})
        )

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception):
        logger.exception("Unhandled error", exc_info=exc)
        return JSONResponse(status_code=500, content=_payload(CommonErrors.INTERNAL_ERROR))
