# Nightly Packaging & Deployment Check — 2026-09-20 08:11 UTC

| Field | Value |
|-------|--------|
| **Verdict** | **PASS** (within known baseline) |
| **When** | 2026-09-20 08:11 UTC |
| **Host** | bt-asp-srv control plane |
| **Repo tip** | `c29de32` (`feat(systemd): cgroup per-agent resource limits via systemd drop-ins (H-012)`) |
| **Version** | 2.2.0 |
| **Script** | `bash scripts/check-nightly.sh` |
| **Exit** | 1 (failure count = known C11 p50 only) |
| **Passed** | **128** |
| **Failed** | **1** (known, hardware-dependent) |
| **Duration** | 14891 ms |
| **nats-server** | v2.14.5 |
| **Issue** | [ASP-622](/ASP/issues/ASP-622) |
| **Executor** | Opencode (Aspen Implementation Engineer) |

## Smoke suites

| Suite | Result |
|-------|--------|
| `make smoke` (`scripts/smoke-test.sh`, 61 tests) | **60 pass / 1 fail** — only C11 p50 (known hw-dep) |
| `make iso-smoke` (`scripts/iso-firstboot-smoke.sh`, 32 checks) | **32 pass / 0 fail** |
| Python test suite (`pytest tests/`) | **338 passed / 0 failed** |

## Results vs baseline (`docs/ops/NIGHTLY_PACKAGING_DEPLOY_CHECK.md`)

| Section | Checks | Result |
|---------|--------|--------|
| 1 Go build | 2 | PASS |
| 2 Rust build (`make build-agent`) | 1 | PASS |
| 3 C11 components | 16 | PASS |
| 4 Smoke suite (61 tests) | 61 | **60 pass / 1 fail — C11 p50 only (known hw-dep)** |
| 5 Debian package + size >1MB | 3 | PASS |
| 6 Systemd units (9 canonical) | 15 | PASS |
| 7 Shell syntax | 35 | PASS |
| 8 Key files + VERSION/control | 19 | PASS |
| 9 Debian metadata | 10 | PASS |
| 10 Windows packaging | 21 | PASS |
| 11 update.sh / update mechanism | 4 | PASS |
| 12 Gatekeeper shim | 2 | PASS |
| 13 Python test suite | 8 | PASS |
| 14 ISO autoinstall structure | 10 | PASS |
| 15 Dashboard static assets | 18 | PASS |
| 16 H-019 dev-only isolation | 1 | PASS |
| 17 H-010 AppArmor in deb (no aa-enforce) | 9 | PASS |
| 18 H-009 NATS secret paths mode 600 | 6 | PASS |
| 19 ASP-375/F-011 NATS rate limits & conn caps | 5 | PASS |
| 20 ASP-376/F-012 cgroup per-agent limits | 6 | PASS |

## Changes landed by this check

- **`scripts/check-nightly.sh`**: fixed the Section 20 "build-deb stages service.d drop-in dirs" check — the BRE pattern `systemd/*.service.d` could never match the literal glob `systemd/*.service.d` (BRE treats `/*` as a quantifier), producing a guaranteed false failure. Changed to fixed-string (`grep -qF`). Verified against `scripts/build-deb.sh` (line 165) via `grep -qF`; independently confirmed all 8 `10-cgroup-limits.conf` drop-ins are staged in the built `.deb` (`dpkg-deb --fsys-tarfile`).

## Known deviation (not actionable)

**C11 p50 under 2ms (ADR 0001)** — hardware-dependent. Measured `c11_v8`? p50 = 3.447 ms (baseline 3.428 ms). Documented in the runbook; requires hardware change (ASP-618, ASP-621 same result).

## Follow-ups

None. No packaging/deployment regressions beyond the known C11 p50 hardware benchmark.
