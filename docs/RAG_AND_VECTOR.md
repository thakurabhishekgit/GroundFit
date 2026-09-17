# RAG and vector strategy

## Short answer

**Hybrid: structured skill graph + selective context packing. RAG is optional.**

For ≤15 users, start **without** a vector DB. Match skills in SQL; pack the best evidence rows into the prompt. Add **pgvector on Neon** only when narratives get long.

---

## Why not RAG-only

| Approach | Pros | Cons |
|----------|------|------|
| Dump full context every time | Simple, accurate for small profiles | Breaks when context grows |
| Pure embedding RAG | Scales | Misses “I used Redis for X”; weak skill inventory |
| **Hybrid (recommended)** | Precise skill match + narrative proof | Slightly more engineering |

---

## Recommended pipeline

1. **Structured Skill Graph**  
   `skill → [{project/role, usage_summary, metrics, confidence}]`  
   Built on onboarding via LLM extraction + user confirm.

2. **JD → Skill Gap Analysis**  
   Extract required skills → intersect graph → Matched / Partial / Missing.

3. **Evidence retrieval**  
   For matched skills, pull best 1–3 `SkillEvidence` rows (+ project metadata) via SQL.

4. **Generation**  
   Rewrite LaTeX sections with original section + evidence; no skill without evidence unless override.

5. **Verifier pass**  
   Flag tech tokens not in graph.

---

## When to turn on vectors

Enable embeddings when **any** of:

- Experience context regularly exceeds ~30–50k tokens in prompts
- Many projects / long narratives per user
- Evidence selection by keyword fails (synonyms, paraphrase)

**Embed:** experience narratives + project summaries — **not** the JD alone.  
JD is short → extract skills with LLM → query graph / vectors by skill metadata.

Example filter: `user_id = ? AND skill = 'redis'` then cosine top-k.

---

## Free vector options compared (10–15 users)

| Option | Free? | Like pgvector? | Verdict for GroundFit |
|--------|-------|----------------|------------------------|
| **None (SQL only)** | Yes | N/A | **MVP default** |
| **Neon + pgvector** | Yes (Neon free) | Yes — it *is* pgvector | **Best phase 1.5** |
| **MongoDB Atlas Vector Search** | Yes on M0 (≤3 indexes, 512 MB) | Yes, different API (`$vectorSearch`) | Use only if Mongo is primary DB |
| **Qdrant Cloud free** | Yes (~1 GB RAM / 4 GB disk) | Dedicated vector DB | Good optional add-on |
| **Pinecone free** | Limited free starter | Dedicated | Extra vendor; skip unless needed |
| **Supabase + pgvector** | Yes free tier | Yes | Neon alternative |

### MongoDB question (direct)

Yes — **MongoDB Atlas provides vector search** on the free M0 cluster (Atlas Vector Search). Limits: small storage, shared resources, max **3** search/vector indexes. Fine for a prototype; not a reason to abandon Postgres for this product’s skill graph.

---

## Embedding model

- OpenAI `text-embedding-3-small` (cheap) unless you standardize elsewhere
- Store dimension consistently (e.g. 1536)
- Re-embed on evidence edit

---

## Product moat reminder

Vectors are infrastructure. The moat is:

1. User-confirmed skill graph  
2. Evidence-linked rewrites  
3. Verify + warning UX  

Do not start build with RAG.
