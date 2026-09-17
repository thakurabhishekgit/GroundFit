# Open decisions

Frozen items are in [STACK.md](STACK.md) and the root README. Remaining choices:

| # | Question | Options | Lean |
|---|----------|---------|------|
| 1 | PDF upload in v1? | LaTeX-only vs PDF parse | **LaTeX-only** — PDF parsing is hard and noisy |
| 2 | Auth library | Auth.js vs FastAPI Google token vs Clerk | Auth.js or FastAPI token — avoid extra SaaS unless speed matters |
| 3 | OpenAI model mix | mini everywhere vs mini extract + stronger rewrite | Start **mini** for all; upgrade rewrite if quality weak |
| 4 | Mongo later? | Keep Neon only vs dual-write Atlas | **Neon only** unless you already depend on Atlas elsewhere |
| 5 | Vectors timing | Week 3 vs when prompts break | **When prompts break** — not calendar-driven |
| 6 | Render cold starts | Accept vs paid always-on | Accept for friends; ping health only if needed |
| 7 | Monorepo tool | npm workspaces vs pnpm vs separate folders | Simple folders first; pnpm later if shared packages grow |

Update this file when a decision freezes.
