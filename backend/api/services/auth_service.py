import uuid
from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.common.security import JwtService, hash_password, verify_password
from api.enums import UserRole
from api.errors.domain_errors import AuthErrors
from api.exceptions import create_error
from api.models import Room, User
from api.repositories.user_repo import RefreshTokenRepository, RoomRepository, UserRepository
from api.schemas.auth import AuthResponse, LoginRequest, RegisterRequest, RoomBrief, UserOut


@dataclass(frozen=True)
class AuthResult:
    response: AuthResponse
    access_token: str
    refresh_token: str


def _default_room_name(full_name: str) -> str:
    return f"{full_name}'s Room"[:120]


def _issue_tokens(db: Session, jwt_service: JwtService, user: User) -> tuple[str, str]:
    access = jwt_service.create_access_token(str(user.id), user.role.value)
    refresh = jwt_service.create_refresh_token(str(user.id), user.role.value)
    RefreshTokenRepository.create(db, user_id=user.id, jti=refresh.jti, expires_at=refresh.expires_at)
    return access.token, refresh.token


def _build_response(user: User, room: Room | None) -> AuthResponse:
    return AuthResponse(
        user=UserOut.model_validate(user),
        room=RoomBrief.model_validate(room) if room else None,
    )


def register(db: Session, jwt_service: JwtService, request: RegisterRequest) -> AuthResult:
    """Create the user and, for a teacher, provision their room in the same transaction."""
    if UserRepository.get_by_email(db, request.email):
        raise create_error(AuthErrors.EMAIL_TAKEN)
    try:
        user = UserRepository.create(
            db,
            email=request.email,
            password_hash=hash_password(request.password),
            full_name=request.full_name,
            role=request.role,
        )
        room = None
        if user.role == UserRole.TEACHER:
            room = RoomRepository.provision_for_teacher(
                db, user.id, request.room_name or _default_room_name(user.full_name)
            )
        access, refresh = _issue_tokens(db, jwt_service, user)
        db.commit()
    except IntegrityError as exc:  # concurrent registration with the same email
        db.rollback()
        raise create_error(AuthErrors.EMAIL_TAKEN) from exc
    return AuthResult(_build_response(user, room), access, refresh)


def login(db: Session, jwt_service: JwtService, request: LoginRequest) -> AuthResult:
    """Validate credentials and return the existing room. Login never creates a room."""
    user = UserRepository.get_by_email(db, request.email)
    if user is None or not verify_password(request.password, user.password_hash):
        raise create_error(AuthErrors.INVALID_CREDENTIALS)
    if not user.is_active:
        raise create_error(AuthErrors.ACCOUNT_INACTIVE)
    room = RoomRepository.get_by_teacher(db, user.id) if user.role == UserRole.TEACHER else None
    access, refresh = _issue_tokens(db, jwt_service, user)
    db.commit()
    return AuthResult(_build_response(user, room), access, refresh)


def refresh(db: Session, jwt_service: JwtService, refresh_token: str | None) -> AuthResult:
    """Rotate the refresh token: the presented one is revoked atomically (single use)."""
    if not refresh_token:
        raise create_error(AuthErrors.MISSING_TOKEN)
    payload = jwt_service.decode(refresh_token, "refresh")
    if payload is None:
        raise create_error(AuthErrors.INVALID_TOKEN)
    if not RefreshTokenRepository.revoke_if_active(db, uuid.UUID(payload.jti)):
        db.rollback()
        raise create_error(AuthErrors.INVALID_TOKEN)
    user = UserRepository.get_by_id(db, uuid.UUID(payload.sub))
    if user is None or not user.is_active:
        db.rollback()
        raise create_error(AuthErrors.INVALID_TOKEN)
    room = RoomRepository.get_by_teacher(db, user.id) if user.role == UserRole.TEACHER else None
    access, new_refresh = _issue_tokens(db, jwt_service, user)
    db.commit()
    return AuthResult(_build_response(user, room), access, new_refresh)


def logout(db: Session, jwt_service: JwtService, refresh_token: str | None) -> None:
    if not refresh_token:
        return
    payload = jwt_service.decode(refresh_token, "refresh")
    if payload is not None:
        RefreshTokenRepository.revoke_if_active(db, uuid.UUID(payload.jti))
        db.commit()


def me(db: Session, user: User) -> AuthResponse:
    room = RoomRepository.get_by_teacher(db, user.id) if user.role == UserRole.TEACHER else None
    return _build_response(user, room)
