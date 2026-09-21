"""Schemas for Lists / job link CRUD."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _empty_to_none(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    return value


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
        host = v.split("://", 1)[-1].split("/")[0]
        if not host:
            raise ValueError("url looks invalid")
        return v

    @field_validator("subject")
    @classmethod
    def strip_subject(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("subject is required")
        return cleaned

    @field_validator("about", mode="before")
    @classmethod
    def empty_about(cls, value: Any) -> Any:
        return _empty_to_none(value)

    @field_validator("expires_at", mode="before")
    @classmethod
    def empty_expires(cls, value: Any) -> Any:
        return _empty_to_none(value)


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
        if not v:
            raise ValueError("url is required")
        if not v.startswith(("http://", "https://")):
            v = "https://" + v
        host = v.split("://", 1)[-1].split("/")[0]
        if not host:
            raise ValueError("url looks invalid")
        return v

    @field_validator("subject")
    @classmethod
    def strip_subject(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("subject is required")
        return cleaned

    @field_validator("about", mode="before")
    @classmethod
    def empty_about(cls, value: Any) -> Any:
        return _empty_to_none(value)

    @field_validator("expires_at", mode="before")
    @classmethod
    def empty_expires(cls, value: Any) -> Any:
        return _empty_to_none(value)


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
