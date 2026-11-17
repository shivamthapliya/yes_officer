"""FastAPI dependencies: app-scoped singletons from `app.state`, auth, roles."""

import hmac
import uuid

from fastapi import Depends, Header, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from api.common.security import JwtService, TokenPayload
from api.config.settings import settings
from api.db.session import get_db
from api.enums import UserRole
from api.errors.base import CommonErrors
from api.errors.domain_errors import AuthErrors
from api.exceptions import create_error
from api.models import User
from api.realtime.connection_manager import ConnectionManager
from api.realtime.live_state import LiveStateStore
from api.repositories.user_repo import UserRepository

limiter = Limiter(key_func=get_remote_address)


def _state(request: Request, name: str):
    value = getattr(request.app.state, name, None)
    if value is None:
        raise RuntimeError(f"{name} is not configured on app state")
    return value


def get_jwt_service(request: Request) -> JwtService:
    return _state(request, "jwt_service")


def get_live_state(request: Request) -> LiveStateStore:
    return _state(request, "live_state")


def get_connection_manager(request: Request) -> ConnectionManager:
    return _state(request, "connection_manager")


def get_token_payload(request: Request, jwt_service: JwtService = Depends(get_jwt_service)) -> TokenPayload:
    token = request.cookies.get(settings.ACCESS_COOKIE_NAME)
    if not token:
        raise create_error(AuthErrors.MISSING_TOKEN)
    payload = jwt_service.decode(token, "access")
    if payload is None:
        raise create_error(AuthErrors.INVALID_TOKEN)
    return payload


def get_current_user(payload: TokenPayload = Depends(get_token_payload), db: Session = Depends(get_db)) -> User:
    user = UserRepository.get_by_id(db, uuid.UUID(payload.sub))
    if user is None or not user.is_active or user.role.value != payload.persona:
        raise create_error(AuthErrors.INVALID_TOKEN)
    return user


def require_teacher(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.TEACHER:
        raise create_error(AuthErrors.INVALID_ROLE)
    return user


def require_student(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.STUDENT:
        raise create_error(AuthErrors.INVALID_ROLE)
    return user


def verify_internal_secret(x_internal_secret: str = Header(..., alias="X-Internal-Secret")) -> None:
    if not hmac.compare_digest(x_internal_secret, settings.INTERNAL_SHARED_SECRET):
        raise create_error(CommonErrors.FORBIDDEN_INTERNAL)
