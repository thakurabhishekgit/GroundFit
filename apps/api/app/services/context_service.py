"""
Experience-context extraction and skill-graph persistence.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.context import ExperienceContext, Project, Role
from app.models.skill import Skill, SkillEvidence
from app.models.user import User
from app.schemas.context import (
    ConfirmGraphRequest,
    ContextBundleOut,
    ExperienceContextOut,
    ExperienceContextUpsert,
    ExtractPreviewOut,
    ProjectOut,
    RoleOut,
    SkillIn,
    SkillOut,
)
from app.services.latex_utils import normalize_skill_name
from app.services.openai_client import chat_json


EXTRACT_SYSTEM = """
You extract a structured career skill graph from a user's raw experience narrative.
Return JSON only with keys: skills, roles, projects, notes.

skills: array of {
  name (canonical lowercase slug),
  display_name,
  category (lang|framework|db|cloud|ai|tool|concept),
  proficiency (optional),
  evidence: [{ source_type: "role"|"project", summary, metrics_json? }]
}
roles: array of { title, org, ownership, description }
projects: array of { name, problem, architecture, description, tech[], metrics_json? }

Rules:
- Never invent employers, metrics, or tools not supported by the text.
- Evidence summaries must say WHERE and WHY the skill was used.
- Prefer fewer high-quality evidence items over spam.
- notes must be a single string (not an array).
""".strip()


async def upsert_raw_context(
    db: AsyncSession,
    user: User,
    payload: ExperienceContextUpsert,
) -> ExperienceContext:
    """Create or update the single ExperienceContext row for this user."""
    result = await db.execute(
        select(ExperienceContext).where(
            ExperienceContext.user_id == user.id,
            ExperienceContext.is_deleted.is_(False),
        )
    )
    ctx = result.scalar_one_or_none()
    if ctx is None:
        ctx = ExperienceContext(
            user_id=user.id,
            raw_text=payload.raw_text,
            created_by_id=user.id,
            updated_by_id=user.id,
        )
        db.add(ctx)
    else:
        ctx.raw_text = payload.raw_text
        ctx.updated_by_id = user.id

    await db.commit()
    await db.refresh(ctx)
    return ctx


async def extract_skill_graph_preview(raw_text: str) -> ExtractPreviewOut:
    """
    LLM pass: turn raw narrative into a draft skill graph (not yet saved).

    User must confirm via confirm_skill_graph before DB write of skills.
    """
    data = await chat_json(
        system=EXTRACT_SYSTEM,
        user=f"Experience narrative:\n\n{raw_text}",
        temperature=0.1,
    )
    skills_raw = data.get("skills") or []
    skills: list[SkillIn] = []
    for item in skills_raw:
        if not isinstance(item, dict) or not item.get("name"):
            continue
        name = normalize_skill_name(str(item["name"]))
        evidence = item.get("evidence") or []
        skills.append(
            SkillIn(
                name=name,
                display_name=item.get("display_name") or item.get("name"),
                category=item.get("category"),
                proficiency=item.get("proficiency"),
                evidence=evidence,
            )
        )
    return ExtractPreviewOut(
        skills=skills,
        roles=data.get("roles") or [],
        projects=data.get("projects") or [],
        notes=data.get("notes"),
    )


async def confirm_skill_graph(
    db: AsyncSession,
    user: User,
    payload: ConfirmGraphRequest,
) -> list[Skill]:
    """
    Persist user-reviewed skills + evidence.

    If replace_existing, soft-deletes prior skills for this user first.
    """
    if payload.replace_existing:
        existing = await db.execute(
            select(Skill).where(Skill.user_id == user.id, Skill.is_deleted.is_(False))
        )
        for skill in existing.scalars().all():
            skill.is_deleted = True
            skill.updated_by_id = user.id

    saved: list[Skill] = []
    for skill_in in payload.skills:
        skill = Skill(
            user_id=user.id,
            name=normalize_skill_name(skill_in.name),
            display_name=skill_in.display_name or skill_in.name,
            category=skill_in.category,
            proficiency=skill_in.proficiency,
            created_by_id=user.id,
            updated_by_id=user.id,
        )
        db.add(skill)
        await db.flush()
        for ev in skill_in.evidence:
            db.add(
                SkillEvidence(
                    skill_id=skill.id,
                    source_type=ev.source_type,
                    source_id=ev.source_id,
                    summary=ev.summary,
                    metrics_json=ev.metrics_json,
                    verified=ev.verified or True,
                    created_by_id=user.id,
                    updated_by_id=user.id,
                )
            )
        saved.append(skill)

    await db.commit()
    return saved


async def get_context_bundle(db: AsyncSession, user: User) -> ContextBundleOut:
    """Load context + skills (with evidence) + roles + projects for the UI."""
    ctx_result = await db.execute(
        select(ExperienceContext).where(
            ExperienceContext.user_id == user.id,
            ExperienceContext.is_deleted.is_(False),
        )
    )
    ctx = ctx_result.scalar_one_or_none()

    skills_result = await db.execute(
        select(Skill)
        .where(Skill.user_id == user.id, Skill.is_deleted.is_(False))
        .options(selectinload(Skill.evidence))
    )
    skills = list(skills_result.scalars().unique().all())
    # filter soft-deleted evidence in python
    for skill in skills:
        skill.evidence = [e for e in skill.evidence if not e.is_deleted]

    roles_result = await db.execute(
        select(Role).where(Role.user_id == user.id, Role.is_deleted.is_(False))
    )
    projects_result = await db.execute(
        select(Project).where(Project.user_id == user.id, Project.is_deleted.is_(False))
    )

    return ContextBundleOut(
        context=ExperienceContextOut.model_validate(ctx) if ctx else None,
        skills=[SkillOut.model_validate(s) for s in skills],
        roles=[RoleOut.model_validate(r) for r in roles_result.scalars().all()],
        projects=[ProjectOut.model_validate(p) for p in projects_result.scalars().all()],
    )
