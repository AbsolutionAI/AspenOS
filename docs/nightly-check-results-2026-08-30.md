# Nightly Check Results — 2026-08-30 19:52 UTC

**Verdict: PASS (1 known failure)**

| Metric | Value |
|--------|-------|
| Passed | 80 |
| Failed | 1 |
| Total  | 81 |
| Time   | 11,618ms |

**Known failure:** C11 p50 benchmark deviation (check 53 of 59 smoke tests) — hardware-dependent, ~3.451ms vs 2ms threshold. Not actionable.

## Toolchain
- nats-server: v2.14.5
- Go: present
- Cargo/Rust: present
- gcc + libseccomp-dev: present

## Section-by-section results
| Section | Name | Pass/Fail |
|---------|------|-----------|
| Pre-flight | Toolchain | 3/0 |
| 1 | Go build | 2/0 |
| 2 | Rust agent build | 1/0 |
| 3 | C11 components | 4/0 |
| 4 | Smoke tests | 58/1 (known C11 p50) |
| 5 | Debian package | 2/0 |
| 6 | Systemd units | 9/0 |
| 7 | Shell syntax | 34/0 |
| 8 | Key file presence | 10/0 |
| 9 | Debian metadata | 5/0 |
| 10 | Windows packaging | 6/0 |
| 11 | Update mechanism | 2/0 |
| 12 | Gatekeeper module | 2/0 |

## Plan items verification (ASP-524 plan)
All 3 plan items confirmed in place:
1. **nats-server v2.14.5** — Both `nightly.yml` and `ci.yml` already use v2.14.5; host also on v2.14.5
2. **Baseline doc updated** — `NIGHTLY_PACKAGING_DEPLOY_CHECK.md` already reflects merged smoke (58 tests), nats-server version, and gatekeeper row
3. **Gatekeeper module check** — Section 12 already exists in `check-nightly.sh` with presence + syntax checks

## Baseline deviations from ops doc
None. Baseline matches: 80 passed, 1 known failure (C11 p50).