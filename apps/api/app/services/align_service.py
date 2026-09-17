"""
Alignment pipeline: JD parse → skill match → section rewrite → verify.

MVP: dumps context evidence into the prompt (no pgvector yet).
Preserves LaTeX structure via section-only body replacement.
"""

from __future__ import annotations

import re
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.resume import AlignmentRun, Resume
from app.models.skill import Skill
from app.models.user import User
from app.schemas.resume import AlignRequest
from app.services.latex_utils import normalize_skill_name, replace_section_body, split_sections
from app.services.openai_client import chat_json, chat_text


JD_EXTRACT_SYSTEM = """
Extract required skills from a job description.
Return JSON: { "must_have": ["skill", ...], "nice_to_have": ["skill", ...] }
Use short canonical names (java, redis, kafka, spring-boot).
""".strip()


REWRITE_SYSTEM = """
You rewrite ONE LaTeX resume section to better match a job description
using ONLY the provided verified skills and evidence.

Hard rules:
- Return ONLY the section BODY as LaTeX (no \\documentclass, no \\section header).
- Preserve the user's formatting style (itemize, bold tech, spacing).
- Do NOT invent employers, metrics, tools, or ownership.
- Do NOT add skills missing from the verified list unless mode is suggest and they are listed under allowed_overrides.
- Prefer rephrasing existing bullets over fabricating new ones.
- No overlapping duplicated bullets.
""".strip()


VERIFY_SYSTEM = """
Given original+rewritten LaTeX and a verified skill list, list unsupported tech tokens
that appear in the rewritten text but not in verified skills.
Return JSON: { "unsupported": ["token", ...], "notes": "..." }
Ignore soft words (team, agile, scalable) — only tech/tools/frameworks.
""".strip()


