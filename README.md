# GroundFit — Personalized, Evidence-Based Resume Alignment

> **One-liner:** Upload a JD + resume; get an ATS-aligned resume that only uses skills you actually have — grounded in your own experience context — with warnings when something isn’t proven.

**Working name options (pick one):**
| Name | Why |
|------|-----|
| **GroundFit** | Grounded fit to JD (recommended) |
| **ProofFit** | Every keyword has proof |
| **AnchorCV** | Experience is the anchor |
| **VeriResume** | Verified resume alignment |
| **ContextCV** | Context-first alignment |

---

## 1. Problem Statement

Generic “align my resume to this JD” LLM flows:

1. Paste JD + resume → model injects JD keywords.
2. User often **doesn’t know** half the added skills.
3. Even if they do, the model **doesn’t know where** those skills were used (which project, what role, what impact).
4. Fixing that is **manual**: “add Redis” → later “wait, I used Redis for processed-ticket cache in Freshdesk polling…”

**GroundFit fixes this** by making a **personal Experience Context** the source of truth. Alignment is:

- JD-aware (ATS keywords)
- **Evidence-aware** (only claim what context supports)
- **Honest** (warn on unverified additions)

**Not a startup pitch** — a practical tool for you and friends applying to jobs.

---

## 2. Product Goals

### Must have
- Auth + user profile
- **Experience Context** onboarding (rich text + structured skills)
- Ingest resume (**LaTeX** primary; PDF optional later)
- Paste / upload **Job Description**
- Generate **aligned resume** (LaTeX out; PDF compile optional)
- **Verification layer:** every suggested skill/bullet maps to context evidence (or is flagged)
- Warning UX: *“Added Apache Kafka but it’s not in your context. Still add?”*

### Nice to have
- Multiple resume versions per JD
- Diff view (before/after)
- “Interview brief” per bullet (where you used X)
- Import LinkedIn / GitHub later

### Non-goals (v1)
- Auto-applying to jobs
- Guaranteed ATS pass scores as a product claim
- Replacing the user’s judgment on honesty

---

## 3. Core Concepts

### 3.1 Experience Context (Source of Truth)
User provides (once, then editable):

- **Roles / internships** — company, title, dates, ownership level (owned / contributed / led)
- **Projects** — name, problem, architecture, tech, metrics, your exact role
- **Skills inventory** — language / framework / cloud / AI / tools
- **Evidence narratives** — free text: *where* and *why* each skill was used  
  Example: *“Redis at Newmark Freshdesk agent: store processed ticket IDs during webhook/polling so already classified tickets are skipped.”*

Store as:
1. **Structured JSON** (skills, projects, roles, metrics) — for matching & UI
2. **Raw narratives** — for LLM grounding & citations

### 3.2 Alignment Modes
| Mode | Behavior |
|------|----------|
| **Strict** | Only skills/evidence in context. Never invent. |
| **Suggest** | May propose JD keywords missing from context → **must confirm** |
| **Explore** | Softer; still labels unverified lines clearly |

Default = **Strict** + confirm gate for gaps.

### 3.3 Output
- Updated LaTeX (section-aware: Summary, Experience, Projects, Skills)
- Change log: added / rephrased / removed + **evidence link**
- Optional warnings list

---

## 4. Should We Use RAG?

### Short answer
**Hybrid: structured skill graph + selective context packing. RAG is optional for large contexts.**

### Why not “RAG-only”
| Approach | Pros | Cons |
|----------|------|------|
| Dump full context into LLM every time | Simple, accurate for small profiles | Breaks when context grows (many jobs, long notes) |
| Pure RAG over embeddings | Scales | Chunks can miss “I used Redis for X”; weaker for skill inventory |
| **Hybrid (recommended)** | Precise skill match + narrative evidence | Slightly more engineering |

### Recommended architecture
1. **Structured Skill Graph**  
   `skill → [{project/role, usage_summary, metrics, confidence}]`  
   Built on onboarding via LLM extraction + user edit/confirm.

