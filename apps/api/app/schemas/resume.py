"""Schemas for resumes and alignment runs."""

from datetime import datetime
from typing import Any, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ResumeCreate(BaseModel):
    title: str = Field(default="Untitled resume", max_length=255)
    latex_source: str = Field(..., min_length=1)


class ResumeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    latex_source: str
    version: int
    created_at: datetime
    updated_at: datetime


class AlignRequest(BaseModel):
    """Start an alignment run against a stored resume + JD text."""

    resume_id: UUID
    jd_text: str = Field(..., min_length=20)
    mode: Literal["strict", "deliberate", "suggest", "explore"] = "strict"


class AlignConfirmRequest(BaseModel):
    """Apply user decisions on warnings (override / skip) — no LaTeX regen."""

    actions: list[dict[str, Any]] = Field(
        default_factory=list,
        description="e.g. [{token, user_action: add_anyway|skip|use_suggestion}]",
    )


class AlignmentRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    resume_id: UUID
    jd_text: str
    mode: str
    result_latex: Optional[str] = None
    changelog_json: Optional[Any] = None
    match_report_json: Optional[dict[str, Any]] = None
    warnings_json: Optional[list[Any]] = None
    coverage_score: Optional[float] = None
    status: str
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
