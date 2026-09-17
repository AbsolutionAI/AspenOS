# ASP-597: Sentinel `fleet.overview` producer

## Problem

ADR-0007 defines `aspen.sentinel.fleet.overview` ("aggregate plants/nodes/status,
`degraded[]`", fan-in from fleet heartbeat), but nothing published it. The
sentinel audit path (ASP-537) had a publisher + consumer; the dashboard's
`/api/sentinel/overview` endpoint and `consumer.fleet_overview()` were documented
as `_stub: true` previews until a producer landed.

## Solution

New `src/python/sentinel/fleet_overview.py` + `FleetOverviewProducer`:

1. **Fan-in from existing fleet subjects** — subscribes to
   `aspen.fleet.node.heartbeat`, `aspen.fleet.node.register`, and
   `aspen.fleet.ops.status` (no new heartbeat source; ops.status seeds known
   node ids before heartbeats arrive).
2. **Aggregation** — `build_overview()` emits `{overview_id, ts, source,
   status, total_nodes, degraded[], nodes[], plants[]}`. A node whose
   `last_seen` is stale (> `ASPEN_FLEET_OVERVIEW_STALE_AFTER`, default 70s vs
   30s heartbeat → >2 missed) or whose status != online lands in `degraded[]`;
   overall status = `offline` / `degraded` / `ok`.
3. **Durability (audit-publisher parity)** — every snapshot is fsync'd onto a
   JSONL journal (`ASPEN_FLEET_OVERVIEW_LOG`) unconditionally and mirrored to
   JetStream `aspen.sentinel.fleet.overview` (best-effort, `Nats-Msg-Id:
   overview_id`). No replay path — only the newest snapshot matters — which
   keeps the module lean vs the audit publisher's idempotent backfill.
4. **Consumer producer-awareness** — `AuditEventConsumer` now subscribes to
   `aspen.sentinel.fleet.overview` (live ring) and `fleet_overview()` prefers
   live → producer journal → local preview stub. The dashboard route is
   unchanged (`/api/sentinel/overview` calls `fleet_overview()`), so the
   consumer path is wired without UI churn.
5. **CLI** — `scripts/sentinel-fleet-overview.py` with
   `emit / daemon / tail / check`.

## Key milestones / gotchas

- **Two subscriptions in `consumer.start()`** break tests that assumed exactly
  one NATS `subscribe()` call; the existing tests were updated to capture
  callbacks per subject and assert both `aspen.sentinel.audit.event` and
  `aspen.sentinel.fleet.overview` are subscribed.
- **Stale-node math** uses naive `datetime.fromisoformat` + explicit UTC offset
  normalization (`Z` → `+00:00`) because Python's `fromisoformat` handling of
  `Z` varies by version.
- **`ops.status` is a summary, not per-node** — it carries flat `plants[]` /
  `nodes[]` id lists, so the producer seeds unknown node ids as `plant:
  "unknown"` and lets subsequent heartbeats reconcile plant/roles.
- **Stream reuse** — the overview shares the `ASPEN_SENTINEL` stream bound to
  `aspen.sentinel.>`; `add_stream` stays idempotent, and both audit + overview
  publishers coexist on one stream.

## Files

New: `src/python/sentinel/fleet_overview.py`,
`scripts/sentinel-fleet-overview.py`, `tests/test_sentinel_fleet_overview.py`,
`docs/plans/ASP-597.md`, this doc.

Modified: `src/python/sentinel/consumer.py` (overview subscribe +
`fleet_overview()` preference, journal fallback),
`src/python/sentinel/__init__.py` (exports),
`tests/test_sentinel_consumer.py` (per-subject subscription capture),
`docs/FLEET.md`, `docs/adr/ADR-0007-*.md`, `docs/ops/FLEET_SUBJECT_PUBLISHERS.md`.

## Verification

- `python3 -m pytest tests/test_sentinel_fleet_overview.py tests/test_sentinel_consumer.py tests/test_sentinel_audit.py -q` → 60 passed, 1 skipped (dashboard-module import skip expected in CI without nats-py).
- Offline CLI smoke: `sentinel-fleet-overview.py emit` → `tail`/`check` round-trip through the JSONL journal with no broker.
- Aider QA + Auditor before `done` (flash-only).