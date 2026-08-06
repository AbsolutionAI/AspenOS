# ASP-57 — BEL-154 ingestion layer (`scripts/memory_ingest.py`)

## Problem

BEL-154 Component 1 (ingestion layer) existed only as a design sketch
(`docs/architecture/MEMORY_LAYER.md`). The promotion pipeline landed in ASP-54
(`scripts/memory_promote.py`) reads raw ingest JSONL from
`/home/tech/.aspen/memory/ingest/{source}/{date}.jsonl` — but **nothing wrote
those files**. The memory layer had an output side (promote → store → search)
with no input side, so the pipeline could only be fed by hand-written JSONL.

## Root cause

Each ASP-52→56 cycle built a downstream stage of the memory stack. The ingest
writer (the earliest stage) was skipped: the design doc listed "ingestion
hooks" as agent-side integrations, and no standalone writer existed for the
shared JSONL schema. Agents had no ergonomic way to emit records.

## Fix

- **`scripts/memory_ingest.py`** — stdlib-only writer:
  - `ingest_record(source, source_id, content, *, agent, company, project,
    tools, files, linear_refs, paperclip_refs, timestamp, ingest_dir)` —
    validates `source` against `{hermes, paperclip, opencode, aider,
    appflowy}`, defaults `timestamp` to now-UTC (`Z` suffix), and appends one
    JSON line to `{ingest_dir}/{source}/{YYYY-MM-DD}.jsonl` (mkdir -p).
  - `daily_path(source, ingest_dir, when)` — the date-stamped filename rule,
    the exact layout `memory_promote._iter_ingest_records` globs.
  - CLI `memory-ingest` — argparse flags mirroring the record fields, comma-
    split lists, `--stdin` support, exit code 2 on invalid source. Prints the
    written path on success (pipeline-friendly).
  - Env override `AGNETIC_MEMORY_INGEST_DIR` for parity with
    `AGNETIC_MEMORY_DB` / `AGNETIC_MEMORY_VECTORS`.
- **Tests** — `tests/test_memory_ingest.py` (8 tests): schema line + daily
  filename, invalid-source rejection, timestamp default/override, metadata
  arrays, append-to-same-file, promotion-pipeline read-back, CLI success, CLI
  invalid-source exit code.
- **Docs** — `MEMORY_LAYER.md` status table now marks Components 1–4
  Implemented (ingest writer, promotion, unified store, access layer, MCP);
  `ARCHITECTURE_COMPLETE.md` 3.2a gains an Ingestion row.

## Lessons

- **Build the input side first, or the pipeline you ship is untestable
  end-to-end.** The promote/access/MCP components were verified against
  fixture JSONL; only adding the writer makes `memory-promote` usable from a
  real agent run.
- **A writer must match the consumer's exact schema + directory convention.**
  The single source of truth for the file layout is
  `memory_promote._iter_ingest_records` (per-source dir, `*.jsonl` glob). Keep
  `daily_path()` next to the writer and assert read-back in tests so the two
  can't drift.
- **Validation at the boundary.** The `source` enum is enforced in the writer
  (where the typo happens), not later in the pipeline where a bad dir would
  just be silently skipped.
- **Daily-file append (a pattern already in `scripts/message_history.py`)**
  needs `mkdir(parents=True, exist_ok=True)` and an append-mode open — the
  per-day glob for consumers only sees files, never the dir itself.

## Verification

- `python3 -m py_compile scripts/memory_ingest.py` OK.
- `tests/test_memory_ingest.py` + `test_memory_promote.py` +
  `test_memory_client.py` + `test_memory_mcp.py`: **33/33 pass**.
- End-to-end: `memory-ingest` writes a decision record →
  `memory-promote` promotes it → `MemoryClient.search("memory_ingest")` and
  `get_by_linear("BEL-154")` return the fact.

## Follow-ups

- Agent-side ingestion hooks (Hermes/OpenCode/Aider/Paperclip) calling
  `memory_ingest.py` — wiring, not new components.
- AppFlowy bidirectional sync (Component 5) — larger scope, future cycle.
- `ProspectiveMemoryManager` — architect decision pending (escalated ASP-53).
