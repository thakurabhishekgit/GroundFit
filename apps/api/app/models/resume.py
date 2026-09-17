"""
Resume versions and alignment runs.
"""

from typing import Any, Optional
from uuid import UUID

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import AuditModel


class Resume(AuditModel, Base):
    """Stored LaTeX resume belonging to a user."""

    __tablename__ = "resumes"

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="Untitled resume")
    latex_source: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    user = relationship("User", back_populates="resumes", foreign_keys=[user_id])
    alignment_runs = relationship("AlignmentRun", back_populates="resume")


class AlignmentRun(AuditModel, Base):
    """
    One JD + resume alignment attempt.

    Stores result LaTeX, changelog, warnings, and pipeline status.
    """

    __tablename__ = "alignment_runs"

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    resume_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("resumes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    jd_text: Mapped[str] = mapped_column(Text, nullable=False)
    mode: Mapped[str] = mapped_column(String(32), nullable=False, default="strict")
    result_latex: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    changelog_json: Mapped[Optional[list[Any]]] = mapped_column(JSONB, nullable=True)
    warnings_json: Mapped[Optional[list[Any]]] = mapped_column(JSONB, nullable=True)
    coverage_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    user = relationship("User", back_populates="alignment_runs", foreign_keys=[user_id])
    resume = relationship("Resume", back_populates="alignment_runs")
