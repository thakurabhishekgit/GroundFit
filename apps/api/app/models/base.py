"""
Base ORM mixins: UUID primary key + audit columns for production tables.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column


class UUIDPrimaryKeyMixin:
    """Surrogate UUID primary key (application-generated)."""

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )


class TimestampMixin:
    """Created / updated timestamps (timezone-aware)."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SoftDeleteMixin:
    """Soft-delete flag — rows stay for audit, queries filter is_deleted=False."""

    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class AuditActorMixin:
    """
    Who created / last updated the row.

    Nullable because system jobs and first-time user insert may have no actor yet.
    """

    created_by_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    updated_by_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )


class AuditModel(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, AuditActorMixin):
    """
    Full production audit base for domain tables.

    Compose: `class Skill(AuditModel, Base): ...`
    User table uses a lighter mix (no self-FK audit on create) to avoid cycles.
    """

    __abstract__ = True
