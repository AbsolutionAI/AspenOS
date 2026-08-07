# ASP-77 — Paperclip memory ingestion hook (BEL-154 Component 1)

**Status:** Plan → Implement → QA → Compound
**Scope:** Aspen OS memory layer, agent-side wiring
**Plan author:** Aspen Implementation Engineer (ASP-77 hourly sweep)

---

## 1. Discovery

Swept the open queue: no coding tasks are assigned to this agent
(ASP-25/17/7/3/26/36/50/46/63/65/66 are `blocked` under the Architect; ASP-5 is
`in_review` under Aider). The documented next implementation cycle on the memory
layer is **agent-side ingestion wiring for Paperclip**
(`docs/architecture/MEMORY_LAYER.md` "Next Steps" #4: "Hermes hook done …
OpenCode hook done … Aider hook done … **Paperclip wiring remains**", plus the
follow-up note in `docs/solutions/asp-61-aider-memory-ingestion-hook.md`:
"Paperclip ingestion hook — same helper pattern, last remaining agent runtime").

The writer (`scripts/memory_ingest.py`), Hermes hook
(`agents/agent_daemon.py::ingest_memory_record`, ASP-59), OpenCode hook
(`agents/opencode_memory.py`, ASP-60), and Aider hook
(`agents/aider_memory.py`, ASP-61) exist. Paperclip is the last runtime in the
BEL-154 Component 1 set (`VALID_SOURCES` already includes `"paperclip"`) with no
ingest path.

## 2. Problem

`memory_ingest.py::ingest_record` accepts `source="paperclip"`, but nothing in
the repo ever calls it with that source. A Paperclip agent/session has no way to
record its work (task summary, files touched, tools used, Linear/Paperclip refs)
into the shared memory bank for the promotion pipeline. Same gap ASP-59/60/61
closed for Hermes/OpenCode/Aider.

## 3. Plan

### 3.1 New file `agents/paperclip_memory.py`

Near-copy of the Aider hook (`agents/aider_memory.py`, ASP-61), retargeted to
Paperclip:

- `ingest_paperclip_record(content, *, source_id="", agent="paperclip",
  company="asp", project="aspen-os", files=None, tools=None, linear_refs=None,
  paperclip_refs=None, ingest_dir=None, max_content_chars=20000) -> Path | None`
  - Injects the repo root onto `sys.path`, imports
    `scripts.memory_ingest.ingest_record`, appends a `source="paperclip"`
    record, returns the written path.
  - Never raises — any error is caught and logged to stderr; returns `None`
    (memory layer "ingestion failure ≠ promotion failure ≠ access failure").
  - `source_id` falls back to `paperclip:{timestamp}`; content truncated to
    `max_content_chars`.
- `main(argv) -> int` argparse CLI (same flags as aider/opencode hooks:
  `--source-id`, `--content`/`--stdin`, `--agent`, `--company`, `--project`,
  `--files`, `--tools`, `--linear-refs`, `--paperclip-refs`, `--ingest-dir`).
  - Prints the written path; exit 0 on success, 2 on error.
  - Guard against the known `ingest_dir=None` footgun: pass
    `ingest_dir or DEFAULT_INGEST_DIR`.

### 3.2 Tests `tests/test_paperclip_memory_ingest.py`

Mirror of `tests/test_aider_memory_ingest.py` (8 tests):
1. Writes `source="paperclip"` record readable by
   `memory_promote._iter_ingest_records`; asserts schema fields.
2. `source_id` fallback to `paperclip:{timestamp}`.
3. Metadata (files/tools/linear_refs/paperclip_refs) round-trips.
4. Content truncation at `max_content_chars`.
5. Failure isolation — broken `scripts.memory_ingest` import never raises.
6. CLI: writes from `--content` and from stdin; error returns 2.
7. CLI with no `--ingest-dir` writes to the default ingest dir (regression
   guard for the `ingest_dir=None` bug).

### 3.3 Docs

- `docs/architecture/MEMORY_LAYER.md`: flip "Paperclip wiring remains" → done;
  mark ingestion hooks complete (Hermes/OpenCode/Aider/Paperclip).
- `docs/ARCHITECTURE_COMPLETE.md`: add Paperclip ingestion hook row.
- `docs/solutions/asp-77-paperclip-memory-ingestion-hook.md`: compound learning.

### 3.4 Runtime wiring (documented, not auto-attached)

Delivered as a versioned CLI with documented invocation points, matching the
ASP-60/61 delivery:
- Paperclip run-completion / hook wrapper invoking
  `python3 agents/paperclip_memory.py --source-id ASP-77 ... || true`.
- A `memory-sync` skill for Paperclip remains a separate cycle.

## 4. QA

- `python3 -m py_compile agents/paperclip_memory.py` — OK.
- New test file passes (8/8); full memory suite (ingest + hermes + promote +
  client + opencode + aider + paperclip) green.
- End-to-end smoke: `paperclip_memory.py` CLI → `memory-promote` promotes →
  `MemoryClient.search()` returns the promoted fact.

## 5. Out of scope / escalation

- AppFlowy bidirectional sync (Component 5) — larger scope, future cycle.
- `src/python/` orphaned mirror drift — still an Architect-routing candidate.
- Live runtime hook (plugin/`post_edit`) — no stable hook schema to target.
