# ASP-98 — Reconcile services/memory.py drift (ProspectiveMemoryManager)

## Architect decision

**Canonical tree: root `services/`** (SQLite + BEL-154 access layer + LanceDB
vector optional path). Runtime `from services.memory import …` and the shipped
deb layout resolve here.

`src/python/services/memory.py` is a **legacy parallel LanceDB-only** module
(not referenced by `scripts/build-deb.sh`). It remains as reference until
ABS-10 / ASP-36 mirror work retires or rewires it; do not point new features at
it.

## Problem

- Thorough / stresstest expected `ProspectiveMemoryManager` on canonical
  `services/memory.py`.
- Daemon tools under `src/python/lib/` imported
  `ProspectiveMemoryManager` / `get_prospective_memory` and silently disabled
  on `ImportError`.

## Fix

Ported prospective memory onto the SQLite canonical manager:

- `MemoryType.PROSPECTIVE` (+ WORKING / RETRIEVAL / PARAMETRIC for mesh audit
  parity)
- `MEMORY_DESCRIPTIONS`
- Schema columns `due_at`, `status` + migration for pre-ASP-98 DBs
- `MemoryManager.prospective_search` / filter-only empty-query search
- `ProspectiveMemoryManager` (async public API + `*_sync` helpers)
- `get_memory_manager()` / `get_prospective_memory()` singletons

## Verification

- `python3 -m py_compile services/memory.py`
- `pytest tests/test_prospective_memory.py tests/test_memory_client.py tests/test_memory_promote.py -q`

## Follow-ups

- ASP-36 / ABS-10: retire or rewire `src/python/` imports so tools call the
  sync canonical manager (or thin adapters) without dual trees.
- Docs: update `docs/AGENTS.md` memory row once ABS packaging lands.
