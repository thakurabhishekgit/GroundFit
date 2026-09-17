"""
Offline + live eval: project restore + JD align against default resume.

Run from apps/api:
  ..\\.venv\\Scripts\\python.exe ..\\..\\scripts\\eval_align.py
"""

from __future__ import annotations

import asyncio
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "apps" / "api"
sys.path.insert(0, str(API))

# Load .env from repo root
env_path = ROOT / ".env"
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        # Skip bare neon URL line without KEY=
        if line.startswith("postgresql://"):
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip())

from app.services.align_service import (  # noqa: E402
    REWRITE_SYSTEM,
    expand_covered_skills,
    restore_protected_sections,
    _build_jd_gap_warnings,
    _filter_jd_skills,
    _unique_norms,
    _apply_cloud_alternatives,
    _concept_covered,
    _rewrite_sections,
    JD_EXTRACT_SYSTEM,
)
from app.services.latex_utils import find_section, split_sections  # noqa: E402
from app.services.openai_client import chat_json  # noqa: E402

RESUME = (ROOT / "apps" / "web" / "src" / "data" / "defaultResume.tex").read_text(encoding="utf-8")

# Skills inferred from the user's resume + typical confirmed context
USER_SKILLS = {
    "java",
    "python",
    "javascript",
    "typescript",
    "c",
    "spring-boot",
    "react",
    "fastapi",
    "kafka",
    "redis",
    "postgresql",
    "mongodb",
    "mysql",
    "microsoft-sql-server",
    "sql",
    "docker",
    "aws",
    "azure",
    "azure-devops",
    "git",
    "ci-cd",
    "rbac",
    "microservices",
    "rag",
    "langchain",
    "jwt",
    "html",
    "css",
    "express.js",
    "asp.net",
    "mcp",
}

EVIDENCE = """
- Java (java): Ticket360 Spring Boot microservices; Wcontent; Knowable.AI
- Spring Boot (spring-boot): Ticket360, Wcontent, Knowable.AI APIs
- Redis (redis): Ticket360 API cache; Knowable.AI latency
- React (react): Ticket360 SPA
- PostgreSQL (postgresql): Knowable.AI
- MongoDB (mongodb): Wcontent
- Kafka (kafka): Wcontent event-driven email alerts
- Azure AI Search / RAG (rag): Freshdesk RAG at Newmark
- Docker (docker): Wcontent / Knowable deploy
- Python (python): FastAPI exposure
- TypeScript (typescript): Express internal apps
- AWS (aws): listed in skills
- Git (git): GitHub workflows
""".strip()

JDS = {
    "clinical_internal_tools": """
What will you do?
Engineering: Understand software requirements from clinical collaborators and internal teams (Product, R&D, Data Engineering, Clinical, Software) to design and engineer various internal tools.
Software Development: Develop, deploy, and maintain a high-quality codebase (behavior-driven design and domain-driven design) with proper testing and re-usability.
Data Management: Implement and maintain databases, and prepare entity-relationship diagrams.

Who are we looking for?
3 to 6 years of experience as a Software Engineer or related experience.
Strong programming skills in one or more languages such as Python, Go, or JavaScript/Typescript.
Familiarity with HTML, CSS, and JavaScript/Typescript for front-end development. Experience in any of the modern JavaScript frontend frameworks, such as Nuxt3, Vue, React, Svelte, etc., is preferred.
Familiarity with database technologies such as Postgres, SQL, and NoSQL.
Understanding of data structures, algorithms, and software design patterns.
Knowledge of software testing using Jest, etc., and other debugging techniques.
Basic understanding and knowledge of: Git and Git Workflow, Containerization (preferably Docker), CI/CD, Cloud provider (preferably AWS), Agile software development methodologies
Ability to work in a team environment and collaborate with other engineers.
Previous internship experience in early-stage startups is a plus.
""".strip(),
    "novapay_java_spring": """
Backend Engineer — Java / Spring Boot (NovaPay)
Strong Java and Spring Boot (REST, Security, JPA)
Microsoft SQL Server or relational DBs
Redis caching and idempotent API design
Microservices, RBAC, SLA-aware workflows
CI/CD on cloud (Azure or AWS)
Nice: Azure App Service, Azure DevOps, Event-driven / Kafka
""".strip(),
    "fullstack_react_spring": """
Full-Stack Engineer — React + Spring (Workstream Labs)
React SPA + Java/Spring Boot APIs
Auth with JWT, RBAC
SQL databases; TypeScript on the UI
Deploying to Vercel/Render or Azure
Nice: Express.js / ASP.NET, dashboard performance
""".strip(),
}


def project_titles(latex: str) -> list[str]:
    proj = find_section(latex, "project")
    if not proj:
        return []
    return re.findall(r"\\resumeProject\s*\{([^}]+)\}", proj.body)


def assert_projects_intact(label: str, original: str, result: str) -> None:
    orig_titles = project_titles(original)
    res_titles = project_titles(result)
    print(f"  [{label}] projects original={orig_titles}")
    print(f"  [{label}] projects result  ={res_titles}")
    assert "Wcontent" in " ".join(res_titles), "Wcontent missing from Projects"
    assert "Knowable" in " ".join(res_titles), "Knowable missing from Projects"
    assert not any("Ticket360" in t for t in res_titles), "Ticket360 must NOT be a Project"
    assert find_section(original, "project").body.strip() == find_section(result, "project").body.strip()


