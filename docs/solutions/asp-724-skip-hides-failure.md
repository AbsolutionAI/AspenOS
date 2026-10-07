# ASP-724 — a skip can hide the failure it was written to catch

**Status:** implemented, awaiting Aider QA · handed off with `READY_FOR_AIDER_QA`
**Issue:** ASP-724 (picked up by the ASP-742 daily sweep) · Parent ASP-722
**Date:** 2026-10-05

## Summary

`test_holographic_ingest.py::test_explicit_db_env_writes_holographic` was failing on
`AttributeError: search_facts` on every host that can import the Hermes holographic plugin.
On this host it reported green — because the host lacks `ruamel`, so the `except ImportError →
pytest.skip` guard fired first and the broken line never ran.

The fix calls the method that exists now (`list_facts`). The durable lesson is the verification
move, not the rename.

## The pattern

A test that skips on the host you are standing on proves nothing about the hosts you are not.
The skip guard was itself correct and deliberate (ASP-706/707 widened it on purpose so a missing
transitive dep would not fail the suite) — and that good guard became the thing hiding the bug.

So the local run read `4 passed, 1 skipped`, and the suite was green, while the assertion the
test exists for had been dead since the store rename.

## What actually proved the fix

Not the green run. The green run was the symptom.

| Step | Result |
| --- | --- |
| `pytest tests/test_holographic_ingest.py -q` on the host | `4 passed, 1 skipped` — unchanged by the fix |
| Same file, venv with `ruamel.yaml` + `pyyaml` + `pytest` (scratch venv, nothing installed system-wide) | `5 passed` — the read-back **ran** |
| Negative control: `ASPEN_HOLOGRAPHIC_DISABLE=1` with that same venv | `1 failed` — `assert hits, facts` → `AssertionError: []` |
| `pytest tests/ -q` | `466 passed, 4 skipped` — matches the 466 board proof |

The third row is the one that matters: it shows the new assertion is load-bearing rather than
vacuously true. A dual-write test that passes when the dual-write is disabled is worse than no
test.

## Rules this yields

1. **A skip is not a pass.** When a test asserts on an out-of-repo dependency, reproduce the
   dependency before believing the run. If you cannot, say so in the handoff instead of
   reporting the skip count as evidence.
2. **Reproduce the failing host in a throwaway venv.** Installing a missing optional dep into a
   scratch venv costs seconds and turns a latent red into a proven green. It needs no host
   change and no package install under the repo.
3. **Prove the assertion can fail.** Any test written against a "never raises, best-effort"
   writer needs a negative control, or it may only be asserting that the writer's `except: return
   None` did not raise.
4. **Assert on keys, not on the producer's formatting.** The read-back matches the source id in
   `content` plus the routed `category`, so it stays green only if the write is real — but it
   does not re-implement `_compose_fact` and so will not drift in lockstep with the formatter.
5. **Two copies of a path constant is a bug.** The test hardcoded `/home/tech/.hermes/hermes-agent`
   while the writer resolved `HERMES_AGENT_ROOT`. On any host that sets that env var the test
   read a different tree than the one written to. The test now imports `hi._HERMES_AGENT` — the
   same constant, one line. (Full de-hardcoding stays ASP-733.)

## Cross-references

- [ASP-730](/ASP/issues/ASP-730) — CI never runs `tests/` wholesale, which is why this class of
  drift stayed invisible.
- [ASP-733](/ASP/issues/ASP-733) — de-hardcodes the `/home/tech` sites; row 5 above is the slice
  of it that had to land with this fix to keep the test honest.
- `docs/plans/ASP-724.md` — discovery table and scope decisions.