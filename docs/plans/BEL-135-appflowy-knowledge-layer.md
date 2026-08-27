# BEL-135 — Knowledge layer (AppFlowy preferred)

**Date:** 2026-08-04  
**Status:** Plan filed — deploy deferred under fiscal freeze unless human prioritizes  
**Routing (2026-08-23):** Paperclip **ASP-79** chose **Defer** for MEMORY_LAYER Component 5 (AppFlowy bidirectional sync). No `scripts/appflowy_sync.py` impl task; no Full deploy. See `docs/architecture/MEMORY_LAYER.md` Component 5.

## Decision
Prefer **AppFlowy** self-hosted for second brain under Paperclip+Hermes (local-first).

## Options
1. **AppFlowy Cloud** docker compose (full multi-user) — higher disk/RAM  
2. **AppFlowy client + folder sync** — lighter  
3. **Interim:** Markdown knowledge base in `aspen-os/docs` + Obsidian skill (active now)

## Acceptance
- Knowledge app reachable on LAN/tailnet **or** explicit interim vault documented  
- Backup path documented  
- Linked from handoff/FOUNDATION  

## Interim knowledge base (active)
- `docs/COMPANY_MAP.md`, `COMPANY_CREDENTIALS.md`, `MODEL_ROUTING.md`  
- `docs/FOUNDATION.md`, `HANDOFF_ASPEN_STACK.md`  
- `docs/security/IDENTIFY-1-asset-inventory.md`  
- `docs/ops/MORNING_BRIEF.md`  
- Gumroad ops: `/home/tech/Gumroad-dev/gumroad-products/GUMROAD_UPLOAD.md`
- Architecture SoR for memory: `docs/architecture/MEMORY_LAYER.md` (Component 5 parked)

## Deploy (when approved)
```bash
mkdir -p /home/tech/aspen-dev/appflowy && cd /home/tech/aspen-dev/appflowy
# pin official compose; docker compose up -d
```

After deploy approval, re-open ASP-79-class routing for either **Scoped v1** (offline-capable skeleton) or **Full sync** against the live API — do not skip architect routing on first bidirectional pattern.

## Blockers / tradeoffs
- Agent Zero image already ~12GB disk  
- Fiscal freeze — avoid always-on heavy apps without revenue need  
- Human choice: full AppFlowy vs vault-only until Gumroad cash flow  

## Disposition

**DEFERRED** (ASP-482 sweep — 2026-08-26) — AppFlowy knowledge layer deferred. Blockers: Agent Zero disk footprint, fiscal freeze, human choice on sync direction. Revisit after memory layer stabilization and budget resolution.  
