# ASP-55 — BEL-154 Python Library (`memory_pkg/aspen_memory`)

**Status:** Plan → Implement → QA → Compound
**Sweep:** Hourly implementation sweep (ASP-55)
**Area:** Long-term memory service — access layer Component 4.1
**CE-GATE:** `discovery` → `plan` → `implement` → `qa` → `compound`
**Pipeline:** Discovery → Plan (docs/plans/<issue>.md) → Implement → QA → Compound

## Discovery

BEL-154's design (`docs/architecture/MEMORY_LAYER.md`) Component 4.1 specifies a
thin `aspen_memory` Python library exposing a `MemoryClient` so agents
(Hermes, OpenCode, Aider, Paperclip) can query and add facts without touching
`services/memory.py` internals. ASP-52 landed the semantic layer, ASP-53 the
access layer (`ingest`/`retrieve`), ASP-54 the promotion pipeline. The library
was explicitly deferred in the ASP-53/54 dispositions ("`memory_pkg/`, MCP
server — out of scope, future cycle"). This sweep lands Component 4.1.

## Objective

Create `memory_pkg/` with an installable `aspen_memory` package exposing a
`MemoryClient` whose API matches the design doc 4.1 snippet:

```python
from aspen_memory import MemoryClient

client = MemoryClient()
results = client.search("UFW hardening", k=5, min_confidence=0.7)
facts = client.get_by_linear("BEL-114")
facts = client.get_by_paperclip("ABS-9")
facts = client.get_by_tags(["security", "ufw"])
client.add_fact(type="decision", content="…", tags=[…],
                linear_refs=[…], paperclip_refs=[…], confidence=0.95)
```

The client is a thin wrapper over the canonical `MemoryManager` — no parallel
store, no schema drift (the ASP-52/53/54 pattern).

## Changes

### 1. `services/memory.py` — metadata lookup helper

Add `MemoryManager.get_by_metadata(key, values, match_all=False, limit=50)`
querying the JSON `metadata` column via SQLite `json_each`:

- `key` in `{tags, linear_refs, paperclip_refs, …}`.
- `match_all=False` → any value match; `True` → every value must be present.
- Returns JSON-friendly dicts (same shape as `retrieve`).
- Add private `_memory_to_dict(m)` and refactor `retrieve()` + `api_search()`
  to reuse it (removes the duplicated dict literal).

### 2. `memory_pkg/aspen_memory/__init__.py` — `MemoryClient`

- `search(query, k=5, min_confidence=0.7, agent=None)` → `manager.retrieve()`.
- `get_by_linear(linear_id)`, `get_by_paperclip(paperclip_id)` →
  `get_by_metadata("linear_refs"/"paperclip_refs", [id])`.
- `get_by_tags(tags)` → `get_by_metadata("tags", tags, match_all=True)`.
- `add_fact(type, content, tags, linear_refs, paperclip_refs, confidence,
  agent="aspen", summary="")` → `manager.ingest()` with the design's metadata
  shape; returns the new memory id.
- `close()` and `__enter__`/`__exit__` context-manager support.
- Locates `services/` via `sys.path` insert relative to the package file (the
  established `memory_promote.py` pattern) so it works both editable-installed
  and from the repo without a build step.

### 3. `memory_pkg/pyproject.toml`

Minimal PEP 621 metadata: name `aspen-memory`, package `aspen_memory`, no
runtime deps (stdlib + optional `sentence-transformers`/`lancedb` already
handled by `services/memory.py`). `pip install -e /home/tech/aspen-dev/repos/aspen-os/memory_pkg`.

### 4. `docs/ARCHITECTURE_COMPLETE.md`

Add the `memory_pkg/` library to the `3.2a Memory Layer` section (access layer,
Component 4.1) — status Implemented.

### 5. Tests

`tests/test_memory_client.py` (canonical pytest style, temp `--db`):
- `search()` returns JSON dicts for a stored fact.
- `get_by_linear` / `get_by_paperclip` resolve facts stored with those refs;
  unknown ref returns `[]`.
- `get_by_tags` match_all semantics (all tags required, partial misses).
- `add_fact` round-trips via `get_by_linear` and `search`.
- Context-manager usage works.

## QA

- `python3 -m py_compile services/memory.py memory_pkg/aspen_memory/__init__.py`
- `pytest tests/test_memory_client.py tests/test_memory_promote.py -q`
- Existing tracked memory tests still pass (no behavior change to `store`/`search`).

## Compound

Record `docs/solutions/asp-55-memory-client-library.md`: JSON-metadata query
pattern, packaging choice, `json_each` pitfalls, reuse of `_memory_to_dict`.

## Out of scope / escalated

- MCP server (Component 4.2) — separate cycle.
- AppFlowy bidirectional sync (Component 5) — larger scope, future cycle.
- `ProspectiveMemoryManager` — architect decision pending (escalated ASP-53).
- ABS mirror deliverables (`docs/FLEET.md`, `docs/FOUNDATION.md`,
  `services/memory-api.py`, `Dockerfile.memory-api`, `services/__init__.py`,
  ABS test harnesses) owned by [ASP-36](/ASP/issues/ASP-36) — left uncommitted.

## Disposition

**COMPLETED** (ASP-482 sweep — 2026-08-26) — Memory client library landed. `MemoryClient` class with `search()`/`store()`/`list_collections()` implemented. `json_each`-based filtering, `_memory_to_dict` reuse pattern documented. Compound learning recorded.
