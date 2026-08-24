# ADR-0006: Tiered memory store (edge LanceDB + plant PG+AGE)

## Status
**Accepted** — 2026-08-24  
**Paperclip:** ASP-428 (accept) · ASP-426 Weekly Architecture Review · ASP-361 (draft)  
**Linear:** BEL-154 (Shared Local Memory & Conversation Caching)  
**SoR:** `docs/sor/MASTER_SPEC.md` §3.1 · `docs/architecture/MEMORY_LAYER.md`  

Architect confirmation (ASP-426 D1): tiered memory SoR is binding. T1 (SQLite + optional LanceDB) remains the agent-facing default; T2 (PostgreSQL + pgvector + Apache AGE) is the optional site/plant plane. **No PostgreSQL install** is required under fiscal freeze.

## Context

Two authoritative sources currently disagree on the **physical** memory SoR:

| Source | Stance |
|--------|--------|
| **Master Spec v4.0 §3.1** | Primary knowledge store = **PostgreSQL 16** polyglot: **pgvector** (semantic/RAG), **Apache AGE** (property graph / causal), TimescaleDB (telemetry); Redis hot session; MinIO large/WORM artifacts |
| **BEL-154 / MEMORY_LAYER.md (implemented)** | Local-first **SQLite FTS5 + optional LanceDB `VectorStore`** (and FAISS notes in the design doc); ingest JSONL → promotion → `MemoryManager` / MCP / `aspen_memory` client — no PostgreSQL required |
| **Live code** | `services/memory.py` and `src/python/services/memory.py` use SQLite + optional LanceDB; graceful degrade when LanceDB missing |

Fiscal freeze and manufacturing constraints forbid installing/operating plant PostgreSQL “because the master spec says so” before there is a clear promote path, offline story, and edge resource budget.

We need a **tiered** SoR that:

1. Keeps **local-first / offline / air-gapped** agent loops working today (BEL-154 path).
2. Preserves Master Spec §3.1 as the **enterprise / plant / multi-node** knowledge plane — not abandoned.
3. Recommends **edge local LanceDB (+ SQLite facts)** with an **optional promote** path into PG+AGE+pgvector when a node or site is ready.
4. Stays plan/ADR-only under freeze — **no PG install required** to accept this decision.

## Decision

### Tier model

```
┌──────────────────────────────────────────────────────────────────┐
│ T0  Working / session                                              │
│     Hermes/OpenCode/Aider/Paperclip session context, Redis (opt)   │
└───────────────────────────────┬────────────────────────────────────┘
                                │ ingest (JSONL, hooks)
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│ T1  Edge local memory  ★ DEFAULT runtime SoR (today)               │
│     • facts: SQLite (+ FTS) via MemoryManager / MEMORY_LAYER       │
│     • vectors: optional LanceDB VectorStore (BEL-153/154)          │
│     • graph lite: typed triples in SQLite/Lance metadata (kg_*)    │
│     • layout: ~/.aspen/memory/ (ingest, facts, vectors)            │
│     Offline-capable · zero server · fiscal-freeze safe             │
└───────────────────────────────┬────────────────────────────────────┘
                                │ promote (optional, gated)
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│ T2  Site / plant knowledge plane  ★ Master Spec §3.1 target        │
│     PostgreSQL 16 + pgvector + Apache AGE (+ Timescale sensors)    │
│     Multi-node query, durable audit, cross-fleet causal graph      │
│     Deploy only when site ops budget + schema migration land       │
└───────────────────────────────┬────────────────────────────────────┘
                                │ archive / large blobs
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│ T3  Object / WORM                                                  │
│     MinIO (or local object dir) — raw transcripts, attachments     │
│     Content-addressed; DB holds pointers + metadata only           │
└──────────────────────────────────────────────────────────────────┘
```

### Rules

1. **T1 is the agent-facing default.** All ingestion hooks, promotion pipeline, MCP (`aspen-memory-mcp`), and `aspen_memory.MemoryClient` continue to target local SQLite + optional LanceDB. Agents must not require PostgreSQL for heartbeats, code sessions, or dark-factory edge loops.
2. **T2 is the multi-node / enterprise SoR**, not a rewrite of T1. Master Spec §3.1 “Primary store: PostgreSQL…” is interpreted as **primary for site-level knowledge federation and Sentinel-grade audit**, not as “delete LanceDB.”
3. **Promote path (T1 → T2) is optional and one-way by default.**  
   - Trigger: explicit site enablement (`ASPEN_MEMORY_PROMOTE=1` or site profile), not every local fact.  
   - Payload: promoted facts (confidence ≥ site threshold, default ≥ local promote threshold), embeddings (or re-embed with site model), and high-confidence graph triples → AGE.  
   - Idempotent upserts by `fact_id` (content hash).  
   - Failures at T2 never block T1 write or agent completion (failure isolation per MEMORY_LAYER).
