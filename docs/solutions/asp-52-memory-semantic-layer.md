# ASP-52 — BEL-153 Semantic Layer for services/memory.py

## Outcome

Landed the BEL-153 semantic/vector layer in `services/memory.py` as a clean,
reviewable change. Added an `EmbeddingProvider` with graceful fallback and an
optional LanceDB-backed vector store for ANN search, keeping the deterministic
zero-dependency `simple_embed` path fully functional.

## What landed

- **`services/memory.py`** — `EmbeddingProvider` lazy-loads
  `sentence-transformers/all-MiniLM-L6-v2` when installed, falls back to
  `simple_embed` (256-dim deterministic hashing). `VectorStore` wraps LanceDB
  for ANN search; dimension auto-derived from the active provider (fixes the
  hardcoded 384 vs 256-dim mismatch). `MemoryManager.store()` mirrors to
  vector store; `search()` tries vector search first then falls back to SQLite
  cosine similarity.
- Configurable vector store path via `AGNETIC_MEMORY_VECTORS` (defaults to
  `/tmp/agnetic-data/vectors`), removing a hardcoded `/home/tech/` dev path.
- Cleanup: removed duplicate `from __future__ import annotations`.

## Verification

- `python3 -m py_compile services/memory.py` OK.
- `MemoryManager` store + search returns the stored memory in fallback mode.
- `memory-api.py` imports cleanly (uses `simple_embed`, `cosine_similarity`).

## Lessons / patterns

- **Derive schema dimensions from runtime, not constants.** The original code
  hardcoded 384 (matching `all-MiniLM-L6-v2`), but the fallback `simple_embed`
  produces 256 dimensions. Deriving from `len(get_embedding(""))` fixes the
  mismatch at the cost of one inference call at startup.
- **`/home/tech` paths are a recurring drift source.** Several hardcoded dev
  paths survived into main — catching them requires explicit env-var gates.
- **Optional dependencies work when the fallback is the default.** Neither
  `sentence-transformers` nor `lancedb` is installed in production; the
  fallback path is the default and must never regress.

## Follow-ups

- Optional ML dependencies (`sentence-transformers`, `lancedb`) — no install
  planned; documented as a performance upgrade path.
- AppFlowy sync, MCP server, promotion pipeline — separate BEL-154 work items.
