# ASP-721 — a stale branch is not a cherry-pick candidate

**Ticket:** [ASP-721](/ASP/issues/ASP-721) · Compound step recorded by [ASP-750](/ASP/issues/ASP-750)

## Problem

`origin/fix/ci-assertion-hardening` (`236f7b1`) was the only home of the `set -euo pipefail` +
`command -v nats-server` guard on the `smoke` job's install step. But its base (`1ccf000`,
PR #15) predates `security-devonly-isolation`, `verify-package-signature`,
`security-model-digests` and ~12 later `scripts/smoke-test.sh` checks, and its version of
`tests/test_ci_assertions.py` deletes 12 of the tests master now holds.

Cherry-picking it would have looked like the cheap fix and quietly:

- removed CI coverage that landed after the fork point, and
- downgraded nats-server `v2.14.5` → `v2.14.3`.

Instead the one useful hunk was ported **by hand** in `0489e41` (PR #67): two lines into the
smoke job's install step plus a contract test scoped to that block.

## Rules worth keeping

1. **Diff the stale branch's base against current master before trusting it.** If master moved
   past the fork point, port by hand; do not cherry-pick.

   ```sh
   base=$(git merge-base origin/master origin/<branch>)
   git log --oneline "$base"..origin/<branch> --name-only   # every file it touched
   for f in <those files>; do
     git diff --stat origin/master origin/<branch> -- "$f"  # zero hunks = superseded
   done
   ```

   Zero surviving hunks across *every* touched file — or you have read every hunk and recorded
   why it is dead. Nothing else counts.

2. **Never inherit a stale branch's version pins.** A pin is a hypothesis from the day the branch
   forked. Keep master's newer pin (`v2.14.5` here, not `v2.14.3`); downgrading a
   security-relevant dependency to satisfy a stale diff is worse than the branch ever was.

3. **Scope contract tests to the block they guard.** A file-wide
   `assert "set -euo pipefail" in ci_text` passes when *any* job has the string. Scope to the
   `smoke` block — `_smoke_job()` in `tests/test_ci_assertions.py` regexes the block — so the
   assertion dies with the block it protects.

4. **A test-count DoD is an assumption, not a spec.** The ticket said `16 passed`; master's file
   held 14 tests, so 15 is correct post-change (`14 -> 15`, full suite `467 passed / 4 skipped`).
   Assert *which* tests survive, not just the total — a count can be satisfied by deleting one
   test and adding another.

5. **`pipefail` is the part with teeth.** GitHub Actions runs `run:` blocks under `bash -e`, so
   the `command -v` guard is idempotency — a failed `curl | tar xz` already fails the step.
   `set -euo pipefail` is what makes the `curl` half of the pipeline fail the step, and `-u`
   turns an unset variable in the multi-line step into a hard failure.

## Key insight

**A stale branch's hunks are hypotheses, not requirements.** Each hunk solved a problem on the
day it forked; read it against current `master` and ask whether that problem still exists. Two of
the branch's five did not — the `export PATH=` rewrites (later commits set `PATH` at step level
already) and the C11 `--help` hunk (its contract test already passed on master). What survived
was the guard, and the guard needed a test, because a two-line CI change with no assertion
regresses silently.

## Related

- `docs/plans/ASP-721.md` — the port plan this learning came from
- `docs/solutions/asp-522-ci-hardening.md` — the `command -v nats-server` guard pattern itself,
  applied to `smoke-test.sh`; ASP-721 applied it to the CI install step

## Files

- `.github/workflows/ci.yml` — `smoke` job install step: `set -euo pipefail`, `command -v` guard,
  `v2.14.5` pin
- `tests/test_ci_assertions.py` — `test_ci_nats_install_is_guarded`, scoped to the `smoke` block