async def run_alignment(
    db: AsyncSession,
    user: User,
    payload: AlignRequest,
) -> AlignmentRun:
    """
    Execute the full hybrid alignment pipeline and persist an AlignmentRun.
    """
    resume = await _get_user_resume(db, user.id, payload.resume_id)
    run = AlignmentRun(
        user_id=user.id,
        resume_id=resume.id,
        jd_text=payload.jd_text,
        mode=payload.mode,
        status="pending",
        created_by_id=user.id,
        updated_by_id=user.id,
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    try:
        skills = await _load_skills(db, user.id)
        skill_names = {s.name for s in skills}
        evidence_blob = _format_evidence(skills)

        jd_skills = await chat_json(
            system=JD_EXTRACT_SYSTEM,
            user=payload.jd_text,
            temperature=0.0,
        )
        must = [normalize_skill_name(s) for s in (jd_skills.get("must_have") or [])]
        nice = [normalize_skill_name(s) for s in (jd_skills.get("nice_to_have") or [])]

        matched = [s for s in must + nice if s in skill_names]
        missing = [s for s in must if s not in skill_names]

        latex = resume.latex_source
        changelog: list[dict[str, Any]] = []
        target_sections = ["summary", "experience", "projects", "skills"]

        present = {sec.name.lower() for sec in split_sections(latex)}
        for wanted in target_sections:
            if not any(wanted in name for name in present):
                continue
            before_sec = next(
                (s for s in split_sections(latex) if wanted in s.name.lower()),
                None,
            )
            if before_sec is None:
                continue

            rewritten_body = await chat_text(
                system=REWRITE_SYSTEM,
                user=_rewrite_user_prompt(
                    section_name=before_sec.name,
                    body=before_sec.body,
                    jd_text=payload.jd_text,
                    mode=payload.mode,
                    matched=matched,
                    missing=missing,
                    evidence_blob=evidence_blob,
                ),
                temperature=0.2,
            )
            rewritten_body = _strip_accidental_section_header(rewritten_body)
            latex = replace_section_body(latex, wanted, rewritten_body)
            changelog.append(
                {
                    "path": f"section.{wanted}",
                    "before": before_sec.body.strip()[:2000],
                    "after": rewritten_body.strip()[:2000],
                    "evidence_ids": [str(e.id) for s in skills for e in s.evidence if s.name in matched],
                    "status": "verified",
                }
            )

        verify = await chat_json(
            system=VERIFY_SYSTEM,
            user=(
                f"Verified skills: {sorted(skill_names)}\n\n"
                f"Rewritten LaTeX:\n{latex}\n"
            ),
            temperature=0.0,
        )
        unsupported = verify.get("unsupported") or []
        # Also force-flag JD must-haves missing from graph
        warnings = []
        for token in missing:
            warnings.append(
                {
                    "token": token,
                    "reason": "not_in_context",
                    "suggestions": [],
                    "user_action": None,
                }
            )
        for token in unsupported:
            norm = normalize_skill_name(str(token))
            if norm in skill_names:
                continue
            if any(w["token"] == norm or w["token"] == token for w in warnings):
                continue
            warnings.append(
                {
                    "token": token,
                    "reason": "unsupported_in_output",
                    "suggestions": [],
                    "user_action": None,
                }
            )

        coverage = (len([m for m in must if m in skill_names]) / len(must)) if must else 1.0

        # Strict mode: if warnings and mode strict, still return result but status needs_review
        run.result_latex = latex
        run.changelog_json = changelog
        run.warnings_json = warnings
        run.coverage_score = round(coverage, 3)
        run.status = "needs_review" if warnings else "done"
        run.updated_by_id = user.id
        await db.commit()
        await db.refresh(run)
        return run
    except Exception as exc:  # noqa: BLE001 — persist failure on the run row
        run.status = "failed"
        run.error_message = str(exc)
        run.updated_by_id = user.id
        await db.commit()
        await db.refresh(run)
        raise


async def _get_user_resume(db: AsyncSession, user_id: UUID, resume_id: UUID) -> Resume:
    """Fetch a resume owned by the current user or 404-equivalent ValueError."""
    result = await db.execute(
        select(Resume).where(
            Resume.id == resume_id,
            Resume.user_id == user_id,
            Resume.is_deleted.is_(False),
        )
    )
    resume = result.scalar_one_or_none()
    if resume is None:
        raise ValueError("Resume not found")
    return resume


async def _load_skills(db: AsyncSession, user_id: UUID) -> list[Skill]:
    """Load non-deleted skills with evidence for the user."""
    result = await db.execute(
        select(Skill)
        .where(Skill.user_id == user_id, Skill.is_deleted.is_(False))
        .options(selectinload(Skill.evidence))
    )
    skills = list(result.scalars().unique().all())
    for skill in skills:
        skill.evidence = [e for e in skill.evidence if not e.is_deleted]
    return skills


def _format_evidence(skills: list[Skill]) -> str:
    """Pack skill → evidence narratives for the rewrite prompt."""
    lines: list[str] = []
    for skill in skills:
        lines.append(f"- {skill.display_name or skill.name} ({skill.name})")
        for ev in skill.evidence:
            lines.append(f"    evidence: {ev.summary}")
    return "\n".join(lines) if lines else "(no verified skills yet)"


def _rewrite_user_prompt(
    *,
    section_name: str,
    body: str,
    jd_text: str,
    mode: str,
    matched: list[str],
    missing: list[str],
    evidence_blob: str,
) -> str:
    """Build the user message for a single-section rewrite."""
    return (
        f"Section name: {section_name}\n"
        f"Mode: {mode}\n"
        f"Matched skills: {matched}\n"
        f"Missing from context (do not invent in strict mode): {missing}\n\n"
        f"Verified evidence:\n{evidence_blob}\n\n"
        f"Job description:\n{jd_text}\n\n"
        f"Current section BODY LaTeX:\n{body}\n"
    )


def _strip_accidental_section_header(body: str) -> str:
    """Remove a leading \\section{...} if the model ignored instructions."""
    return re.sub(r"^\\section\*?\{[^}]+\}\s*", "", body.strip(), count=1, flags=re.IGNORECASE)