def test_nested_section_parse() -> None:
    secs = split_sections(RESUME)
    names = [s.name for s in secs]
    print("sections:", names)
    assert "Projects" in names
    assert "Experience" in names
    assert_projects_intact("original", RESUME, RESUME)

    # Simulate model inventing Ticket360 project
    mangled = RESUME
    fake = r"""
\vspace{-0.4mm}
\resumeSubHeadingListStart
\resumeProject
  {Ticket360: AI-Powered Helpdesk Platform}
  {Java, Spring Boot, Redis, Microservices}
  {2026}
  {{}[]}
\resumeItemListStart
\item Fake invented project
\resumeItemListEnd
\resumeSubHeadingListEnd
\vspace{-6mm}
"""
    mangled = mangled.replace(find_section(RESUME, "project").body, fake)
    assert any("Ticket360" in t for t in project_titles(mangled))
    fixed = restore_protected_sections(RESUME, mangled)
    assert_projects_intact("restore-after-invent", RESUME, fixed)

    # Simulate deleted Projects section
    deleted = RESUME
    proj = find_section(RESUME, "project")
    deleted = deleted[: proj.start] + deleted[proj.end :]
    assert find_section(deleted, "project") is None
    fixed2 = restore_protected_sections(RESUME, deleted)
    assert_projects_intact("restore-after-delete", RESUME, fixed2)
    print("PASS nested parse + restore\n")


async def eval_jd(name: str, jd: str) -> dict:
    covered = expand_covered_skills(USER_SKILLS)
    jd_skills = await chat_json(system=JD_EXTRACT_SYSTEM, user=jd, temperature=0.0)
    must = _filter_jd_skills(_unique_norms(jd_skills.get("must_have") or []))
    nice = _filter_jd_skills(_unique_norms(jd_skills.get("nice_to_have") or []))
    must, nice = _apply_cloud_alternatives(must, nice, jd, covered)
    matched_must = [s for s in must if s in covered or _concept_covered(s, covered)]
    missing_must = [s for s in must if s not in covered and not _concept_covered(s, covered)]
    matched_nice = [s for s in nice if s in covered or _concept_covered(s, covered)]

    latex = await _rewrite_sections(
        latex=RESUME,
        jd_text=jd,
        mode="strict",
        matched=list(dict.fromkeys(matched_must + matched_nice)),
        missing=missing_must,
        evidence_blob=EVIDENCE,
        allowed_overrides=[],
        extra_note="Do not emit \\section or \\resumeProject. Projects are restored automatically.",
    )
    latex = restore_protected_sections(RESUME, latex)

    exp_orig = find_section(RESUME, "experience").body
    exp_new = find_section(latex, "experience").body
    sum_orig = find_section(RESUME, "summary").body
    sum_new = find_section(latex, "summary").body
    skills_orig = find_section(RESUME, "skills").body
    skills_new = find_section(latex, "skills").body

    warnings = _build_jd_gap_warnings(missing_must=missing_must)

    report = {
        "name": name,
        "must": must,
        "nice": nice,
        "matched_must": matched_must,
        "missing_must": missing_must,
        "matched_nice": matched_nice,
        "warnings": [w["token"] for w in warnings],
        "summary_changed": sum_orig.strip() != sum_new.strip(),
        "experience_changed": exp_orig.strip() != exp_new.strip(),
        "skills_changed": skills_orig.strip() != skills_new.strip(),
        "projects_ok": True,
        "ticket360_in_projects": any("Ticket360" in t for t in project_titles(latex)),
        "has_wcontent": any("Wcontent" in t for t in project_titles(latex)),
        "has_knowable": any("Knowable" in t for t in project_titles(latex)),
        "summary_snippet": re.sub(r"\s+", " ", sum_new)[:280],
        "exp_snippet": re.sub(r"\s+", " ", exp_new)[:280],
    }
    try:
        assert_projects_intact(name, RESUME, latex)
    except AssertionError as e:
        report["projects_ok"] = False
        report["project_error"] = str(e)

    out_path = ROOT / "scripts" / f"eval_out_{name}.tex"
    out_path.write_text(latex, encoding="utf-8")
    report["wrote"] = str(out_path)
    return report


async def main() -> None:
    print("=== Unit: section parse + restore ===")
    test_nested_section_parse()

    print("=== Live: JD align evals ===")
    results = []
    for name, jd in JDS.items():
        print(f"\n--- Running {name} ---")
        try:
            r = await eval_jd(name, jd)
            results.append(r)
            for k in (
                "matched_must",
                "missing_must",
                "warnings",
                "summary_changed",
                "experience_changed",
                "skills_changed",
                "projects_ok",
                "ticket360_in_projects",
                "has_wcontent",
                "has_knowable",
            ):
                print(f"  {k}: {r[k]}")
            print(f"  summary: {r['summary_snippet'][:160]}...")
        except Exception as e:
            print(f"  FAIL {name}: {type(e).__name__}: {e}")
            results.append({"name": name, "error": str(e)})

    print("\n=== FINAL ===")
    for r in results:
        if "error" in r:
            print(f"{r['name']}: ERROR {r['error']}")
            continue
        print(
            f"{r['name']}: projects_ok={r['projects_ok']} "
            f"sum={r['summary_changed']} exp={r['experience_changed']} "
            f"skills={r['skills_changed']} missing={r['missing_must']}"
        )


if __name__ == "__main__":
    asyncio.run(main())
