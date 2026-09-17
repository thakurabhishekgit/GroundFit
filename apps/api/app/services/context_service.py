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

    Default (replace_existing=False): merge into the existing graph —
    keep prior skills, upsert overlaps, append non-duplicate evidence.
    replace_existing=True: soft-delete skills missing from the payload and
    refresh evidence on skills that remain.
    """
    # Merge duplicate names in the payload (e.g. React listed twice)
    merged: dict[str, SkillIn] = {}
    for skill_in in payload.skills:
        name = normalize_skill_name(skill_in.name)
        if not name:
            continue
        if name not in merged:
            merged[name] = SkillIn(
                name=name,
                display_name=skill_in.display_name or skill_in.name,
                category=skill_in.category,
                proficiency=skill_in.proficiency,
                evidence=list(skill_in.evidence or []),
            )
        else:
            existing_in = merged[name]
            if skill_in.display_name and not existing_in.display_name:
                existing_in.display_name = skill_in.display_name
            if skill_in.category and not existing_in.category:
                existing_in.category = skill_in.category
            existing_in.evidence = list(existing_in.evidence or []) + list(
                skill_in.evidence or []
            )

    result = await db.execute(
        select(Skill)
        .where(Skill.user_id == user.id)
        .options(selectinload(Skill.evidence))
    )
    by_name: dict[str, Skill] = {
        normalize_skill_name(s.name): s for s in result.scalars().unique().all()
    }

    incoming_names = set(merged.keys())

    if payload.replace_existing:
        for name, skill in by_name.items():
            if name not in incoming_names and not skill.is_deleted:
                skill.is_deleted = True
                skill.updated_by_id = user.id
                for ev in skill.evidence:
                    if not ev.is_deleted:
                        ev.is_deleted = True
                        ev.updated_by_id = user.id

    for name, skill_in in merged.items():
        skill = by_name.get(name)
        if skill is None:
            skill = Skill(
                user_id=user.id,
                name=name,
                display_name=skill_in.display_name or skill_in.name,
                category=skill_in.category,
                proficiency=skill_in.proficiency,
                created_by_id=user.id,
                updated_by_id=user.id,
            )
            db.add(skill)
            await db.flush()
            by_name[name] = skill
            existing_summaries: set[str] = set()
        else:
            skill.is_deleted = False
            skill.display_name = skill_in.display_name or skill.display_name or name
            skill.category = skill_in.category or skill.category
            skill.proficiency = skill_in.proficiency or skill.proficiency
            skill.updated_by_id = user.id
            if payload.replace_existing:
                for ev in skill.evidence:
                    if not ev.is_deleted:
                        ev.is_deleted = True
                        ev.updated_by_id = user.id
                existing_summaries = set()
            else:
                existing_summaries = {
                    (e.summary or "").strip().lower()
                    for e in skill.evidence
                    if not e.is_deleted
                }

        for ev in skill_in.evidence or []:
            summary = (ev.summary or "").strip()
            if not summary:
                continue
            # On merge, skip evidence we already stored for this skill
            if not payload.replace_existing and summary.lower() in existing_summaries:
                continue
            existing_summaries.add(summary.lower())
            db.add(
                SkillEvidence(
                    skill_id=skill.id,
                    source_type=ev.source_type,
                    source_id=ev.source_id,
                    summary=summary,
                    metrics_json=ev.metrics_json,
                    verified=True if ev.verified is None else ev.verified,
                    created_by_id=user.id,
                    updated_by_id=user.id,
                )
            )

    await db.commit()

    out_result = await db.execute(
        select(Skill)
        .where(Skill.user_id == user.id, Skill.is_deleted.is_(False))
        .options(selectinload(Skill.evidence))
    )
    skills = list(out_result.scalars().unique().all())
    for skill in skills:
        skill.evidence = [e for e in skill.evidence if not e.is_deleted]
    return skills


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
