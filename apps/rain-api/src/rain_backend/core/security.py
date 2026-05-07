"""Password hashing and JWT utilities."""

from datetime import datetime, timedelta, UTC
from typing import Any
import jwt
from passlib.context import CryptContext
from rain_backend.settings import settings

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days


def hash_password(plain: str) -> str:
    return _pwd_ctx.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


def create_access_token(subject: str, extra: dict[str, Any] | None = None) -> str:
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": datetime.now(UTC),
        "exp": datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.session_secret_key, algorithm="HS256")


def decode_access_token(token: str) -> dict[str, Any]:
    """Raises jwt.InvalidTokenError on failure."""
    return jwt.decode(token, settings.session_secret_key, algorithms=["HS256"])
