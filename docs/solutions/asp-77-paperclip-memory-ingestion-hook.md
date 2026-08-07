# ASP-77 — Paperclip memory ingestion hook (BEL-154 Component 1)

## Outcome

Closed the last Component 1 agent-runtime gap: Paperclip sessions now have an
agent-side ingestion hook (`agents/paperclip_memory.py`) that writes raw
BEL-154 ingest records (`source="paperclip"`) into the shared memory bank for
the promotion pipeline. `VALID_SOURCES` already listed `paperclip`; this is the
first caller.

## What landed

- `agents/paperclip_memory.py` — `ingest_paperclip_record()` + argparse CLI,
  near-copy of the Aider hook (ASP-61) retargeted to Paperclip. Best-effort and
  failure-isolated: any error logs to stderr and returns `None`; CLI exits 0 on
  success, 2 on hard error.
- `tests/test_paperclip_memory_ingest.py` — 9 tests (schema round-trip,
  source-id fallback, truncation, failure isolation, CLI args/stdin/error,
  default-ingest-dir regression guard).
- Docs: `MEMORY_LAYER.md` status table + next-steps flipped to implemented;
  `ARCHITECTURE_COMPLETE.md` ingestion-hook table row added.

## Verification

- `python3 -m py_compile agents/paperclip_memory.py` OK.
- Full memory suite: **56/56 pass** (47 baseline + 9 new paperclip).
- E2E smoke: `paperclip_memory.py` CLI → `memory_promote` promoted 3 facts →
  `MemoryManager.search()` returned the promoted fact + its auto-typed
  BEL-154/ASP-77 references.

## Lessons / patterns

- **"Copy-paste carries bugs across copies" (ASP-61 lesson, now validated
  twice).** The `ingest_dir=None` footgun from ASP-61 was proactively guarded in
  this hook (`ingest_dir or DEFAULT_INGEST_DIR`) AND locked with a regression
  test (`test_cli_no_ingest_dir_uses_default`) — the test harness, not memory,
  is what actually prevents recurrence.
- **A "last remaining runtime" in a source-validated schema is a code smell.**
  `VALID_SOURCES` included `paperclip` with zero callers; the gap only surfaced
  by diffing the doc'd status table against `git grep` for real call sites.
  When a writer validates a source enum, every enum member should have a caller
  or a ticket.
- **CLI-as-hook seam is stable.** Four runtimes (Hermes inline fn, OpenCode,
  Aider, Paperclip CLIs) now share one ingestion core with one JSONL schema —
  the marginal cost of adding a new agent runtime is a ~140-line mirror + tests.

## Follow-ups

- Live Paperclip runtime hook (plugin/run-completion) — invoke the CLI with
  `--source-id <run-id> ... || true` once a stable hook surface exists.
- `memory-sync` skill for Paperclip — separate cycle.
- AppFlowy bidirectional sync (Component 5) — larger scope, future cycle.
- `src/python/` orphaned mirror drift — Architect-routing candidate.
