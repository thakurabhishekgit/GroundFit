# Stack decisions

## Frozen for v1

| Layer | Choice | Why |
|-------|--------|-----|
| Frontend | React + TypeScript + Vite | Familiar; deploys cleanly on Vercel |
| Backend | FastAPI (Python) | Easiest OpenAI + structured JSON pipelines |
| DB | **PostgreSQL on Neon (free)** | Relational skill graph, ACID, one place for data |
| Vectors | **pgvector on Neon** (phase 1.5) | Free with same DB; enough for 10–15 users |
| Auth | **Google OAuth** | Fast, no password UX |
| LLM | **OpenAI** | Structured outputs / JSON schema |
| Web host | **Vercel** (Hobby) | Free static/SPA or Next later |
| API host | **Render** (Free web service) | Free FastAPI; cold starts acceptable |
| Files | DB text for LaTeX first | S3/R2 later if needed |

---

## “Completely free” — honest breakdown

| Cost | Free? | Notes |
|------|-------|--------|
| Vercel Hobby | Yes | Bandwidth limits; fine for friends |
| Render Free | Yes | Spins down after idle (~cold start 30–60s) |
| Neon Free | Yes | ~0.5 GB storage, compute hours/month — enough for 15 users |
| Google OAuth | Yes | Google Cloud project free quotas |
| **OpenAI API** | **No** | Pay per token. Hosting free ≠ LLM free |
| Domain | Optional | Use `*.vercel.app` + `*.onrender.com` |

**If you need $0 LLM too:** swap later to Gemini free tier / Groq free models — product design stays the same. v1 assumes OpenAI and a small personal API budget.

---

## MongoDB Atlas vs PostgreSQL

You already have Atlas free (M0). Does it do vectors like pgvector?

| | Neon Postgres + pgvector | MongoDB Atlas M0 |
|--|--------------------------|------------------|
| App data | Excellent for users, joins, skill graph | Fine document store |
| Vector search | **pgvector** extension | **Atlas Vector Search** yes on free tier |
| Free limits | ~0.5 GB + compute hours | 512 MB storage; max **3** search/vector indexes |
| Skill matching | SQL `JOIN` skill → evidence → project | Embeddings + `$lookup` or denormalize |
| Fit for GroundFit | **Better default** | OK if you prefer Mongo everywhere |

**Verdict:** Keep **Postgres (Neon)** as primary. Atlas Vector Search works for prototypes, but GroundFit’s moat is a **structured skill graph**, which is relational. Don’t add Mongo *and* Postgres unless you have a strong reason.

---

## Free vector DB options (for ≤15 users)

For 10–15 users with a few thousand narrative chunks max, **any** of these free tiers is overkill. Prefer order:

| Priority | Option | Free tier (approx) | When to use |
|----------|--------|--------------------|-------------|
| **1** | **Skip vectors** | $0 | MVP: SQL fetch by `skill_id` |
| **2** | **Neon + pgvector** | Included in Neon free | Best: one DB |
| **3** | **Qdrant Cloud free** | ~1 GB RAM / 4 GB disk | If you want dedicated vectors without Postgres extension fuss |
| **4** | **Mongo Atlas Vector Search** | M0 + up to 3 indexes | Only if primary DB is Mongo |
| **5** | Pinecone Starter | Free tier with vector caps | Extra vendor; avoid unless needed |
| **6** | Supabase free | Postgres + pgvector | Alternative to Neon |

**Recommendation:** MVP with **no vector DB**. Add **pgvector on Neon** when context packing gets expensive. Qdrant free only if pgvector setup is painful.

---

## Vercel + Render — what’s worth it?

| | Vercel | Render |
|--|--------|--------|
| Best for | Frontend (React/Vite SPA or Next) | Long-running FastAPI / workers |
| Free catch | Serverless functions short timeout | Free web service **sleeps**; cold start |
| GroundFit | Host `apps/web` | Host `apps/api` |
| OpenAI calls | Prefer **not** from Vercel serverless for long aligns | Better on Render (or async job + poll) |

**Pattern:**

```
Browser → Vercel (UI) → Render (API + OpenAI) → Neon (data)
```

Alternatives if Render free is too sleepy:

- Fly.io free allowance
- Railway trial credits (not forever free)
- Cloudflare Workers + separate Python host (more glue)

---

## Auth implementation options

| Option | Notes |
|--------|--------|
| **Auth.js + Google** on web, API trusts session/JWT | Clean for React |
| **FastAPI** exchanges Google ID token → own JWT | Simple SPA |
| Firebase Auth Google | Free; another vendor |
| Clerk Google | Free tier MAU limits; fastest UI |

**Pick:** Google via Auth.js or FastAPI Google token verify — zero extra SaaS if possible.

---

## Why FastAPI over Nest for this project

- OpenAI Python SDK + pydantic structured outputs is frictionless.
- Alignment pipeline is sequential Python-friendly.
- Nest is fine if you want one TS monorepo; not required for free deploy story.
