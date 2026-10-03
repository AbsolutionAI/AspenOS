# ASP-721 — Stale is not superseded: how to triage a long-lived unmerged branch

## Problem

[ASP-694](/ASP/issues/ASP-694) listed `origin/fix/ci-assertion-hardening` under
"branches safe to delete (content already on `master`)" on two pieces of
evidence. Both were wrong, and both were checkable in one command.

The evidence was:

- `scripts/smoke-test.sh:37` already has the PATH + `command -v` guard
- `scripts/smoke-test.sh:58` and `ci.yml:121` already use `--help >/dev/null`
- `tests/test_ci_assertions.py` collides add/add with `d2738a8`, "which asserts
  the same contracts"

Each of those is true and each is irrelevant to the question asked. The branch
touched three files. Two of them were genuinely superseded. The third,
`.github/workflows/ci.yml`, was checked at `smoke-test.sh` and never at the
branch's actual diff. One command settles it:

```sh
git show origin/master:.github/workflows/ci.yml | grep -n 'set -euo\|command -v nats-server'
# no matches
```

The `smoke` job's nats-server install had no guard on `master`.

## The transferable lesson

**Diff the branch's files, not the files you remember.** The triage compared
`scripts/smoke-test.sh` — the file whose *guards* it had already confirmed — and
generalized to the branch. The one genuinely-unique hunk lived in a file that
wasn't opened. A branch is superseded only when `git cherry` / `git range-diff`
shows zero surviving hunks, or when you have read every file in its diff.

**"Add/add conflict" is evidence of danger, not evidence of redundancy.** The
note treated a colliding file as a reason the branch was safe. It is the
opposite. `236f7b1` created `tests/test_ci_assertions.py` as a 5-test file;
`master` has since grown it to 16. Cherry-picking resolves add/add by taking one
side whole. That side deletes 12 tests, including three security gates
(`test_build_deb_stages_apparmor_profiles`, `test_postinst_loads_apparmor_without_enforce`,
`test_nightly_section_17_apparmor_deb_shipped`) and the F-014 conftest-dependency
gate. A reviewer who saw "conflict" and reached for "so it's a no-op" would have
shipped a security regression while believing they had deleted dead code.

This is the same failure mode as
[the F-014 gate that passed while testing nothing](asp-693-ci-conftest-dependency-gate.md):
a green-looking signal (`cherry-pick conflicts` → `no-op`) standing in for a check
nobody ran.

## The port, and what was deliberately not ported

`236f7b1` is based on `1ccf000` (PR #15). It predates three CI jobs
(`security-devonly-isolation`, `verify-package-signature`,
`security-model-digests`) and the `v2.14.3` → `v2.14.5` nats-server bump. Port
by hand:

- `set -euo pipefail` and the `if ! command -v nats-server` guard went in.
- The `v2.14.3` pin did not. Downgrading a security-relevant dependency to
  satisfy a stale diff is worse than the branch ever being.
- The two `export PATH=...:/usr/local/bin:$PATH` rewrites did not. `ci.yml:86`
  already sets `PATH: ...:/usr/local/bin:...` as step-level `env:`, and each
  `export` prepends to `$PATH`, so the directory survives. The branch was fixing
  a PATH problem that a later commit had already fixed upstream.
- The C11 `sandbox_run --help | grep -q built-in` → `> /dev/null` hunk did not.
  Out of scope, and `test_ci_c11_help_is_not_coupled_to_builtin_string` already
  passes on `master`.

The lesson generalizes past this issue: **a stale branch's hunks are hypotheses,
not requirements.** Read each one against current `master` and ask what problem it
solved, then check whether that problem still exists. Two of five did not.

## On the honest value note

`set -euo pipefail` is the hunk with teeth. GitHub Actions runs `run:` blocks
under `bash -e`, so `command -v` is idempotency, not correctness — a failed
`curl | tar xz` already fails the step. `pipefail` catches the partial-download
case, and `-u` catches an unset variable in this multi-line step.

It is still a small change. The value is not the guard; it is that the branch can
now be deleted with a recorded reason instead of parked indefinitely. **Repo
hygiene tasks should end in a decision, not in a deferral** — and when the
decision is "port the one useful hunk", the port needs a test, because a
two-line CI guard with no assertion regresses silently.

## Reusable check

```sh
# Before calling any unmerged branch superseded:
git log --oneline master..origin/<branch> --name-only   # every file it touched
for f in <those files>; do
  git diff --stat master origin/<branch> -- "$f"        # zero hunks = superseded
done
```

Zero surviving hunks across every touched file, or you read every hunk and
recorded why it is dead. Nothing else counts.

## The gate that caught the gate: "full suite still green" is a criterion

The QA gate returned `CE-GATE` on a change that was, functionally, correct. The
reason was one line of the success criteria — *full suite still green* — which
the first pass reported as `1 failed, 469 passed` and annotated "pre-existing,
not ours."

That annotation was true and useless. `tests/test_holographic_ingest.py` was
failing for a reason that had nothing to do with NATS, and the criterion said
the suite must be green. Two habits were in tension, and the criterion is the
one that holds.

**A pre-existing failure inside a criterion you are asserting is your
obligation.** "Not mine" is true of the diff and irrelevant to the criterion.
The blocker is a 3-line test fix; leaving it is not neutral, it leaves the
branch unmergeable.

The fix had its own lesson. The test re-imported the Hermes plugin and skipped
only on a `ModuleNotFoundError` naming `tools.registry` or `holographic`:

```python
except ModuleNotFoundError as exc:
    if "tools.registry" in str(exc) or "holographic" in str(exc):
        pytest.skip(...)
    raise
```

The local checkout fails one level earlier — on `ruamel` — so the allowlist
missed. Meanwhile `scripts/holographic_ingest.py:add_fact` catches `except
Exception` and returns `None`. **The test was stricter than the code it covers.**
A test that enforces more than its subject is not a stronger gate; it is a
dependency pin in disguise. Fix was `except ImportError` → `pytest.skip`, plus
reading the checkout root from the existing `HERMES_AGENT_ROOT` env var instead
of a hardcoded `/home/tech/...`.

The same gate pass found the *ported test itself* was weak: it asserted two
strings exist somewhere in `ci.yml`, while the DoD was *smoke job only* —
and job-level edits are exactly what could not be cherry-picked. A presence
assertion cannot see a leak. Worth checking on every port: **does the new test
fail if the thing you ported is removed, and if it is placed in the wrong
place?** Both answers were "no" before, "yes" now — verified by mutation, not
by reading.

## Files

- `docs/plans/ASP-721.md`
- `.github/workflows/ci.yml` — `smoke` job install step
- `tests/test_ci_assertions.py` — `test_ci_nats_install_is_guarded`
- `tests/test_holographic_ingest.py` — skip guard matches the code's isolation
