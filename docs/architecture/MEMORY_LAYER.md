# MEMORY_LAYER.md — Shared Local Memory & Conversation Caching Layer

**Linear:** BEL-154 (Shared Local Memory & Conversation Caching Layer)  
**Paperclip:** ABS-10 (Shared Local Memory & Conversation Caching Layer)  
**Company:** Absolution Studios (ABS) / Aspen OS Development Company (ASP)  
**Agents:** Proxy (Implementation), Ergo (Architecture), Romi (Design)  
**Date:** 2026-08-04  
**Status:** ✅ Implemented — Components 1–4 complete (ingest writer, promotion, unified store, access layer, MCP)

---

## Problem Statement

Close the gap between:
1. **Hermes per-agent memory** — isolated, session-scoped, not shared
2. **AppFlowy** — human-readable knowledge root (pages, databases)
3. **Semantic/vector layer (BEL-153)** — embeddings for semantic search

**Goal:** One unified local memory bank accessible by default to:
- Hermes roles (Ergo, Proxy, Romi, aspen, domain agents)
- OpenCode (code execution)
- Aider (code editing)
- Paperclip agents (all companies)

**Constraints:** Local-first, offline-capable, modular service principles.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    UNIFIED MEMORY LAYER                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  INGESTION   │──│  PROMOTION   │──│  UNIFIED     │          │
│  │  LAYER       │  │  PIPELINE    │  │  STORE       │          │
│  └──────────────┘  └──────────────┘  └──────┬───────┘          │
│         ▲                    ▲               │                  │
│         │                    │               ▼                  │
│  ┌──────┴──────┐       ┌─────┴─────┐  ┌──────────────┐        │
│  │ Hermes      │       │ Fact      │  │ ACCESS LAYER │        │
│  │ Sessions    │       │ Extraction│  │ (MCP + Lib)  │        │
│  │ Paperclip   │       │ Confidence│  │              │        │
│  │ Runs        │       │ Scoring   │  │ Hermes       │        │
│  │ OpenCode    │       └───────────┘  │ OpenCode     │        │
│  │ Aider       │                     │ Aider        │        │
│  │ AppFlowy    │                     │ Paperclip    │        │
│  └─────────────┘                     └──────┬───────┘        │
│                                             │                  │
│                                             ▼                  │
│                                    ┌──────────────┐           │
│                                    │ AppFlowy     │           │
│                                    │ SYNC         │           │
│                                    │ (Bidirect)   │           │
│                                    └──────────────┘           │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component 1: Ingestion Layer

### Sources

| Source | Hook Point | Format | Frequency |
|--------|------------|--------|-----------|
| Hermes sessions | `on_session_end` / `on_memory_save` | JSONL | Per session |
| Paperclip runs | `heartbeat` completion callback | JSON | Per run |
| OpenCode | `agents/opencode_memory.py` CLI (`on_task_complete`) | JSONL | Per task/session |
| Aider | `agents/aider_memory.py` CLI (`on_commit` / `on_edit` / `post_edit`) | JSONL | Per edit |
| AppFlowy | Webhook / poll | REST API | Configurable |

### Schema (JSONL)

```json
{
  "source": "hermes|paperclip|opencode|aider|appflowy",
  "source_id": "session-uuid|run-id|task-id|commit-sha|page-id",
  "timestamp": "2026-08-04T21:00:00Z",
  "agent": "ergo|proxy|romi|opencode|aider|human",
  "company": "asp|abs|absa|content",
  "project": "aspen-os|absolution-studios|gumroad|content",
  "content": "raw conversation / code / output / page content",
  "metadata": {
    "tools_used": ["terminal", "web_search", "paperclip"],
    "files_touched": ["path/to/file.py"],
    "linear_refs": ["BEL-153", "BEL-114"],
    "paperclip_refs": ["ABS-7", "ABS-9"]
  }
}
```

### Storage

- **Raw ingest:** `/home/tech/.aspen/memory/ingest/{source}/{date}.jsonl`
- **Rotation:** Daily files, gzip after 7 days
- **Retention:** 90 days raw, promoted facts permanent

---

## Component 2: Promotion Pipeline

### Fact Extraction

Run asynchronously on ingest files (cron every 15 min or on-demand).

**Extraction targets:**
- Decisions (architecture, tool choice, model routing)
- Patterns (code snippets, config templates, workflows)
- Configurations (env vars, CLI flags, service configs)
- Credentials references (NOT secrets — only paths/names)
- Architecture choices (ADR references, diagram links)
- Linear/Paperclip cross-references

