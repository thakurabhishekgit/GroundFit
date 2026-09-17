# Architecture

## System diagram

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│ Web App     │────▶│ FastAPI          │────▶│ Neon Postgres   │
│ React/Vite  │     │ Auth, jobs, align│     │ users, context, │
│ (Vercel)    │     │ (Render)         │     │ resumes, runs   │
└─────────────┘     └────────┬─────────┘     │ + pgvector later│
                             │               └────────┬────────┘
                             ▼                        │
                    ┌──────────────────┐              │
                    │ AI Orchestrator  │◀─────────────┘
                    │ 1 JD parse       │
                    │ 2 Skill match    │
                    │ 3 Evidence fetch │
                    │ 4 Rewrite LaTeX  │
                    │ 5 Verify         │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │ OpenAI API       │
                    │ (structured JSON)│
                    └──────────────────┘
```

Optional later: LaTeX→PDF worker; dedicated vector store (Qdrant) only if Neon/pgvector is insufficient.

---

## AI pipeline (multi-step, not one giant prompt)

| Step | Name | Type | Output |
|------|------|------|--------|
| 1 | `extract_jd_skills` | LLM | JSON skill list (must / nice) |
| 2 | `match_skills` | Code + light LLM | matched / partial / missing |
| 3 | `select_evidence` | DB filter (+ RAG later) | top 1–3 snippets per skill |
| 4 | `rewrite_section` | LLM | LaTeX fragments only |
| 5 | `verify_claims` | LLM + rules | unsupported tokens list |

### Hard rules (system prompt)

- Never invent employers, metrics, or tools.
- Metrics only if present in evidence (or user override).
- Prefer rephrasing existing bullets over fabricating ownership.
- Ownership language: owned / contributed / collaborated — from context.
- No skill without evidence unless `user_override=true`.

---

## Auth flow (Google)

1. User clicks “Continue with Google” on web.
2. Frontend uses Auth.js / Google Identity Services → ID token or session cookie.
3. API verifies Google JWT (`aud`, `iss`, `email_verified`) on protected routes.
4. Upsert `User` row; attach `ExperienceContext`, resumes, runs to `user_id`.

No passwords. Session: HTTP-only cookie (preferred) or Bearer for SPA↔API.

---

## Hybrid retrieval (why not RAG-only)

```
JD skills ──▶ intersect Skill Graph ──▶ matched skills
                                            │
                                            ▼
                                   fetch SkillEvidence rows
                                   (SQL by skill_id / project_id)
                                            │
                                            ▼
                                   pack into rewrite prompt
```

When narratives exceed ~30–50k tokens, add embeddings on narratives + `skill` / `project` metadata filters (pgvector). See [RAG_AND_VECTOR.md](RAG_AND_VECTOR.md).

---

## Section rewrite strategy

Parse LaTeX into sections (regex / lightweight AST helpers in `packages/latex-utils`):

- Summary
- Experience
- Projects
- Skills

Rewrite **one section at a time** with:

- Original section LaTeX
- Matched skills + evidence snippets
- Mode (`strict` | `suggest`)
- Forbidden invent list from verify rules

Merge fragments back into full document; keep preamble untouched.

---

## Verifier pass

After rewrite:

1. Extract tech tokens from new/changed bullets (LLM or allowlist NER).
2. Check each against user’s skill graph (normalized names: `k8s` → `kubernetes`).
3. Any orphan → `warnings_json` + UI confirm.
4. Persist changelog with `status: verified | override | rejected`.

---

## API surface (v1 sketch)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/auth/me` | Current user |
| GET/PUT | `/context` | Raw + structured context |
| POST | `/context/extract` | LLM extract → draft graph |
| POST | `/context/confirm` | Accept/edit skills & evidence |
| POST | `/resumes` | Upload LaTeX |
| POST | `/align` | Start alignment run |
| GET | `/align/{id}` | Result + warnings + changelog |
| POST | `/align/{id}/confirm` | Apply overrides |

Async later: long runs via job id + polling if Render timeouts bite.

---

## Security notes

- Never send other users’ context in prompts (strict `user_id` filter).
- Store OpenAI key only on API (Render env), never in Vercel client.
- Rate-limit `/align` and `/context/extract` (OpenAI cost + abuse).
- Sanitize LaTeX size caps to avoid huge prompt bills.
