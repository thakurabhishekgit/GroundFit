"""
Skill inventory + evidence linking skills to roles/projects.
"""

from typing import Any, Optional
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import AuditModel


class Skill(AuditModel, Base):
    """
    Canonical skill on the user's graph.

    `name` is lowercase slug (redis); `display_name` is UI label (Redis).
    """

    __tablename__ = "skills"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_skills_user_name"),)

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    proficiency: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    user = relationship("User", back_populates="skills", foreign_keys=[user_id])
    evidence = relationship("SkillEvidence", back_populates="skill", cascade="all, delete-orphan")


class SkillEvidence(AuditModel, Base):
    """
    Proof that a skill was used in a role or project.

    Alignment rewrite and verify steps cite these rows.
    """

    __tablename__ = "skill_evidence"

    skill_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("skills.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)  # role|project
    source_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    metrics_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    skill = relationship("Skill", back_populates="evidence")
