# ASP-57 — BEL-154 Ingestion Layer (`scripts/memory_ingest.py`)

**Status:** Plan → Implement → QA → Compound
**Sweep:** Hourly implementation sweep (ASP-57)
**Area:** Long-term memory service — Component 1 (Ingestion Layer)
**Pipeline:** Discovery → Plan (docs/plans/<issue>.md) → Implement → QA → Compound

## Discovery

BEL-154's design (`docs/architecture/MEMORY_LAYER.md`) Component 1 defines the
raw ingestion layer: agents (Hermes, Paperclip, OpenCode, Aider, AppFlowy)
write JSONL records under `/home/tech/.aspen/memory/ingest/{source}/{date}.jsonl`
so the promotion pipeline (`scripts/memory_promote.py`, landed in ASP-54) can
extract and promote facts.

ASP-52 → ASP-56 landed the semantic layer, access layer, promotion pipeline,
client library, and MCP server. The **ingestion writer** was never built: the
promotion pipeline reads from the ingest dir, but nothing writes those JSONL
files. Component 1 is the missing input side of the pipeline and the natural
next cycle.

## Objective

Create `scripts/memory_ingest.py` — a CLI + importable helper that appends
BEL-154-schema JSONL records to the per-source daily file, matching the exact
schema `memory_promote.py` consumes (`source`, `source_id`, `timestamp`,
`agent`, `company`, `project`, `content`, `metadata.{tools_used,
files_touched, linear_refs, paperclip_refs}`).

## Changes

### 1. `scripts/memory_ingest.py`

- `DEFAULT_INGEST_DIR = /home/tech/.aspen/memory/ingest` (env-overridable via
  `AGNETIC_MEMORY_INGEST_DIR` for parity with the other memory env vars).
- `VALID_SOURCES = {"hermes", "paperclip", "opencode", "aider", "appflowy"}`.
- `ingest_record(source, source_id, content, *, agent="opencode",
  company="asp", project=None, tools=None, files=None, linear_refs=None,
  paperclip_refs=None, timestamp=None, ingest_dir=None) -> Path`:
  - validates `source` against `VALID_SOURCES` (raise `ValueError`),
  - defaults `timestamp` to now (UTC, `Z`-suffixed ISO),
  - writes one JSON line (with trailing newline) to
    `{ingest_dir}/{source}/{YYYY-MM-DD}.jsonl`, `mkdir -p` first,
  - returns the file path.
- CLI: `memory-ingest --source paperclip --source-id run-123 --content "…"
  [--agent] [--company] [--project] [--tools a,b] [--files x,y]
  [--linear-refs BEL-1,BEL-2] [--paperclip-refs ABS-1] [--timestamp ISO]
  [--ingest-dir PATH]`. Reads `--content` from stdin when omitted or when
  `--stdin` is passed. Mirrors `memory_promote.py` conventions (argparse,
  `main(argv)` return int, prints the written path).
- No new dependencies; stdlib only (`json`, `argparse`, `datetime`, `pathlib`).

### 2. Tests — `tests/test_memory_ingest.py`

- Appends a valid record and asserts the exact JSONL line + daily filename.
- `ingest_record` with an invalid source raises `ValueError`.
- Timestamp defaults to now in the right format when omitted; honored when given.
- Metadata lists (tools/files/refs) survive as JSON arrays in the written line.
- Round-trip: written file parses as JSON and is accepted by
  `memory_promote._iter_ingest_records`.
- CLI (`main([...])`) returns 0 and creates the file; `--stdin` path works.

## QA

- `python3 -m py_compile scripts/memory_ingest.py`
- `pytest tests/test_memory_ingest.py tests/test_memory_promote.py -q`
- Round-trip with the promotion pipeline on a temp ingest dir (writes a
  decision record, runs `memory-promote`, asserts the fact appears).

## Compound

Record `docs/solutions/asp-57-memory-ingestion-layer.md`: the input-side gap,
daily-file append pattern (reusing `message_history.py`'s date-stamped JSONL
approach), schema parity with the promotion pipeline, validation-at-boundary.

## Out of scope / escalated

- AppFlowy bidirectional sync (Component 5) — larger scope, future cycle.
- Ingestion hooks in Hermes/OpenCode/Aider runtimes themselves (Component 1
  supplies the writer; runtime hooks are agent-side wiring).
- `ProspectiveMemoryManager` — architect decision pending (escalated ASP-53).
- ABS mirror deliverables owned by [ASP-36](/ASP/issues/ASP-36) — left
  uncommitted.

## Disposition

**COMPLETED** (ASP-482 sweep — 2026-08-26) — Memory ingestion layer (`scripts/memory_ingest.py`) landed. Validation-at-boundary approach, schema parity with promotion pipeline. Compound learning recorded.
