"""
JWT helpers and password-less session tokens for Google-authenticated users.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

from jose import JWTError, jwt

from app.core.config import get_settings


def create_access_token(*, subject: UUID, extra: Optional[dict[str, Any]] = None) -> str:
    """
    Issue a signed JWT for an authenticated GroundFit user.

    Args:
        subject: User.id (UUID) stored in `sub` claim.
        extra: Optional additional claims (email, name).
    """
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT.

    Raises:
        JWTError: if signature invalid or token expired.
    """
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
