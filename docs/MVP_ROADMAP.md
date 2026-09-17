# MVP roadmap (2–3 weeks)

## Week 1 — Foundation

- [ ] Scaffold `apps/web` (Vite React TS) + `apps/api` (FastAPI)
- [ ] Neon Postgres + migrations for User, ExperienceContext, Skill, SkillEvidence, Role, Project
- [ ] Google OAuth login (web → API verify)
- [ ] Context paste UI + `extract` endpoint (OpenAI → draft graph)
- [ ] Review UI: accept/edit skills & evidence → confirm
- [ ] LaTeX upload/store (`Resume`)

## Week 2 — Align core

- [ ] JD paste → `extract_jd_skills`
- [ ] Deterministic match against skill graph
- [ ] Rewrite **Experience** + **Skills** sections
- [ ] Verifier pass + warnings JSON
- [ ] Override confirm UX + changelog
- [ ] Deploy: Vercel (web) + Render (api) + Neon

## Week 3 — Polish

- [ ] Projects + Summary alignment
- [ ] Export LaTeX download
- [ ] Optional PDF compile worker (skip if hard)
- [ ] Eval metrics on AlignmentRun (coverage, hallucination, evidence rate)
- [ ] Add pgvector **only if** prompt size hurts

## Explicitly skip (MVP)

- Browser extension
- LinkedIn / GitHub scrape
- Multi-language resumes
- Guaranteed ATS score product claims
- Fancy dedicated vector DB day one

---

## Definition of done (friends usable)

1. Friend signs in with Google
2. Pastes experience once, confirms skill graph
3. Pastes JD + LaTeX
4. Gets aligned LaTeX in Strict mode without invented skills
5. Sees warning + can override for missing JD keywords
