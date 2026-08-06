# ASP-53 — BEL-154 access layer + memory layer architecture coverage

## Problem

The BEL-154 memory design (`docs/architecture/MEMORY_LAYER.md`) specifies an
access layer with ingestion and retrieval entry points, but `services/memory.py`
only exposed `store`/`search`/`recall`. The QA harness
(`tests/smoke_test_bel_abs.py` / `tests/thorough_test_bel_abs.py`) flagged 14
smoke and 8 thorough failures, a mix of genuine gaps and test-harness bugs.

## Root cause

1. Missing access-layer methods: `ingest()` (auto-typed store) and
   `retrieve()` (JSON-friendly search).
2. `docs/ARCHITECTURE_COMPLETE.md` had zero coverage of the memory layer despite
   it being a core service.
3. Test-harness bugs producing false failures:
   - Case-sensitive keyword matching (docs legitimately use `Compound`).
   - `plan_files[0]` / `solutions[:3]` arbitrary sampling — could land on
     non-CE plans (e.g. `2026-08-05-github-package-mesh.md`) or thin fleet
     stubs (`bel-182`/`bel-191`, blocked under ASP-50).
   - Singular `binary` vs. the doc's plural `binaries`.

## Fix

- Added `MemoryManager.ingest(agent, content, mem_type=None, ...)` that infers
  `MemoryType.DECISION` via `_is_decision()` else `EPISODIC`, wrapping `store()`.
- Added `MemoryManager.retrieve(query, ...)` returning the same JSON shape as
  `api_search` — an access-layer consumer surface with zero new dependencies.
- Added a `3.2a Memory Layer` section to `ARCHITECTURE_COMPLETE.md` covering the
  7 `MemoryType`s, the `MemoryManager` API, embeddings (simple_embed +
  optional sentence-transformers), the optional LanceDB `VectorStore` (BEL-153),
  config env vars, `auto_memory`, and the BEL-154 roadmap.
- Fixed the harness: case-insensitive matching; deterministic CE-plan sampling
  (`discovery`+`ce-gate` present); substantive-solution check (≥3, not random);
  adapter binary plural.
- Corrected the stale `docs/AGENTS.md` memory.py row (claimed
  `ProspectiveMemoryManager` / `get_memory_manager()` that the canonical module
  never defined).

## Lessons

- **Documentation gap signals are real.** `ARCHITECTURE_COMPLETE.md` lacked the
  memory layer entirely; the failure bucket was 14 smoke / 8 thorough, most of
  which were genuine missing coverage, not test noise.
- **Arbitrary list sampling in harnesses is a latent bug.** `plan_files[0]` and
  `solutions[:3]` produce non-deterministic results; filter to the population
  you actually want to assert on (CE-structured plans, substantive solutions).
- **Canonical vs legacy module drift.** `ProspectiveMemoryManager` exists only in
  the legacy `src/python/services/memory.py` (async, `PROSPECTIVE` type,
  `prospective_search`, `due_at`/`status` columns) and requires a new memory
  type + API — an architectural addition, not a port. Escalated rather than
  silently implemented.
- **Verify doc keyword claims against the codebase before trusting a doc.**
  AGENTS.md listed classes the canonical module never defined.

## Verification

- `python3 -m py_compile services/memory.py`
- `ingest` → `retrieve` round-trip returns the stored memory in fallback mode;
  type auto-inference yields `decision` for decision-like text.
- `tests/smoke_test_bel_abs.py`: 74/74 passed (was 14 failures).
- `tests/thorough_test_bel_abs.py`: 58/59 (remaining failure is the escalated
  `ProspectiveMemoryManager`).
