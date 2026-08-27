# ASP-61 — Aider memory ingestion hook (BEL-154 Component 1)

**Status:** Implemented → QA → Compound
**Scope:** Aspen OS memory layer, agent-side wiring
**Plan author:** Aspen Implementation Engineer (ASP-61 hourly sweep)

---

## 1. Discovery

Swept the open queue: no coding tasks are assigned to this agent
(ASP-25/17/7/3/26/36/50/46 are `blocked` under the Architect; ASP-5 is
`in_review` under Aider). The documented next implementation cycle on the memory
layer is **agent-side ingestion wiring for Aider/Paperclip**
(`docs/architecture/MEMORY_LAYER.md` "Next Steps" #4, and the follow-up note in
`docs/solutions/asp-60-opencode-memory-ingestion-hook.md`: "Aider + Paperclip
ingestion hooks — same helper pattern per agent").

The writer (`scripts/memory_ingest.py`), Hermes hook
(`agents/agent_daemon.py::ingest_memory_record`, ASP-59), and OpenCode hook
(`agents/opencode_memory.py`, ASP-60) exist. Aider is the remaining large agent
producer with no ingest path. Aider is also the second agent runtime on this
project (ASP-5), so wiring it closes the last "agent always writes to memory"
gap in the current set.

## 2. Problem

`memory_ingest.py::ingest_record` accepts `source="aider"`, but nothing in the
repo ever calls it with that source. An Aider session has no way to record its
work (task summary, files touched, tools used, Linear/Paperclip refs) into the
shared memory bank for the promotion pipeline. Same gap ASP-59 closed for Hermes
and ASP-60 closed for OpenCode.

## 3. Plan

### 3.1 New file `agents/aider_memory.py`

Near-copy of the OpenCode hook (`agents/opencode_memory.py`, ASP-60), retargeted
to Aider:

- `ingest_aider_record(content, *, source_id="", agent="aider", company="asp",
  project="aspen-os", files=None, tools=None, linear_refs=None,
  paperclip_refs=None, ingest_dir=None, max_content_chars=20000) -> Path | None`
  - Injects the repo root onto `sys.path` (module may be launched from any cwd),
    imports `scripts.memory_ingest.ingest_record`, appends a `source="aider"`
    record, returns the written path.
  - Never raises — any error (missing module, bad write) is caught and logged to
    stderr at debug; returns `None`. Per the memory layer's "ingestion failure ≠
    promotion failure ≠ access failure" principle.
  - `source_id` falls back to `aider:{timestamp}`; content is truncated to
    `max_content_chars`.
- `main(argv) -> int` argparse CLI so the hook is invocable as a command / Aider
  post-edit hook / wrapper:
  - `--source-id`, `--content` (or stdin when `--stdin`/empty), `--agent`,
    `--company`, `--project`, `--files`, `--tools`, `--linear-refs`,
    `--paperclip-refs`, `--ingest-dir`.
  - Prints the written path; exit 0 on success, 2 on error (matches
    `memory_ingest.py`). Hook callers should run `|| true` if they want silence.

### 3.2 Tests `tests/test_aider_memory_ingest.py`

Mirror of `tests/test_opencode_memory_ingest.py` (8 tests):
1. Writes `source="aider"` record readable by
   `memory_promote._iter_ingest_records`; asserts schema fields.
2. `source_id` fallback to `aider:{timestamp}`.
3. Metadata (files/tools/linear_refs/paperclip_refs) round-trips.
4. Content truncation at `max_content_chars`.
5. Failure isolation — broken `scripts.memory_ingest` import never raises.
6. CLI: writes from `--content` and from stdin; error returns 2.

### 3.3 Docs

- `docs/architecture/MEMORY_LAYER.md`: flip "Ingestion hooks (Aider)" status to
  ✅ Implemented; add Aider row to the sources table if present + next-steps
  note (Paperclip remains).
- `docs/ARCHITECTURE_COMPLETE.md` §3.2a: add Aider ingestion hook row.
- `docs/solutions/asp-61-aider-memory-ingestion-hook.md`: compound learning.

### 3.4 Runtime wiring (documented, not auto-attached)

Aider supports post-edit hooks (`--watch-files` / `.aider` `post_edit` hooks /
`--message-file` completion wrapper). Delivered as a versioned CLI with
documented invocation points rather than mutating live runtime config, matching
the ASP-60 delivery:
- Aider `post_edit`/completion wrapper invoking
  `python3 agents/aider_memory.py --source-id <session> ... || true`.
- Paperclip run-completion callback (same CLI), source `aider`.
- `memory-sync` skill for Paperclip remains a separate cycle.

## 4. QA

- `python3 -m py_compile agents/aider_memory.py` — OK.
- New test file passes (8/8); full memory suite (ingest + hermes + promote +
  client + opencode + aider) green: **47/47** (39 baseline + 8 new).
- End-to-end smoke: `aider_memory.py` CLI → `memory-promote` promotes 3 facts →
  `MemoryClient.search()` returns them.
- Bug found + fixed during e2e: `ingest_dir=None` default crashed the CLI when
  `--ingest-dir` omitted; fixed in both `aider_memory.py` and
  `opencode_memory.py` (`ingest_dir or DEFAULT_INGEST_DIR`).

## 5. Out of scope / escalation

- Paperclip ingestion hook (same pattern, future cycle).
- AppFlowy bidirectional sync (Component 5).
- `src/python/` orphaned mirror drift — still an Architect-routing candidate.
- Live Aider/OpenCode runtime hook (plugin) — no stable hook schema to target.

## Disposition

**COMPLETED** (ASP-482 sweep — 2026-08-26) — Aider memory ingestion hook landed. `aider_memory.py` CLI with `ingest_dir=None` bug fixed (backported to `opencode_memory.py`). Full memory suite green. Compound learning recorded.
