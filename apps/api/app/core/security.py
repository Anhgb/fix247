"""
JWT authentication utilities.
FR-AUTH-02: JWT access (15 min) + refresh (30 days).
"""
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt

from app.core.config import get_settings

settings = get_settings()


def create_access_token(data: dict[str, Any]) -> str:
    """Create JWT access token (15 min expiry)."""
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(minutes=settings.jwt_access_expire_minutes)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(data: dict[str, Any]) -> str:
    """Create JWT refresh token (30 day expiry)."""
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(days=settings.jwt_refresh_expire_days)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    """Decode and verify JWT. Raises JWTError on failure."""
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def verify_token_type(payload: dict[str, Any], expected_type: str) -> bool:
    return payload.get("type") == expected_type
