# Nightly Packaging & Deployment Check — 2026-09-22 02:00 UTC

| Field | Value |
|-------|--------|
| **Verdict** | **PASS** (within known baseline) |
| **When** | 2026-09-22 02:00 UTC |
| **Host** | bt-asp-srv control plane |
| **Repo tip** | `8ebf26b` (`docs(ops): ASP-369 wrap-up — nightly clean (105/108, 3 cosmetic), auditor gate open, prod GO`) |
| **Version** | 2.2.0 |
| **Script** | `bash scripts/check-nightly.sh` |
| **Exit** | 1 (failure count = known C11 p50 only) |
| **Passed** | **149** |
| **Failed** | **1** (known, hardware-dependent) |
| **Duration** | 18588 ms |
| **nats-server** | v2.14.5 |
| **Issue** | [ASP-632](/ASP/issues/ASP-632) |
| **Executor** | packndeploy agent |

## Smoke suites

| Suite | Result |
|-------|--------|
| `make smoke` (`scripts/smoke-test.sh`, 62 tests) | **61 pass / 1 fail** — only C11 p50 (known hw-dep) |
| `make iso-smoke` (`scripts/iso-firstboot-smoke.sh`, 32 checks) | **32 pass / 0 fail** (static check) |
| Python test suite (`pytest tests/`) | **418 passed / 4 skipped, 0 failed** |

## Results vs baseline (`docs/ops/NIGHTLY_PACKAGING_DEPLOY_CHECK.md`)

| Section | Checks | Result |
|---------|--------|--------|
| Pre-flight toolchain (go/cargo/gcc+seccomp) | 3 | PASS |
| 1 Go build | 2 | PASS |
| 2 Rust build (`make build-agent`) | 1 | PASS |
| 3 C11 components | 4 | PASS |
| 4 Smoke suite (62 tests) | 1 | FAIL — sub-count 61 pass / 1 fail, C11 p50 only (known hw-dep) |
| 5 Debian package + size >1MB | 2 | PASS |
| 6 Systemd units (9 canonical) | 9 | PASS |
| 7 Shell syntax | 43 | PASS |
| 8 Key files + VERSION/control | 10 | PASS |
| 9 Debian metadata | 5 | PASS |
| 10 Windows packaging | 6 | PASS |
| 11 Update mechanism | 2 | PASS |
| 12 Gatekeeper module | 2 | PASS |
| 13 Python test suite | 4 | PASS (418 passed / 4 skipped) |
| 14 ISO build structure | 8 | PASS |
| 15 Dashboard static assets | 8 | PASS |
| 16 H-019 dev-only isolation | 1 | PASS |
| 17 H-010 AppArmor in deb | 4 | PASS |
| 18 F-009 NATS secret paths mode 600 | 6 | PASS |
| 19 F-011 NATS rate limits & caps | 5 | PASS |
| 20 F-012 cgroup per-agent limits | 5 | PASS |
| 21 F-014 package signature gate | 7 | PASS |
| 22 F-013 model digest pinning | 11 | PASS |
| **Total** | **149** | **148 PASS / 1 FAIL (known)** |

## Static inventory

| Item | Value |
|-------|--------|
| systemd unit files | **9** (in `systemd/`) |
| Debian metadata | `debian/DEBIAN/`: control, postinst, postrm, prerm present |
| `scripts/update.sh` | present, executable (6388 bytes) |
| Windows packaging | `packaging/windows/`: install.bat, configure.bat, uninstall.bat, staragent.exe, staragent.yaml, README.txt — all present |
| Version consistency | VERSION `2.2.0` == `debian/DEBIAN/control` `Version: 2.2.0` |
| Deb artifact | built, 6.0MB |
| ISO structure | 3 autoinstall profiles (edge/server/ops), chroot hooks, package lists present |
| Dashboard assets | 8 files present (style.css, ui.js, dashboard.js, agents.js, chat.js, panels.js, incidents.js, boot.js) |

## Known deviation (not actionable)

**C11 sandbox p50 under 2ms** — ADR 0001 threshold. Measured **3.481 ms** on this run
(prior runs 3.2–3.5 ms). Hardware-dependent; documented in the runbook. Not a packaging regression.

## Deviations from baseline doc

- Baseline: 149 checks across 22 sections; this run produced identical counts (149 pass / 1 C11 p50 known failure). No deviations.

## Repo changes in this run

- `docs/ops/nightly-results-2026-09-22T02-00.md` — this results file.

## Findings

1. **C11 p50 benchmark** — 3.481 ms, above the 2 ms ADR 0001 threshold. Consistent with prior runs (3.181 ms on 2026-09-21, 3.428 ms on 2026-09-19); not actionable without hardware change or sandbox optimization.
2. **No packaging regressions** — all 22 sections pass structurally. Deb build, systemd units, Debian metadata, ISO structure, Windows packaging, and all security gates (H-010/H-019/F-009/F-011/F-012/F-013/F-014) green.