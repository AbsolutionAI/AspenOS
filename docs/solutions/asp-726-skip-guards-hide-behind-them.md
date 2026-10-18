# Learning: a skip guard can hide the bug it sits in front of (ASP-726)

**Date:** 2026-10-03
**Issues:** [ASP-726](/ASP/issues/ASP-726), [ASP-706](/ASP/issues/ASP-706), [ASP-709](/ASP/issues/ASP-709)
**Source:** ASP-706 daily implementation sweep

## Bug

`tests/test_holographic_ingest.py` called `MemoryStore.search_facts()`. That method has
never existed — not in the Hermes plugin, not anywhere:

```sh
grep -rn "search_facts" /home/tech/.hermes/hermes-agent --include=*.py   # no matches
```

The suite was green because the import above it raised `ModuleNotFoundError: ruamel`, and
an `except ImportError` guard skipped the test. The skip ran first. The `AttributeError`
was one line behind it and had never executed on any host, ever.

The assertion was *also* wrong on its own terms — `search_facts("OpenCode holographic")`
looks for a substring that `_compose_fact`'s provenance header splits apart
(`[opencode/ASP-HOLO-1 ...]` puts `ASP-HOLO-1` between the words). Even against a working
substring search it would have returned zero hits and failed. So the test had no reachable
passing state, and had been providing zero coverage of the dual-write it names.

## Pattern

**A skip guard proves the import path is sound. It proves nothing about the code behind the
import.** When the guarded block calls into an external object, the guard can silently
suppress an `AttributeError` in code you own — the *call site* is yours even when the
callee is not.

Three things had to be true at once for this to survive since `5c92f5b` (ASP-541):

1. The optional dep is absent on the dev host *and* on CI.
2. The guard is above the call.
3. Nothing ever runs the file in a context where the dep resolves.

`ruamel.yaml==0.18.16` is declared in the Hermes tree for Python ≥ 3.14
(`pyproject.toml:56`), and this repo is on 3.14.4. So the configuration the dependency
documents as supported is precisely the one that turns this test red. "Green here" was
never "green everywhere."

**The check that finds this class in one line:** for every attribute called on an object
from an optional/external module, confirm it exists in that module's real API. `grep -rn
"<attr>" <external tree>`. A skip guard will not do this for you, and neither will a green
suite.

## How to verify a guard is not lying

Reproduce the *other* host. The guard exists precisely because the normal host doesn't reach
the code, so the green run is not evidence. A minimal stub on `PYTHONPATH` is enough:

```sh
mkdir -p stub/ruamel/yaml
printf '' > stub/ruamel/__init__.py
printf 'class YAMLError(Exception): pass\n' > stub/ruamel/yaml/error.py
PYTHONPATH=stub pytest tests/test_holographic_ingest.py -q -rs
```

That flipped the skip into an `AttributeError` and made the latent bug visible in one
command. Note it must be the **single-file** invocation: under `pytest tests/` another test
pollutes `sys.path` and the import fails earlier on `tools.registry`, so the block stays
unreached. Reachability is order-dependent, which is its own reason to check per-file.

## Mutation testing is what separates a skip from a guard

The pre-existing DoD for the ASP-706 fix asserted that a broken dual-write "still fails at
line 38 and never reaches the skip" — true for the JSONL leg, but it never tested what
happens *after* a successful import. The two mutations that matter both mutate production
code and assert the test **fails rather than skips**:

| Mutation | Before fix | After fix |
|---|---|---|
| `write_holographic` → no-op | skip (masked) | **FAIL** — empty store |
| `_compose_fact` drops `source_id` | skip (masked) | **FAIL** — header lacks marker |

The rule: for a skip-guarded test, a mutation test that still passes *through the skip* is
not evidence of anything. Assert on the failure mode, not just the exit code.

## Related: the same shape in `test_memory_mcp.py`

[ASP-709](/ASP/issues/ASP-709) carries a CE-GATE on widening that file's guard to
`except ImportError`. The shapes look alike and the verdicts differ, and the difference is
worth stating precisely:

- `test_holographic_ingest.py` — the callee is out-of-repo, but the **call is ours**, and
  it was wrong. Guard correct, assertion wrong.
- `test_memory_mcp.py` — the module under test is **in-repo**
  (`mcp/aspen-memory-mcp/src`), so a catch-all skip removes coverage of code this repo
  ships. There the guard is the hazard.

Does the callee live in this repo? That single question decides it. Here it doesn't, so the
`ImportError` guard stands and the assertion was the bug.

## Files touched

- `tests/test_holographic_ingest.py` — assert via the real `list_facts()` API, match the
  `source_id` header, and make the skip message state that the read-back did not run
- `docs/plans/ASP-726.md` — plan

No production code changed. `scripts/holographic_ingest.py` behaves identically; only the
test's ability to notice a regression changed.