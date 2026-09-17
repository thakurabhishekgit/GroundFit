"""
Google ID token verification and user upsert.
"""

from typing import Any

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import create_access_token
from app.models.user import User
from app.schemas.auth import TokenResponse, UserOut


class GoogleAuthError(Exception):
    """Raised when Google token verification fails."""


async def verify_google_id_token(token: str) -> dict[str, Any]:
    """
    Cryptographically verify a Google Sign-In ID token.

    Checks:
      - signature / certs from Google
      - audience == our GOOGLE_CLIENT_ID
      - email_verified is true

    Returns:
        Decoded claims dict (sub, email, name, picture, …).
    """
    settings = get_settings()
    if not settings.google_client_id:
        raise GoogleAuthError("GOOGLE_CLIENT_ID is not configured")

    try:
        # verify_oauth2_token is sync; fine for request path at friend scale
        claims = id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            settings.google_client_id,
        )
    except ValueError as exc:
        raise GoogleAuthError(f"Invalid Google ID token: {exc}") from exc

    if claims.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
        raise GoogleAuthError("Invalid token issuer")
    if not claims.get("email_verified", False):
        raise GoogleAuthError("Google email is not verified")
    if not claims.get("sub") or not claims.get("email"):
        raise GoogleAuthError("Token missing sub or email")
    return claims


async def upsert_user_from_google_claims(
    db: AsyncSession,
    claims: dict[str, Any],
) -> User:
    """
    Create or update a User row from verified Google claims.

    Match key: `google_sub`. Also refreshes name / picture / email.
    """
    google_sub = claims["sub"]
    email = claims["email"]
    name = claims.get("name")
    picture = claims.get("picture")

    result = await db.execute(
        select(User).where(User.google_sub == google_sub, User.is_deleted.is_(False))
    )
    user = result.scalar_one_or_none()

    if user is None:
        # Email collision with different google_sub → reject to avoid account takeover
        existing_email = await db.execute(
            select(User).where(User.email == email, User.is_deleted.is_(False))
        )
        if existing_email.scalar_one_or_none() is not None:
            raise GoogleAuthError("Email already registered with a different Google account")

        user = User(
            email=email,
            name=name,
            picture_url=picture,
            google_sub=google_sub,
            is_active=True,
        )
        db.add(user)
    else:
        user.email = email
        user.name = name
        user.picture_url = picture

    await db.commit()
    await db.refresh(user)
    return user


async def login_with_google_id_token(db: AsyncSession, raw_id_token: str) -> TokenResponse:
    """
    Full Google login pipeline: verify → upsert user → issue GroundFit JWT.
    """
    claims = await verify_google_id_token(raw_id_token)
    user = await upsert_user_from_google_claims(db, claims)
    access_token = create_access_token(
        subject=user.id,
        extra={"email": user.email, "name": user.name},
    )
    return TokenResponse(
        access_token=access_token,
        user=UserOut.model_validate(user),
    )
