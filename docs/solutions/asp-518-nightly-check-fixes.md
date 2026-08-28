# Learning: Nightly check must validate sibling repo dependencies and shell syntax

**Ticket:** ASP-518

## Problem

The nightly check introduced in ASP-512 had two gaps:

1. **Sibling repo checkout missing.** The smoke test suite gained a `fleet-bus smoke` check (ASP-493) that exercises the `aspen-edge-rrm` fleet bus module in-process. The nightly workflow (`nightly.yml`) didn't clone sibling repos, so this check would fail in CI at 02:00 UTC every night.

2. **Shell syntax regression in `restore.sh`.** Line 157 used `[[ ! - "$archive" = /* ]]` — the `-` after `!` is invalid in bash test syntax. This was a pre-existing bug in the repo that `bash -n` now catches. The correct forms are `[[ ! "$archive" = /* ]]` or `[[ "$archive" != /* ]]`.

Running `scripts/check-nightly.sh` locally surfaced 4 failures:
- `staragent builds` — local cargo path mismatch (not a repo bug; CI installs via rustup)
- `smoke test suite` — 1 failure (`C11 p50 under 2ms`), performance-dependent on local machine
- `deb package builds` — local `dpkg-deb` liblzma conflict from npm paperclip (not a repo bug)
- `restore.sh` — genuine shell syntax error (fixed)

## Fix

1. **`scripts/restore.sh` line 157:** Removed spurious `-` after `!` in `[[ ! "$archive" = /* ]]`.
2. **`.github/workflows/nightly.yml`:** Added sibling repo checkout step (clones `aspen-edge-rrm` and `aspen-swarm-manager` at pinned commits from `third_party/pins.json`), matching the same pattern used in `ci.yml`.
3. **`docs/ops/NIGHTLY_PACKAGING_DEPLOY_CHECK.md`:** Updated section table to note fleet-bus smoke relies on sibling repos, and added a CI infrastructure subsection.

## Patterns to reuse

- **Run `check-nightly.sh` before merging nightly workflow changes.** The script catches shell syntax errors, missing files, and broken build steps that GitHub Actions would only surface after the next scheduled run.
- **When adding a smoke test that depends on a sibling repo**, update both the CI workflow (`ci.yml`) and the nightly workflow (`nightly.yml`) to checkout that repo. The nightly workflow is a separate file and does not inherit `ci.yml` steps.
- **Shell syntax checks catch real bugs.** The `bash -n` pass in Section 7 of `check-nightly.sh` caught a pre-existing bug in `restore.sh` that would have caused a runtime error on any restore operation.
- **Environment-specific failures (cargo path, dpkg-deb library conflicts) are expected locally.** The nightly check is designed for CI; local runs may have extra failures from toolchain differences. Always check whether a failure reproduces the actual CI environment before treating it as a repo bug.