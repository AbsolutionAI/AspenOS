# ASP-539: Replace hardcoded NATS URL in scheduler.py with env/config

## Problem

`scheduler.py` (both `agents/scheduler.py` and `src/python/lib/scheduler.py`) hardcoded the NATS URL directly in the `nats.connect()` call with no env-var indirection. This was the only module in the codebase still doing this — every other service uses `os.getenv("NATS_URL", "nats://[IP_ADDRESS]:4222")`.

## Solution

Two changes per file:

1. Added `import os` to imports
2. Replaced `nats_connect("nats://[IP_ADDRESS]:4222")` with `nats_connect(os.getenv("NATS_URL", "nats://[IP_ADDRESS]:4222"))`

## Pattern

Follows the established codebase convention: `os.getenv("NATS_URL", "nats://[IP_ADDRESS]:4222")`, used by 30+ services. The fallback default preserves backward compatibility — systems that don't set `NATS_URL` keep working as before.

## Files changed

- `agents/scheduler.py` (lines 6, 101)
- `src/python/lib/scheduler.py` (lines 6, 100)

## Testing

No scheduler-specific tests exist. Change is a one-line mechanical substitution matching an established convention. Verified by reading final file state.