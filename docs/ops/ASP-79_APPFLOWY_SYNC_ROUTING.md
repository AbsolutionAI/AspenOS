# ASP-79 — AppFlowy bidirectional sync routing

**Date:** 2026-08-23  
**Agent:** aspen (Architect)  
**Issue:** Paperclip ASP-79  
**Related:** BEL-135 (knowledge layer), BEL-154 / MEMORY_LAYER Component 5

## Decision

**Defer** (option 1 of 3).

| # | Option | Selected |
|---|--------|----------|
| 1 | Defer — Component 5 stays design; no impl task | **Yes** |
| 2 | Scoped v1 — local skeleton + no-op without `APPFLOWY_API_URL` | No (this cycle) |
| 3 | Full deploy + sync | No |

## Rationale

1. **BEL-135** already files deploy as deferred under fiscal freeze; interim knowledge base is markdown under `docs/` + Obsidian.
2. **Fiscal freeze** — avoid always-on heavy apps without revenue need; Agent Zero image already ~12GB disk.
3. **No live consumer** — E2E against AppFlowy Cloud is impossible until deploy is approved; inventing the repo’s first bidirectional sync pattern without a target API wastes implementer budget.
4. **Memory layer is otherwise green** — ingestion, promotion, store, client, MCP, BEL-153 vector path are implemented; Component 5 is the only remaining design row and is intentionally parked.
5. **Scoped v1** remains a valid *future* path when unblock criteria fire; it was not authorized this cycle so Fast Coder/Opencode do not pick up speculative skeleton work.

## Unblock criteria

Re-open architect routing (new issue or `resume` on ASP-79) when any of:

- Human prioritizes AppFlowy deploy / lifts freeze for knowledge layer
- Gumroad cash flow verified and optional services fit budget
- Explicit ask for Scoped v1 skeleton only

## Durable artifacts

- `docs/architecture/MEMORY_LAYER.md` — Component 5 routing block + status ⏸ Deferred
- `docs/plans/BEL-135-appflowy-knowledge-layer.md` — cross-link to ASP-79
- This ops note

## Explicit non-work

- No `scripts/appflowy_sync.py`
- No AppFlowy compose deploy
- No child implementation issue for Opencode/Fast Coder
