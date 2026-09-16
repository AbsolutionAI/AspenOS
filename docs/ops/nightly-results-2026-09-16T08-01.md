# Nightly Packaging & Deployment Check — 2026-09-16 08:01 UTC

| Field | Value |
|-------|--------|
| **Verdict** | **PASS** (within known baseline) |
| **When** | 2026-09-16 08:01:45 UTC |
| **Host** | bt-asp-srv control plane |
| **Repo tip** | `aab225e` (`docs(ops): land ASP-604 verified nightly 2026-09-16…`) |
| **Version** | 2.2.0 |
| **Script** | `bash scripts/check-nightly.sh` |
| **Exit** | 1 (failure count = known C11 p50 only) |
| **Passed** | **107** |
| **Failed** | **1** (known, hardware-dependent) |
| **Duration** | 61791 ms (~62 s) |
| **nats-server** | v2.14.5 |
| **Issue** | [ASP-606](/ASP/issues/ASP-606) |
| **Executor** | Opencode (Aspen Implementation Engineer) |

## Smoke suites

| Suite | Result |
|-------|--------|
| `make smoke` (`scripts/smoke-test.sh`, 61 tests) | **60 pass / 1 fail** — only `C11 p50 under 2ms` (known hw-dep) |
| `make iso-smoke` (`scripts/iso-firstboot-smoke.sh`) | **32 pass / 0 fail** |
| Python test suite (`pytest tests/`) | **303 passed, 4 skipped** (optional deps aiohttp, mcp.server), **0 failures** |

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

## Static inventory

| Item | Value |
|-------|--------|
| systemd unit files | **18** (9 in `systemd/`, 9 in `dist/pkgroot/lib/systemd/system/`) — includes 2 `agnetic-mesh.target` |
| Debian metadata | `debian/DEBIAN/`: control, postinst, postrm, prerm present |
| `scripts/update.sh` | present, executable |
| Windows packaging | `packaging/windows/`: install.bat, configure.bat, uninstall.bat, staragent.exe, staragent.yaml, README.txt — all present |
| Version consistency | VERSION `2.2.0` == `debian/DEBIAN/control` `Version: 2.2.0` |

## Known deviation (not actionable)

**C11 sandbox p50 under 2ms** — ADR 0001 threshold. Control-plane host historically ~3.45 ms; hardware-dependent. Documented in the runbook; no fix ticket should be opened from this nightly alone.

## Deviations from baseline doc

None. All 17 sections match the baseline table; suite counts unchanged (smoke 61 tests, python 303 passed / 4 skipped). ISO/deb build steps skipped by design on this host (Option B, `docs/ops/ISO_BUILDER.md`).

## Follow-ups

None. No new packaging/deploy regressions.

## Log

Full stdout retained on run scratch for ASP-606 heartbeat (`check-nightly-ASP-606.log`, ~17 KB).