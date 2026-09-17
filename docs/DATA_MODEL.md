# Data model (v1)

PostgreSQL on Neon. IDs: UUID preferred.

---

## Entities

```text
User
  id              UUID PK
  email           TEXT UNIQUE NOT NULL
  name            TEXT
  google_sub      TEXT UNIQUE NOT NULL
  created_at      TIMESTAMPTZ

ExperienceContext
  id              UUID PK
  user_id         UUID FK → User UNIQUE
  raw_text        TEXT NOT NULL
  updated_at      TIMESTAMPTZ

Skill
  id              UUID PK
  user_id         UUID FK → User
  name            TEXT NOT NULL          -- canonical: "redis"
  display_name    TEXT                  -- "Redis"
  category        TEXT                  -- lang|framework|db|cloud|ai|tool|concept
  proficiency     TEXT NULL             -- optional
  UNIQUE(user_id, name)

Role
  id              UUID PK
  user_id         UUID FK
  title           TEXT
  org             TEXT
  start_date      DATE NULL
  end_date        DATE NULL
  ownership       TEXT                  -- owned|contributed|led
  description     TEXT

Project
  id              UUID PK
  user_id         UUID FK
  name            TEXT
  problem         TEXT
  architecture    TEXT
  description     TEXT
  tech            TEXT[]                -- denormalized tags
  metrics_json    JSONB

SkillEvidence
  id              UUID PK
  skill_id        UUID FK → Skill
  source_type     TEXT                  -- role|project
  source_id       UUID                  -- Role.id or Project.id
  summary         TEXT NOT NULL         -- "Redis used to cache processed Freshdesk ticket IDs..."
  metrics_json    JSONB
  verified        BOOLEAN DEFAULT false -- user confirmed extraction

Resume
  id              UUID PK
  user_id         UUID FK
  title           TEXT
  latex_source    TEXT NOT NULL
  version         INT DEFAULT 1
  created_at      TIMESTAMPTZ

AlignmentRun
  id              UUID PK
  user_id         UUID FK
  resume_id       UUID FK → Resume
  jd_text         TEXT NOT NULL
  mode            TEXT                  -- strict|suggest|explore
  result_latex    TEXT
  changelog_json  JSONB
  warnings_json   JSONB
  coverage_score  FLOAT NULL
  status          TEXT                  -- pending|done|failed
  created_at      TIMESTAMPTZ
```

---

## Changelog item shape

```json
{
  "path": "experience.ticket360.bullet_2",
  "before": "...",
  "after": "...",
  "evidence_ids": ["uuid-1", "uuid-2"],
  "status": "verified"
}
```

`status`: `verified` | `override` | `rejected`

---

## Warning item shape

```json
{
  "token": "Apache Kafka",
  "reason": "not_in_context",
  "suggestions": ["Redis pub/sub", "Azure Service Bus"],
  "user_action": null
}
```

`user_action` after confirm: `add_anyway` | `use_suggestion` | `skip`

---

## Optional later: embeddings

```text
EvidenceEmbedding
  evidence_id   UUID FK → SkillEvidence
  embedding     vector(1536)   -- OpenAI text-embedding-3-small
  metadata      JSONB          -- { skill, project_id, user_id }
```

Index: IVFFlat / HNSW via pgvector. Always filter `user_id` in queries.

---

## Skill name normalization

Store canonical lowercase slug (`apache-kafka`, `redis`). Maintain alias map in code or table:

| alias | canonical |
|-------|-----------|
| k8s | kubernetes |
| js | javascript |
| ts | typescript |
| spring | spring-boot |

Matching JD skills should normalize before graph lookup.
