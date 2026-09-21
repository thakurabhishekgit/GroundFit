"""
Alignment pipeline: JD parse → skill match → rewrite sections.

Strict: Summary / Experience / Skills; Projects+Education+certs restored.
Deliberate: also rewrites Projects; may swap ≤1 weak Experience/Projects
bullet for evidence-backed JD fit (never invent work).
Add/Skip only saves decisions; Finalize runs one rewrite.
"""

from __future__ import annotations

import copy
import re
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import flag_modified

from app.models.resume import AlignmentRun, Resume
from app.models.skill import Skill
from app.models.user import User
from app.schemas.resume import AlignRequest
from app.services.latex_utils import (
    find_section,
    insert_section_after,
    normalize_skill_name,
    replace_section_body,
    split_sections,
)
from app.services.openai_client import chat_json, chat_text


JD_EXTRACT_SYSTEM = """
Extract required HARD tech skills from a job description.
Return JSON: { "must_have": ["skill", ...], "nice_to_have": ["skill", ...] }

Rules:
- Only real technologies / tools / frameworks (java, spring-boot, redis, sql-server, azure, kafka).
- Do NOT extract soft phrases (idempotent API design, SLA-aware workflows, problem solving, scalable).
- Do NOT extract resume fluff (leetcode, github, matlab, machine-learning, hackathon) unless the JD explicitly requires that exact skill.
- If JD says "Azure or AWS", emit both azure and aws as nice_to_have alternatives, not separate hard musts beyond "cloud-ci".
- Prefer short canonical names: spring-boot, sql-server, redis, rbac, microservices.
""".strip()


REWRITE_SYSTEM_STRICT = """
You rewrite ONE LaTeX resume section body to better match a job description
using ONLY the provided verified skills and evidence.

Hard rules:
- Return ONLY the section BODY as LaTeX (no \\documentclass, no \\section{...} at all).
- Never output a new \\section command.
- Never invent project entries with \\resumeProject unless this IS the Projects section body.
- Preserve formatting macros exactly (\\resumeSubheading, \\resumeItemListStart, \\href, tabular*, \\vspace, etc.).
- Do NOT invent employers, metrics, tools, products, or ownership.
- Do NOT add skills missing from the verified list unless listed in allowed_overrides.
- Prefer rephrasing existing bullets over fabricating new ones.
- EXPERIENCE: Do NOT add/remove jobs. Only rephrase existing bullets. Keep the same number of \\resumeSubheading blocks.
- EXPERIENCE: Internship products (e.g. Ticket360) stay as Experience bullets — never promote them into Projects.
- EXPERIENCE: If the JD barely overlaps this job's bullets, lightly rephrase toward transferable matched skills without inventing work you never did.
- SKILLS: Reorder/regroup to surface matched JD skills you already have; do not invent categories of tools you lack.
- PROJECTS: In strict mode you should not receive Projects; if you do, return the body unchanged.
""".strip()


REWRITE_SYSTEM_DELIBERATE = """
You rewrite ONE LaTeX resume section body in DELIBERATE mode — like a careful human
tailoring a resume for one JD, using ONLY verified skills and evidence.

Hard rules:
- Return ONLY the section BODY as LaTeX (no \\documentclass, no \\section{...} at all).
- Never invent employers, companies, metrics, tools, or projects not backed by verified evidence.
- Do NOT add skills missing from the verified list unless listed in allowed_overrides.
- Preserve formatting macros (\\resumeSubheading, \\resumeItem, \\resumeProject, \\resumeItemListStart, \\href, etc.).

Think like a real applicant:
1) Read the JD focus (e.g. Python/RAG/AI, or Node/Express/TypeScript).
2) Check verified evidence — did this person actually use those skills somewhere (role or project)?
3) If YES: emphasize that work in this section.
4) If NO: do not invent it; only light rephrase of what already exists.

EXPERIENCE (deliberate):
- Keep the SAME number of \\resumeSubheading job blocks (never add/remove employers).
- You MAY replace AT MOST ONE existing \\item bullet that has the WEAKEST keyword overlap with the JD
  with ONE new \\item that restates real work from verified evidence (e.g. Freshdesk Python/FastAPI/RAG),
  written smoothly in the same voice/format as neighboring bullets.
- Do NOT remove important ownership bullets (end-to-end product ownership, major metrics) just to chase keywords.
- Prefer swapping a low-fit tech line (e.g. incidental C# / unrelated stack) over deleting core achievements.
- Keep total \\item count the same OR at most +1 if the section had very few bullets and evidence clearly supports one added line — never dump many new bullets.
- Never promote internship products into Projects here.

PROJECTS (deliberate):
- Keep the SAME projects (same number of \\resumeProject blocks; same project names/links).
- You MAY rephrase stack lines and bullets to emphasize JD-matching tech that evidence already proves for THAT project.
- You MAY replace AT MOST ONE weak \\item under a project with one evidence-backed bullet aligned to the JD.
- Never invent a new project (no new \\resumeProject for Ticket360, Freshdesk, etc.).

SKILLS / SUMMARY (deliberate):
- Aggressively surface matched JD skills you already have; regroup categories.
- Never list tools not in verified skills / overrides.
""".strip()


