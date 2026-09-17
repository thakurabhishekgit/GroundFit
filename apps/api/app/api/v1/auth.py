"""
Auth endpoints — Google Sign-In → GroundFit JWT.
"""

from fastapi import APIRouter, HTTPException, status

from app.core.deps import CurrentUser, DbSession
from app.schemas.auth import GoogleAuthRequest, TokenResponse, UserOut
from app.services.google_auth import GoogleAuthError, login_with_google_id_token


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/google",
    response_model=TokenResponse,
    summary="Exchange Google ID token for GroundFit JWT",
)
async def auth_google(payload: GoogleAuthRequest, db: DbSession) -> TokenResponse:
    """
    Frontend sends the GIS `credential` (ID token).

    Steps:
      1. Verify token with Google (aud = GOOGLE_CLIENT_ID)
      2. Upsert User by google_sub
      3. Return access_token + user profile
    """
    try:
        return await login_with_google_id_token(db, payload.id_token)
    except GoogleAuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


@router.get(
    "/me",
    response_model=UserOut,
    summary="Current authenticated user",
)
async def auth_me(user: CurrentUser) -> UserOut:
    """Return the User mapped from the Bearer JWT."""
    return UserOut.model_validate(user)
