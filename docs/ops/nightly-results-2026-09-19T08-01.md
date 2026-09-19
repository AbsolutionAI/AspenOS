# Nightly Packaging & Deployment Check — 2026-09-19 08:01 UTC

| Field | Value |
|-------|--------|
| **Verdict** | **PASS** (within known baseline) |
| **When** | 2026-09-19 08:01 UTC |
| **Host** | bt-asp-srv control plane |
| **Repo tip** | `c238837` (`feat(security): enforce mode 600 on NATS creds & secret paths (ASP-373)`) |
| **Version** | 2.2.0 |
| **Script** | `bash scripts/check-nightly.sh` |
| **Exit** | 1 (failure count = known C11 p50 only) |
| **Passed** | **114** |
| **Failed** | **1** (known, hardware-dependent) |
| **Duration** | 13983 ms |
| **nats-server** | v2.14.5 |
| **Issue** | [ASP-618](/ASP/issues/ASP-618) |
| **Executor** | Opencode (Aspen Implementation Engineer) |

## Smoke suites

| Suite | Result |
|-------|--------|
| `make smoke` (`scripts/smoke-test.sh`, 61 tests) | **60 pass / 1 fail** — only `C11 p50 under 2ms` (known hw-dep) |
| `make iso-smoke` (`scripts/iso-firstboot-smoke.sh`) | **32 pass / 0 fail** |
| Python test suite (`pytest tests/`) | **338 passed, 4 skipped** (optional deps aiohttp, mcp.server), **0 failures** |

## Results vs baseline (`docs/ops/NIGHTLY_PACKAGING_DEPLOY_CHECK.md`)

| Suite | Result |
|-------|--------|
| Toolchain (go/cargo/gcc+seccomp) | PASS |
| §1 Go build (`make build`, version) | PASS |
| §2 Rust agent (`make build-agent`) | PASS |
| §3 C11 components | PASS |
| §4 Smoke suite | 60 pass / 1 fail — only C11 p50 known failure |
| §5 Debian package + size >1MB | PASS |
| §6 Systemd units (9 canonical) | PASS |
| §7 Shell syntax | PASS |
| §8 Key files + VERSION↔control | PASS |
| §9 Debian metadata | PASS |
| §10 Windows packaging | PASS |
| §11 `scripts/update.sh` | PASS |
| §12 Gatekeeper shim | PASS |
| §13 Python tests (≥150, 0 failures) | PASS |
| §14 ISO autoinstall structure | PASS |
| §15 Dashboard static assets | PASS |
| §16 H-019 no Dev-only in prod | PASS |
| §17 H-010 AppArmor in deb (no aa-enforce) | PASS |
| §18 NATS secret paths mode 600 (ASP-373/F-009) | PASS |

## Static inventory

| Item | Value |
|-------|--------|
| systemd unit files | **18** (9 in `systemd/`, 9 in `dist/pkgroot/lib/systemd/system/`) — includes 2 `agnetic-mesh.target` |
| Debian metadata | `debian/DEBIAN/`: control, postinst, postrm, prerm present |
| `scripts/update.sh` | present, executable |
| Windows packaging | `packaging/windows/`: install.bat, configure.bat, uninstall.bat, staragent.exe, staragent.yaml, README.txt — all present |
| Version consistency | VERSION `2.2.0` == `debian/DEBIAN/control` `Version: 2.2.0` |

## Known deviation (not actionable)

**C11 sandbox p50 under 2ms** — ADR 0001 threshold. Measured `c11_internal_wall` p50 = 3.428 ms (bench-sandbox.sh 100 iterations) on 2026-09-19; historical ~3.4–3.5 ms. Hardware-dependent; documented in the runbook. No fix ticket should be opened from this nightly alone.

## Deviations from baseline doc

- **Nightly suite grew 108 → 115 checks** since [ASP-615](/ASP/issues/ASP-615): §18 NATS secret paths mode 600 (ASP-373) adds 6 checks; §7 shell syntax grew 36 → 37 scripts (new `install-starship.sh` now parsed by `bash -n`).
- **Python test suite count rose 335 → 338 passed** (4 skipped, 0 failures) — growth from `tests/test_nats_secret_modes.py` (3 tests) landed with ASP-373. Comfortably above the ≥150 gate.
- **§18 fixture check defect found and fixed**: the `nats secret mode fixture tests` check piped through `grep` at the wrong level, so its PASS/FAIL line and the run summary were swallowed (the pipeline's `grep` exit code triggered `set -e`/pipefail after the check). Fixed by wrapping the pipeline in `bash -c` (matching the §13 pytest pattern); the re-run now prints the full summary (114 pass / 1 fail). Landed with this nightly in `scripts/check-nightly.sh`.
- ISO/deb build steps skipped by design on this host (Option B, `docs/ops/ISO_BUILDER.md`). No other deviations; all 18 sections match the baseline table.

## Follow-ups

None. No new packaging/deploy regressions.

## Log

Full stdout retained on run scratch for ASP-618 heartbeat (`nightly-check-run.log`, `iso-smoke.log`, `nightly-check-run2.log`).