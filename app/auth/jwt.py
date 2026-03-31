"""JWT token creation and validation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from jose import JWTError, jwt

from app.config import settings

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7


def _get_secret() -> str:
    return settings.jwt_secret


def create_access_token(user_id: str) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": user_id, "exp": expire, "jti": uuid4().hex}, _get_secret(), algorithm=ALGORITHM)


def create_refresh_token(user_id: str) -> tuple[str, datetime]:
    """Return (token, expires_at) tuple."""
    expires_at = datetime.now(UTC) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    token = jwt.encode({"sub": user_id, "exp": expires_at, "type": "refresh", "jti": uuid4().hex}, _get_secret(), algorithm=ALGORITHM)
    return token, expires_at


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, _get_secret(), algorithms=[ALGORITHM])
    except JWTError:
        return None
