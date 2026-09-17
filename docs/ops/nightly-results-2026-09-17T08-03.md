# Nightly Packaging & Deployment Check — 2026-09-17 08:03 UTC

| Field | Value |
|-------|--------|
| **Verdict** | **PASS** (within known baseline) |
| **When** | 2026-09-17 08:03:06 UTC |
| **Host** | bt-asp-srv control plane |
| **Repo tip** | `a28955d` (`docs(solutions): compound ASP-607 gatekeeper rate limiting close`) |
| **Version** | 2.2.0 |
| **Script** | `bash scripts/check-nightly.sh` |
| **Exit** | 1 (failure count = known C11 p50 only) |
| **Passed** | **107** |
| **Failed** | **1** (known, hardware-dependent) |
| **Duration** | 12513 ms |
| **nats-server** | v2.14.5 |
| **Issue** | [ASP-610](/ASP/issues/ASP-610) |
| **Executor** | Opencode (Aspen Implementation Engineer) |

## Smoke suites

| Suite | Result |
|-------|--------|
| `make smoke` (`scripts/smoke-test.sh`, 61 tests) | **60 pass / 1 fail** — only `C11 p50 under 2ms` (known hw-dep) |
| `make iso-smoke` (`scripts/iso-firstboot-smoke.sh`) | **32 pass / 0 fail** |
| Python test suite (`pytest tests/`) | **316 passed, 4 skipped** (optional deps aiohttp, mcp.server), **0 failures** |

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

- **Python test suite count rose 303 → 316 passed** (4 skipped, 0 failures) — growth from gatekeeper rate-limiting tests merged in [ASP-607](/ASP/issues/ASP-607). Still comfortably above the ≥150 gate.
- No other deviations. All 17 sections match the baseline table. ISO/deb build steps skipped by design on this host (Option B, `docs/ops/ISO_BUILDER.md`).

## Follow-ups

None. No new packaging/deploy regressions.

## Log

Full stdout retained on run scratch for ASP-610 heartbeat (`check-nightly-ASP-610.log`, ~12 KB).