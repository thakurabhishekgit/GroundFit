# Deployment (free path for ~10–15 users)

## Target topology

```
┌────────────────┐      ┌─────────────────┐      ┌──────────────┐
│ Vercel         │      │ Render          │      │ Neon         │
│ apps/web       │─────▶│ apps/api        │─────▶│ Postgres     │
│ React SPA      │      │ FastAPI         │      │ (+ pgvector) │
└────────────────┘      └────────┬────────┘      └──────────────┘
                                 │
                                 ▼
                          ┌──────────────┐
                          │ OpenAI API   │
                          │ (paid usage) │
                          └──────────────┘
```

Google OAuth: Google Cloud Console OAuth client (Web) with authorized origins = Vercel URL; redirect URIs as needed.

---

## What Vercel is good for

- Static / SPA frontend (Vite build → `dist`)
- Preview deploys per branch
- Free Hobby: enough for friends sharing one app URL
- **Not ideal** as the only place for multi-minute OpenAI alignment (timeouts)

**Deploy:** connect GitHub repo → root `apps/web` → build `npm run build` → output `dist`.

Env (public only):

```env
VITE_API_URL=https://groundfit-api.onrender.com
VITE_GOOGLE_CLIENT_ID=...
```

---

## What Render is good for

- Host FastAPI 24/7-ish on free tier
- **Catch:** free instances **spin down** after ~15 min idle → first request cold (~30–60s)
- For 10–15 friends who use it occasionally, cold starts are acceptable
- Put `OPENAI_API_KEY`, `DATABASE_URL`, `GOOGLE_CLIENT_ID` in Render secrets

### Step-by-step (manual Web Service)

1. Push latest `apps/api` to GitHub (`thakurabhishekgit/GroundFit`).
2. [render.com](https://render.com) → **New → Web Service** → connect the repo.
3. Settings:
   - **Name:** `groundfit-api`
   - **Root Directory:** `apps/api`
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Health Check Path:** `/health`
4. **Environment** (Environment tab):

| Key | Value |
|-----|--------|
| `DATABASE_URL` | Neon connection string (`postgresql://…?sslmode=require`) — API normalizes to asyncpg |
| `OPENAI_API_KEY` | your OpenAI key |
| `OPENAI_CHAT_MODEL` | e.g. `gpt-4o-mini` or your luna model |
| `GOOGLE_CLIENT_ID` | same Web client ID as frontend |
| `GOOGLE_CLIENT_SECRET` | from Google Cloud (optional for GIS token verify) |
| `JWT_SECRET` | long random string |
| `CORS_ORIGINS` | `https://YOUR-APP.vercel.app,http://localhost:2000` |
| `FRONTEND_URL` | `https://YOUR-APP.vercel.app` |
| `PYTHON_VERSION` | `3.12.8` (optional but recommended) |

5. **Create Web Service** → wait for deploy → open `https://groundfit-api.onrender.com/health` (should return OK).
6. Wire frontend: Vercel env `VITE_API_URL=https://groundfit-api.onrender.com` → Redeploy web.
7. Google Cloud → OAuth client → Authorized JavaScript origins: add Vercel URL (keep localhost).

### Or Blueprint

Repo includes `render.yaml`. Render → **New → Blueprint** → select repo → fill the `sync: false` secrets when prompted.

**Deploy:** Web Service → Docker or native Python → `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

Health check: `GET /health`

If cold starts annoy: upgrade Render paid, or move API to Fly.io / always-on cheap VPS.

---

## Neon Postgres

1. Create free project
2. Copy connection string → Render `DATABASE_URL`
3. Enable `CREATE EXTENSION vector;` when adding RAG
4. Watch free storage (~0.5 GB) and compute hours — 15 users + resumes/context is fine if you don’t store huge PDFs as blobs

---

## Environment checklist

| Variable | Where | Secret? |
|----------|-------|---------|
| `DATABASE_URL` | Render | Yes |
| `OPENAI_API_KEY` | Render | Yes |
| `GOOGLE_CLIENT_ID` | Render + Vercel | Public-ish (restrict by origin) |
| `GOOGLE_CLIENT_SECRET` | Render only (if code flow) | Yes |
| `CORS_ORIGINS` | Render | No — set to Vercel URL |
| `VITE_API_URL` | Vercel | No |

---

## Cost expectations (friends scale)

| Item | Est. |
|------|------|
| Hosting (Vercel + Render + Neon) | **$0** |
| OpenAI | **$1–20/month** depending on align frequency & model (use `gpt-4o-mini` for extract/verify; stronger model only for rewrite if needed) |
| Domain | $0–12/year optional |

---

## GitHub Actions → Vercel (frontend)

Workflow: `.github/workflows/deploy-web-vercel.yml` deploys `apps/web` on push to `main`.

1. Create a Vercel project linked to this repo, **Root Directory** = `apps/web`
2. In Vercel project settings, set env: `VITE_API_URL`, `VITE_GOOGLE_CLIENT_ID`
3. Copy from Vercel → Project Settings → General:
   - Org ID → GitHub secret `VERCEL_ORG_ID`
   - Project ID → GitHub secret `VERCEL_PROJECT_ID_WEB`
4. Create a Vercel token → GitHub secret `VERCEL_TOKEN`
5. Push to `main` (or run workflow manually)

---

## Can both frontend and backend live on Vercel?

| Piece | On Vercel? | Notes |
|-------|------------|--------|
| **Frontend** (`apps/web`) | **Yes — recommended** | Vite SPA; same or separate Vercel project |
| **API** (`apps/api` FastAPI) | **Possible, not ideal** | Runs as serverless; Hobby ~10s / Pro ~60s request limits. Align does several OpenAI calls and often needs longer. Cold starts + no always-on worker. |
| **Postgres** | **No** | Keep **Neon** (you already have a URL) |

**Recommended (what we document):**

```
Vercel (web)  →  Render / Railway / Fly (FastAPI)  →  Neon
```

**Two Vercel projects** is fine for web + a thin API only if you accept timeout risk, or split align into async jobs (more work).

**Same Vercel project for both:** possible with monorepo + serverless Python under `/api`, but fighting the platform for this FastAPI + long LLM align flow — skip for now.

---

## Operational tips

- Cap `raw_text` and `jd_text` lengths in API.
- Rate-limit align endpoints per user.
- Prefer `gpt-4o-mini` (or current cheap structured model) for extract + verify.
- Log token usage per `AlignmentRun` for cost visibility.
- Render free: add a cheap cron ping `/health` only if you accept waking the box (still free but burns spin-up).

---

## Alternative free-ish maps

| Goal | Swap |
|------|------|
| Prefer Mongo you already have | Atlas M0 primary + Atlas Vector Search; skip Neon |
| One platform for web+api | Railway credits (not forever free) |
| Stronger free vectors | Qdrant Cloud free + Neon for relational |
| $0 LLM experiments | Gemini / Groq free tiers — keep same orchestrator interface |
