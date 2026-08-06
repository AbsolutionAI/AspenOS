# ASP-60 — OpenCode memory ingestion hook (BEL-154 Component 1)

**Status:** Implemented → QA → Compound
**Scope:** Aspen OS memory layer, agent-side wiring
**Plan author:** Aspen Implementation Engineer (ASP-60 hourly sweep)

---

## 1. Discovery

Swept the open queue: no coding tasks are assigned to this agent
(ASP-25/17/7/3/26/36/50/46 are `blocked` under the Architect; ASP-5 is
`in_review` under Aider). The documented next implementation cycle on the memory
layer is **agent-side ingestion wiring for OpenCode/Aider/Paperclip**
(`docs/architecture/MEMORY_LAYER.md` "Next Steps" #4, and the follow-up note in
`docs/solutions/asp-59-hermes-memory-ingestion-hook.md`).

The writer (`scripts/memory_ingest.py`) and Hermes hook
(`agents/agent_daemon.py::ingest_memory_record`, ASP-59) exist. OpenCode agents
are the largest remaining producer with no ingest path — and the implementing
agent itself runs inside OpenCode, so this is the highest-value wiring cycle.

## 2. Problem

`memory_ingest.py::ingest_record` accepts `source="opencode"`, but nothing in the
repo ever calls it with that source. An OpenCode session has no way to record its
work (task summary, files touched, tools used, Linear/Paperclip refs) into the
shared memory bank for the promotion pipeline. Same gap ASP-59 closed for Hermes.

## 3. Plan

### 3.1 New file `agents/opencode_memory.py`

Mirror of the Hermes hook pattern (helper seam + failure isolation):

- `ingest_opencode_record(content, *, source_id="", agent="opencode",
  company="asp", project="aspen-os", files=None, tools=None, linear_refs=None,
  paperclip_refs=None, ingest_dir=None, max_content_chars=20000) -> Path | None`
  - Injects the repo root onto `sys.path` (module may be launched from any cwd),
    imports `scripts.memory_ingest.ingest_record`, appends a `source="opencode"`
    record, returns the written path.
  - Never raises — any error (missing module, bad write) is caught and logged to
    stderr at debug; returns `None`. Per the memory layer's "ingestion failure ≠
    promotion failure ≠ access failure" principle.
  - `source_id` falls back to `opencode:{timestamp}`; content is truncated to
    `max_content_chars`.
- `main(argv) -> int` argparse CLI so the hook is invocable as a command / hook /
  wrapper:
  - `--source-id`, `--content` (or stdin when `--stdin`/empty), `--agent`,
    `--company`, `--project`, `--files`, `--tools`, `--linear-refs`,
    `--paperclip-refs`, `--ingest-dir`.
  - Prints the written path; exit 0 on success, 2 on error (matches
    `memory_ingest.py`). Hook callers should run `|| true` if they want silence.

### 3.2 Tests `tests/test_opencode_memory_ingest.py`

1. Writes `source="opencode"` record readable by
   `memory_promote._iter_ingest_records`; asserts schema fields.
2. `source_id` fallback to `opencode:{timestamp}`.
3. Metadata (files/tools/linear_refs/paperclip_refs) round-trips.
4. Content truncation at `max_content_chars`.
5. Failure isolation — broken `scripts.memory_ingest` import never raises.
6. CLI: writes from `--content` and from stdin.

### 3.3 Docs

- `docs/architecture/MEMORY_LAYER.md`: flip "Ingestion hooks (OpenCode/Aider)"
  status; add OpenCode row to the diagram sources table + next-steps note.
- `docs/ARCHITECTURE_COMPLETE.md` §3.2a: add OpenCode ingestion hook row.
- `docs/solutions/asp-60-opencode-memory-ingestion-hook.md`: compound learning.

### 3.4 Runtime wiring (documented, not auto-attached)

OpenCode's current config schema has no stable `hooks` key and the repo's
`config/hooks.json` uses a non-standard event shape, so the hook is delivered as
a versioned CLI rather than mutating live runtime config. Integration points
documented in the solution doc:
- OpenCode plugin / `agent.completed`-style wrapper invoking
  `python3 agents/opencode_memory.py --source-id <session> ... || true`.
- Paperclip run-completion callback (same CLI), source `opencode`.
- `memory-sync` skill for Paperclip remains a separate cycle.

## 4. QA

- `python3 -m py_compile agents/opencode_memory.py`.
- New test file passes; full memory suite (minus MCP, which needs `mcp` pkg)
  stays green: ingest + hermes + promote + client = 31 + 6.
- End-to-end smoke: CLI writes a real record → `memory-promote` promotes a fact
  → `MemoryClient.search()` returns it.

## 5. Out of scope / escalation

- Paperclip and Aider hooks (same pattern, future cycles).
- AppFlowy bidirectional sync (Component 5).
- `src/python/` orphaned mirror drift — still an Architect-routing candidate.
- Live OpenCode runtime hook wiring (plugin) — no stable hook schema to target.
