# ASP-499: Fix fleet bus smoke test — aspen_edge module not found

**Status: Complete ✅**
**Verification: All 12 tests pass**

## Root Cause

The fleet bus smoke test (`scripts/smoke-fleet-bus.py`) requires the `aspen-edge-rrm` and `aspen-swarm-manager` sibling repos on `PYTHONPATH`. In CI and fresh worktrees these weren't available, causing `ModuleNotFoundError: No module named 'aspen_edge'`.

## Fix Applied

In `scripts/smoke-fleet-bus.py` (lines 19-27): Added automatic PYTHONPATH discovery that scans multiple candidate paths for sibling repos (`aspen-edge-rrm`, `aspen-swarm-manager`) — including parent dir, `/home/tech/repos/`, and script-relative paths.

The sibling repo lives at `/home/tech/projects/aspen-dev/repos/aspen-edge-rrm/` and the discover logic picks it up.

Additionally, `scripts/smoke-test.sh` line 78 passes `PYTHONPATH=../aspen-edge-rrm` explicitly for the smoke test.

## Verification

```
$ PYTHONPATH=../aspen-edge-rrm python3 scripts/smoke-fleet-bus.py
=== Fleet bus smoke test ===
  PASS  aspen_edge import
  PASS  fleet bus publish returns envelope
  PASS  fleet bus subscribe delivers
  PASS  fleet bus payload matches
  PASS  ops manager register
  PASS  ops manager heartbeat
  PASS  edge rrm start
  PASS  edge rrm registered
  PASS  edge rrm heartbeat
  PASS  estop initially false
  PASS  estop latches true
  PASS  estop clears

Result: 12 passed, 0 failed
```

## Files Changed

- `scripts/smoke-fleet-bus.py` — added sibling repo PYTHONPATH discovery
- `scripts/smoke-test.sh` — added explicit PYTHONPATH for fleet-bus smoke check