# ASP-52 — BEL-153 Semantic Layer for Services/memory.py

**Status:** Plan → Implement
**Sweep:** Hourly implementation sweep (ASP-52)
**Area:** Long-term memory service (`services/memory.py`)

## Objective

Land the in-progress BEL-153 semantic/vector layer in `services/memory.py`
as a clean, reviewable change. Add an embedding provider with graceful
fallback and an optional LanceDB-backed vector store for semantic search,
keeping the deterministic zero-dependency path fully functional.

## Background

`services/memory.py` currently does semantic search via `simple_embed` (a
deterministic 256-dim hashing embedding) + cosine similarity over the SQLite
`memories` table. The BEL-153 vector layer adds:

- An `EmbeddingProvider` that uses `sentence-transformers/all-MiniLM-L6-v2`
  when installed, falling back to `simple_embed` otherwise.
- A `VectorStore` (LanceDB) for ANN search when `lancedb` is available.
- Wiring into `MemoryManager.store()` / `MemoryManager.search()`.

Neither `sentence_transformers` nor `lancedb` is installed in this
environment, so the fallback path must remain the default and must not break
existing behavior.

## Changes

1. `EmbeddingProvider` — lazy CPU model load, `embed`/`embed_batch` with
   `simple_embed` fallback.
2. `VectorStore` — LanceDB-backed store; schema dimension derived from the
   actual embedding provider (fixes hardcoded 384 vs 256-dim mismatch).
3. `MemoryManager` — optional `vector_store`, `store()` mirrors to vector
   store, `search()` tries vector search first then falls back to SQLite.
4. Configurable vector store path via `AGNETIC_MEMORY_VECTORS` (defaults to
   `/tmp/agnetic-data/vectors`), removing a hardcoded `/home/tech/` dev path.

## Fixes applied during implementation

- Removed duplicate `from __future__ import annotations`.
- Vector schema dimension now derives from `len(get_embedding(""))` instead
  of a hardcoded 384 (which mismatched the 256-dim fallback).
- Default vector path no longer hardcoded `/home/tech/.aspen/memory/vectors`.

## Verification

- `python3 -m py_compile services/memory.py`
- `MemoryManager` store + search returns the stored memory in fallback mode.
- `memory-api.py` imports cleanly (uses `simple_embed`, `cosine_similarity`).

## Out of scope

- Installing `sentence-transformers` / `lancedb` (not present; optional).
- AppFlowy sync, MCP server, promotion pipeline (separate BEL-154 work items).

## Disposition

**COMPLETED** (ASP-482 sweep — 2026-08-26) — Memory semantic layer with embedding provider + LanceDB vector store landed. `MemoryManager` store/search functional in fallback mode. `memory-api.py` imports cleanly. Compound learning: `docs/solutions/asp-52-memory-semantic-layer.md`.
