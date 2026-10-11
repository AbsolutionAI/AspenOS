# ASP-696: Delete the HybridIntel stub and reconcile the `osint-threat` skill

Implements the [ASP-695](/ASP/issues/ASP-695) architect decision: **delete as dead
code**, do not build an OSINT engine.

## Problem

The repo shipped a 30-line self-labelled stub (`services/hybrid_intel.py`:
`sweep()` is `pass`, `get_status()` returns `{"enabled": False}`,
`generate_brief()` returns `"Intel engine not fully configured"`,
`IntelItem.to_dict()` returns `{}`, and it logged `"HybridIntel initialized
(stub)"`) plus a 17 KB dashboard page (`src/python/lib/dashboard/intel.html`)
bound to an API with no handler. Neither had a single importer or route.

The real OSINT contract is ADR-0007's publish-only diode subject
`aspen.sentinel.osint.ingest`. A second aggregation engine in `services/` would
have forked that contract, which is why four sweeps deferred the call and an
architect had to make it.

## Solution

Deleted two files, fixed the prose in one.

1. **`src/python/services/hybrid_intel.py` — deleted.** `services/__init__.py`
   is 0 bytes, so no package export needed pruning. Zero importers, no test, no
   packaging or systemd reference.
2. **`src/python/lib/dashboard/intel.html` — deleted.** It was provably
   unreachable, not merely unlinked.
3. **`src/python/lib/skills/osint-threat/SKILL.md` — reconciled.** Skill stays
   registered; only the phantom-service lines are gone.

## Key milestones / gotchas

- **`intel.html` was unservable, not just unlinked — worth proving, not assuming.**
  `dashboard/server.py:42` sets `STATIC_DIR = _HERE / "static"` and
  `_serve_static_file()` resolves strictly inside it. `intel.html` sits *beside*
  `server.py`, so no URL could ever reach it. It is also absent from the
  top-level `dashboard/` tree (where `index.html` and `marketplace.html` do
  live), and neither `index.html` has an `intel` nav link. A repo-wide `rg` for
  `intel.html` returns zero hits. If you ever find a sibling page that is
  unlinked but genuinely served, this reasoning does not transfer — check
  `STATIC_DIR` first.

- **`/api/intel` had seven fetches and zero handlers.** All seven were inside
  `intel.html` itself. The stub could never have backed them anyway: `sweep()`
  was `pass`, so every panel would have rendered an empty state. Keeping the page
  would have required inventing the API, which the ticket explicitly forbids.

- **Third phantom found in the same file.** `SKILL.md` line 10 read
  `Store findings as DECISION / SEMANTIC memories`. There is no `DECISION`
  memory type — `services/memory.py:26-35` defines ten
  (`working`, `semantic`, `episodic`, `procedural`, `retrieval`, `parametric`,
  `prospective`, `temporal`, `knowledge_graph`, `preference`). Corrected to
  `SEMANTIC / EPISODIC`, which is what the skill actually does: durable facts
  plus "what happened on past runs". **Lesson: when a file names a service or
  type, verify the name against the definition, not against how plausible it
  sounds.** Two phantom references in one 20-line file means the file was never
  executed.

- **The "Not this skill" section is a negative-space guard.** After deleting
  `hybrid_intel` and `osint_sensor`, the next agent to read this skill has no
  in-repo signal that those never existed. The section names the ADR-0007 subject
  (`aspen.sentinel.osint.ingest`, publish-only) as the *actual* contract and
  states explicitly that this skill does not publish to it. It is the difference
  between "the service is gone" and "the service was never real, and here is
  where the real thing lives."

- **`services/` import failures in a bare env are pre-existing, not regressions.**
  4 of 25 service modules fail to import locally: `telemetry` and `agent_email`
  (no `httpx`), `checkpoint` and `projects` (no write access to
  `/var/lib/agnetic`). Verified by running the identical import matrix against a
  `master` checkout with the stub still present — same four names, same errors.

## Files

Deleted: `src/python/services/hybrid_intel.py`,
`src/python/lib/dashboard/intel.html`

Modified: `src/python/lib/skills/osint-threat/SKILL.md`

New: `docs/plans/ASP-696.md`, this doc

Deliberately unchanged: `docs/sweep-results-2026-09-{16,18,19,29}.md` (historical
record), `agents/proxy.yaml`, `src/python/lib/proxy.yaml`, `README.md` skill
list, `docs/adr/ADR-0007-nats-subject-contracts-sentinel-c2.md`,
`docs/solutions/asp-368-data-diode-recipe.md`, WorldMonitor / ASP-651 / diode
config.

## Verification

Repo-wide `rg` for `hybrid_intel`, `HybridIntel`, `osint_sensor`, `/api/intel`,
`intel.html`: **zero hits outside `docs/sweep-results-*.md`, this ticket's plan
doc, and the new "Not this skill" negative guard.**

- AST import scan over all 141 tracked `.py` files: 0 unresolved `hybrid_intel`
  imports, 0 syntax errors.
- `services` import matrix: 21 import cleanly, same 4 environmental failures as
  the pre-change baseline; `find_spec('services.hybrid_intel')` is now `False`.
- `pytest tests/ -q --collect-only`: 470 collected at `HEAD` (`cba7f7a`) and 470
  after — zero delta.
- `pytest tests/ -q`: `1 failed, 468 passed, 3 skipped` both before and after.
  The single failure is `test_holographic_ingest.py::test_explicit_db_env_writes_holographic`,
  caused by a missing `ruamel` module — pre-existing and unrelated.
