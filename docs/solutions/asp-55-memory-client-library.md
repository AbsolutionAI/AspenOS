# ASP-55 — BEL-154 Python library (`memory_pkg/aspen_memory`)

## Problem

BEL-154 Component 4.1 (access-layer Python library) existed only as a design
snippet (`docs/architecture/MEMORY_LAYER.md`). Agents had to reach into
`services/memory.py` internals or the raw SQLite store to query by
Linear/Paperclip refs or tags; `retrieve()` only did semantic search.

## Root cause

`MemoryManager` had no metadata-lookup surface, so tag/ref filtering meant
either scanning all rows in Python or hand-writing SQL against the JSON
`metadata` column. No packaged client existed.

## Fix

- **`MemoryManager.get_by_metadata(key, values, match_all=False, limit=50)`** —
  filters via SQLite `json_each` over the JSON `metadata` column. `match_all`
  uses a grouped `COUNT(DISTINCT matched) = len(values)` subquery. Returns the
  same JSON-friendly shape as `retrieve()`.
- **Refactor** — extracted `_memory_to_dict(m)` and reused it in `retrieve()`
  and `api_search()` (removed a duplicated dict literal).
- **`memory_pkg/aspen_memory`** — `MemoryClient` with the design-doc API:
  `search(query, k, min_confidence, agent)`, `get_by_linear`,
  `get_by_paperclip`, `get_by_tags` (match_all), `add_fact(...)` →
  `manager.ingest()` with the BEL-154 metadata shape. Context-manager support,
  `close()`, locates `services/` via `sys.path` insert (the established
  `memory_promote.py` pattern), minimal PEP 621 `pyproject.toml`.
- **Tests** — `tests/test_memory_client.py`: 6 tests covering search
  round-trip, linear/paperclip/tag lookups, match_all semantics, context
  manager, and the raw `get_by_metadata` path.

## Lessons

- **SQLite `json_each` over a JSON text column is the zero-schema way to index
  metadata.** No FTS table, no migration — `json_each(m.metadata, '$.tags')`
  walks the array in SQL. Only works because metadata is stored as JSON.
- **`match_all` needs a grouped HAVING, not `AND` on one row.** Correlating
  multiple tags across a single JSON array requires `GROUP BY id HAVING
  COUNT(DISTINCT matched) = N`; a naive `value IN (...)` gives match_any.
- **Keep the client a thin wrapper.** `MemoryClient` adds no state of its own;
  the manager is the single source of truth (the ASP-52/53/54 pattern). A
  context manager prevents connection leaks when used inline.
- **Packaging a repo-internal lib is a judgment call.** No `pyproject.toml`
  existed in-repo, so the minimal PEP 621 file + `sys.path` fallback keeps it
  runnable without an install step — matching how `scripts/memory_promote.py`
  imports the service.

## Verification

- `python3 -m py_compile services/memory.py memory_pkg/aspen_memory/__init__.py` OK.
- `tests/test_memory_client.py` + `tests/test_memory_promote.py`: **18/18 pass**.
- Full tracked suite (minus `test_server.py` env gap): **85 pass**.
- `test_server.py` collection error is a missing `aiohttp` in the scratch venv,
  unrelated to this change.

## Follow-ups

- MCP server (Component 4.2) — next access-layer cycle.
- AppFlowy bidirectional sync (Component 5) — larger scope, future cycle.
- `ProspectiveMemoryManager` — architect decision pending (escalated ASP-53).
