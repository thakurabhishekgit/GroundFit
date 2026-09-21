"""Schemas for Lists / job link CRUD."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class JobLinkCreate(BaseModel):
    subject: str = Field(..., min_length=1, max_length=255)
    url: str = Field(..., min_length=1, max_length=2000)
    about: Optional[str] = Field(default=None, max_length=4000)
    expires_at: Optional[datetime] = None
    applied: bool = False

    @field_validator("url")
    @classmethod
    def normalize_url(cls, value: str) -> str:
        v = value.strip()
        if not v:
            raise ValueError("url is required")
        if not v.startswith(("http://", "https://")):
            v = "https://" + v
        # Validate shape via HttpUrl without changing type of field
        HttpUrl(v)
        return v

    @field_validator("subject")
    @classmethod
    def strip_subject(cls, value: str) -> str:
        return value.strip()


class JobLinkUpdate(BaseModel):
    subject: Optional[str] = Field(default=None, min_length=1, max_length=255)
    url: Optional[str] = Field(default=None, min_length=1, max_length=2000)
    about: Optional[str] = Field(default=None, max_length=4000)
    expires_at: Optional[datetime] = None
    applied: Optional[bool] = None
    clear_expires_at: bool = False

    @field_validator("url")
    @classmethod
    def normalize_url(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        v = value.strip()
        if not v.startswith(("http://", "https://")):
            v = "https://" + v
        HttpUrl(v)
        return v

    @field_validator("subject")
    @classmethod
    def strip_subject(cls, value: Optional[str]) -> Optional[str]:
        return value.strip() if value is not None else value


class JobLinkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    subject: str
    url: str
    about: Optional[str] = None
    expires_at: Optional[datetime] = None
    applied: bool
    reminder_sent_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
