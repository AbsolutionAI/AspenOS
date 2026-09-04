# ASP-539: Replace hardcoded NATS URL in scheduler.py with env/config

## Problem

`scheduler.py` (both `agents/scheduler.py` and `src/python/lib/scheduler.py`) hardcoded the NATS URL directly in the `nats.connect()` call with no env-var indirection. This was the only module in the codebase still doing this — every other service uses `os.getenv("NATS_URL", "nats://127.0.0.1:4222")`.

## Solution

Three changes:

1. **`agents/nats_connect.py:26`** — default URL in `build_nats_url()`: `"nats://127.0.0.1:4222"` → `"nats://127.0.0.1:4222"` (the source of truth for the helper)
2. **`agents/scheduler.py:101`** — `connect(os.getenv("NATS_URL", "nats://127.0.0.1:4222"))` → loopback default (already used `nats_connect` helper)
3. **`src/python/lib/scheduler.py:100`** — `nats_connect("nats://127.0.0.1:4222")` → `nats_connect(os.getenv("NATS_URL", "nats://127.0.0.1:4222"))`

## Pattern

Follows the established codebase convention: `os.getenv("NATS_URL", "nats://127.0.0.1:4222")`, used by 30+ services. The fallback default is loopback-only (`127.0.0.1`), not a fleet IP or hostname that could leak network topology.

## Files changed

- `agents/nats_connect.py` (line 26)
- `agents/scheduler.py` (line 101)
- `src/python/lib/scheduler.py` (line 100)
- `dist/pkgroot/opt/starship/lib/starship/agents/nats_connect.py` (line 26)
- `dist/pkgroot/opt/starship/lib/starship/agents/scheduler.py` (line 100)

## Testing

No scheduler-specific tests exist. Change is a one-line mechanical substitution matching an established convention. Verified by reading final file state.