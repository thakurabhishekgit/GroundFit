# GroundFit Skill Graph — Abhishek (Experience + Projects)

Paste this into **Context** as your experience write-up, then confirm skills.
Sources: Newmark internship bullets you provided, Desktop repos under `C:\Users\AS162723\Desktop`, and GitHub [Wcontent](https://github.com/thakurabhishekgit/Wcontent) / [Knowable.AI](https://github.com/thakurabhishekgit/Knowable.AI).

---

## EXPERIENCE — Newmark (Software Engineer Intern / IT Associate – Trainee)

**Role:** Owned and shipped internal tools for Admin/Finance and IT ops at Hyderabad Newmark. Primary product: **Ticket360** (AI-powered helpdesk). Also contributed across Desktop codebases: FreshDesk-Agent, EHTS / Backend-Sp, ADO-Analytics, Atlas-Backend, IRCM / IRCM-APP, NMRK-Goals, helpdesk-ui-mockups.

### Side project: Ticket360 (product under Experience — NOT a resume Projects entry)

- Designed and owned Ticket360 end-to-end (requirements → deployment) for Admin and Finance.
- Automated ~70% of repetitive ticket handling/classification via AI routing, duplicate detection, role-based SLA across lifecycle, queues, incidents, and RBAC.
- Stack on product: React SPA, Java / Spring Boot, Microsoft SQL Server.
- Deployed on Azure App Service via Azure DevOps CI/CD; Azure Portal for ops, monitoring, multi-env config.

### Side project: Freshdesk AI agent + RAG (Desktop: `FreshDesk-Agent`)

- Configured Freshdesk RAG: embed knowledge-base PDFs into Azure AI Search (index + vector retrieval) for grounded classification, assignment, and answers (~40% IT agent effort cut).
- Integrated MCP server for tool-based auto-resolution (e.g. account unlock) with confidence-gated Freshdesk writeback (~15–20% of repetitive tickets).
- Used Redis to cache Ticket360 / agent API reads and persist processed-ticket state so polling/webhooks skip already classified tickets.
- Agent stack: Python, FastAPI, OpenAI, Redis, SQLAlchemy/pyodbc → SQL Server, MCP, OpenTelemetry → Azure Monitor, Azure AI Search + Blob, Bicep IaC.
- React + MUI dashboard for agent visibility (MSAL-branded).

### Side project: EHTS enterprise helpdesk (Desktop: `EHTS`, Spring mirror `Backend-Sp`)

- Enterprise helpdesk domain: tickets, queues, SLA clocks, incidents, KB, admin, AI prompt hooks.
- .NET: ASP.NET Core Clean Architecture, EF Core, SQL Server, JWT, Serilog, SignalR; React 19 + Vite + Tailwind + TanStack Query.
- Spring Boot mirror (`Backend-Sp`): Java 21, Spring Web/Data JPA/Security/WebSocket, PostgreSQL, JWT — same JSON contracts as .NET for the React SPA (~242 Java files).

### Side project: ADO / Cursor analytics (Desktop: `ADO-Analytics`, `Atlas-Backend`)

- ADO-Analytics: Node/Express + React/TS dashboard merging Cursor usage with Azure DevOps velocity; Azure MSAL; mssql; Azure Web Apps / Blob.
- Atlas-Backend: ASP.NET Core Clean Architecture + EF Core + SQL Server; syncs overview API into sectioned analytics for React lazy-load dashboard.

### Side project: IRCM commercial RE platform (Desktop: `IRCM`, `IRCM-APP`)

- Full-stack property/lease platform: Admin/Agent/Tenant RBAC dashboards.
- ASP.NET Core + EF Core + SQL Server + JWT; React + MUI; OpenAI / Semantic Kernel insights; Cloudinary uploads; Azure Pipelines.

### Side project: NMRK-Goals (Desktop: `NMRK-Goals`)

- Goals/OKR platform: multi-project ASP.NET Core 8 solution, Azure AD + Graph, Azure Functions user sync, React + MSAL + Teams JS; JMeter load tests; Azure Pipelines.

### Side project: Internal apps / dashboards (your bullets + Desktop)

- Express.js + TypeScript and C# / ASP.NET Core internal apps.
- Optimized cloud-cost leadership dashboard APIs from 3–4s to &lt;300ms.
- Microservices, Python FastAPI, LLM integration, React + TypeScript across helpdesk and analytics workstreams.
- UI mockups (`helpdesk-ui-mockups`): Python/Pillow Newmark-branded helpdesk flows.

### Experience skill evidence (where / how)

| Skill | Where used | How used |
|-------|------------|----------|
| Java / Spring Boot | Ticket360, Backend-Sp | Microservices/APIs for helpdesk lifecycle, RBAC, SLA |
| React / TypeScript | Ticket360 SPA, Freshdesk UI, EHTS web, ADO/Atlas/IRCM | SPAs, dashboards, MSAL-auth apps |
| Microsoft SQL Server | Ticket360, Freshdesk agent metrics, Atlas, EHTS, IRCM, Goals | Primary OLTP store for tickets/analytics |
| PostgreSQL | Backend-Sp (EHTS Spring) | JPA-backed helpdesk API |
| Redis | Freshdesk/Ticket360 agent | Cache API reads; persist processed-ticket IDs for idempotent polling/webhooks |
| Python / FastAPI | FreshDesk-Agent | LLM agent service, RAG tooling, MCP orchestration |
| RAG / Azure AI Search | FreshDesk-Agent | PDF + Solutions KB embeddings → grounded triage |
| MCP | FreshDesk-Agent | Tool calling (account unlock) with confidence-gated writeback |
| OpenAI / LLMs | Freshdesk, IRCM, EHTS prompts | Classification, resolution steps, RE insights |
| Azure App Service / DevOps / Portal | Ticket360, ADO, Goals | Deploy, CI/CD pipelines, multi-env ops |
| ASP.NET Core / EF Core / C# | EHTS, Atlas, IRCM, Goals, EcomAPI | Clean Architecture enterprise APIs |
| Express.js | Internal Newmark apps | Node APIs for internal tools |
| RBAC / SLA / queues | Ticket360, EHTS | Role-based access, SLA clocks, department queues |
| SignalR / WebSocket | EHTS / Backend-Sp | Realtime agent/employee updates |
| Azure AD / MSAL | ADO-Analytics, Freshdesk UI, Goals, EHTS | Enterprise SSO |
| Azure Functions | NMRK-Goals | Timer sync AAD → DB |
| Bicep / OpenTelemetry | FreshDesk-Agent | IaC + Azure Monitor observability |
| Microservices | Ticket360 + Spring/EHTS split | Service boundaries, mirrored contracts |

---

## PERSONAL PROJECTS (resume Projects section only)

### Project: Wcontent — Creator Workflow Platform

**Links:** [GitHub](https://github.com/thakurabhishekgit/Wcontent) · Demo: https://wcontent-app-in.vercel.app  
**Repo layout:** `frontend/` (React), `backend/` (Spring Boot), `Backend - MicroServices/` (auth / user / opportunity + Eureka registry), `PythonML/`, `Wcontent-RAG/`

**What it does**
- Predict creator reach from YouTube-style stats (comments, likes, subscribers, etc.).
- AI comment summarization from a YouTube URL.
- Collaboration / sponsorship posting & applications with email-style activity notifications.
- Bridges small and larger creators for networking.

**Confirmed from repo**
- **React.js** frontend (Vite); live on Vercel.
- **Spring Boot** backend + **MongoDB**.
- **Microservices:** `auth-service`, `user-service`, `opportunity-service`, `service-registry` — Spring Boot 3.2, Java 17, Spring Security, Validation, **JWT (jjwt)**, **Spring Data MongoDB**, **Netflix Eureka** client, **OpenFeign**.
- **PythonML:** Flask + CORS API on port 5001; pandas / scikit-learn **GradientBoostingRegressor** models (views, likes, comments, shares, subscribers); StandardScaler + joblib `.pkl` artifacts; `/predict` endpoint.
- **Comment LLM:** Flask service calling **YouTube Data API** + **Gemini 1.5 Flash** for comment summarization (CORS to localhost:5173).
- **Wcontent-RAG:** LangChain + OpenAI Chat/Embeddings + **FAISS**; YouTube comments fetch; RAG content suggestion; LLM performance prediction pipeline.

**Skill evidence**

| Skill | Where | How |
|-------|-------|-----|
| Java / Spring Boot | backend + microservices | REST APIs for auth, users, collabs/opportunities |
| Microservices / Eureka / Feign | Backend - MicroServices | Service discovery + inter-service HTTP |
| Spring Security / JWT | auth-service | Stateless login/register |
| MongoDB | Spring Data Mongo | Creator/user/opportunity documents |
| React | frontend | Creator UI (predict, summary, collab) |
| Python / Flask | PythonML, SummaryComments | ML predict API + Gemini comment summary |
| scikit-learn / pandas | PythonML | Train & serve GBR reach models |
| YouTube Data API | SummaryComments, RAG | Fetch comment threads |
| Gemini LLM | SummaryComments | Comment insight summarization |
| LangChain / OpenAI / FAISS / RAG | Wcontent-RAG | Vector RAG for content ideas + predictions |
| Docker / Render / Vercel | resume + hosting | Deploy frontend/backend/ML pieces |
| Kafka (resume) | event-driven alerts (resume claim) | Prefer stating “event-driven email notifications”; confirm Kafka in runtime config before Align “must” |

---

### Project: Knowable.AI — AI-Powered Academic Assistant

**Links:** [GitHub](https://github.com/thakurabhishekgit/Knowable.AI) · Demo: https://knowable-ai.vercel.app/  
**Repo layout:** `Frontend/` (Next.js), `Backend/Knowable/` (Spring Boot), Redis notes, Docker/Render deploy

**What it does**
- Upload study docs (PDF/DOCX/PPTX) into workspaces.
- Chat with documents, generate flashcards & MCQ quizzes, analyze past papers, auto study guides.
- Turns passive PDF reading into active LLM-assisted study.

**Confirmed from repo / README**
- **Frontend:** Next.js 15 App Router, React, Tailwind, ShadCN UI, Genkit AI flows; Vercel.
- **Backend:** Spring Boot 3.5 / Java 17 — Web, Data JPA, Security, OAuth2 client, JWT (jjwt), **Redis** + cache, PostgreSQL, Lombok, springdoc OpenAPI.
- **Document AI:** Spring AI Tika document reader, Apache Tika parsers, PDFBox; Cloudinary uploads (sprint plan + dependency).
- **AI:** Google Gemini / Genkit on frontend; Spring AI BOM on backend; Redis for caching (RedisCommands.txt).
- **Deploy:** Frontend Vercel; Backend Docker on Render; Postgres on Render.
- Resume metrics: Gemini quizzes/flashcards in &lt;30s; Spring APIs ~1000+ req/day, &lt;200ms with Redis + JWT.

**Skill evidence**

| Skill | Where | How |
|-------|-------|-----|
| Java / Spring Boot | Backend/Knowable | REST academic APIs, auth, uploads |
| Spring Security / JWT / OAuth2 | pom + security starters | Stateless + social-capable auth |
| Spring Data JPA / PostgreSQL | Backend | Users, PDFs, workspace persistence |
| Redis / caching | starter-data-redis + RedisCommands | Latency cache for hot API paths |
| Apache Tika / PDFBox / Spring AI | document pipeline | Parse PDFs → text for LLM/RAG |
| Cloudinary | upload sprints | Store study document binaries |
| Next.js / React / Tailwind / ShadCN | Frontend | SaaS study UI |
| Genkit / Gemini | Frontend AI flows | Chat, quizzes, flashcards, guides |
| LangChain (resume) | RAG study pipeline | Chunk/retrieve/generate study aids |
| Docker / Render / Vercel | deploy | Containerized API + hosted SPA |
| OpenAPI / springdoc | Backend | API docs for clients |

---

## LEARNING / SIDE (Desktop — optional Context notes, not resume Projects)

- **product-management-api:** Express 5 + TypeScript + Prisma + PostgreSQL + Zod + JWT (users/products/cart).
- **EcomAPI:** ASP.NET Core + EF + SQL Server learning ecommerce scaffold.
- **TypeScript:** drills on unions, soft-delete entities, domain modeling.

---

## Flat skill list (confirm in GroundFit)

**Languages:** Java, Python, JavaScript, TypeScript, C#, SQL  
**Frontend:** React, Next.js, HTML, CSS, Tailwind, MUI, Vite  
**Backend:** Spring Boot, FastAPI, Flask, ASP.NET Core, Express.js, Microservices, JWT, RBAC  
**Data:** PostgreSQL, Microsoft SQL Server, MongoDB, Redis, Prisma, EF Core, JPA  
**AI/ML:** OpenAI, Gemini, LangChain, Genkit, RAG, Azure AI Search, FAISS, scikit-learn, MCP, Semantic Kernel  
**Cloud/DevOps:** Azure App Service, Azure DevOps CI/CD, Azure Portal, Azure AD/MSAL, Azure Functions, Azure Blob, Bicep, AWS (listed), Docker, Git, Vercel, Render, OpenTelemetry  
**Other:** YouTube Data API, Cloudinary, SignalR, Eureka, OpenFeign, JMeter  

---

## Paste-ready Context narrative (single block)

```
EXPERIENCE — Newmark (Software Engineer Intern / IT Associate – Trainee), Hyderabad

I designed and owned Ticket360, an AI-powered helpdesk for Admin and Finance — requirements to deployment — and automated ~70% of repetitive ticket handling/classification via AI routing, duplicate detection, and role-based SLA across lifecycle, queues, incidents, and RBAC (React SPA, Java/Spring Boot, Microsoft SQL Server).

I configured a Freshdesk RAG pipeline by embedding knowledge-base PDFs into Azure AI Search for grounded classification, assignment, and answers (~40% IT agent effort reduction). I integrated an MCP server for tool-based auto-resolution (e.g. account unlock) with confidence-gated Freshdesk writeback (~15–20% of repetitive tickets), and used Redis to cache Ticket360/agent API reads and persist processed-ticket state so polling/webhooks skip already classified tickets. The agent is Python FastAPI with OpenAI, Redis, SQL Server, OpenTelemetry to Azure Monitor, and Bicep IaC (Desktop: FreshDesk-Agent).

I deployed services on Azure App Service via Azure DevOps CI/CD and used Azure Portal for cloud ops, monitoring, and multi-environment configuration. I also worked on internal apps with Express.js, TypeScript, and C# / ASP.NET Core, and optimized APIs for a cloud-cost leadership dashboard from 3–4s to <300ms.

Across Newmark Desktop work I used microservices and Spring Boot (Backend-Sp mirroring EHTS), ASP.NET Core Clean Architecture (EHTS, Atlas-Backend, IRCM, NMRK-Goals), React + TypeScript dashboards (ADO-Analytics with Azure DevOps + Cursor metrics, MSAL), PostgreSQL, SQL Server, SignalR, Azure AD, Azure Functions, and LLM integrations.

PERSONAL PROJECT — Wcontent (https://github.com/thakurabhishekgit/Wcontent)
Full-stack creator platform (React + Spring Boot + MongoDB) for reach prediction, AI comment summarization, and collaboration/sponsorship flows. Microservices (auth, user, opportunity) with Eureka, OpenFeign, Spring Security, JWT. PythonML Flask API with scikit-learn GradientBoosting models for views/likes/comments/shares/subscribers. Gemini + YouTube Data API for comment summaries. LangChain + OpenAI embeddings + FAISS RAG for content ideas. Deployed with Docker / Render / Vercel.

PERSONAL PROJECT — Knowable.AI (https://github.com/thakurabhishekgit/Knowable.AI)
AI academic assistant: upload PDFs/DOCX/PPTX, chat with docs, flashcards, quizzes, study guides. Next.js 15 + Tailwind + ShadCN + Genkit/Gemini frontend (Vercel). Spring Boot 3 + Java 17 backend with JPA, PostgreSQL, Redis cache, JWT/OAuth2, Apache Tika/PDFBox/Spring AI document reading, Cloudinary uploads; Docker on Render. RAG-style study pipelines with low-latency Redis-backed APIs.
```
