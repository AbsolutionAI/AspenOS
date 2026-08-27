# ASP-499: Fleet bus smoke test for aspen-edge-rrm + aspen-swarm-manager

## Problem

The CI smoke suite had a dead reference: `third_party/pins.json` declared `aspen-edge-rrm` was consumed by `scripts/smoke-fleet-bus.py`, but that file never existed. The CI cloned the sibling repo but had no test to exercise it, leaving 1 of 68 checks missing.

## Root cause

The `pins.json` entry was added when the fleet-bus integration was designed, but the corresponding smoke test was never implemented. The `used_by` field became an untracked promise.

## Solution

Created `scripts/smoke-fleet-bus.py` — 18 checks covering:
- `aspen_edge` module import (FleetBus, OpsManager, EdgeRRM)
- In-process pub/sub round-trip with CloudEvents envelopes
- OpsManager node registration + heartbeat → status aggregation
- EdgeRRM lifecycle (start, register, heartbeat, audit)
- Estop/clear dual-authorization cycle with micro-agent mediation
- `aspen_swarm` import + SwarmManager mission lifecycle

Wired into `scripts/smoke-test.sh` with `PYTHONPATH=../aspen-edge-rrm:../aspen-swarm-manager`.

### Key design decisions

1. **In-process bus only** — the smoke test uses `FleetBus` (in-process), not `NatsFleetBus`. This avoids requiring a running NATS server in CI, matching what other examples in `aspen-edge-rrm/examples/` do.

2. **Dual sibling import** — the smoke test imports both `aspen_edge` and `aspen_swarm` to verify both sibling packages are available where the CI places them (`../aspen-edge-rrm`, `../aspen-swarm-manager` per pins.json `clone_into`).

3. **Standalone exit code** — the script returns `0`/`1` so the `check` wrapper in `smoke-test.sh` gets a clean pass/fail signal. Stdout is suppressed in CI (`>/dev/null`).

## Lessons

- When adding a `used_by` reference in `pins.json`, create the consumer file in the same PR — or at minimum add an issue to track it.
- Smoke tests for external-dependency packages should use in-process stubs (like `FleetBus` vs `NatsFleetBus`) to avoid infrastructure requirements in CI.
- The `aspen-edge-rrm` and `aspen-swarm-manager` packages are designed for in-process testing out of the box — both use dataclass-based in-process buses by default.

## Files touched

- `scripts/smoke-fleet-bus.py` — new smoke test (86 lines)
- `scripts/smoke-test.sh` — added `check "fleet-bus smoke"` at line 80
- `docs/plans/ASP-499.md` — plan document