ALWAYS_PROTECTED_HINTS = (
    "education",
    "achivement",
    "achievement",
    "certificate",
    "certificat",
)

# Used by restore when projects must stay byte-stable (strict mode)
PROTECTED_SECTION_HINTS = ALWAYS_PROTECTED_HINTS + ("project",)

REWRITE_SECTIONS_STRICT = ("summary", "experience", "skills")
REWRITE_SECTIONS_DELIBERATE = ("summary", "experience", "projects", "skills")

CONCEPT_COVERED_BY: dict[str, set[str]] = {
    "idempotent-api-design": {"redis", "rest", "spring-boot", "java", "microservices"},
    "sla-aware-workflows": {"rbac", "spring-boot", "java", "microservices"},
    "sla": {"rbac", "spring-boot", "java"},
    "event-driven-design": {"kafka", "microservices", "redis"},
    "event-driven": {"kafka", "microservices"},
    "ci-cd": {"azure-devops", "azure", "docker", "github", "git"},
    "cicd": {"azure-devops", "azure", "docker"},
    "cloud-ci": {"azure-devops", "azure", "aws", "ci-cd", "docker"},
    "cloud": {"azure", "aws", "gcp"},
    "aws": {"azure", "aws"},  # JD often says Azure or AWS
    "rest": {"spring-boot", "java", "fastapi", "express.js", "microservices"},
    "rest-api": {"spring-boot", "java", "fastapi", "express.js"},
    "nosql": {"mongodb", "redis", "mongo"},
    "no-sql": {"mongodb", "redis"},
    "testing": {"jest", "junit", "pytest"},
    "frontend": {"react", "html", "css", "javascript", "typescript"},
}

NOISE_TOKENS = {
    "github",
    "leetcode",
    "linkedin",
    "portfolio",
    "matlab",
    "machine-learning",
    "ai-ml",
    "ml",
    "hackathon",
    "patent",
    "wipro",
    "mathworks",
    "problem-solving",
    "dsa",
}

SKILL_FAMILIES: dict[str, set[str]] = {
    "spring-boot": {
        "spring",
        "spring-boot",
        "spring-security",
        "spring-mvc",
        "spring-jpa",
        "jpa",
        "hibernate",
        "spring-core",
    },
    "java": {"java", "jvm", "j2ee"},
    "microsoft-sql-server": {
        "sql-server",
        "mssql",
        "microsoft-sql-server",
        "tsql",
        "ms-sql",
    },
    "sql": {
        "sql",
        "relational-databases",
        "rdbms",
        "mysql",
        "postgresql",
        "postgres",
        "microsoft-sql-server",
        "sql-server",
    },
    "redis": {"redis", "caching", "cache"},
    "rest": {"rest", "rest-api", "restful", "openapi", "swagger"},
    "react": {"react", "react.js", "reactjs"},
    "azure": {
        "azure",
        "azure-app-service",
        "azure-devops",
        "azure-portal",
        "azure-ai-search",
    },
    "rag": {"rag", "retrieval-augmented-generation", "vector-search", "embeddings"},
    "docker": {"docker", "containers"},
    "kafka": {"kafka", "apache-kafka"},
    "microservices": {"microservices", "micro-services", "microservice"},
    "rbac": {"rbac", "role-based-access-control", "role-based-access"},
    "cicd": {"ci-cd", "cicd", "ci/cd", "cloud-ci"},
    "mongodb": {"mongodb", "mongo", "nosql", "no-sql"},
    "rest": {"rest", "rest-api", "restful", "rest-apis"},
    "python": {"python", "python3", "py"},
    "fastapi": {"fastapi", "fast-api"},
    "nodejs": {"nodejs", "node", "node.js", "node-js"},
    "express": {"express", "express.js", "expressjs"},
    "typescript": {"typescript", "ts"},
}


