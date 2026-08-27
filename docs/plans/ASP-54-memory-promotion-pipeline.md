# ASP-54 — BEL-154 Promotion Pipeline (`scripts/memory_promote.py`)

**Status:** Plan → Implement → QA → Compound
**Sweep:** Hourly implementation sweep (ASP-54)
**Area:** Long-term memory service — promotion pipeline component
**CE-GATE:** `discovery` → `plan` → `implement` → `qa` → `compound`
**Pipeline:** Discovery → Plan (docs/plans/<issue>.md) → Implement → QA → Compound

## Discovery

BEL-154's design (`docs/architecture/MEMORY_LAYER.md`) splits the memory layer
into five components. ASP-52 landed the BEL-153 semantic layer (EmbeddingProvider
+ LanceDB VectorStore) in `services/memory.py`; ASP-53 landed the BEL-154 access
layer (`ingest()` / `retrieve()`). The promotion pipeline — Component 2 — was
explicitly flagged as the next-cycle candidate in the ASP-53 disposition.

## Objective

Land a well-scoped `scripts/memory_promote.py` that reads raw ingest JSONL files,
extracts fact-worthy content, scores confidence per the BEL-154 design table, and
promotes facts with `confidence >= 0.7` into the canonical `MemoryManager` store
(single source of truth). Follow the pattern established by ASP-52/53: implement
into the existing service rather than spinning up a parallel store.

## Background / constraints

- The design doc's `facts.sqlite` (FTS5 + triggers) layout is aspirational; the
  canonical codebase stores memories in `MemoryManager`'s SQLite `memories` table
  + optional LanceDB vector index. The pipeline promotes **into** `MemoryManager`
  via its existing API — no schema drift, no parallel store.
- Raw ingest dir `/home/tech/.aspen/memory/ingest/{source}/{date}.jsonl` does not
  exist yet (only `vectors/`). The script must handle empty/missing dirs, and
  ship with a test fixture so behavior is verified deterministically.
- The untracked ABS test harnesses (`tests/{smoke,thorough}_test_bel_abs.py`) are
  ABS mirror deliverables owned by [ASP-36](/ASP/issues/ASP-36), blocked — do not
  modify them.
- `ProspectiveMemoryManager` remains escalated to the Architect (stale AGENTS.md
  claim; requires new MemoryType + API). Out of scope here.

## Changes

### 1. `scripts/memory_promote.py` — new CLI

- `FactCandidate` dataclass: `content`, `fact_type`, `tags`, `linear_refs`,
  `paperclip_refs`, `source`, `source_id`, `agent`, `timestamp`, `confidence`.
- `extract_facts(record: dict) -> list[dict]` — heuristic extraction targets from
  the design doc: decisions (declaration cues), patterns/configs (code/config
  snippets), credential references (names/paths only, never secrets),
  Linear/Paperclip cross-references.
- `score_confidence(candidate, authored_by_human) -> float` — implements the
  BEL-154 confidence table deterministically:
  - explicit declaration → 1.0 base
  - linear **and** paperclip cross-ref → 0.9; either ref → 0.8
  - pattern/config content → 0.75; generic → 0.5
  - agent-authored 0.7 / human-authored 0.9 multiplier
  - recency factor: within 30 days → 1.0, else 0.6
  - result clamped to [0, 1]
- `promote(manager, candidate) -> str | None` — calls
  `manager.ingest(agent, content, mem_type=DECISION|SEMANTIC,
  importance=confidence, metadata={tags, linear_refs, paperclip_refs, source,
  source_id, timestamp})`. Returns the new memory id (or `None` if
  `confidence < threshold`).
- `main()` — argparse CLI:
  - `--ingest-dir` (default `/home/tech/.aspen/memory/ingest`)
  - `--db` (default `$AGNETIC_MEMORY_DB` / `/tmp/agnetic-data/memory.db`)
  - `--min-confidence` (default `0.7`)
  - `--dry-run` (report only, no writes)
  - `--source` (filter by ingest source dir)
  - Iterates `{ingest_dir}/{source}/*.jsonl`, parses records, extracts, scores,
    dedupes by `sha256(content)[:16]`, skips fact_ids already in the append-only
    `facts.jsonl` log, promotes survivors, and appends promoted facts to
    `{ingest_dir}/../facts/facts.jsonl`.
- No new dependencies — uses `services.memory.py` via `sys.path` insert.

### 2. `docs/ARCHITECTURE_COMPLETE.md` — promotion coverage

Add promotion-pipeline rows to the `3.2a Memory Layer` section: extraction
targets, confidence scoring, threshold, `scripts/memory_promote.py`, facts log.

### 3. Tests

Add `tests/test_memory_promote.py` (canonical pytest style — verify there is an
existing test convention first) or a self-contained `--self-test` invocation:
- Fixture ingest JSONL with a declared decision + a cross-referenced config fact.
- Dry-run reports 2 candidates, promotes the `>=0.7` one, skips the weak one.
- `MemoryManager.retrieve()` round-trips the promoted fact.

## QA

- `python3 -m py_compile scripts/memory_promote.py services/memory.py`
- Run promote against the fixture into a temp `--db`; assert promoted count and
  that `retrieve("decision topic")` returns the fact.
- Run against the real ingest dir (currently empty) — exits cleanly, reports 0.
- Re-run the existing tracked memory smoke checks if any exist.

## Compound

Record a `docs/solutions/asp-54-memory-promotion-pipeline.md` with lessons:
heuristic extraction limits, confidence calibration, facts-log dedup.

## Out of scope / escalated

- `ProspectiveMemoryManager` (architect decision pending).
- AppFlowy bidirectional sync (Component 5 — larger scope, future cycle).
- MCP server / `memory_pkg/` Python library (Components 4.1/4.2).

## Disposition

**COMPLETED** (ASP-482 sweep — 2026-08-26) — Memory promotion pipeline (`scripts/memory_promote.py`) landed. Heuristic extraction, confidence calibration, facts-log dedup all implemented. Compound learning: `docs/solutions/asp-54-memory-promotion-pipeline.md`.