2. **JD → Skill Gap Analysis** (deterministic-ish)  
   Extract required skills from JD → intersect with skill graph →  
   - **Matched** / **Partial** / **Missing**

3. **Evidence retrieval** (light RAG or filtered fetch)  
   For matched skills, pull the **best 1–3 narrative snippets** + project metadata.

4. **Generation**  
   LLM rewrites resume sections using:
   - Original LaTeX AST/sections
   - Matched skills + evidence snippets
   - Strict instruction: no skill without evidence unless `user_override=true`

5. **Verifier pass** (second LLM or rules)  
   Check every bolded tech in new bullets against skill graph. Flag orphans.

**When to turn on full RAG:**  
User context > ~30–50k tokens, or many projects. Embed narratives with metadata filters (`skill:redis`, `project:freshdesk`).

**Embedding target:** experience narratives + project summaries — **not** the JD alone.  
JD is short; extract skills with LLM/NER, then query the graph/RAG.

---

## 5. System Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│ Web App     │────▶│ API (Nest/FastAPI)│────▶│ Postgres        │
│ React       │     │ Auth, jobs, align │     │ users, context, │
└─────────────┘     └────────┬─────────┘     │ resumes, runs   │
                             │               └────────┬────────┘
                             ▼                        │
                    ┌──────────────────┐              │
                    │ AI Orchestrator  │◀─────────────┘
                    │ 1 JD parse       │
                    │ 2 Skill match    │     ┌─────────────────┐
                    │ 3 Evidence fetch │────▶│ Vector DB       │
                    │ 4 Rewrite LaTeX  │     │ (optional v1.5) │
                    │ 5 Verify         │     │ pgvector / Qdrant│
                    └──────────────────┘     └─────────────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │ LaTeX → PDF      │
                    │ (optional worker)│
                    └──────────────────┘
```

### Suggested stack (pragmatic for you)
| Layer | Choice | Why |
|-------|--------|-----|
| Frontend | React + TypeScript + Vite | Matches your stack |
| Backend | **FastAPI (Python)** or NestJS | FastAPI easier for AI pipelines |
| DB | PostgreSQL | Profiles, resumes, alignment runs |
| Auth | Clerk / Auth.js / Firebase | Fast to ship |
| LLM | OpenAI / Azure OpenAI / Gemini | Structured outputs (JSON schema) |
| Vectors | **pgvector first** | One DB; add Qdrant if needed |
| Queue | Optional Redis + worker | PDF compile, long aligns |
| Storage | S3 / Azure Blob | PDF/LaTeX files |

---

## 6. Data Model (v1)

```text
User
  id, email, name

ExperienceContext
  user_id
  raw_text (full dump)
  updated_at

Skill
  user_id, name, category (lang|framework|db|cloud|ai|tool|concept)
  proficiency (optional)

SkillEvidence
  skill_id
  source_type (role|project)
  source_id
  summary          # "Redis used to cache processed Freshdesk ticket IDs..."
  metrics_json     # {"agent_effort_reduction": "40%"}
  verified (bool)  # user confirmed extraction

Role / Project
  title, org, dates, ownership, description, tech[]

Resume
  user_id, title, latex_source, version

AlignmentRun
  resume_id, jd_text, mode (strict|suggest)
  result_latex
  changelog_json   # [{path, before, after, evidence_ids[], status: verified|override|rejected}]
  warnings_json
