# GroundFit

> Upload a JD + resume → get an ATS-aligned resume that **only claims skills you actually have**, grounded in your Experience Context, with warnings when something isn’t proven.

**Audience:** you + friends applying to jobs (not a startup pitch).

---

## Frozen decisions (v1)

| Area | Choice | Notes |
|------|--------|--------|
| **Name** | GroundFit | |
| **Auth** | Google OAuth | Via Auth.js (frontend) or FastAPI Google ID token verify |
| **Primary DB** | **PostgreSQL** (local dev + Neon free for cloud) | Connection string only — no Neon MCP/Auth/Functions |
| **Vectors (later)** | **pgvector** (same Postgres) | Optional when context gets large |
| **LLM** | **OpenAI** | API is **usage-billed** (hosting can be free; tokens are not) |
| **Frontend** | React + TypeScript + Vite → **Vercel** | Free Hobby tier |
| **Backend** | FastAPI → **Render** (free web service) | Cold starts OK for 10–15 users |
| **Resume format** | LaTeX in / LaTeX out | PDF compile optional later |
| **Alignment default** | Strict + confirm gate | Never invent skills without override |

**Not using for v1 primary store:** MongoDB Atlas (fine free tier, but skill-graph + joins fit Postgres better). Atlas *does* have Vector Search on M0 — see [docs/STACK.md](docs/STACK.md).

---

## The problem in one paragraph

Paste JD + resume into ChatGPT → it injects JD keywords. You may not know those skills; even if you do, the model doesn’t know *where* you used them (which project, what role). Fixing that is manual (“add Redis” → later explain Freshdesk ticket-ID cache). GroundFit stores your experience once as context, then aligns with evidence — or warns: *“Kafka isn’t in your context. Still add?”*

---

## How it works (high level)

1. **Onboard once** — paste detailed experience → LLM extracts skills + evidence → you review/confirm → skill graph saved.
2. **Align** — JD + LaTeX resume → extract JD skills → match graph → pull evidence snippets → rewrite sections → **verify** → warnings for orphans.
3. **Override** — user may force-add missing keywords; changelog records `verified | override | rejected`.

**RAG:** not required at day one. Use structured skill graph + selective narrative packing. Turn on **pgvector** when context gets large (~30–50k tokens). Details: [docs/RAG_AND_VECTOR.md](docs/RAG_AND_VECTOR.md).

---

## Free deployment target (≈10–15 users)

```
Vercel (web)  →  Render (FastAPI)  →  Neon Postgres (+ pgvector later)
                      ↓
                   OpenAI API (paid per token)
```

Full cost/ops notes: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

---

## Repo layout

```text
groundfit/
  apps/web/              # React + Vite (to scaffold)
  apps/api/              # FastAPI (to scaffold)
  packages/prompts/      # versioned prompts (later)
  packages/latex-utils/  # section split/merge (later)
  docs/                  # planning source of truth
  README.md
```

---

## Docs index

| Doc | What |
|-----|------|
| [docs/PRODUCT.md](docs/PRODUCT.md) | Problem, goals, UX flows, success criteria |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design, agents, verify pass |
| [docs/STACK.md](docs/STACK.md) | Auth, DB, Mongo vs Postgres, vector free tiers |
| [docs/DATA_MODEL.md](docs/DATA_MODEL.md) | Schema + JSON shapes |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Vercel + Render + Neon free path |
| [docs/RAG_AND_VECTOR.md](docs/RAG_AND_VECTOR.md) | When/why RAG; pgvector vs Atlas vs Qdrant |
| [docs/MVP_ROADMAP.md](docs/MVP_ROADMAP.md) | 2–3 week build plan |
| [docs/OPEN_DECISIONS.md](docs/OPEN_DECISIONS.md) | Remaining choices |
| [docs/AUTH_GOOGLE.md](docs/AUTH_GOOGLE.md) | Google OAuth local setup (ports 2000 / 7000) |
| [docs/RUN_LOCAL.md](docs/RUN_LOCAL.md) | How to run API + web locally |

---

## Run locally

See [docs/RUN_LOCAL.md](docs/RUN_LOCAL.md).

- API: `http://localhost:7000/docs`
- Web: `http://localhost:2000`

```bash
# API
cd apps/api && py -3 -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 7000

# Web (other terminal)
cd apps/web && npm install && npm run dev
```

Do **not** start with a fancy RAG stack — structured context + verification is the product moat.