### Confidence Scoring

| Factor | Weight |
|--------|--------|
| Explicit declaration ("Decision: ...") | 1.0 |
| Cross-referenced (Linear + Paperclip + code) | 0.9 |
| Repeated across sessions/runs | 0.8 |
| Agent-authored vs human-authored | 0.7/0.9 |
| Recency (last 30 days) | 0.6-1.0 |

**Threshold:** `confidence >= 0.7` → promote to unified store

### Output Schema (Promoted Facts)

```json
{
  "fact_id": "sha256(content)[:16]",
  "type": "decision|pattern|config|credential_ref|architecture|reference",
  "content": "normalized, deduplicated fact text",
  "confidence": 0.87,
  "sources": [
    {"source": "hermes", "source_id": "uuid", "timestamp": "..."},
    {"source": "paperclip", "source_id": "run-id", "timestamp": "..."}
  ],
  "tags": ["security", "ufw", "ssh", "hardening"],
  "linear_refs": ["BEL-114"],
  "paperclip_refs": ["ABS-9"],
  "created_at": "2026-08-04T21:00:00Z",
  "updated_at": "2026-08-04T21:00:00Z",
  "version": 1
}
```

---

## Component 3: Unified Store

### Physical Layout

```
/home/tech/.aspen/memory/
├── ingest/                    # Raw JSONL (90-day retention)
│   ├── hermes/
│   ├── paperclip/
│   ├── opencode/
│   ├── aider/
│   └── appflowy/
├── facts/                     # Promoted facts (permanent)
│   ├── facts.sqlite          # SQLite FTS5 + vector index
│   └── facts.jsonl           # Append-only log for audit
├── vectors/                   # Embeddings for BEL-153
│   ├── index.faiss           # FAISS HNSW index
│   └── metadata.jsonl        # fact_id → vector mapping
└── appflowy/                  # Bidirectional sync
    ├── pages/                # AppFlowy page exports
    └── sync_state.json       # Last sync timestamps
```

### SQLite Schema (facts.sqlite)

```sql
CREATE TABLE facts (
    fact_id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    content TEXT NOT NULL,
    confidence REAL NOT NULL,
    tags TEXT,           -- JSON array
    linear_refs TEXT,    -- JSON array
    paperclip_refs TEXT, -- JSON array
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    version INTEGER DEFAULT 1
);

-- FTS5 for full-text search
CREATE VIRTUAL TABLE facts_fts USING fts5(
    fact_id UNINDEXED,
    content,
    tags,
    tokenize='porter'
);

-- Triggers to keep FTS in sync
CREATE TRIGGER facts_ai AFTER INSERT ON facts BEGIN
    INSERT INTO facts_fts(fact_id, content, tags) 
    VALUES (new.fact_id, new.content, new.tags);
END;

CREATE TRIGGER facts_ad AFTER DELETE ON facts BEGIN
    DELETE FROM facts_fts WHERE fact_id = old.fact_id;
END;

CREATE TRIGGER facts_au AFTER UPDATE ON facts BEGIN
    UPDATE facts_fts SET content = new.content, tags = new.tags 
    WHERE fact_id = new.fact_id;
END;
```

### Vector Index (FAISS for BEL-153 integration)

- **Embedding model:** `sentence-transformers/all-MiniLM-L6-v2` (local, 384-dim, fast)
- **Index type:** HNSW (efConstruction=200, M=16) — balances speed/accuracy
- **Update strategy:** Incremental add on promotion; rebuild nightly
- **Query:** `k=10` nearest neighbors, filter by confidence >= 0.7

---

## Component 4: Access Layer

### 4.1 Python Library (`aspen_memory`)

```python
# pip install -e /home/tech/aspen-dev/repos/aspen-os/memory_pkg
from aspen_memory import MemoryClient

client = MemoryClient()

# Query
results = client.search("UFW hardening", k=5, min_confidence=0.7)

# Get by Linear/Paperclip ref
facts = client.get_by_linear("BEL-114")
facts = client.get_by_paperclip("ABS-9")

# Get by tags
facts = client.get_by_tags(["security", "ufw"])

# Add fact (for agents)
client.add_fact(
    type="decision",
    content="Use DeepSeek V4-Flash for all ABS agents",
    tags=["model-routing", "fiscal-freeze"],
    linear_refs=["BEL-154"],
    paperclip_refs=["ABS-10"],
    confidence=0.95
)
```

