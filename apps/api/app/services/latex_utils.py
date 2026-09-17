"""
LaTeX section split / merge helpers.

Goal: rewrite only section bodies and preserve the user's exact document
structure (preamble, macros, spacing commands) — no overlapping dumps.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


# Common resume section headings we care about (case-insensitive)
SECTION_NAMES = ("summary", "experience", "education", "projects", "skills", "technical skills")


@dataclass
class LatexSection:
    """One \\section{...} (or \\section*{...}) block in the document."""

    name: str
    start: int
    end: int
    header: str
    body: str


_SECTION_RE = re.compile(
    r"(?P<header>\\section\*?\{(?P<name>[^}]+)\})",
    re.IGNORECASE,
)


def split_sections(latex: str) -> list[LatexSection]:
    """
    Split a LaTeX resume into section regions by \\section / \\section*.

    Content before the first section is treated as preamble (not returned).
    Each section body runs until the next section header or end of doc.
    """
    matches = list(_SECTION_RE.finditer(latex))
    sections: list[LatexSection] = []
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(latex)
        header = match.group("header")
        name = match.group("name").strip()
        body = latex[match.end() : end]
        sections.append(
            LatexSection(name=name, start=start, end=end, header=header, body=body)
        )
    return sections


def find_section(latex: str, wanted: str) -> Optional[LatexSection]:
    """Find first section whose name contains `wanted` (case-insensitive)."""
    needle = wanted.lower().strip()
    for section in split_sections(latex):
        if needle in section.name.lower():
            return section
    return None


def replace_section_body(latex: str, wanted: str, new_body: str) -> str:
    """
    Replace only the body of a named section; keep header and surrounding doc.

    `new_body` should be LaTeX fragment only (no \\section header, no preamble).
    Raises ValueError if the section is missing.
    """
    section = find_section(latex, wanted)
    if section is None:
        raise ValueError(f"Section not found: {wanted}")

    # Preserve leading newline style after header when possible
    body = new_body
    if not body.startswith("\n"):
        body = "\n" + body
    if not body.endswith("\n") and section.end < len(latex):
        body = body + "\n"

    return latex[: section.start] + section.header + body + latex[section.end :]


def normalize_skill_name(raw: str) -> str:
    """Canonical lowercase slug for skill matching."""
    aliases = {
        "k8s": "kubernetes",
        "js": "javascript",
        "ts": "typescript",
        "spring": "spring-boot",
        "nodejs": "node.js",
        "node": "node.js",
        "postgres": "postgresql",
        "gcp": "google-cloud",
        "mssql": "microsoft-sql-server",
        "sqlserver": "sql-server",
        "ms-sql-server": "microsoft-sql-server",
        "rest-apis": "rest",
        "restful-apis": "rest",
        "reactjs": "react",
        "react.js": "react",
    }
    slug = re.sub(r"[^a-z0-9.+#]+", "-", raw.strip().lower()).strip("-")
    return aliases.get(slug, slug)
