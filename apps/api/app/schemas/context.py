"""Schemas for experience context, skills, roles, projects."""

from datetime import date, datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ExperienceContextUpsert(BaseModel):
    """Save / replace optional notes / legacy narrative."""

    raw_text: str = Field(default="", min_length=0)


class ExperienceContextOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    raw_text: str
    created_at: datetime
    updated_at: datetime


class SkillEvidenceIn(BaseModel):
    source_type: str = Field(default="project", pattern="^(role|project|work_item)$")
    source_id: Optional[UUID] = None
    summary: str = Field(default="")
    metrics_json: Optional[dict[str, Any]] = None
    verified: bool = False


class SkillEvidenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    skill_id: UUID
    source_type: str
    source_id: Optional[UUID] = None
    summary: str
    metrics_json: Optional[dict[str, Any]] = None
    verified: bool


class SkillIn(BaseModel):
    name: str
    display_name: Optional[str] = None
    category: Optional[str] = None
    proficiency: Optional[str] = None
    evidence: list[SkillEvidenceIn] = Field(default_factory=list)


class SkillOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    display_name: Optional[str] = None
    category: Optional[str] = None
    proficiency: Optional[str] = None
    evidence: list[SkillEvidenceOut] = Field(default_factory=list)


class RoleWorkItemIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    summary: Optional[str] = None
    technical: Optional[str] = None
    tech: list[str] = Field(default_factory=list)


class RoleWorkItemUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    summary: Optional[str] = None
    technical: Optional[str] = None
    tech: Optional[list[str]] = None


class RoleWorkItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role_id: UUID
    name: str
    summary: Optional[str] = None
    technical: Optional[str] = None
    tech: Optional[list[str]] = None
    created_at: datetime
    updated_at: datetime


class RoleCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    org: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    ownership: Optional[str] = None
    description: Optional[str] = None


class RoleUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    org: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    ownership: Optional[str] = None
    description: Optional[str] = None


class RoleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    org: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    ownership: Optional[str] = None
    description: Optional[str] = None
    work_items: list[RoleWorkItemOut] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    problem: Optional[str] = None
    architecture: Optional[str] = None
    description: Optional[str] = None
    tech: list[str] = Field(default_factory=list)
    metrics_json: Optional[dict[str, Any]] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    problem: Optional[str] = None
    architecture: Optional[str] = None
    description: Optional[str] = None
    tech: Optional[list[str]] = None
    metrics_json: Optional[dict[str, Any]] = None


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    problem: Optional[str] = None
    architecture: Optional[str] = None
    description: Optional[str] = None
    tech: Optional[list[str]] = None
    metrics_json: Optional[dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime


class ExtractPreviewOut(BaseModel):
    """LLM extraction draft before user confirms into DB."""

    skills: list[SkillIn]
    roles: list[dict[str, Any]] = Field(default_factory=list)
    projects: list[dict[str, Any]] = Field(default_factory=list)
    notes: Optional[str] = None

    @field_validator("notes", mode="before")
    @classmethod
    def coerce_notes_to_str(cls, value: Any) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, list):
            parts = [str(item).strip() for item in value if item is not None and str(item).strip()]
            return " ".join(parts) if parts else None
        return str(value)


class ConfirmGraphRequest(BaseModel):
    skills: list[SkillIn]
    replace_existing: bool = False


class ContextBundleOut(BaseModel):
    """Full context payload for the dashboard."""

    context: Optional[ExperienceContextOut] = None
    skills: list[SkillOut] = Field(default_factory=list)
    roles: list[RoleOut] = Field(default_factory=list)
    projects: list[ProjectOut] = Field(default_factory=list)