### 4.2 MCP Server (`aspen-memory-mcp`)

```bash
# Install
cd /home/tech/aspen-dev/repos/aspen-os/mcp/aspen-memory-mcp
pip install -e .

# Run
aspen-memory-mcp --db /home/tech/.aspen/memory/facts/facts.sqlite \
                 --vectors /home/tech/.aspen/memory/vectors
```

**Tools exposed:**
- `memory_search(query, k=5, min_confidence=0.7)`
- `memory_get_by_linear(linear_id)`
- `memory_get_by_paperclip(paperclip_id)`
- `memory_get_by_tags(tags)`
- `memory_add_fact(type, content, tags, linear_refs, paperclip_refs, confidence)`

### 4.3 Hermes Integration

In `hermes_agent/tools/memory_tool.py` or via skill:
- Inject `MemoryClient` into agent context
- Auto-promote on `memory_save` tool calls
- Pre-load relevant facts at session start (by project/tags)

### 4.4 OpenCode/Aider Integration

```bash
# OpenCode: via plugin or wrapper
opencode --plugin aspen-memory

# Aider: via post_edit hook / completion wrapper / one-off
#   (aider_memory.py is failure-isolated — safe as a hook: wraps with || true)
python3 agents/aider_memory.py --source-id <session> \
    --content "$(cat /tmp/last_edit_summary.txt)" --files <changed-files> || true
```

Both `agents/opencode_memory.py` and `agents/aider_memory.py` append BEL-154 raw
ingest records (`source="opencode"` / `source="aider"`) with files/tools/refs
metadata, content truncation, and full failure isolation.

### 4.5 Paperclip Integration

- Built-in skill: `paperclipai/bundled/paperclip-operations/memory-sync`
- Heartbeat callback: `on_run_complete → ingest → promote`
- Agent can call `memory_search` via `paperclip` skill

---

## Component 5: AppFlowy Bidirectional Sync

### Routing decision (ASP-79 / BEL-135) — 2026-08-23

**Decision: Defer** — no implementation task; no AppFlowy deploy; no `scripts/appflowy_sync.py` skeleton in this cycle.

| Option | Outcome |
|--------|---------|
| (1) Defer | **Selected.** Component stays design-only under fiscal freeze. |
| (2) Scoped v1 | Rejected for this cycle — pure skeleton without a live API still spends implementer budget and invents the first bidirectional-sync pattern without a consumer. Revisit when deploy is approved. |
| (3) Full deploy + sync | Rejected — BEL-135 and fiscal freeze bar always-on heavy apps (Agent Zero image ~12GB already); no revenue need for AppFlowy Cloud. |

**Unblock criteria (any one is enough to re-open routing):**

1. Human prioritizes AppFlowy deploy / lifts freeze for knowledge layer, **or**
2. Gumroad cash-flow verified and stack budget allows optional services, **or**
3. Architect re-routes to Scoped v1 explicitly (local transforms + `sync_state.json` + graceful no-op without `APPFLOWY_API_URL`).

**Still open when unblocked (do not invent in freeze):** target AppFlowy API surface (self-hosted Cloud REST vs client/folder), fact↔page schema, templates per fact type, conflict resolution.

**Refs:** Paperclip [ASP-79](/ASP/issues/ASP-79); plan `docs/plans/BEL-135-appflowy-knowledge-layer.md`; interim knowledge base remains markdown under `docs/` (+ Obsidian skill).

### AppFlowy → Memory

- **Trigger:** Page create/update/delete (webhook or poll)
- **Transform:** Page blocks → normalized facts
- **Dedupe:** Match by content hash + tags

### Memory → AppFlowy

- **Trigger:** High-confidence fact promoted (confidence >= 0.85)
- **Transform:** Fact → AppFlowy page/database row
- **Template:** Structured pages per fact type (decision, pattern, config)

### Sync State

```json
{
  "appflowy_last_sync": "2026-08-04T21:00:00Z",
  "memory_last_sync": "2026-08-04T21:00:00Z",
  "synced_fact_ids": ["abc123", "def456"],
  "pending_to_appflowy": ["ghi789"],
  "pending_to_memory": []
}
```

---

## Integration with BEL-153 (Semantic/Vector Layer)

