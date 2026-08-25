# CI assertion hardening — brittle smoke gates

## Problem

The Starship OS CI had two fragile assertions that caused false-negative
failure notifications without actual product breakage:

1. **NATS `gen accounts conf valid` check** — Overwrote `PATH` to
   `$HOME/go/bin:/root/go/bin`, excluding `/usr/local/bin` where the CI
   smoke step installs `nats-server`. The silent `curl | tar` install
   pattern also masked failures (no `set -e` guard, no `command -v`
   verification).

2. **`sandbox_run --help | grep -q built-in`** — The C11 sandbox binary's
   `--help` output changed during a refactor and no longer contained the
   string `built-in`. This caused a false failure even though the binary
   built correctly and passed runtime checks (echo, deny-mount).

These two false signals generated 43 of the 50 unread GitHub notifications
on the `AbsolutionAI` account on 2026-08-24, because every Hermes PR branch
that wasn't rebased onto the latest `master` would fail these checks.

## Solution

### NATS install hardening (`.github/workflows/ci.yml`, `scripts/smoke-test.sh`)

- Guard install with `command -v nats-server` so the step is idempotent
  and silently skipped when the binary already exists
- Add `set -euo pipefail` to the CI smoke run block so a failed `curl`,
  `tar`, or `cp` aborts immediately instead of silently continuing
- Add `/usr/local/bin` to `PATH` in the `gen accounts conf valid` check
  inside `smoke-test.sh`
- Make the check **skip** (not fail) when `nats-server` is absent, since
  other checks in the same script already cover the template and
  generation script existence

### C11 sandbox assertion (`.github/workflows/ci.yml`, `scripts/smoke-test.sh`)

- Replace `--help | grep -q built-in` with `--help >/dev/null` — verifies
  the binary produces help text and exits zero without coupling to
  specific wording
- The runtime assertions already on lines 61–62 (`-- echo ok` and
  `-- mount` deny) cover actual sandbox behavior

### Contract tests added

A subsequent refinement (`236f7b1` on `fix/ci-assertion-hardening`) added
`tests/test_ci_assertions.py` — a dedicated contract test that asserts:

- The `gen accounts conf valid` smoke check includes `/usr/local/bin` in PATH
- The check skips gracefully when `nats-server` is absent
- Neither `ci.yml` nor `smoke-test.sh` contain `grep -q built-in` (regression guard)
- The CI workflow guards NATS install with `command -v`
- `sandbox_run --help` uses `>/dev/null` not `grep -q built-in`

The same refinement also minor-cleaned the PATH order in `ci.yml`
(`/usr/local/bin` first) and the skip mechanism in `smoke-test.sh`
(using `exit 0` instead of the accumulator `PASS=$((PASS+1))`).

## Reflection

The root cause was coupling CI assertions to incidental output strings
rather than functional behavior, and using brittle PATH construction in
subshells. The NATS check was especially insidious: CI *looked* like it
was installing the dependency, but the PATH rewrite in the child shell
made the binary invisible.

The inbox review doc (`docs/ops/GITHUB_CI_INBOX_REVIEW_2026-08-25.md`)
identified these correctly as "real CI contract fixes" with minimal blast
radius.

## Files changed

- `.github/workflows/ci.yml` — `set -euo pipefail`, `command -v` guard
  for NATS install, `sandbox_run --help >/dev/null` replacement
- `scripts/smoke-test.sh` — PATH fix + skip-on-missing for NATS check,
  `sandbox_run --help >/dev/null` replacement
- `tests/test_ci_assertions.py` — contract tests for CI assertion patterns

## Related

- ASP-463 (hourly implementation sweep — CI inbox review trigger)
- `docs/ops/GITHUB_CI_INBOX_REVIEW_2026-08-25.md` — full inbox analysis
