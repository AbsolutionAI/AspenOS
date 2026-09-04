# ASP-553 — fleet-bus smoke dual-auth + sibling path

## Problem
Nightly packaging sweep failed `fleet-bus smoke` after aspen-edge-rrm added dual-human
estop clear (bare `aspen.safety.clear` no longer unlatches). Hermes worktrees also
resolved a stale `/home/tech/repos/aspen-edge-rrm` ahead of the pinned projects clone.

## Fix
- `scripts/smoke-fleet-bus.py`: prefer projects/CI sibling paths; dual-auth propose +
  estop clear protocol aligned with `aspen-edge-rrm/examples/fleet_e2e.py`.
- Baseline refresh in `docs/ops/NIGHTLY_PACKAGING_DEPLOY_CHECK.md`.

## Verify
- `python3 scripts/smoke-fleet-bus.py` → 20 passed, 0 failed
- `make smoke` → 58 passed, 1 failed (C11 p50 only)
- `make iso-smoke` → 32 passed, 0 failed
- `bash scripts/check-nightly.sh` → 99 passed, 3 known (C11 + pytest×2)
