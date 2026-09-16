# Nightly Packaging & Deployment Check — 2026-09-16

| Field | Value |
|-------|--------|
| **Verdict** | **PASS** (within known baseline) |
| **When** | 2026-09-16 04:03:25 UTC |
| **Host** | bt-asp-srv control plane |
| **Repo tip** | `fe432eb` (`docs(sweep): ASP-603…`) |
| **Version** | 2.2.0 |
| **Script** | `bash scripts/check-nightly.sh` |
| **Exit** | 1 (failure count = known C11 p50 only) |
| **Passed** | **107** |
| **Failed** | **1** (known) |
| **Duration** | 63720 ms (~64 s) |
| **nats-server** | v2.14.5 |
| **Issues** | ASP-604 (execution), ASP-605 (productivity review → stop packndeploy thrash) |
| **Executor** | aspen (after packndeploy plan_only loop cancelled) |

## Supersedes

Earlier draft of this filename claimed ALL GREEN citing packndeploy run `83f76e18` / host `ronsay` without real `check-nightly.sh` evidence. That draft is **void**. This file is the verified run.

## Results vs baseline (`docs/ops/NIGHTLY_PACKAGING_DEPLOY_CHECK.md`)

| Suite | Result |
|-------|--------|
| Toolchain (go/cargo/gcc+seccomp) | PASS |
| §1 Go build (`make build`, version) | PASS |
| §2 Rust agent (`make build-agent`) | PASS |
| §3 C11 components | PASS |
| §4 Smoke suite | **60 pass / 1 fail** — only `C11 p50 under 2ms` (known hw-dep) |
| §5 Debian package + size >1MB | PASS |
| §6 Systemd units (9) | PASS |
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

## Known deviation (not actionable)

**C11 sandbox p50 under 2ms** — ADR 0001 threshold. Control-plane host historically ~3.45 ms. Documented in runbook; do not open a fix ticket from this nightly alone.

## Follow-ups

None. No new packaging/deploy regressions.

## Log

Full stdout retained on run scratch for ASP-605 heartbeat (`check-nightly-ASP-604.log`, ~9 KB).