```

---

## 7. Key Flows

### A. Onboarding (critical UX)
1. Paste detailed experience (guided prompts per role/project).
2. LLM extracts skills + evidence → **review UI** (user accepts/edits).
3. Save skill graph + raw text + optional embeddings.

Guided prompts example:
- What did you own vs contribute?
- For each tech: where used, why chosen, any metric?
- Any tools you do **not** want on resumes?

### B. Align resume
1. Upload/paste LaTeX + JD.
2. Parse JD skills.
3. Match against skill graph.
4. Retrieve evidence for top matches.
5. Rewrite Summary / Experience / Projects / Skills (section prompts).
6. Verify pass → warnings for unverified keywords.
7. User confirms overrides → final LaTeX (+ PDF).

### C. Warning example
> Proposed: “Apache Kafka event-driven pipeline”  
> **Not found** in your Experience Context.  
> [Add anyway] [Suggest similar from your stack: Redis pub/sub? Azure Service Bus?] [Skip]

---

## 8. Prompt / Agent Design

Use **multi-step agents**, not one giant prompt:

1. `extract_jd_skills` → JSON  
2. `match_skills` → code + LLM assist  
3. `select_evidence` → top snippets  
4. `rewrite_section` → LaTeX fragments only  
5. `verify_claims` → list unsupported tokens  

**Hard rules in system prompt:**
- Never invent employers, metrics, or tools.
- Metrics only if present in evidence (or user override).
- Prefer rephrasing existing bullets over fabricating new ownership.
- Ownership language: owned / contributed / collaborated — from context.

---

## 9. MVP Scope (ship in 2–3 weeks)

**Week 1**
- Auth, context paste + extract + review
- Skill graph CRUD
- LaTeX upload + store

**Week 2**
- JD paste + match + align (Experience + Skills sections)
- Warnings + override
- Changelog UI

**Week 3**
- Projects + Summary alignment
- Export LaTeX; optional PDF
- pgvector if context size hurts

Skip for MVP: browser extension, LinkedIn scrape, multi-language resumes.

---

## 10. Evaluation (so it doesn’t become keyword spam)

For each alignment run, score:
- **Coverage:** % of JD must-have skills that are *verified* in context  
- **Hallucination rate:** unsupported tech tokens in output (target → 0 in Strict)  
- **Evidence rate:** % of new/changed bullets with ≥1 evidence id  
- User thumbs up/down on honesty

---

## 11. Example User Story (you)

Context includes:
- Ticket360 owned end-to-end — Spring Boot, SQL Server, AI classification, SLA, RBAC  
- Freshdesk — RAG PDFs → Azure AI Search; MCP auto-resolve 15–20%; Redis processed-ticket skip  
- Internal dashboards — Express/TS/ASP.NET; latency 3–4s → &lt;300ms  

JD: “Backend Engineer — Java, Kafka, Redis, microservices”

**GroundFit:**
- Emphasizes Java/Spring, Redis (with Freshdesk + Ticket360 evidence)
- Kafka: **warn** if only in Wcontent personal project — allow if context has it under Projects
- Does **not** invent Kubernetes if absent

---

## 12. Repo Structure (suggested)

```text
groundfit/
  apps/web/                 # React
  apps/api/                 # FastAPI
  packages/prompts/         # versioned prompts
  packages/latex-utils/     # section split / merge helpers
  README.md                 # this file
  docs/PRODUCT.md
  docs/ARCHITECTURE.md
```

---

## 13. Success Criteria

- Aligning a resume takes **&lt; 5 minutes** after context is filled once.
- In Strict mode, **zero** unverified skills unless user overrides.
- Friends can use it without explaining their whole career to a new chat each time.

---

## 14. Open Decisions

1. LaTeX-only v1 vs PDF upload (PDF needs parsing — harder)?  
2. FastAPI vs Nest for API?  
3. Name: **GroundFit** vs **ProofFit** vs **AnchorCV**?  
4. Host LLM: OpenAI vs Azure (you already use Azure at work)?

---

## 15. Next Build Step

Start with:
1. Freeze name  
2. Schema + onboarding extract/review UI  
3. Align pipeline: JD → match → rewrite Experience/Skills → verify  

Do **not** start with a fancy RAG stack — structured context + verification is the product moat.

---

### Name pick
**GroundFit** — short, unique, matches the idea (grounded JD fit). Alternatives: **ProofFit**, **AnchorCV**.

### RAG verdict
Use **structured skill + evidence graph first**; add **pgvector RAG** only when narratives get long. Always run a **verify pass** so “add Redis” can’t happen without Freshdesk/Ticket360-style proof (or an explicit override).
