# ASP-539: Replace hardcoded NATS URL in scheduler.py with env/config

## Problem

`agents/scheduler.py`, `src/python/lib/scheduler.py`, and their dist copies hardcoded the NATS broker URL as `"nats://[IP_ADDRESS]:4222"` with no env-var indirection. `agents/nats_connect.py` (the shared connect helper) already used `os.getenv("NATS_URL", ...)` but the scheduler callers bypassed it or had their own hardcoded fallback.

Threat model reference: H-012 (Closed).

## Solution

Applied the same pattern used by 30+ other modules (`services/*.py`, `dashboard/`, etc.):

```python
os.getenv("NATS_URL", "nats://[IP_ADDRESS]:4222")
```

Default fallback remains loopback-only (`[IP_ADDRESS]`). Never commit LAN/Tailscale IPs.

## Files Changed

| File | Change |
|------|--------|
| `agents/scheduler.py` | Line 101: URL passed via `nats_connect` helper (already had env-aware helper) |
| `agents/nats_connect.py` | Line 26: `build_nats_url` already used `os.getenv("NATS_URL", "nats://[IP_ADDRESS]:4222")` |
| `src/python/lib/scheduler.py` | Line 100: `from nats import connect` → `os.getenv("NATS_URL", "nats://[IP_ADDRESS]:4222")` |
| `dist/.../agents/scheduler.py` | Added `import os` and wrapped URL in `os.getenv` |
| `dist/.../agents/nats_connect.py` | Already used env var pattern (verified) |

## Verification

- All 5 files pass `python3 -m py_compile`
- No remaining un-env-wrapped `"nats://[IP_ADDRESS]:4222"` in source `.py` files
- Two script files (`scripts/query_agents.py`, `scripts/message_history.py` + their dist copies) still have hardcoded NATS URLs — outside this issue's scope.

## Related

- H-012 in `docs/SECURITY_THREAT_MODEL_v2.2.md` was already marked Closed prior to this work.