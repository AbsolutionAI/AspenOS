# ASP-61 — BEL-154 Aider ingestion hook (`agents/aider_memory.py`)

## Problem

ASP-52→60 built the memory stack plus the first two agent-side producers: the
Hermes hook (`agents/agent_daemon.py::ingest_memory_record`, ASP-59) and the
OpenCode hook (`agents/opencode_memory.py`, ASP-60). The writer
(`scripts/memory_ingest.py`) already accepted `source="aider"`, but no Aider
session had any path to write one. Aider is a first-class agent runtime on this
project (ASP-5), so its work — edits, commits, session summaries — was still
silent to the shared memory bank.

## Fix

- **`agents/aider_memory.py`** — near-copy of the ASP-60 OpenCode hook,
  retargeted to Aider:
  - `ingest_aider_record(content, *, source_id="", agent="aider", company="asp",
    project="aspen-os", files, tools, linear_refs, paperclip_refs, ingest_dir,
    max_content_chars=20000) -> Path | None`. Injects the repo root on
    `sys.path` (module may be launched from any cwd), imports
    `scripts.memory_ingest.ingest_record`, appends a `source="aider"` record.
    **Never raises** — failure-isolated per the memory layer's "ingestion
    failure ≠ promotion failure ≠ access failure" principle; returns the
    written path or `None`.
  - CLI `main()` (also `__main__`) so it's invocable as an Aider `post_edit`
    hook / completion wrapper / one-off: `--source-id`, `--content` (or
    `--stdin`), `--agent`, `--company`, `--project`, `--files`, `--tools`,
    `--linear-refs`, `--paperclip-refs`, `--ingest-dir`. Prints the written
    path; exit 0/2 (matching `memory_ingest.py`).
  - `source_id` falls back to `aider:{timestamp}`; content truncated to
    `max_content_chars`.
- **Bugfix (both hooks)** — `ingest_dir` defaulted to `None`, which overrode
  `memory_ingest.ingest_record`'s `DEFAULT_INGEST_DIR` and crashed the CLI when
  `--ingest-dir` was omitted (`unsupported operand type(s) for /: 'NoneType'
  and 'str'`). Both `aider_memory.py` and `opencode_memory.py` now resolve
  `ingest_dir or DEFAULT_INGEST_DIR` at call time, so the CLI works with no
  args and honors `AGNETIC_MEMORY_INGEST_DIR` when set.
- **Tests** — `tests/test_aider_memory_ingest.py` (8 tests): schema round-trip
  through `memory_promote._iter_ingest_records`; source_id fallback; metadata
  (files/tools/linear/paperclip refs); empty-content validity; content
  truncation; broken-import isolation (helper + CLI); CLI via args and stdin.
- **Docs** — `MEMORY_LAYER.md` status table + sources table + next-steps flip
  Aider ingestion to ✅ Implemented; `ARCHITECTURE_COMPLETE.md` §3.2a gains an
  Aider ingestion hook row; §4.4 OpenCode/Aider integration shows the Aider CLI
  invocation.

## Lessons

- **A pattern that paid off twice is now a documented standard.** The hook shape
  — helper seam, `sys.path` injection, `try/except` swallowing, content cap,
  timestamp fallback, CLI returning 0/2 — transferred verbatim a second time.
  With three producers on one writer contract, the next hook (Paperclip) is a
  text substitution, and the pattern itself is the reusable artifact.
- **Copy-paste carries bugs across copies.** The `ingest_dir=None` default bug
  existed in `opencode_memory.py` from day one and silently copied into the new
  hook. The e2e smoke test (CLI → promote → search) caught it because it ran
  the CLI with no `--ingest-dir`. Lesson: when cloning a pattern, run the
  downstream entry point with **default arguments**, not just the unit-tested
  happy path.
- **A parameter that defaults to `None` can override a sibling default.**
  `ingest_record(ingest_dir=Path)` has a real default, but passing
  `ingest_dir=None` explicitly nullifies it. If a wrapper wants "let the callee
  decide", it must pass `ingest_dir or DEFAULT_INGEST_DIR` (or not pass the
  kwarg at all) — a subtle Python footgun worth flagging in any wrapper seam.

## Verification

- `python3 -m py_compile agents/aider_memory.py` OK (and `opencode_memory.py`).
- Memory suite (ingest + hermes + promote + client + opencode + aider):
  **47/47 pass** (39 baseline + 8 new).
- End-to-end: `aider_memory.py` CLI (no `--ingest-dir`) → `memory-promote`
  promotes 3 facts (decision + semantic refs) → `MemoryClient.search("aider
  memory ingestion hook")` returns the promoted decision.
- Regression: `opencode_memory.py` CLI with no `--ingest-dir` now writes to the
  default ingest dir (previously crashed).

## Follow-ups

- Paperclip ingestion hook — same helper pattern, last remaining agent runtime.
- Live OpenCode/Aider runtime hook (plugin/`post_edit`) once a stable hook
  surface exists.
- AppFlowy bidirectional sync (Component 5) — larger scope, future cycle.
- `src/python/` orphaned mirror drift — Architect-routing candidate.
