# ASP-98 — Prospective memory on canonical `services/memory.py`

## Decision

**Canonical tree:** root `services/` (shipped by deb / runtime imports).  
**Legacy:** `src/python/services/memory.py` remains a parallel LanceDB/async sketch; do not extend it for production.

## Change

- Added `MemoryType.PROSPECTIVE`, `MEMORY_DESCRIPTIONS`, `due_at`/`status` columns (with PRAGMA migration).
- Ported `ProspectiveMemoryManager` + `get_memory_manager` / `get_prospective_memory` as **sync** APIs over SQLite.
- Verification: `python3 -m unittest tests.test_prospective_memory`

## Related

- ASP-121: `systemd/agnetic-nats.service` ExecStart uses `/usr/bin/env nats-server` so apt (`/usr/bin`) and local installs both resolve.
