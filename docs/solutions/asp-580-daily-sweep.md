# ASP-580: Daily Implementation Sweep — 2026-09-09

## What was done

Daily implementation sweep. Merged origin/master (ASP-563 weekly architecture review + ADR-0012), resolved merge conflict in SECURITY_THREAT_MODEL_v2.2.md, and committed 6 pending changesets covering sentinel consumer, Dev-only gate improvements, Agent Zero retirement docs, CE gate update, plans/solutions docs, and nightly results.

## Changes committed

| Area | Files | Description |
|------|-------|-------------|
| Sentinel consumer | `src/python/sentinel/consumer.py`, `src/python/sentinel/__init__.py`, `dashboard/server.py`, `tests/test_sentinel_consumer.py` | Local-first audit consumer: JSONL journal reads + optional NATS live subscription. 3 dashboard endpoints. 20 tests. |
| Dev-only gate | `scripts/check-no-devonly-in-prod.sh` | Narrowed scan scope to shipped content only; dual-form matching; self-exclusion |
| Agent Zero retirement | `docs/FOUNDATION.md`, `docs/MODEL_ROUTING.md`, `docs/ops/AGENT_ZERO_RETIRED.md`, `docs/sor/ASPENGROVE_MASTER_SPEC_v4.0.md` | Remove A0 references across docs (BEL-262) |
| CE gates | `docs/COMPOUND_ENGINEERING.md` | Updated pipeline: Opencode → Aider QA → Auditor approve → aspen proof → done |
| Plans/solutions | 5 plans + 5 solutions for ASP-537/538/539/575 | Sentinel, estop, NATS URL, AppArmor |
| Nightly + marketing | 2 docs | Sweep results and marketing schedule |

## Key observation

The nightly check baseline has reached 107 passed + 1 known failure (C11 p50). The sentinel consumer addition (ASP-537) completed the ADR-0007 audit trail read path. The Dev-only gate improvements (ASP-574) tighten the security boundary by scanning only shipped content rather than all scripts.

## What was learned

- **Merge conflict resolution for security docs:** When two branches both update the same "Changes Since Last Refresh" table in SECURITY_THREAT_MODEL_v2.2.md, keep the more comprehensive set (origin/master's 8-row ADR table) and append any unique rows from HEAD (ASP-568 reconciliation). Don't try to interleave.
- **Sentinel consumer pattern:** The AuditEventConsumer follows the same offline-first pattern as AuditEventPublisher — journal reads work without NATS, live subscription is best-effort. The `deque(maxlen=ring_size)` ring buffer with `appendleft` gives newest-first ordering for free.
- **Dev-only gate scope refinement:** Scanning the entire `scripts/` tree produces noise because scripts/ itself is Dev-only. The fix is an explicit `RUNTIME_SCRIPTS` list of files actually shipped in the deb package.

## Verification

- Python tests: 303 passed, 4 skipped, 0 failures
- Nightly check: 107 passed, 1 known failure (C11 p50)
- All 8 commits pushed to `origin/master`