| BEL-153 Provides | Memory Layer Consumes |
|------------------|----------------------|
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| FAISS index management | `vectors/index.faiss` |
| Semantic search API | `memory_search_semantic(query, k=10)` |
| Re-ranking | Applied to fact search results |

**Memory layer is the *source of truth* for facts; BEL-153 adds semantic search on top.**

---

## Local-First / Offline Guarantees

1. **No external dependencies** for core read/write — SQLite + FAISS local files
2. **Embedding model cached locally** — `~/.cache/huggingface/sentence-transformers/`
3. **All ingestion/promotion runs locally** — cron or systemd timer
4. **AppFlowy sync is optional** — works without AppFlowy running
5. **No telemetry/phoning home** — fully air-gapped capable

---

## Modular Service Principles Alignment

| Principle | Implementation |
|-----------|----------------|
| Single responsibility | Each component (ingest, promote, store, access, sync) is independent |
| Explicit contracts | JSON schemas for ingest/promoted facts; SQLite FTS5; FAISS index |
| Config over code | Paths, thresholds, retention via env/config |
| Observability | Structured logs, sync state, promotion metrics |
| Failure isolation | Ingestion failure ≠ promotion failure ≠ access failure |
| Upgradability | Schema versioning in SQLite; FAISS rebuild on model change |

---

## Implementation Status

| Component | Status | Location |
|-----------|--------|----------|
| Ingestion writer (raw JSONL) | ✅ Implemented | `scripts/memory_ingest.py` |
| Ingestion hooks (Hermes) | ✅ Implemented | `agents/agent_daemon.py` `ingest_memory_record()` |
| Ingestion hooks (OpenCode) | ✅ Implemented | `agents/opencode_memory.py` `ingest_opencode_record()` + CLI |
| Ingestion hooks (Paperclip) | ✅ Implemented | `agents/paperclip_memory.py` `ingest_paperclip_record()` + CLI |
| Ingestion hooks (Aider) | ✅ Implemented | `agents/aider_memory.py` `ingest_aider_record()` + CLI |
| Promotion pipeline | ✅ Implemented | `scripts/memory_promote.py` |
| Unified store (SQLite + FAISS) | ✅ Implemented | `services/memory.py` |
| Python library (`aspen_memory`) | ✅ Implemented | `memory_pkg/` |
| MCP server | ✅ Implemented | `mcp/aspen-memory-mcp/` |
| AppFlowy sync | ⏸ Deferred (fiscal freeze / ASP-79) | target `scripts/appflowy_sync.py` — not started; design above |
| BEL-153 vector integration | ✅ Implemented | `services/memory.py` + LanceDB `VectorStore` |

---

## Next Steps (Implementation)

1. **Extend `services/memory.py`** with SQLite + FAISS + promotion logic — done
2. **Create `memory_pkg/`** Python library with `MemoryClient` — done
3. **Build `aspen-memory-mcp`** MCP server — done
4. **Add ingestion hooks** to Hermes, Paperclip, OpenCode, Aider — writer done (`scripts/memory_ingest.py`); Hermes hook done (`agents/agent_daemon.py`); OpenCode hook done (`agents/opencode_memory.py`); Aider hook done (`agents/aider_memory.py`); Paperclip hook done (`agents/paperclip_memory.py`)
5. **Build promotion cron** (`scripts/memory_promote.py`) — done
6. **Implement AppFlowy sync** (webhook + poll) — **deferred** (ASP-79 Defer; see Component 5 routing). Re-open only under unblock criteria above. No child impl issue until then.
7. **Wire BEL-153** semantic search on top — done (LanceDB `VectorStore`)

**Memory-layer cycle status:** components 1–4 + BEL-153 are green; Component 5 is the only remaining design item and is intentionally parked.

---

## Linear Sync

- **BEL-154** updated with this design doc
- **ABS-10** (Paperclip) marked done with evidence link
- Implementation tasks tracked as sub-issues

---

## Sign-off

**Architect:** Ergo (CEO)  
**Implementer:** Proxy (Execution Specialist)  
**Designer:** Romi (Creative Director)  
**Date:** 2026-08-04  
**Verdict:** ✅ **Design complete — ready for implementation**

---

*This design satisfies BEL-154 / ABS-10 requirements. Local-first, offline-capable, modular, and integrates with Hermes, OpenCode, Aider, Paperclip, AppFlowy, and BEL-153 semantic layer.*