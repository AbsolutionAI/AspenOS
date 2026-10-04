# ASP-733 — Host-relative paths, and the class of bug a green CI suite can hide

## The pattern

Aspen OS wrote for `/home/tech`, then fixed up at install. That is a reasonable
deployment choice and a terrible default for code: the author gets a working
system, everyone else gets a path that silently does not exist.

What made it expensive was not the literals. It was that **the test suite could
not see the problem**, for three separate reasons that reinforced each other:

1. **The assertion was self-cancelling.** `test_cli_no_ingest_dir_uses_default`
   wrapped its real check in `if default.exists():`. On any host without
   `/home/tech` the guard was false, the body was skipped, and the test passed
   *because the code was broken*. The only host that ever exercised the
   assertion was the one host where the hardcoded path happened to work.
2. **The unit was environmental, not hermetic.** The test needed a writable
   directory but derived it from the ambient environment, so it either wrote
   outside `tmp_path` or skipped.
3. **A required CI job failed on it, and the fix went the wrong way.**
   [ASP-730](/ASP/issues/ASP-730) added the suite to CI and got
   `Permission denied: '/home/tech'`. The tempting fix is to make the test
   conditional or to stub the path — both make CI green and leave production
   exactly as broken.

## What actually fixed it

Deriving at **call time** from the environment, with the override precedence
explicit and ordered:

```
explicit per-path env var  →  ASPEN_DATA_HOME / XDG_DATA_HOME  →  $HOME
```

The call-time part is load-bearing and easy to get wrong. A module-level
constant computed at import freezes whichever host imported the module first,
which reintroduces the identical bug under a new name — and makes it
un-testable, because a test cannot relocate `$HOME` for a value that was
already computed. `scripts/paths.py` therefore exposes functions, and
`tests/test_home_paths.py::test_derivation_is_per_call_not_frozen_at_import`
asserts that property directly rather than trusting it.

`DEFAULT_INGEST_DIR` and friends were kept as module attributes because four
`agents/*_memory.py` modules import them, but every call site that *matters*
resolves the function instead. Two names, two jobs: the attribute is an import
convenience, the function is the source of truth.

## $HOME was the deployment target all along

`$HOME` **is** `/home/tech` on the packaged host. So deriving from `$HOME` is a
strict generalization, not a migration — the existing deployment resolves to
byte-identical paths and every other host resolves to its own. That fact is
what made this a one-commit change instead of a data-migration project, and it
is worth checking *before* designing the fix.

## The finding that changed the plan

The plan assumed the risky case was `systemd/agnetic-agent@.service`: it runs
as `User=agnetic`, so `$HOME` derivation would relocate the store. Reading the
unit instead of assuming showed the opposite — that path was **already dead**:

```
ProtectHome=true      # /home is entirely inaccessible to the unit
ReadWritePaths=/var/log/starship /var/log/agnetic /tmp
```

`/home/tech` sits behind `ProtectHome=true`, so ingest raised `EACCES` on every
command, and `agent_daemon.py:84` swallowed it at `log.debug`. The packaged
deployment has been silently dropping agent memory ingest, and the hardcoded
path is why nobody found out.

Two lessons worth keeping:

- **A `$HOME`-derived default fails the same way a hardcoded one does here.**
  Neutral is not fixed. Checking "does my change make this worse?" is a
  different question from "does this work?", and only the second one matters.
- **Choosing the durable data root is an architecture decision**, because it
  moves the unit's `ProtectHome`/`ReadWritePaths` hardening and requires
  migrating existing data. Escalated rather than guessed. `ASPEN_DATA_HOME`
  exists so that decision lands as one `Environment=` line instead of a
  re-derivation.

## Guard, do not just fix

`tests/test_home_paths.py::test_no_functional_source_hardcodes_the_operator_home`
greps `scripts/`, `services/scripts/` and `agents/` for `/home/tech` and fails
on anything not justified in an explicit allowlist. Each entry carries the
substring that must appear on the offending line, so a *new* line in an
exempted file still fails, and `test_every_allowlisted_exception_is_still_live_and_justified`
fails if an exemption stops matching anything at all — a stale exemption reads
like an approved exception while silently covering whatever comes next.

The two `subprocess` tests run the real CLI with `$HOME` pointed at `tmp_path`,
including one with **no** override at all. That is the assertion the hardcoded
literal made impossible: it cannot pass on any host, so it can only pass for the
right reason.

## Adjacent defects found, not silently fixed

- `services/scripts/start-all-agents.sh` **does not parse** — `local
  _config_json=${${1//-/}}`, an unbalanced quote, and a stray
  `> /dev/null) || { return; }`. Pre-existing on master, no callers. The
  `PROJECT_ROOT` derivation is correct, but the file cannot run until ~12 lines
  of unrelated corruption are repaired, and guessing the intent of a dead
  3 KB script with no tests is not a call worth making inside a path ticket.
- `src/python/lib/scripts/push-ci-workflows.py` is a **drifted mirror** of the
  live script carrying the same token scrape. 10 of its 28 files already differ
  from `scripts/`, so it is a stale vendored copy, not a second live path.
  Widening the diff to re-sync a mirror is churn; deleting it is a decision
  above this ticket.
- `services/scripts/shared-store-init.sh` declared `SHARED_STORE` but read
  `$SHARE_STORE` at all six use sites, and called an undefined `log`. Fixed,
  because leaving a known-broken variable in a file being rewritten is worse
  than the two-line behavior change — but it *is* a behavior change and is
  called out for QA.

## Verification worth copying

| Check | Why it matters |
|---|---|
| full suite at baseline `HOME` | no regression (466 → 488 passed, same 4 optional-dep skips) |
| full suite with `HOME` relocated to `mktemp -d` | the actual ticket criterion; pytest must stay importable via `PYTHONPATH`, since it lives in `$HOME/.local` here |
| full suite with `HOME` unset | systemd units have no `HOME` |
| full suite with `HOME` mode `555` | surfaces `EACCES`; the one failure is `gpg` refusing to create `~/.gnupg` in an unrelated signature test |
| `diff` of the real `~/.aspen` tree before/after | proves acceptance criterion 2 — nothing written outside `tmp_path` |
| `bash -n` plus running each installer from a relocated copy | a derivation that only works in-tree is not a derivation |
