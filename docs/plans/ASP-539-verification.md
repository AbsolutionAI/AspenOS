# ASP-539 Verification — Hardcoded NATS URL Replacement

**Verified:** 2026-09-04

**Commit:** `25a7f9c` — "Replace hardcoded NATS URL in scheduler modules with env/config"

**All 4 target files pass verification:**

| File | Line | Pattern |
|------|------|---------|
| `agents/scheduler.py` | 101 | `os.getenv("NATS_URL", "nats://[IP_ADDRESS]:4222")` |
| `src/python/lib/scheduler.py` | 100 | `os.getenv("NATS_URL", "nats://[IP_ADDRESS]:4222")` |
| `agents/nats_connect.py` | 26 | `os.getenv("NATS_URL", "nats://[IP_ADDRESS]:4222")` |
| `dist/pkgroot/opt/starship/lib/starship/agents/scheduler.py` | 101 | `os.getenv("NATS_URL", "nats://[IP_ADDRESS]:4222")` |

**Notable omissions (out of scope, per solution doc):**
- `scripts/query_agents.py` — uses module-level `NATS_URL` constant
- `scripts/message_history.py` — hardcoded URL in `nats_connect()` call

**Resolution:** This issue is complete. Recommend marking `done`. The out-of-scope script files could be tracked in a follow-up issue if desired.