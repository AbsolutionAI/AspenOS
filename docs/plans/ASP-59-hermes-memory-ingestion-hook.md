# ASP-59 — BEL-154 Hermes memory ingestion hook (`agents/agent_daemon.py`)

**Status:** Plan → Implement → QA → Compound
**Sweep:** Hourly implementation sweep (ASP-59)
**Area:** Long-term memory service — Component 1 follow-up (agent-side ingestion hooks)
**Pipeline:** Discovery → Plan (docs/plans/<issue>.md) → Implement → QA → Compound

## Discovery

ASP-52 → ASP-57 landed the memory stack: semantic layer, access layer, promotion
pipeline (`scripts/memory_promote.py`), client library (`memory_pkg/aspen_memory`),
MCP server (`mcp/aspen-memory-mcp`), and the raw ingestion writer
(`scripts/memory_ingest.py`). ASP-57's plan and solution both record the remaining
follow-up verbatim:

> Agent-side ingestion hooks (Hermes/OpenCode/Aider/Paperclip) calling
> `memory_ingest.py` — wiring, not new components.

Today the promotion pipeline reads raw JSONL from the ingest dir, and the
ingestion writer exists, but **no agent runtime calls it**. The Hermes agent
daemon (`agents/agent_daemon.py`, the live tree — `src/python/` is an orphaned
mirror referenced by nothing) processes commands via `process_command()` and
already archives each command to `services.archive.ArchiveService`, but never
writes a BEL-154 ingest record. That is the missing input side of the pipeline
for the Hermes source.

## Objective

Wire the Hermes agent daemon to write one BEL-154 raw ingest record
(`source="hermes"`) per processed command, best-effort and failure-isolated so a
memory error never breaks the command loop.

## Changes

### 1. `agents/agent_daemon.py`

- Add a module-level helper `ingest_memory_record(agent_name, command, args, response, *, subject="", ingest_dir=None)`:
  - inserts `_PROJECT_ROOT` into `sys.path` (daemon runs from `agents/`, repo root may not be on path),
  - imports `scripts.memory_ingest.ingest_record`,
  - builds `content` = `"Command: {command}\nArgs: {json}\nResponse: {response}"` (truncate response to ~2000 chars),
  - calls `ingest_record(source="hermes", source_id=subject or f"{agent_name}:{datetime.now().isoformat()}", agent=agent_name, company="asp", project="aspen-os", content=content, ingest_dir=ingest_dir)`,
  - wraps everything in `try/except Exception` and logs at debug on failure (failure isolation per MEMORY_LAYER.md: "Ingestion failure ≠ promotion failure ≠ access failure").
- In `process_command()`, after the existing archive write block (line ~355), call
  `ingest_memory_record(agent_name, command, args, response, subject=subject)` inside a
  small `try/except` that only logs — never propagates into the command loop.
- `subject` is the NATS subject the command arrived on (a stable per-command id).

### 2. Tests — `tests/test_agent_memory_ingest.py`

- Import `agents/agent_daemon` module (adds repo root to `sys.path`).
- Unit-test `ingest_memory_record` directly with a `tmp_path` ingest dir:
  - writes a record under `{tmp}/{source}/{YYYY-MM-DD}.jsonl`,
  - the record parses as JSON and has `source == "hermes"`, `agent` matches, `company == "asp"`,
  - metadata-free call still produces a schema-valid line,
  - the written line is accepted by `memory_promote._iter_ingest_records` (round-trip),
  - a mocked failing import / exception does not raise (failure isolation) — verify via monkeypatch that raises inside the import branch.
- Note: `process_command` itself requires Ollama/NATS so it is not exercised end-to-end in unit tests; the helper is the tested seam.

## QA

- `python3 -m py_compile agents/agent_daemon.py scripts/memory_ingest.py scripts/memory_promote.py`
- `pytest tests/test_agent_memory_ingest.py tests/test_memory_ingest.py tests/test_memory_promote.py -q`
- End-to-end: write a record via `ingest_memory_record` into a temp dir, run `memory-promote` against it, assert the fact lands in a `MemoryManager`/`MemoryClient` search.

## Compound

Record `docs/solutions/asp-59-hermes-memory-ingestion-hook.md`: the "writer exists, no runtime calls it" gap, the helper-seam test pattern (don't unit-test `process_command`'s Ollama path — extract a pure helper), failure isolation, and the `sys.path` insert needed because the daemon runs from `agents/`.

## Out of scope / escalated

- AppFlowy bidirectional sync (Component 5) — larger scope, future cycle.
- OpenCode/Aider/Paperclip ingestion wiring — same pattern per agent, future cycles.
- `ProspectiveMemoryManager` — architect decision pending (escalated ASP-53).
- `src/python/` orphaned mirror drift (`emit_event`/`load_hooks_from_directory` missing in `src/python/services/event_hooks.py`) — noted; that tree is referenced by nothing in the repo and the root `agents/` daemon does not use it. Escalation candidate for the Architect if the mirror is meant to be maintained.
- ABS mirror deliverables owned by [ASP-36](/ASP/issues/ASP-36) — left uncommitted.

## Disposition

**COMPLETED** (ASP-482 sweep — 2026-08-26) — Hermes daemon memory ingestion hook landed. Helper-seam test pattern, `sys.path` insert for daemon runtime. Compound learning: `docs/solutions/asp-59-hermes-memory-ingestion-hook.md`.
