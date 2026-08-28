# Learning: Fleet-bus smoke test must self-discover sibling repo locations and skip gracefully when absent

**Ticket:** ASP-499

## Problem

The nightly check introduced in ASP-512 added a `fleet-bus smoke` check to `smoke-test.sh`, but the referenced script `scripts/smoke-fleet-bus.py` did not exist in the repo. The plan referenced in `third_party/pins.json` listed it, but the actual implementation was never written.

Adding the script naively with a hardcoded `PYTHONPATH=../aspen-edge-rrm` would cause two issues:

1. **CI would fail** if the sibling repo checkout step (added in ASP-518) was missing from the workflow.
2. **Developer checkouts** without the sibling repos cloned would see a hard failure from a script that should be optional — the fleet-bus smoke check depends on `aspen-edge-rrm`, which is not a build dependency of AspenOS itself.

## Fix

1. **Created `scripts/smoke-fleet-bus.py`** — a standalone smoke test that:
   - Auto-discovers sibling repos (`aspen-edge-rrm`, `aspen-swarm-manager`) via multiple candidate paths (CI clone location, dev workspace conventions, script-relative paths).
   - Gracefully skips with exit code 0 when the `aspen_edge` module is not available, printing a clear hint about the missing dependency.
   - Exercises FleetBus publish/subscribe round-trip, OpsManager node registration/heartbeat, EdgeRRM lifecycle (start, register, heartbeat), and estop/clear dual-authorization cycle — all in-process via the module's test doubles.

2. **Added `check "fleet-bus smoke"` to `scripts/smoke-test.sh`** — invokes `smoke-fleet-bus.py` and discards stdout (only the exit code matters for the smoke suite result).

## Patterns to reuse

- **Smoke tests with optional dependencies should skip, not fail.** A missing optional dependency should produce a clear SKIP message and exit 0, so CI and developer runs don't break when the dependency is unavailable.
- **Use pathlib-based auto-discovery for sibling repos.** Multiple candidate paths (CI checkout relative, dev workspace absolute, script-relative) ensure the test works both in CI and in local development without environment-specific configuration.
- **When a plan file references a script that doesn't exist yet**, create the script as part of the implementation — don't leave a dangling reference in pins.json or the plan.
- **Test doubles in the dependency module itself are preferable to mocking.** The `aspen_edge` module includes in-process FleetBus, OpsManager, and EdgeRRM implementations that can be exercised directly without starting NATS or any external service.