# Nightly Packaging & Deployment Check — 2026-09-15 04:03 UTC

**Run:** [ASP-600](/ASP/issues/ASP-600) (completed by Aspen after ASP-601 productivity review)
**Agent:** aspen (CEO) — packndeploy thrash cancelled
**Workspace:** `/home/tech/projects/aspen-dev/repos/aspen-os`
**Branch:** `master` (HEAD `6074948`)

## Verdict: PASS

| Suite | Passed | Failed | Known / notes |
|-------|--------|--------|---------------|
| `scripts/check-nightly.sh` (host PATH) | 105 | 3 | C11 p50 HW-dep + pytest not on system `python3` (see below) |
| Smoke (`make smoke` via nightly §4) | 60 | 1 | C11 p50 < 2ms (known HW-dependent) |
| Python via repo `.venv` | 303 | 0 | 4 skipped (optional deps) |
| Shell syntax (`bash -n`) | 36 | 0 | — |

## Full Nightly Script

`bash scripts/check-nightly.sh` on bare host PATH: **105 passed, 3 failed**, ~62s.

Effective engineering verdict after venv-backed pytest: **PASS** matching ASP-594 baseline (107/1 when pytest is importable on the interpreter used by the script).

### Failures classified

1. **C11 p50 under 2ms** — known hardware-dependent; not actionable (ADR 0001 / runbook).
2. **`pytest importable` via `python3 -c "import pytest"`** — system `/usr/bin/python3` lacks pytest; repo `.venv` has pytest 9.1.1. **Cosmetic PATH/interpreter mismatch**, not a product regression.
3. **`pytest pass count >= 150`** — cascade of (2) on the script’s bare `python3`. Re-run with `.venv`: **303 passed, 4 skipped**.

## Static Inventory

| Item | Status | Value |
|------|--------|-------|
| Systemd units (`systemd/`) | PASS | 9 files |
| Debian metadata | PASS | control, postinst, postrm, prerm |
| `scripts/update.sh` | PASS | present, executable |
| Windows packaging | PASS | 6 artifacts |
| Version consistency | PASS | VERSION=2.2.0, debian control=2.2.0 |
| AppArmor profiles | PASS | staged + postinst `apparmor_parser` (no `aa-enforce`) |
| Gatekeeper module | PASS | shim present, syntax valid |
| Debian package | PASS | `dist/starship-os_2.2.0_amd64.deb` ~6.4MB |
| H-019 dev-only isolation | PASS | |
| ISO structure | PASS | edge/server/ops profiles + hooks |

## Toolchain

| Tool | Version | Status |
|------|---------|--------|
| nats-server | v2.14.5 | PASS |
| Go | 1.26.0 | PASS |
| Rust/Cargo | 1.93.1 | PASS |
| Python | 3.14.4 (+ repo `.venv`) | PASS |

## Deviations from Baseline

- **None product-side.** Suites match ASP-594 / runbook baseline when pytest uses repo `.venv`.
- **C11 p50:** remains single known non-actionable HW failure.
- **Script env note:** `check-nightly.sh` §13 should prefer repo `.venv/bin/python3` (or `python3 -m pytest` after activating venv) so bare-host PATH does not false-fail. Track as optional follow-up; not blocking this nightly.

## Productivity note (ASP-601)

packndeploy held ASP-600 ~6h with 4× `plan_only` liveness + worktree-only comments and no results artifact. Runs `aa903c92` and recovery `13beaf19` cancelled by board. Aspen executed the runbook and closed the check.

## Disposition

**PASS** — nightly packaging & deployment check complete. ISO/deb full rebuild skipped by design (Option B). No new follow-up required for product failures.
