# ASP-59 — BEL-154 Hermes ingestion hook (`agents/agent_daemon.py`)

## Problem

ASP-52→57 built the memory stack — semantic layer, promotion pipeline
(`memory_promote.py`), client library (`memory_pkg/aspen_memory`), MCP server,
and the raw ingestion writer (`memory_ingest.py`). The writer existed but was
**never called by any agent runtime**: the promotion pipeline read raw JSONL from
the ingest dir, but nothing on the Hermes side produced that JSONL. The memory
layer had a full input *writer* with zero live producers, so the only way to feed
it was hand-written files.

## Root cause

Each prior cycle built a downstream stage of the pipeline. The agent-side wiring
(the actual "source" in `{hermes, paperclip, opencode, aider, appflowy}`) was
deferred as "wiring, not new components" in ASP-57's disposition and never
landed. `agents/agent_daemon.py` already archived every command to
`services.archive.ArchiveService` but had no path to the memory ingest writer.

## Fix

- **`agents/agent_daemon.py`**:
  - New module-level helper `ingest_memory_record(agent_name, command, args,
    response, *, subject="", ingest_dir=None)`. It inserts `_PROJECT_ROOT` into
    `sys.path` (the daemon runs from `agents/`, so the repo root is not on the
    path by default), imports `scripts.memory_ingest.ingest_record`, builds a
    `Command/Args/Response` content string (response truncated to 2000 chars),
    and writes a `source="hermes"` record with `company="asp"`,
    `project="aspen-os"`, and `source_id` = the NATS subject (or
    `{agent}:{timestamp}` fallback).
  - Wired into `process_command()` right after the existing archive write,
    inside a `try/except` that only logs — a memory failure can never break the
    command loop.
  - **Failure isolation** per the design doc: ingestion failure ≠ promotion
    failure ≠ access failure. Any error in the hook (missing module, bad write)
    is caught and logged at debug.
- **Tests** — `tests/test_agent_memory_ingest.py` (5 tests): writes a
  `source="hermes"` record readable by `memory_promote._iter_ingest_records`;
  subject fallback to agent-timestamp; no-args schema validity; response
  truncation; and a broken-import path that must not raise.
- **Docs** — `MEMORY_LAYER.md` status table flips "Ingestion hooks (Hermes)" to
  ✅ Implemented; `ARCHITECTURE_COMPLETE.md` 3.2a gains a Hermes ingestion hook row.

## Lessons

- **A writer is not a pipeline until something calls it.** The ingest writer was
  "complete" for two cycles, but the e2e path only became real when the daemon
  started producing records. Verify upstream producers, not just downstream
  consumers.
- **Don't unit-test the Ollama path — extract a helper seam.** `process_command`
  calls Ollama over NATS, so it's untestable in isolation. The helper
  (`ingest_memory_record`) is the seam; tests hit it directly and assert the
  written record round-trips through the promotion reader. Keep IO-adjacent
  call sites thin and delegate logic to pure-ish helpers.
- **The daemon cwd is `agents/`, not the repo root.** The existing
  `services.archive` import silently no-ops when the repo root isn't on
  `sys.path`. Inserting `_PROJECT_ROOT` inside the helper makes the memory path
  work regardless of launch cwd.
- **Failure isolation is a contract, not an afterthought.** Wrapping the hook in
  its own try/except (and testing the broken-import case) guarantees a memory
  hiccup can't take down the agent loop.

## Verification

- `python3 -m py_compile agents/agent_daemon.py scripts/memory_ingest.py scripts/memory_promote.py` OK.
- `test_agent_memory_ingest.py` + `test_memory_ingest.py` + `test_memory_promote.py` + `test_memory_client.py`: **31/31 pass**.
- End-to-end: `ingest_memory_record("proxy", "Decide model routing", …, "Decision: use DeepSeek V4-Flash…")` → `memory-promote` promotes 1 fact → `MemoryClient.search("DeepSeek V4-Flash")` returns it.

## Follow-ups

- Paperclip/OpenCode/Aider ingestion wiring — same helper pattern per agent.
- AppFlowy bidirectional sync (Component 5) — larger scope, future cycle.
- `ProspectiveMemoryManager` — architect decision pending (escalated ASP-53).
- `src/python/` orphaned mirror drift (`emit_event`/`load_hooks_from_directory`
  missing from `src/python/services/event_hooks.py`, imported by
  `src/python/lib/tools.py` + `src/python/services/skills_hub.py`) — that tree is
  referenced by nothing in the repo and the live `agents/` daemon doesn't use it;
  candidate to escalate or delete.