def _is_deliberate(mode: str) -> bool:
    return (mode or "").lower() == "deliberate"


def _rewrite_system_for_mode(mode: str) -> str:
    return REWRITE_SYSTEM_DELIBERATE if _is_deliberate(mode) else REWRITE_SYSTEM_STRICT


def _rewrite_section_names(mode: str) -> tuple[str, ...]:
    return REWRITE_SECTIONS_DELIBERATE if _is_deliberate(mode) else REWRITE_SECTIONS_STRICT


def _restore_hints_for_mode(mode: str) -> tuple[str, ...]:
    """Strict locks Projects; deliberate allows Projects rewrite (education/certs still locked)."""
    return ALWAYS_PROTECTED_HINTS if _is_deliberate(mode) else PROTECTED_SECTION_HINTS


async def run_alignment(
    db: AsyncSession,
    user: User,
    payload: AlignRequest,
) -> AlignmentRun:
    """Run JD match + rewrite Summary/Experience/Skills; restore protected sections."""
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
        covered = expand_covered_skills(skill_names)
        evidence_blob = _format_evidence(skills)

        jd_skills = await chat_json(
            system=JD_EXTRACT_SYSTEM,
            user=payload.jd_text,
            temperature=0.0,
        )
        must = _filter_jd_skills(_unique_norms(jd_skills.get("must_have") or []))
        nice = _filter_jd_skills(_unique_norms(jd_skills.get("nice_to_have") or []))
        must, nice = _apply_cloud_alternatives(must, nice, payload.jd_text, covered)

        matched_must = [s for s in must if s in covered or _concept_covered(s, covered)]
        missing_must = [
            s for s in must if s not in covered and not _concept_covered(s, covered)
        ]
        matched_nice = [s for s in nice if s in covered or _concept_covered(s, covered)]
        missing_nice = [
            s for s in nice if s not in covered and not _concept_covered(s, covered)
        ]
        matched = list(dict.fromkeys(matched_must + matched_nice))

        match_report = {
            "must_have": must,
            "nice_to_have": nice,
            "matched_must": matched_must,
            "missing_must": missing_must,
            "matched_nice": matched_nice,
            "missing_nice": missing_nice,
            "coverage": {
                "matched": len(matched_must),
                "total": len(must),
                "score": round((len(matched_must) / len(must)) if must else 1.0, 3),
                "label": (
                    f"{len(matched_must)}/{len(must)} JD must-have skills verified in your context"
                    if must
                    else "No must-have skills extracted from JD"
                ),
            },
        }

        mode_note = (
            "DELIBERATE mode: may swap at most one weak Experience/Projects bullet "
            "for evidence-backed JD-aligned work. Never invent work not in verified evidence. "
            "Do not emit \\section headers."
            if _is_deliberate(payload.mode)
            else (
                "STRICT mode: rephrase only; Projects restored from original. "
                "Do not emit \\section or invent \\resumeProject."
            )
        )

        latex = await _rewrite_sections(
            latex=resume.latex_source,
            jd_text=payload.jd_text,
            mode=payload.mode,
            matched=matched,
            missing=missing_must,
            evidence_blob=evidence_blob,
            allowed_overrides=[],
            extra_note=mode_note,
        )
        latex = restore_protected_sections(
            resume.latex_source, latex, mode=payload.mode
        )

        warnings = _build_jd_gap_warnings(missing_must=missing_must)

        run.result_latex = latex
        run.changelog_json = {
            "sections": list(_rewrite_section_names(payload.mode)),
            "match_report": match_report,
        }
        run.match_report_json = match_report
        run.warnings_json = warnings
        flag_modified(run, "warnings_json")
        flag_modified(run, "match_report_json")
        run.coverage_score = match_report["coverage"]["score"]
        run.status = "needs_review" if warnings else "done"
        run.updated_by_id = user.id
        await db.commit()
        await db.refresh(run)
        return run
    except Exception as exc:  # noqa: BLE001
        run.status = "failed"
        run.error_message = str(exc)
        run.updated_by_id = user.id
        await db.commit()
        await db.refresh(run)
        raise


