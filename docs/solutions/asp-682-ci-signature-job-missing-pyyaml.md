# ASP-682: `verify-package-signature` failed on a missing transitive pytest dep

## Problem

The `verify-package-signature` job in `.github/workflows/ci.yml` installs only `pytest`
and then runs `python -m pytest tests/test_package_signatures.py -q`. The job died during
collection with `ModuleNotFoundError: No module named 'yaml'` (run 36263233523) — it never
reached the F-014 signed-package assertions.

The trigger is `tests/conftest.py`, which imports `yaml` at module scope. Collection
executes `conftest.py` before any test module, so *any* job in the matrix that runs pytest
against this tree inherits that import — even a job whose own test file never touches YAML.
The sibling job `security-model-digests` already installed `pyyaml`, so the correct fix
was inferable from the workflow itself.

## Solution

One line in `.github/workflows/ci.yml`, matching the sibling job:

```diff
           sudo apt-get install -y -qq gnupg2
-          pip install pytest
+          pip install pytest pyyaml
       - name: F-014 signed-package gate (unsigned/tampered fixtures must fail)
         run: python -m pytest tests/test_package_signatures.py -q
```

No gpg fixtures, keys, or threat-model text were touched. Merged via PR #48 (`3a6f065`).

## Key findings / gotchas

- **`conftest.py` imports are a hidden dependency for every pytest job in the matrix.** A
  per-job `pip install` line only declares what that job's *test module* imports. When a
  `conftest.py` imports a third-party lib, every job running pytest in that tree must
  install it, regardless of the target test file. The right long-term fix is a
  `requirements-test.txt` (or `pip install -e '.[test]'`) sourced by all jobs, so the
  matrix has one dependency surface instead of four hand-maintained `pip install` lines.
- **Read the sibling jobs before diagnosing.** Three of the four pytest jobs already
  installed `pyyaml`; the fourth was the outlier. This was a consistency bug, not a
  missing-dependency design problem.
- **Do not "fix" it by trimming the conftest import.** The obvious-looking wrong fix is to
  make `conftest.py` import `yaml` lazily so the signature job skips it. That trades a CI
  failure for a fixture that silently mis-parses threat-model documents in the jobs that
  *do* depend on it.

## Test evidence

| Case | Result |
|------|--------|
| `python -m pytest tests/test_package_signatures.py -q` with `pyyaml` present | 9 passed |
| Same command on the original job definition | collection error, `No module named 'yaml'` |
| `verify-package-signature` on PR #45 head `fed7ab6` after the fix | SUCCESS (run 36639602365, job 109648488575) |

The signature job's `F-014 signed-package gate` step is a fail-closed gate — it asserts
that *unsigned and tampered fixtures must fail*. It passing is positive evidence the gate
executes its assertions, not just that collection stopped erroring.

## Files

| File | Purpose |
|------|---------|
| `.github/workflows/ci.yml` | `verify-package-signature` job — added `pyyaml` |
| `tests/conftest.py` | Unchanged; the import that made `pyyaml` a real dependency |

## Future improvements

- Introduce `requirements-test.txt` and have every CI job install from it, removing the
  four divergent hand-written `pip install` lines (ASP-682 was the third drift this year
  between `verify-package-signature`, `security-model-digests`, and the smoke job).
- Consider a fast preflight (`python -c "import conftest_deps"`) that fails with a clear
  message naming the missing package, instead of surfacing a `ModuleNotFoundError` from
  inside collection.
