# Nightly Check Results — 2026-09-26T12:20 MDT

**Run ID:** 863a67cf-aefc-4ae7-98f6-770f0279b2e5
**Run issue:** ASP-656
**Runbook:** `docs/ops/NIGHTLY_PACKAGING_DEPLOY_CHECK.md`
**Workspace:** `/home/tech/projects/aspen-dev/repos/aspen-os` @ `0ab00d9` (master, ahead 1)

## Verdict: PASS (149/150, known hardware deviation only)

## Suite Results

| Check | Result | vs Baseline |
|---|---|---|
| `scripts/check-nightly.sh` | **149 passed, 1 failed** (150 total, 22 sections) | Match |
| `make smoke` | **61 passed, 1 failed** (62 total) | Match |
| `make iso-smoke` | **32 passed, 0 failed** | Match |
| Python suite (section 13) | **470 passed, 4 skipped**, 0 failures | +4 vs baseline table (refreshed below) |

`check-nightly.sh` exit code `1` (= number of failed checks), elapsed 67.99s.
`make smoke` exit code `2`, elapsed 6.82s. `make iso-smoke` exit `0`, elapsed 0.06s.

## Known Failure

- **C11 p50 benchmark** — `c11_internal` p50 = **3.651 ms** vs the ADR 0001 threshold of 2 ms.
  Hardware-dependent, non-actionable on this host. Same single known failure as the previous
  five consecutive nightlies. p50 has drifted up slightly: the runbook records a 3.2–3.5 ms
  observed range, and 3.651 ms sits just above it. Still the same order of magnitude and the
  same known deviation, but the trend is worth watching if it keeps climbing.

## Toolchain

| Component | Version | vs Baseline |
|---|---|---|
| nats-server | v2.14.5 | Match |
| go | 1.26.0 linux/amd64 | — |
| rustc / cargo | 1.93.1 | — |
| python3 | 3.14.4 | — |

`nats-server` required the runbook PATH export (`$HOME/go/bin:$HOME/.local/bin:$PATH`);
resolved from `/home/tech/go/bin/nats-server`.

## Static Inventory

| Item | Observed | Baseline | Status |
|---|---|---|---|
| systemd unit files | 18 (9 in `systemd/`, 9 in `dist/pkgroot/lib/systemd/system/`) | 18 | Match |
| Debian metadata | `control`, `postinst`, `postrm`, `prerm` all present | 4/4 | Match |
| `debian/DEBIAN/control` | `starship-os` 2.2.0 amd64 | same | Match |
| `VERSION` vs control | 2.2.0 vs 2.2.0 | consistent | Match |
| `scripts/update.sh` | present, executable, 6388 bytes | present + exec | Match |
| Windows packaging | 6/6 (`install.bat`, `configure.bat`, `uninstall.bat`, `staragent.exe`, `staragent.yaml`, `README.txt`) | 6/6 | Match |
| Shell syntax coverage | 44 scripts (43 `scripts/`, 1 `packaging/`), 0 `bash -n` failures | 44 | Match |
| ISO / deb build | SKIP by design (Option B, `docs/ops/ISO_BUILDER.md`) | SKIP | Match |

Section 6 validated all 9 canonical units individually (nats, staragent, agent template,
dashboard, fleet, health-checker, mesh target, status bridge). Section 5 built a real
`.deb` (>1 MB) and passed, so the deb path is exercised even though ISO source build is skipped.

## Deviations from Baseline

1. **Python test count is stale in the runbook** — observed 470 passed / 4 skipped, table said
   466 / 4. Updated `docs/ops/NIGHTLY_PACKAGING_DEPLOY_CHECK.md` in this run per the runbook's
   own instruction to refresh the table when suites gain checks.
2. **C11 p50 marginally above the documented range** — 3.651 ms vs the 3.2–3.5 ms range in the
   runbook's "Known deviations" section. Same known failure, slightly worse number.
3. **Repo scratch pollution (not a runbook check)** — the working tree carries untracked
   `'$PAPERCLIP_SCRATCH_DIR'/` and `'$PAPERCLIP_RUN_SCRATCH_DIR'/` directories at the repo root.
   The `$` is literal: a prior run created them from an unexpanded shell variable. They hold
   real disposition docs, so this run did not move or delete them. Tracked as a child issue.
4. **Unlanded prior results docs** — five `nightly-results-2026-09-25T*.md` files are written
   but never committed, and `master` is 1 commit ahead of `origin/master` (the 2026-09-24
   results commit). Not a check failure; noted so the record is complete.

## Duration

- `scripts/check-nightly.sh`: 67,984 ms
- `make smoke`: 6.82 s (also runs inside section 4 of the nightly suite)
- `make iso-smoke`: 0.06 s
- Full sweep: ~75 s