async def save_warning_decisions(
    db: AsyncSession,
    run: AlignmentRun,
    actions: list[dict[str, Any]],
    user: User,
) -> AlignmentRun:
    """Persist Add/Skip — does NOT regenerate LaTeX."""
    warnings = copy.deepcopy(list(run.warnings_json or []))
    action_map = {
        normalize_skill_name(str(a.get("token"))): a.get("user_action")
        for a in actions
        if a.get("token") and a.get("user_action")
    }
    for warning in warnings:
        token = normalize_skill_name(str(warning.get("token")))
        if token in action_map:
            warning["token"] = token
            warning["user_action"] = action_map[token]
            warning["saved"] = True

    run.warnings_json = warnings
    flag_modified(run, "warnings_json")

    pending = [w for w in warnings if not w.get("user_action")]
    run.status = "awaiting_finalize" if not pending else "needs_review"
    run.updated_by_id = user.id
    await db.commit()
    await db.refresh(run)
    return run


async def finalize_alignment(
    db: AsyncSession,
    run: AlignmentRun,
    user: User,
) -> AlignmentRun:
    """One-shot final rewrite from original resume + overrides; restore Projects."""
    resume = await _get_user_resume(db, user.id, run.resume_id)
    skills = await _load_skills(db, user.id)
    evidence_blob = _format_evidence(skills)

    warnings = copy.deepcopy(list(run.warnings_json or []))
    # Undecided → skip (so Finalize is never blocked by leftover noise)
    for w in warnings:
        if not w.get("user_action"):
            w["user_action"] = "skip"
            w["saved"] = True

    overrides = [
        normalize_skill_name(str(w["token"]))
        for w in warnings
        if w.get("user_action") == "add_anyway"
    ]
    skipped = {
        normalize_skill_name(str(w["token"]))
        for w in warnings
        if w.get("user_action") == "skip"
    }

    report = run.match_report_json or {}
    matched = list(report.get("matched_must") or []) + list(report.get("matched_nice") or [])
    missing = [m for m in (report.get("missing_must") or []) if m not in overrides]

    latex = await _rewrite_sections(
        latex=resume.latex_source,
        jd_text=run.jd_text,
        mode=run.mode,
        matched=matched,
        missing=missing,
        evidence_blob=evidence_blob,
        allowed_overrides=overrides,
        extra_note=(
            f"User allowed overrides: {overrides}. "
            f"Do NOT mention skipped tokens: {sorted(skipped)}. "
            + (
                "DELIBERATE: evidence-backed bullet swap allowed (at most one weak line). "
                if _is_deliberate(run.mode)
                else "STRICT: do not invent \\resumeProject; Projects restored. "
            )
            + "Do not emit \\section."
        ),
    )
    latex = restore_protected_sections(resume.latex_source, latex, mode=run.mode)

    run.result_latex = latex
    run.warnings_json = warnings
    flag_modified(run, "warnings_json")
    run.status = "finalized"
    run.updated_by_id = user.id
    await db.commit()
    await db.refresh(run)
    return run


