# ASP-693 — A `done` status is not proof the fix is on the default branch

## Problem

The F-014 signed-package security gate did not run in CI, and had been "fixed"
already.

`.github/workflows/ci.yml` job `verify-package-signature` installed only
`pytest`, then ran `python -m pytest tests/test_package_signatures.py -q`.
`tests/conftest.py:3` imports `yaml`. pytest loads `conftest.py` for every
module under `tests/`, so collection died before any F-014 assertion ran — the
gate was a green checkmark that verified nothing. The runner installs
`gnupg2`, so the `skipif(not gpg)` in that test file did **not** rescue it.

The fix was already written: [ASP-682](/ASP/issues/ASP-682), commit `6ce85f7`,
one line, `pip install pytest` → `pip install pytest pyyaml`. ASP-682 is closed
`done`. The commit lives only on `fix/ci-verify-package-signature-pyyaml` and
was never merged.

## The transferable lesson

Two independent failures compounded:

1. **A security gate that fails open.** The gate did not report failure. It
   reported success while testing nothing, which is the worst failure mode for a
   gate — a red CI run gets fixed, a silently-green one does not.
2. **`done` was asserted about the commit, not about `master`.** The issue
   closed on evidence that correct code existed somewhere, not that CI would run
   it. The audit that mattered was one line and was never run:

   ```bash
   git merge-base --is-ancestor 6ce85f7 master   # -> NO
   ```

### Rule to reuse

Before closing an issue whose deliverable is a commit, prove the commit is
reachable from the branch CI builds:

```bash
git merge-base --is-ancestor <sha> origin/master || echo "STRANDED"
```

If it prints `STRANDED`, the work is not done regardless of what the commit
message, the branch name, or the issue status say.

### Rule to reuse

A CI job that runs `pytest` under a directory with a `conftest.py` has an
undeclared dependency on everything `conftest.py` imports. Derive the contract
from `conftest.py` instead of trusting the job's install line to stay in sync:

```python
tree = ast.parse((ROOT / "tests" / "conftest.py").read_text())
# third-party top-level modules → must appear in the job's pip install line
```

`test_ci_jobs_running_tests_install_conftest_deps` in
`tests/test_ci_assertions.py` does this. It failed against the unfixed
`ci.yml` with `{'verify-package-signature': ['yaml']}` and passes after the one-
line fix, so the guard is proven by a red-then-green transition rather than by
assertion.

## Verifying a CI job's dependency list without a runner

`pip install` lists are hard to check by reading. Shadow the module instead —
hermetic, no venv, no network:

```bash
mkdir -p "$SCRATCH/noyaml"
printf 'raise ImportError("No module named %s")\n' "'yaml'" > "$SCRATCH/noyaml/yaml.py"
PYTHONPATH="$SCRATCH/noyaml" python3 -m pytest tests/test_package_signatures.py -q
# ImportError while loading conftest ... exit=4
```

exit 0 with `yaml` present, exit 4 without. That is the CI failure mode,
reproduced on a workstation in under a second.

## Result

- `verify-package-signature` installs `pyyaml`, matching sibling job
  `security-model-digests` which already did.
- `tests/test_ci_assertions.py`: two tests added (14 → 16), including the
  generic conftest-dependency contract. `DIST_ALIASES` covers module names that
  differ from their distribution (`yaml` → `pyyaml`).
- `tests/test_package_signatures.py`: 9 passed locally with `gpg` present —
  the gate's assertions are now reachable.
- No gpg fixture, key, or threat-model content touched.