4. **Pull path (T2 → T1) is optional cache.** Edge nodes may **pull** a filtered projection (tags/project/plant ACL) into local LanceDB/SQLite for offline work. Pull is cache; T1 remains authoritative while offline. On reconnect, conflict policy = **last-writer-wins on `updated_at` + audit append**, with human review for `type=decision` conflicts above threshold.
5. **LanceDB stays edge-native.** Do not run LanceDB as the multi-site shared server. Do not require a LanceDB cluster. If ANN must live in T2, use **pgvector**; LanceDB remains the embedded edge index.
6. **Apache AGE owns durable property-graph semantics at T2.** T1 may keep lightweight subject/predicate/object rows for `kg_store` / `kg_query` tools; those are a **projection**, not a second enterprise graph product (Neo4j remains rejected per Master Spec §5).
7. **Redis remains hot session only** (T0), not fact SoR.
8. **No PostgreSQL install is required** to accept this ADR or to keep shipping BEL-154 work under fiscal freeze.

### Responsibility split

| Concern | Home | Notes |
|---------|------|--------|
| Session notes / dual-brain MEMORY.md | Hermes profiles / `memory/<agent>/` | Not replaced by this ADR |
| Raw ingest JSONL | T1 `~/.aspen/memory/ingest/` | 90-day retention design |
| Promoted facts + FTS | T1 SQLite `MemoryManager` | BEL-154 Components 2–3 |
| Local ANN / semantic | T1 LanceDB `VectorStore` | Optional dep; degrade to embedding scan |
| Site semantic RAG | T2 pgvector | When T2 enabled |
| Site causal / fleet graph | T2 Apache AGE | Preferred over Neo4j |
| Sensor time-series | T2 Timescale (or existing telemetry bus) | Out of BEL-154 fact path |
| Large raw artifacts | T3 MinIO / local object | Pointers in T1/T2 |
| Access API | `aspen_memory` + MCP | Backend selected by config: `local` (default) \| `local+promote` \| `site` |

### Configuration sketch (non-binding; implement later)

```yaml
# conceptual — not required for ADR acceptance
memory:
  tier_default: local          # local | site
  local:
    sqlite_path: ~/.aspen/memory/facts/facts.sqlite
    lancedb_uri: ~/.aspen/memory/vectors/lancedb
    require_lancedb: false
  promote:
    enabled: false             # freeze default
    target: postgres://...     # only when T2 provisioned
    min_confidence: 0.85
    include_types: [decision, architecture, config, pattern]
  pull:
    enabled: false
    filter_tags: []            # plant ACL / project scope
```

### Non-goals

- Installing or operating PostgreSQL/AGE/pgvector in this heartbeat  
- Migrating all historical JSONL into PG in one shot  
- Replacing Paperclip/Hermes memory files with a remote DB  
- Choosing embedding model vendors beyond existing MiniLM / local defaults  
- Making AppFlowy the SoR (sync remains optional Component 5)

## Consequences

### Positive
- Reconciles BEL-154 implementation with Master Spec §3.1 without a rewrite  
- Edge/dark-factory nodes stay offline-capable and freeze-cheap  
- Clear promote gate for Phase B (“Polyglot PostgreSQL schema + AGE graph seed”)  
- Single mental model for agents: write local; promote is ops policy  

### Negative / costs
- Two physical stores until T2 is live → need idempotent IDs and promote metrics  
- Temporary dual graph representations (lite triples vs AGE)  
- Docs must stop saying “LanceDB is the only memory DB” **or** “PG is required on day one”  

### Follow-ups (not in this ADR’s acceptance)
1. Schema sketch: `facts`, `fact_sources`, `embeddings`, AGE labels for `Decision` / `Config` / `Ref` (child issue when freeze allows ops work).  
2. `MemoryClient` backend interface: `LocalMemoryBackend` vs `PromoteMemoryBackend`.  
3. Update `MEMORY_LAYER.md` status blurb to point at this ADR (tier diagram).  
4. Master Spec §3.1 one-line cross-link: “edge default T1 per ADR-0006; PG is site plane.”  
5. Defer actual PG install to Phase B / unblocked infra ticket.

## Alternatives rejected

| Alternative | Why rejected |
|-------------|--------------|
| **PG+AGE+pgvector only immediately** | Violates local-first, offline, and fiscal freeze; blocks current agent mesh |
| **LanceDB / SQLite only forever** | Contradicts Master Spec enterprise knowledge plane; weak multi-node causal graph & audit story |
| **Neo4j or Milvus/Weaviate as primary** | Already rejected in Master Spec §5 (ops surface sprawl) |
| **FAISS files as long-term edge SoR without LanceDB option** | LanceDB already integrated and degrades cleanly; FAISS remains an implementation detail inside BEL-153 notes |
| **Every edge writes directly to central PG** | Breaks air-gap, e-stop isolation, and edge store-and-forward norms (ADR-0002 offline edge) |

## References

- `docs/sor/MASTER_SPEC.md` §3.1 Data & Memory; §5 Knowledge row  
- `docs/architecture/MEMORY_LAYER.md` — BEL-154 components 1–4 (implemented)  
- `services/memory.py` — `MemoryManager` + optional `VectorStore` (LanceDB)  
- `docs/SYSTEM_GUIDE.md` — “Why LanceDB for memory?”  
- ADR-0002 — offline edge store-and-forward (same isolation principle)  
- ADR-0005 — LangGraph plugin may consume memory via bus/MCP; does not own storage  

## Decision log

| Date | Event |
|------|--------|
| 2026-08-23 | Drafted under ASP-361 / ASP-166; status **Proposed** pending architecture review acceptance |
| 2026-08-24 | **Accepted** via ASP-428 (follow-up to ASP-426 weekly architecture review D1). No PG/T2 runtime install. |
