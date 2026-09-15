# Nightly Packaging & Deployment Check — 2026-09-15 04:07 UTC

**Run:** [ASP-600](/ASP/issues/ASP-600) (Aspen after ASP-601; durable artifact + §13 fix)
**Agent:** aspen (CEO) — packndeploy thrash cancelled
**Workspace:** `/home/tech/projects/aspen-dev/repos/aspen-os`
**Branch:** `master` (results @ HEAD after `6aa0040`; check base `6074948`)

## Verdict: PASS

| Suite | Passed | Failed | Known / notes |
|-------|--------|--------|---------------|
| `scripts/check-nightly.sh` **post §13 fix** | **107** | **1** | C11 p50 HW-dep only |
| Pre-fix bare PATH | 105 | 3 | C11 + system python3 missing pytest ×2 |
| Smoke (`make smoke` via nightly §4) | 60 | 1 | C11 p50 < 2ms (known HW-dependent) |
| Python via repo `.venv` | 303 | 0 | 4 skipped (optional deps) |
| Shell syntax (`bash -n`) | 36 | 0 | — |

## Full Nightly Script

1. Pre-fix on bare host PATH: **105 passed, 3 failed**, ~12–62s.
2. **Fix landed:** `scripts/check-nightly.sh` §13 prefers `$REPO_DIR/.venv/bin/python3` when executable (ASP-600).
3. Post-fix re-run: **107 passed, 1 failed**, ~14s — matches ASP-594 baseline.

### Failures classified (pre-fix)

1. **C11 p50 under 2ms** — known hardware-dependent; not actionable (ADR 0001 / runbook). **Still the sole post-fix failure.**
2. **`pytest importable` via bare `python3`** — system `/usr/bin/python3` lacks pytest; repo `.venv` has pytest. **Fixed by §13 interpreter preference.**
3. **`pytest pass count >= 150`** — cascade of (2). **Fixed.** Venv run: **303 passed, 4 skipped**.

## Static Inventory

| Item | Status | Value |
|------|--------|-------|
| Systemd units (`systemd/`) | PASS | 9 files |
| Debian metadata | PASS | control, postinst, postrm, prerm |
| `scripts/update.sh` | PASS | present, executable (5036 bytes) |
| Windows packaging | PASS | 6 artifacts |
| Version consistency | PASS | VERSION=2.2.0, debian control=2.2.0 |
| AppArmor profiles | PASS | 3 profiles; staged + postinst `apparmor_parser` (no `aa-enforce`) |
| Gatekeeper module | PASS | shim present, syntax valid |
| Debian package | PASS | `dist/starship-os_2.2.0_amd64.deb` ~6.4MB |
| H-019 dev-only isolation | PASS | Section 16 |
| H-010 AppArmor in deb | PASS | Section 17 |
| ISO structure | PASS | edge/server/ops profiles + hooks |
| ISO/deb full rebuild | SKIP | Option B |

## Toolchain

| Tool | Version | Status |
|------|---------|--------|
| nats-server | v2.14.5 | PASS |
| Go | 1.26.0 | PASS |
| Rust/Cargo | 1.93.1 | PASS |
| Python | 3.14.x (+ repo `.venv`) | PASS |

## Deviations from Baseline

- **None product-side.** Post-fix suite matches ASP-594 baseline: **107 pass / 1 known C11 fail**.
- **C11 p50:** remains single known non-actionable HW failure.
- **§13 follow-up:** **done** in this run (`scripts/check-nightly.sh`).

## Productivity note (ASP-601)

packndeploy held ASP-600 ~6h with 4× `plan_only` liveness + worktree-only comments and no results artifact. Runs `aa903c92` and recovery `13beaf19` cancelled by board. Aspen executed the runbook, landed results + §13 fix, closed the check. Do not re-wake packndeploy on this issue.

## Disposition

**PASS** — nightly packaging & deployment check complete. Results on master; §13 false-fail closed. No further product follow-up required.