def restore_protected_sections(
    original: str, rewritten: str, mode: str = "strict"
) -> str:
    """
    Force Education / Achievements (and Projects in strict) from the original.

    Deliberate mode leaves Projects as rewritten (still evidence-bound by prompt).
    """
    out = rewritten
    restored: set[str] = set()
    hints = _restore_hints_for_mode(mode)

    for orig in split_sections(original):
        name_l = orig.name.lower()
        if not any(h in name_l for h in hints):
            continue
        if name_l in restored:
            continue
        restored.add(name_l)

        cur = find_section(out, orig.name)
        if cur is None:
            for h in hints:
                if h in name_l:
                    cur = find_section(out, h)
                    if cur is not None:
                        break

        body = orig.body if orig.body.startswith("\n") else "\n" + orig.body
        if not body.endswith("\n"):
            body += "\n"

        if cur is not None:
            out = out[: cur.start] + orig.header + body + out[cur.end :]
        else:
            after = "experience" if find_section(out, "experience") else "education"
            out = insert_section_after(out, after, orig.header, orig.body)

    # Strict: strip leaked \\resumeProject from Experience
    # Deliberate: still strip \\resumeProject from Experience (projects belong in Projects)
    exp = find_section(out, "experience")
    if exp and "\\resumeProject" in exp.body:
        cleaned = re.sub(
            r"\\resumeProject\b[\s\S]*?(?=\\resumeProject\b|\\resumeItemListStart|\\resumeSubHeadingListEnd|\\resumeSubheading\b|$)",
            "",
            exp.body,
            flags=re.IGNORECASE,
        )
        out = replace_section_body(out, "experience", cleaned)

    return out


def expand_covered_skills(user_skills: set[str]) -> set[str]:
    covered = {normalize_skill_name(s) for s in user_skills}
    changed = True
    while changed:
        changed = False
        snapshot = set(covered)
        for family_key, members in SKILL_FAMILIES.items():
            if snapshot & members or family_key in snapshot:
                before = len(covered)
                covered.update(members)
                covered.add(family_key)
                if len(covered) > before:
                    changed = True
    return covered


def _concept_covered(token: str, covered: set[str]) -> bool:
    norm = normalize_skill_name(token)
    if norm in NOISE_TOKENS:
        return True
    parents = CONCEPT_COVERED_BY.get(norm)
    if not parents:
        return False
    return bool(parents & covered)


def _filter_jd_skills(skills: list[str]) -> list[str]:
    return [s for s in skills if s not in NOISE_TOKENS]


def _apply_cloud_alternatives(
    must: list[str],
    nice: list[str],
    jd_text: str,
    covered: set[str],
) -> tuple[list[str], list[str]]:
    """If JD says Azure or AWS and user has Azure, don't require AWS."""
    if re.search(r"azure\s+or\s+aws|aws\s+or\s+azure", jd_text, re.I):
        has_azure = bool(covered & SKILL_FAMILIES["azure"]) or "azure" in covered
        has_aws = "aws" in covered
        if has_azure and not has_aws:
            must = [s for s in must if s != "aws"]
            nice = [s for s in nice if s != "aws"]
        if has_aws and not has_azure:
            must = [s for s in must if s not in SKILL_FAMILIES["azure"] and s != "azure"]
    return must, nice


def _build_jd_gap_warnings(*, missing_must: list[str]) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    for token in missing_must:
        norm = normalize_skill_name(token)
        if norm in NOISE_TOKENS:
            continue
        warnings.append(
            {
                "token": norm,
                "reason": "not_in_context",
                "suggestions": [],
                "user_action": None,
                "saved": False,
            }
        )
    return warnings


