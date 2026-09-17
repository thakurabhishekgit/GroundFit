# Run locally

## Prerequisites
- Python 3.11+
- Node 20+
- Postgres 17 local with database `groundfit`
- Google OAuth Web client (origins: `http://localhost:2000`)
- OpenAI API key + a **real OpenAI model id** (e.g. `gpt-4o-mini`). Values like `gpt-5.6-luna` are not OpenAI API model names.

## Env
Edit repo-root `.env`:
- `DATABASE_URL=postgresql://postgres:<password>@localhost:5432/groundfit`
- Google + OpenAI keys (already sketched)
- Ports: API `7000`, web `2000`

## API
```bash
cd apps/api
python -m venv .venv
# Windows:
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 7000
```
Docs: http://localhost:7000/docs

## Web
```bash
cd apps/web
npm install
npm run dev
```
App: http://localhost:2000
