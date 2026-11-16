# ASP-837 — ADR-0012 step 1: operator-of-record registry

**Ticket:** [ASP-837](/ASP/issues/ASP-837) · QA gate: [ASP-847](/ASP/issues/ASP-847)

## Problem

ADR-0012 (Proposed) defines the operator-of-record binding model for DualHumanGate authorizations on non-sim plant profiles. No enrollment mechanism existed — `human_id` values were free strings with no canonical registry enforcing one human → one identity.

## Implementation

### Files

| File | Change |
|------|--------|
| `src/python/services/operator_registry.py` | NEW — `OperatorRegistry` class: local JSON-backed store at `/var/lib/aspen/operator-registry.json` |
| `scripts/operator-registry.py` | NEW — CLI with `enroll`, `list`, `revoke`, `show` subcommands |
| `tests/test_operator_registry.py` | NEW — 28 hermetic tests covering all operations and error paths |
| `docs/plans/ASP-837.md` | Implementation plan |

### CE-GATE items (Auditor, comment `d6f494af`)

1. **Fail closed on corrupt JSON.** `_load` catches `json.JSONDecodeError`, `IOError`, `OSError`, `TypeError` (extra keys in `Operator(**item)`), and `ValueError` (non-list root, non-dict items). Sets `_load_error = True` and empties `_operators`. `_persist` raises `RuntimeError` — no writes over corrupted data.

2. **Atomic persist.** Same-directory `.tmp` file write, `os.chmod(tmp, 0o600)`, then `os.replace(tmp, path)`. Matches `FilePulseBackend` pattern in `estop_watchdog.py`.

3. **Mode 0600.** `os.chmod(tmp, _DEFAULT_FILE_MODE)` where `_DEFAULT_FILE_MODE = 0o600`, independent of umask.

4. **Case-fold human_id uniqueness.** `_find_by_casefold(value)` checks both `human_id.lower()` and all `alias.lower()` across all operators. `enroll()` rejects a human_id that case-folds equal to an existing record — even revoked. Exact same-case re-enrollment after revoke is preserved.

5. **Alias cross-checks human_ids.** Alias collision uses `_find_by_casefold` which checks operators' `human_id` fields in addition to aliases. An alias matching an existing operator's `human_id` (case-insensitive) is rejected.

6. **Removed unused `import secrets`.**

### Key decisions

- **Monorepo interim SoR** in `src/python/services/`, matching the pattern of sentinel journals, gatekeeper audit, and service accounts.
- **JSON-file backend** (`/var/lib/aspen/operator-registry.json`). No SQLite dependency — inspectable, sufficient for initial enrollment. Follows established local-first pattern. SQLite upgrade can layer later without breaking the JSON schema.
- **Schema matches ADR-0012 §4-5:** `human_id` (canonical stable string), `display_name`, `enrolled_at`, `enrolled_by`, `aliases`, `status` (`active`/`revoked`), `plant_id`.
- **CLI subcommands** `enroll`, `list`, `revoke`, `show` — same pattern as `scripts/tool-anomaly.py`, `scripts/sentinel-audit.py`.
- **No gatekeeper integration** in this step (follow-up ASP-777). This step is the registry itself.

## Testing

```
python3 -m pytest tests/test_operator_registry.py -q
28 passed in 0.08s

python3 -m pytest tests/ -q
544 passed, 4 skipped
```

## What was learned

- **CE-GATE is a gating mechanism, not a review substitute.** Auditor flagged 6 items (1 blocking for fail-open + 3 blocking for persist/umask/case-fold, 2 non-blocking). Each was concrete, testable, and had a clear pass criterion. The pipeline works as designed: implement → QA → security review → fix → re-QA.
- **`_find_by_casefold` as a single dedup method** handles 3 distinct collision paths (human_id vs human_id, alias vs human_id, alias vs alias) without duplication. The key insight is that `enroll()` needs to check a candidate human_id against ALL existing records' human_ids and aliases, and candidate aliases against ALL existing records' human_ids and aliases — the same method serves both.
- **Atomic persistence with `os.replace` requires `os.chmod` before the replace**, not after, because `os.replace` atomically replaces the target. Chmod after replace would race with readers. The pattern is `tmp → chmod(0600) → replace(tmp, path)`.
- **The stuck QA gate (ASP-840) was a workspace pin issue**, not a code issue. Aider's instructions validate `sourceIssueId` against the issue under review or its direct parent. When ASP-840 inherited the ASP-837 workspace (`sourceIssueId` = ASP-837) instead of ASP-838's workspace (`sourceIssueId` = ASP-838), Aider aborted with QA_ABORT. The fix is to create the QA child with the correct `inheritExecutionWorkspaceFromIssueId` pointing to the parent QA gate, not the grandparent.

## Verification

- Python tests: 28/28 pass for operator registry, full suite 544/548 pass
- CE-GATE items: all 6 addressed (4 blocking, 2 non-blocking)
- Push: `8eb81d9` on `ASP-837-daily-implementation-sweep`

## Remaining

- QA gate [ASP-847](/ASP/issues/ASP-847) assigned to Aider for CE-GATE fix re-check
- Auditor security approve after Aider passes
- aspen local-proof and merge to master
- ADR-0012 remains Proposed until follow-up ASP-777 (gatekeeper binding)