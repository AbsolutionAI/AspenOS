# ASP-842: Nightly Packaging & Deployment Check — 2026-11-02

## What

Recurring nightly check (`scripts/check-nightly.sh`) on the control-plane host — 23 sections covering Go/Rust/C11 builds, smoke tests (62), Debian/Windows packaging, systemd units, shell syntax (45 scripts), static inventory, gatekeeper, Python test suite (516 passed, 4 skipped), ISO build structure, dashboard assets (8 files), H-019 dev-only isolation, H-010 AppArmor profiles, F-009 NATS secret paths, F-011 NATS rate limits, F-012 cgroup limits, F-014 package signature gate, F-013 model digest pinning, and H-024 NATS TLS by default.

## Results

- **Verdict:** PASS
- **check-nightly:** 158 passed, 1 failed (known C11 p50 hardware deviation)
- **Python suite:** 516 passed, 4 skipped (+16 net new tests since ASP-764 baseline of 500)
- **All static inventories matched** — no baseline drift in any section

## Observations

1. **Python test count grew organically** — from 500 to 516 since the last nightly (ASP-764, 2026-10-11). All +16 are unit tests from the intervening commits (ASP-762 tool-anomaly consumer, ASP-758 HybridIntel deletion, ASP-773 weekly review). No new failures or skips. Baseline updated in the ops doc.

2. **Toolchain drift:** Go upgraded from 1.26.0 → 1.26.8 (minor patch). No impact on any build step.

3. **Known C11 p50 persists** — ~3.655 ms vs the 2 ms threshold. Same order of magnitude, same host, non-actionable without a hardware change.

4. **No new security/fixture regressions** — Sections 16–23 all passed clean (AppArmor, NATS hardening, cgroups, signatures, model digests, TLS-by-default).

## Action items

- None. Clean sweep — no fixes required.