"""
User model — mapped from Google OAuth identity.
"""

from typing import Optional

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class User(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """
    Application user, keyed by Google `sub` (stable subject id).

    Auth flow:
      Google ID token → verify → upsert by google_sub → issue GroundFit JWT.
    """

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    picture_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Google OpenID Connect subject — primary external identity
    google_sub: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships (lazy selectin for async friendliness where needed)
    experience_context = relationship(
        "ExperienceContext",
        back_populates="user",
        uselist=False,
        foreign_keys="ExperienceContext.user_id",
    )
    skills = relationship("Skill", back_populates="user", foreign_keys="Skill.user_id")
    roles = relationship("Role", back_populates="user", foreign_keys="Role.user_id")
    projects = relationship("Project", back_populates="user", foreign_keys="Project.user_id")
    resumes = relationship("Resume", back_populates="user", foreign_keys="Resume.user_id")
    alignment_runs = relationship(
        "AlignmentRun",
        back_populates="user",
        foreign_keys="AlignmentRun.user_id",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r}>"
