"""Pydantic schemas for auth and user profile."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class GoogleAuthRequest(BaseModel):
    """Body from frontend Google Identity Services callback."""

    id_token: str = Field(..., description="Google JWT credential from GIS")


class TokenResponse(BaseModel):
    """App session returned after Google login."""

    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


class UserOut(BaseModel):
    """Public user profile (never expose google_sub secrets beyond id)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    name: Optional[str] = None
    picture_url: Optional[str] = None
    google_sub: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


TokenResponse.model_rebuild()