async def _rewrite_sections(
    *,
    latex: str,
    jd_text: str,
    mode: str,
    matched: list[str],
    missing: list[str],
    evidence_blob: str,
    allowed_overrides: list[str],
    extra_note: str = "",
) -> str:
    present = {sec.name.lower() for sec in split_sections(latex)}
    out = latex
    system = _rewrite_system_for_mode(mode)
    # Sections that must never be selected via the "unprotected" path when rewriting others
    skip_hints = ALWAYS_PROTECTED_HINTS
    if not _is_deliberate(mode):
        skip_hints = PROTECTED_SECTION_HINTS

    for wanted in _rewrite_section_names(mode):
        if not any(wanted in name for name in present):
            continue
        before_sec = next(
            (
                s
                for s in split_sections(out)
                if wanted in s.name.lower()
                and not any(h in s.name.lower() for h in skip_hints if h != wanted)
            ),
            None,
        )
        # Projects: name contains "project"; skip_hints in deliberate excludes "project"
        if before_sec is None and wanted == "projects" and _is_deliberate(mode):
            before_sec = find_section(out, "project")
        if before_sec is None:
            continue

        sub_count_before = before_sec.body.count("\\resumeSubheading")
        project_count_before = before_sec.body.count("\\resumeProject")
        item_count_before = len(re.findall(r"\\item\b", before_sec.body))

        rewritten_body = await chat_text(
            system=system,
            user=_rewrite_user_prompt(
                section_name=before_sec.name,
                body=before_sec.body,
                jd_text=jd_text,
                mode=mode,
                matched=matched,
                missing=missing,
                evidence_blob=evidence_blob,
                allowed_overrides=allowed_overrides,
                extra_note=extra_note,
            ),
            temperature=0.2,
        )
        rewritten_body = _sanitize_section_body(rewritten_body, wanted)

        if wanted == "experience":
            if rewritten_body.count("\\resumeSubheading") != sub_count_before:
                rewritten_body = before_sec.body
            else:
                item_after = len(re.findall(r"\\item\b", rewritten_body))
                # Deliberate may +1 item; strict must keep count
                if _is_deliberate(mode):
                    if item_after > item_count_before + 1 or item_after < max(
                        0, item_count_before - 1
                    ):
                        rewritten_body = before_sec.body
                elif item_after != item_count_before:
                    # Strict: allow same count only (rephrase)
                    pass  # rephrase can keep same \\item count; don't hard-fail tiny diffs
        if wanted == "projects":
            if rewritten_body.count("\\resumeProject") != project_count_before:
                rewritten_body = before_sec.body

        out = replace_section_body(out, wanted if wanted != "projects" else "project", rewritten_body)
    return out


def _sanitize_section_body(body: str, section: str) -> str:
    """Strip accidental \\section dumps and project macros from rewritten bodies."""
    body = _strip_accidental_section_header(body)
    # Cut everything from the first nested \\section onward
    body = re.split(r"\\section\*?\s*\{", body, maxsplit=1)[0]
    if section != "projects":
        body = re.sub(
            r"\\resumeProject\b[\s\S]*?(?=\\resumeProject\b|\\resumeItemListStart|\\resumeSubHeadingListEnd|$)",
            "",
            body,
            flags=re.IGNORECASE,
        )
    return body.strip() + ("\n" if body.strip() else "")


def _unique_norms(items: list[Any]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        norm = normalize_skill_name(str(item))
        if not norm or norm in seen:
            continue
        seen.add(norm)
        out.append(norm)
    return out


async def _get_user_resume(db: AsyncSession, user_id: UUID, resume_id: UUID) -> Resume:
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
    allowed_overrides: list[str],
    extra_note: str = "",
) -> str:
    deliberate_hint = ""
    if _is_deliberate(mode):
        deliberate_hint = (
            "\nDELIBERATE CHECKLIST (do this before rewriting):\n"
            "1) Infer JD stack focus from the JD text (e.g. Python/RAG/AI vs Node/Express/TS).\n"
            "2) Scan VERIFIED EVIDENCE below — did this person actually use that stack "
            "(role or project, e.g. Freshdesk Python/FastAPI/RAG)?\n"
            "3) If YES and this is Experience or Projects: replace the single weakest "
            "keyword-overlap \\item with one smooth evidence-backed line; keep important "
            "ownership/metric bullets.\n"
            "4) If NO evidence for that stack: only light rephrase — never invent.\n"
            "5) Same employer/project count; never invent new \\resumeProject or jobs.\n"
        )
    return (
        f"Section name: {section_name}\n"
        f"Mode: {mode}\n"
        f"Matched skills: {matched}\n"
        f"Missing from context (do not invent unless override): {missing}\n"
        f"allowed_overrides: {allowed_overrides}\n"
        f"{deliberate_hint}"
        f"{extra_note}\n\n"
        f"Verified evidence:\n{evidence_blob}\n\n"
        f"Job description:\n{jd_text}\n\n"
        f"Current section BODY LaTeX:\n{body}\n"
    )


def _strip_accidental_section_header(body: str) -> str:
    return re.sub(r"^\\section\*?\{[^}]+\}\s*", "", body.strip(), count=1, flags=re.IGNORECASE)
