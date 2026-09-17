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


# Match \section{...} / \section*{...} with nested braces (e.g. \section{\textbf{Projects}})
_SECTION_START_RE = re.compile(r"\\section\*?\{", re.IGNORECASE)


def _closing_brace_index(text: str, open_brace_at: int) -> int:
    """Index of the `}` that closes the `{` at open_brace_at, respecting nesting."""
    depth = 0
    i = open_brace_at
    while i < len(text):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i
        elif ch == "\\" and i + 1 < len(text):
            # Skip escaped char so \{ \} don't confuse depth (rare in section titles)
            i += 1
        i += 1
    raise ValueError("Unbalanced braces in \\section header")


def _plain_section_name(raw: str) -> str:
    """Strip LaTeX commands from a section title for matching."""
    plain = re.sub(r"\\[a-zA-Z]+\*?", "", raw)
    plain = re.sub(r"[{}]", "", plain)
    return plain.strip()


def split_sections(latex: str) -> list[LatexSection]:
    """
    Split a LaTeX resume into section regions by \\section / \\section*.

    Content before the first section is treated as preamble (not returned).
    Each section body runs until the next section header or end of doc.
    """
    starts = list(_SECTION_START_RE.finditer(latex))
    sections: list[LatexSection] = []
    for i, match in enumerate(starts):
        open_brace = match.end() - 1  # points at '{'
        try:
            close = _closing_brace_index(latex, open_brace)
        except ValueError:
            continue
        header = latex[match.start() : close + 1]
        raw_name = latex[open_brace + 1 : close]
        name = _plain_section_name(raw_name) or raw_name.strip()
        body_start = close + 1
        end = starts[i + 1].start() if i + 1 < len(starts) else len(latex)
        body = latex[body_start:end]
        sections.append(
            LatexSection(name=name, start=match.start(), end=end, header=header, body=body)
        )
    return sections


def find_section(latex: str, wanted: str) -> Optional[LatexSection]:
    """Find first section whose plain name contains `wanted` (case-insensitive)."""
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


def insert_section_after(latex: str, after_hint: str, header: str, body: str) -> str:
    """Insert a full section (header+body) after the section matching after_hint."""
    anchor = find_section(latex, after_hint)
    if anchor is None:
        # Append before \\end{document} if present
        end_doc = re.search(r"\\end\{document\}", latex, re.IGNORECASE)
        chunk = header + (body if body.startswith("\n") else "\n" + body)
        if end_doc:
            return latex[: end_doc.start()] + chunk + "\n" + latex[end_doc.start() :]
        return latex + "\n" + chunk

    chunk = header + (body if body.startswith("\n") else "\n" + body)
    if not chunk.endswith("\n"):
        chunk += "\n"
    return latex[: anchor.end] + chunk + latex[anchor.end :]


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
        "jest": "jest",
        "vue": "vue",
        "nuxt": "nuxt",
        "svelte": "svelte",
    }
    slug = re.sub(r"[^a-z0-9.+#]+", "-", raw.strip().lower()).strip("-")
    return aliases.get(slug, slug)
