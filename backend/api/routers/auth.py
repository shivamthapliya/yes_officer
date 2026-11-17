from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from api.common.security import JwtService
from api.config.settings import settings
from api.db.session import get_db
from api.dependencies import get_current_user, get_jwt_service, limiter
from api.models import User
from api.schemas.auth import AuthResponse, LoginRequest, RegisterRequest
from api.schemas.common import MessageResponse
from api.services import auth_service

router = APIRouter(prefix="/auth", tags=["Auth"])


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    common = {"httponly": True, "secure": settings.COOKIE_SECURE, "samesite": settings.COOKIE_SAMESITE}
    response.set_cookie(
        settings.ACCESS_COOKIE_NAME, access_token, max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60, path="/", **common
    )
    # The refresh cookie is only ever sent to the auth endpoints.
    response.set_cookie(
        settings.REFRESH_COOKIE_NAME, refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400, path=f"{settings.API_PREFIX}/auth", **common,
    )


def _clear_auth_cookies(response: Response) -> None:
    # Must carry the same attributes the cookies were set with, or a cross-site
    # browser (SameSite=None deployments) ignores the deletion and the session survives.
    common = {"httponly": True, "secure": settings.COOKIE_SECURE, "samesite": settings.COOKIE_SAMESITE}
    response.delete_cookie(settings.ACCESS_COOKIE_NAME, path="/", **common)
    response.delete_cookie(settings.REFRESH_COOKIE_NAME, path=f"{settings.API_PREFIX}/auth", **common)


@router.post("/register", response_model=AuthResponse, status_code=201, summary="Register a teacher or student")
@limiter.limit(settings.AUTH_RATE_LIMIT)
def register(
    request: Request,
    response: Response,
    body: RegisterRequest,
    db: Session = Depends(get_db),
    jwt_service: JwtService = Depends(get_jwt_service),
):
    result = auth_service.register(db, jwt_service, body)
    _set_auth_cookies(response, result.access_token, result.refresh_token)
    return result.response


@router.post("/login", response_model=AuthResponse, summary="Log in")
@limiter.limit(settings.AUTH_RATE_LIMIT)
def login(
    request: Request,
    response: Response,
    body: LoginRequest,
    db: Session = Depends(get_db),
    jwt_service: JwtService = Depends(get_jwt_service),
):
    result = auth_service.login(db, jwt_service, body)
    _set_auth_cookies(response, result.access_token, result.refresh_token)
    return result.response


@router.post("/refresh", response_model=AuthResponse, summary="Rotate the session tokens")
@limiter.limit("30/minute")
def refresh(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    jwt_service: JwtService = Depends(get_jwt_service),
):
    result = auth_service.refresh(db, jwt_service, request.cookies.get(settings.REFRESH_COOKIE_NAME))
    _set_auth_cookies(response, result.access_token, result.refresh_token)
    return result.response


@router.post("/logout", response_model=MessageResponse, summary="Log out")
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    jwt_service: JwtService = Depends(get_jwt_service),
):
    auth_service.logout(db, jwt_service, request.cookies.get(settings.REFRESH_COOKIE_NAME))
    _clear_auth_cookies(response)
    return MessageResponse(message="Logged out")


@router.get("/me", response_model=AuthResponse, summary="Current user")
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return auth_service.me(db, user)
