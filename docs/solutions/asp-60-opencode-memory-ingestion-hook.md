# ASP-60 — BEL-154 OpenCode ingestion hook (`agents/opencode_memory.py`)

## Problem

ASP-52→59 built the memory stack and its first agent-side producer: the Hermes
hook (`agents/agent_daemon.py::ingest_memory_record`). The writer
(`scripts/memory_ingest.py`) already accepted `source="opencode"`, but no
OpenCode session had any path to write one — the largest remaining producer
class (and the class the implementing agent itself runs inside) was still
silent. The ingestion layer's sources table listed OpenCode but nothing in the
repo ever produced those records.

## Fix

- **`agents/opencode_memory.py`** — mirror of the ASP-59 Hermes hook:
  - `ingest_opencode_record(content, *, source_id="", agent="opencode",
    company="asp", project="aspen-os", files, tools, linear_refs,
    paperclip_refs, ingest_dir, max_content_chars=20000) -> Path | None`.
    Injects the repo root on `sys.path` (module may be launched from any cwd),
    imports `scripts.memory_ingest.ingest_record`, appends a
    `source="opencode"` record. **Never raises** — failure-isolated per the
    memory layer's "ingestion failure ≠ promotion failure ≠ access failure"
    principle; returns the written path or `None`.
  - CLI `main()` (also `__main__`) so it's invocable as an OpenCode hook /
    wrapper / one-off: `--source-id`, `--content` (or `--stdin`), `--agent`,
    `--company`, `--project`, `--files`, `--tools`, `--linear-refs`,
    `--paperclip-refs`, `--ingest-dir`. Prints the written path; exit 0/2
    (matching `memory_ingest.py`).
  - `source_id` falls back to `opencode:{timestamp}`; content truncated to
    `max_content_chars`.
- **Tests** — `tests/test_opencode_memory_ingest.py` (8 tests): schema
  round-trip through `memory_promote._iter_ingest_records`; source_id fallback;
  metadata (files/tools/linear/paperclip refs); empty-content validity; content
  truncation; broken-import isolation (helper + CLI); CLI via args and stdin.
- **Docs** — `MEMORY_LAYER.md` status table + sources table + next-steps flip
  OpenCode ingestion to ✅ Implemented; `ARCHITECTURE_COMPLETE.md` §3.2a gains
  an OpenCode ingestion hook row.

## Lessons

- **A pattern that paid off is a pattern worth copying verbatim.** The Hermes
  hook's shape — helper seam, `sys.path` injection, `try/except` swallowing,
  content cap, timestamp fallback — transferred almost 1:1 to a second agent
  runtime. Two producers now share one writer contract; the third (Aider) is a
  near-copy away.
- **Don't ship an unwired "integration" you can't verify.** OpenCode's config
  schema has no stable `hooks` key, and the repo's `config/hooks.json` uses a
  non-standard event shape, so editing live runtime config would have been
  untestable risk. Delivering a versioned CLI + documented invocation points
  (`python3 agents/opencode_memory.py --source-id <session> ... || true` from a
  wrapper/plugin) is honest: it works today as a one-off and is trivially
  attachable once a real hook surface exists.
- **Failure isolation must survive the CLI layer too.** A unit helper that
  swallows exceptions is not enough if the argparse entry point can still blow
  up a hook runner — but `main` must also return a real error code (2) for
  standalone use. Both are tested (helper returns `None`, CLI returns 2).
- **Tests are a QA loop, not a one-shot.** My first CLI error test monkeypatched
  `__import__` to fail *everything*, which detonated pytest's own reporting
  machinery (internal error after the test passed). Norrowing the patch to just
  `scripts.memory_ingest` fixed it — a reminder that a too-global monkeypatch is
  a test-fixture bug, not a product bug.

## Verification

- `python3 -m py_compile agents/opencode_memory.py` OK.
- Memory suite (ingest + hermes + promote + client + opencode): **39/39 pass**
  (31 baseline + 8 new).
- End-to-end: `opencode_memory.py` CLI → `memory-promote` promotes 3 facts
  (decision + semantic refs) → `MemoryClient.search("opencode ingest record")`
  returns the promoted decision.

## Follow-ups

- Aider + Paperclip ingestion hooks — same helper pattern per agent.
- Live OpenCode runtime hook (plugin/wrapper) once a stable hook surface exists.
- AppFlowy bidirectional sync (Component 5) — larger scope, future cycle.
- `src/python/` orphaned mirror drift — Architect-routing candidate.
