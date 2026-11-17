import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt

from api.config.settings import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


@dataclass(frozen=True)
class TokenPayload:
    sub: str          # user id
    persona: str      # UserRole value
    token_type: str   # access | refresh
    jti: str
    exp: int
    claims: dict[str, Any]

    @staticmethod
    def from_dict(payload: dict[str, Any]) -> "TokenPayload":
        reserved = {"sub", "persona", "typ", "jti", "exp", "iat"}
        return TokenPayload(
            sub=payload["sub"],
            persona=payload["persona"],
            token_type=payload["typ"],
            jti=payload["jti"],
            exp=int(payload["exp"]),
            claims={k: v for k, v in payload.items() if k not in reserved},
        )


@dataclass(frozen=True)
class IssuedToken:
    token: str
    jti: uuid.UUID
    expires_at: datetime


class JwtService:
    def __init__(self, secret_key: str, algorithm: str):
        self.secret_key = secret_key
        self.algorithm = algorithm

    def _issue(self, *, user_id: str, persona: str, typ: str, ttl: timedelta, extra: dict | None) -> IssuedToken:
        now = datetime.now(UTC)
        jti = uuid.uuid4()
        expires_at = now + ttl
        payload = {
            "sub": user_id,
            "persona": persona,
            "typ": typ,
            "jti": str(jti),
            "iat": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
            **(extra or {}),
        }
        return IssuedToken(jwt.encode(payload, self.secret_key, algorithm=self.algorithm), jti, expires_at)

    def create_access_token(self, user_id: str, persona: str, extra: dict | None = None) -> IssuedToken:
        return self._issue(
            user_id=user_id, persona=persona, typ="access",
            ttl=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES), extra=extra,
        )

    def create_refresh_token(self, user_id: str, persona: str) -> IssuedToken:
        return self._issue(
            user_id=user_id, persona=persona, typ="refresh",
            ttl=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS), extra=None,
        )

    def decode(self, token: str, expected_type: str) -> TokenPayload | None:
        try:
            data = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            payload = TokenPayload.from_dict(data)
        except (jwt.InvalidTokenError, KeyError, ValueError):
            return None
        return payload if payload.token_type == expected_type else None
