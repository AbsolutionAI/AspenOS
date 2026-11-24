# Nightly Check Results — 2026-11-24T09:00 UTC

**Run ID:** ASP-958
**Runbook:** `docs/ops/NIGHTLY_PACKAGING_DEPLOY_CHECK.md`
**Workspace:** `/home/tech/projects/aspen-dev/repos/aspen-os` @ `0d1bd83` (master, ASP-958 branch)

## Verdict: PASS (158/159, known hardware deviation only)

## Suite Results

| Check | Result | vs Baseline |
|---|---|---|
| `scripts/check-nightly.sh` | **158 passed, 1 failed** (159 total, 23 sections) | Match |
| `make iso-smoke` | **32 passed, 0 failed** | Match |
| Python suite (section 13) | **573 passed, 3 skipped**, 0 failures | +107 vs baseline table |

`check-nightly.sh` exit code `1` (= number of failed checks), elapsed ~170s.
`make iso-smoke` exit `0`.

## Known Failure

- **C11 p50 benchmark** — `c11_internal` p50 exceeds the ADR 0001 threshold of 2 ms.
  Hardware-dependent, non-actionable on this host. Same single known failure as all
  previous consecutive nightlies.

## Toolchain

| Component | Version | vs Baseline |
|---|---|---|
| go | 1.26.0 linux/amd64 | — |
| rustc / cargo | 1.93.1 | — |
| python3 | 3.14.4 | — |

## Static Inventory

| Item | Observed | Baseline | Status |
|---|---|---|---|
| systemd unit files | 9 in `systemd/` | 9 | Match |
| Debian metadata | `control`, `postinst`, `postrm`, `prerm` all present | 4/4 | Match |
| `debian/DEBIAN/control` | `starship-os` 2.2.0 amd64 | same | Match |
| `VERSION` vs control | 2.2.0 vs 2.2.0 | consistent | Match |
| `scripts/update.sh` | present, executable | present + exec | Match |
| Windows packaging | 6/6 | 6/6 | Match |
| Shell syntax coverage | 44 scripts, 0 `bash -n` failures | 44 | Match |
| ISO / deb build | SKIP by design (Option B) | SKIP | Match |

## Deviations from Baseline

1. **Python test count is well above baseline** — 573 passed / 3 skipped vs the
   runbook's 466 / 4. The test suite has grown substantially since the baseline was set.
2. **C11 p50** — same known hardware-dependent deviation.
3. **Uncommitted results docs** — previous `nightly-results-2026-09-25T*.md` docs remain
   uncommitted on master. Not a check failure; noted for record completeness.

## Duration

- `scripts/check-nightly.sh`: ~170 s
- Full sweep: ~170 s (ISO smoke runs inside check-nightly section 4)