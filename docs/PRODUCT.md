# Product — GroundFit

## 1. Problem statement

Generic “align my resume to this JD” LLM flows:

1. Paste JD + resume → model injects JD keywords.
2. User often **doesn’t know** half the added skills.
3. Even if they do, the model **doesn’t know where** those skills were used (project, role, impact).
4. Fixing that is **manual**: “add Redis” → later “wait, I used Redis for processed-ticket cache in Freshdesk polling…”

**GroundFit** makes a personal **Experience Context** the source of truth. Alignment is:

- JD-aware (ATS keywords)
- **Evidence-aware** (only claim what context supports)
- **Honest** (warn on unverified additions)

Practical tool for friends applying to jobs — not a startup pitch.

---

## 2. Goals

### Must have
- Google Auth + user profile
- Experience Context onboarding (rich text + structured skills)
- Ingest resume (**LaTeX** primary)
- Paste / upload Job Description
- Generate aligned resume (LaTeX out; PDF optional)
- Verification layer: every suggested skill/bullet maps to evidence (or flagged)
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
- Fully $0 including OpenAI tokens (hosting free; LLM usage billed)

---

## 3. Core concepts

### 3.1 Experience Context (source of truth)

User provides (once, then editable):

- **Roles / internships** — company, title, dates, ownership (owned / contributed / led)
- **Projects** — name, problem, architecture, tech, metrics, exact role
- **Skills inventory** — language / framework / cloud / AI / tools
- **Evidence narratives** — free text: *where* and *why* each skill was used  
  Example: *“Redis at Newmark Freshdesk agent: store processed ticket IDs during webhook/polling so already classified tickets are skipped.”*

Store as:

1. **Structured data** (skills, projects, roles, metrics) — matching & UI
2. **Raw narratives** — LLM grounding & citations

### 3.2 Alignment modes

| Mode | Behavior |
|------|----------|
| **Strict** (default) | Only skills/evidence in context. Never invent. |
| **Suggest** | May propose JD keywords missing from context → **must confirm** |
| **Explore** | Softer; still labels unverified lines clearly |

### 3.3 Output

- Updated LaTeX (section-aware: Summary, Experience, Projects, Skills)
- Changelog: added / rephrased / removed + **evidence link**
- Optional warnings list

---

## 4. Key flows

### A. Onboarding (critical UX)

1. Paste detailed experience (guided prompts per role/project).
2. LLM extracts skills + evidence → **review UI** (accept/edit).
3. Save skill graph + raw text (+ embeddings later if needed).

Guided prompts:

- What did you own vs contribute?
- For each tech: where used, why chosen, any metric?
- Any tools you do **not** want on resumes?

### B. Align resume

1. Upload/paste LaTeX + JD.
2. Parse JD skills.
3. Match against skill graph.
4. Retrieve evidence for top matches.
5. Rewrite Summary / Experience / Projects / Skills.
6. Verify pass → warnings for unverified keywords.
7. User confirms overrides → final LaTeX (+ PDF later).

### C. Warning example

> Proposed: “Apache Kafka event-driven pipeline”  
> **Not found** in your Experience Context.  
> [Add anyway] [Suggest similar: Redis pub/sub? Azure Service Bus?] [Skip]

---

## 5. Example user story

Context includes:

- Ticket360 owned end-to-end — Spring Boot, SQL Server, AI classification, SLA, RBAC
- Freshdesk — RAG PDFs → Azure AI Search; MCP auto-resolve 15–20%; Redis processed-ticket skip
- Internal dashboards — Express/TS/ASP.NET; latency 3–4s → &lt;300ms

JD: “Backend Engineer — Java, Kafka, Redis, microservices”

**GroundFit:**

- Emphasizes Java/Spring, Redis (with Freshdesk + Ticket360 evidence)
- Kafka: **warn** unless present under Projects/context
- Does **not** invent Kubernetes if absent

---

## 6. Evaluation (avoid keyword spam)

Per alignment run:

- **Coverage:** % of JD must-have skills *verified* in context
- **Hallucination rate:** unsupported tech tokens (target → 0 in Strict)
- **Evidence rate:** % of new/changed bullets with ≥1 evidence id
- User thumbs up/down on honesty

---

## 7. Success criteria

- Align takes **&lt; 5 minutes** after context is filled once.
- Strict mode: **zero** unverified skills unless user overrides.
- Friends reuse context without re-explaining their career to a new chat each time.
