# Nightly latest

- Timestamp (UTC): 2026-09-29T14:21:38Z
- Git SHA: 6fd9c8d711ea0f272df659168bc4b794cb6e743f
- Verdict: PASS
- check-nightly: 149/150
- Deviations:
  - C11 p50 3.690 ms (known hardware deviation; ADR 0001 threshold is 2 ms). Same single known
    failure as the prior consecutive nightlies. `bash scripts/bench-sandbox.sh 200`:
    `c11_internal p50 3.690`, `p95 4.654`, `mean 3.773` (N=200), inside the documented
    3.2–3.7 ms host range.
- Issue: ASP-691

## Notes for this run

Static inventory matched the runbook baseline with no deviation: 16 systemd unit files (8 in
`systemd/`, 8 in `dist/pkgroot/lib/systemd/system/`), 8 `.service.d` drop-in dirs in each tree,
complete `debian/DEBIAN/` metadata (`starship-os 2.2.0 amd64`), `VERSION` 2.2.0 consistent with
`debian/DEBIAN/control`, `scripts/update.sh` present and executable, all 6 `packaging/windows/`
artifacts present, 44 shell scripts passing `bash -n`. Toolchain: nats-server v2.14.5 (matches
baseline), go 1.26.0, cargo 1.93.1, Python 3.14.4, pytest 9.1.1. ISO/deb image builds SKIP by design
on this host; static checks only. Smoke suite inside section 4: 61 passed, 1 failed (C11 p50 only).

Aspen local-proof after Auditor `plan_only` stall (ASP-692). Authoritative invocation used the repo
`.venv` (`python3` = that interpreter). An earlier invocation in the same heartbeat, under Hermes
`python3` (missing `pygments` and `yaml`), false-failed 10 checks and is not the record.

The holographic skip fix is in the recorded SHA (`tests/test_holographic_ingest.py` resolves
`HERMES_AGENT_ROOT` and skips on any `ModuleNotFoundError`). Python suite on that tree:
**466 passed, 4 skipped, 0 failures**. The baseline row still reads `470 passed, 4 skipped`; that
gap is test-count drift, not new failures.

This file is the live record and is overwritten in place by each nightly run. Do not add
`docs/ops/nightly-results-*.md`.
