"""
Experience context, roles, role work-items, and personal projects.
"""

from datetime import date
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import Date, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import AuditModel


class ExperienceContext(AuditModel, Base):
    """
    Optional notes / legacy narrative dump per user.

    Structured roles + projects are the primary source of truth going forward.
    """

    __tablename__ = "experience_contexts"
    __table_args__ = (UniqueConstraint("user_id", name="uq_experience_contexts_user"),)

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    raw_text: Mapped[str] = mapped_column(Text, nullable=False, default="")

    user = relationship("User", back_populates="experience_context", foreign_keys=[user_id])


class Role(AuditModel, Base):
    """Employment / internship entry."""

    __tablename__ = "roles"

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    org: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    ownership: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    user = relationship("User", back_populates="roles", foreign_keys=[user_id])
    work_items = relationship(
        "RoleWorkItem",
        back_populates="role",
        foreign_keys="RoleWorkItem.role_id",
        cascade="all, delete-orphan",
    )


class RoleWorkItem(AuditModel, Base):
    """
    Product / initiative under a company role (e.g. Ticket360 at Newmark).

    Distinct from personal Project entries on the resume Projects section.
    """

    __tablename__ = "role_work_items"

    role_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # what it does
    technical: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tech: Mapped[Optional[list[str]]] = mapped_column(ARRAY(String), nullable=True)

    role = relationship("Role", back_populates="work_items", foreign_keys=[role_id])


class Project(AuditModel, Base):
    """Personal / side project (resume Projects section)."""

    __tablename__ = "projects"

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    problem: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # what it does
    architecture: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # technical
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tech: Mapped[Optional[list[str]]] = mapped_column(ARRAY(String), nullable=True)
    metrics_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    user = relationship("User", back_populates="projects", foreign_keys=[user_id])
