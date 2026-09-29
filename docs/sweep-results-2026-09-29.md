# Daily Implementation Sweep — 2026-09-29

**Ticket:** [ASP-693](/ASP/issues/ASP-693)
**Status:** COMPLETE

## Queue sweep

| Engineer | Open implementation tickets |
|---|---|
| Opencode | this sweep only |
| Aspen Fast Coder | none |

No queued work. The company-wide open set is 9 issues: 3 blocked, 5 `in_review`,
this sweep. Nothing assignable to implementation. The sweep therefore took the
highest-priority actionable item it could **prove**, and it is a security gate.

## Actionable item: F-014 signed-package gate is dead on `master`

`verify-package-signature` installs `pytest` only; `tests/conftest.py:3` imports
`yaml`; pytest loads `conftest.py` for every module under `tests/`. The F-014
gate aborted at collection with exit 4 and ran zero assertions, while the job
installs `gnupg2` so the `skipif(not gpg)` guard did not apply. Green checkmark,
zero verification.

**The fix already existed and was never merged.** [ASP-682](/ASP/issues/ASP-682)
is closed `done`; its one-line commit `6ce85f7` sits only on
`fix/ci-verify-package-signature-pyyaml`:

```bash
git merge-base --is-ancestor 6ce85f7 master   # -> NO
git show master:.github/workflows/ci.yml       # still `pip install pytest`
```

Landed the fix and added a guard for the class:
`test_ci_jobs_running_tests_install_conftest_deps` derives the third-party
imports of `tests/conftest.py` via `ast` and requires every CI job that runs
`pytest tests/` to `pip install` them. It reported
`{'verify-package-signature': ['yaml']}` against the unfixed tree and passes
after the fix.

Plan: `docs/plans/ASP-693.md` · Compound: `docs/solutions/asp-693-ci-conftest-dependency-gate.md`

## Stale CI branches — audited, no code landed

Two branches have been carried in sweep backlogs since 2026-09-18. Both are
already covered on `master` by a different route; they are stale, not pending.

| Branch | Claim | Verdict on `master` |
|---|---|---|
| `origin/fix/ci-assertion-hardening` | guard NATS install, drop `grep -q built-in` | `smoke-test.sh:37` has the PATH + `command -v` skip guard; `smoke-test.sh:58` and `ci.yml:121` use `--help >/dev/null`. Its `tests/test_ci_assertions.py` collides add/add with `d2738a8`, which already asserts the same contracts. |
| `origin/fix/test-collection-optional-deps` | `importorskip` for aiohttp / mcp | `tests/test_server.py:5` has the aiohttp `importorskip`; `tests/test_memory_mcp.py:20-24` has a module-level `pytest.skip` for `mcp.server`. |

Both should be deleted, not merged — merging either would be a no-op at best.
Deletion is a repo-hygiene call, flagged here rather than taken unilaterally.

## Verification

| Check | Result |
|---|---|
| Guard red-then-green | fail on unfixed `ci.yml` (`verify-package-signature: ['yaml']`) → pass after |
| `pytest tests/` | **468 passed, 1 failed, 3 skipped** (was 469 + 2 new = 472 total) |
| `pytest tests/test_package_signatures.py` | **9 passed** — F-014 assertions reachable, `gpg` present |
| `pytest tests/test_ci_assertions.py` | 16 passed (was 14) |
| `ruff check tests/test_ci_assertions.py` | All checks passed |
| `bash -n scripts/*.sh` | 43/43 OK |

The 1 failure is `tests/test_holographic_ingest.py::test_explicit_db_env_writes_holographic`
— `ruamel.yaml` not installed in this workspace. Confirmed pre-existing: it
fails identically on clean `origin/master` with my changes stashed. Not a
regression and not in scope.

## Backlog carried forward

- **HybridIntel stub** (`src/python/services/hybrid_intel.py`) — 30 lines, no
  importer anywhere in the tree; only `src/python/lib/skills/osint-threat/SKILL.md`
  names it. Carried since 2026-09-16. It is either dead code to delete or an
  unimplemented OSINT engine to design — that is an Architect call, not a sweep
  call. Escalated.
- Network marketplace fetch (`MARKETPLACE_URL`) — Architect decision, already
  escalated 2026-09-19.
- ADR-0012 operator-of-record x6 follow-ups — unmerged draft ADR.
- `asp-514-adr-0008-operator-binding` and the two stale CI branches above.

## Notes

- [ASP-680](/ASP/issues/ASP-680) reproduced again this run: `PAPERCLIP_API_URL`
  is `http://10.242.32.120:3100` and refuses every call; the tailnet base
  `http://100.78.55.13:3100` answers 200. Patch is staged under
  `/home/tech/.aspen/ops`, CHG-0023 proposed, owner `aspen`. Not implementation's
  lever; untouched.
- ASP-678's branch is 3 commits ahead of `master` and still unmerged
  (`9c6d5e5`, `1ca4d7f`, plus `e3b1d59` content) — same stranding shape as
  ASP-682, and the reason ASP-680's diagnosis is not on the default branch yet.
