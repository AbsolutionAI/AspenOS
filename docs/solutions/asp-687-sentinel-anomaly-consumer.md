# ASP-687: Wire the tool-anomaly detector to the live audit feed

**Status:** READY_FOR_AIDER_QA
**Mode:** IMPLEMENTATION
**Source:** Sentinel Threat Model / F-015 — closes the ASP-379 live-consumer follow-up
**Plan:** `docs/plans/ASP-687.md`
**Updated:** 2026-10-02

## Summary

ASP-379 shipped `ToolAnomalyDetector` as a pure library plus an offline CLI.
Nothing in the running system ever called `feed()`, so a read of `/etc/shadow`
followed by an outbound `http_post` produced no signal at all. This adds the
missing edge:

```
aspen.sentinel.audit.event  ──▶  ToolAnomalyDetector.feed()
                                       │
                                       ▼
                             aspen.sentinel.tools.anomaly
```

`AnomalyConsumer` (`src/python/sentinel/anomaly_consumer.py`) subscribes the
audit subject, feeds each event through the detector, appends findings to
`/var/lib/aspen/sentinel/anomaly.jsonl` (flush + fsync), and mirrors them to
JetStream with `Nats-Msg-Id: finding_id`. `scripts/sentinel-tool-anomaly.py`
exposes `daemon` / `scan` / `tail` / `check`. Still **fail-open and log-only**:
nothing here can block a tool call or alter a verdict.

## The bug this had to fix first

Wiring the detector to a live stream exposed a defect the offline CLI hid.
`ToolAnomalyDetector._check_actor` re-evaluated every rule on every event, and
R1 was written as a **set-state predicate**: "does the current window contain a
sensitive read followed by an egress?" That stays true for every subsequent
event the actor produces. Feeding a 12-event sequence containing a single
read+egress pair emitted **11 identical R1 findings** — one incident, one page
per later event.

Fixed at the source, in the detector, not by filtering in the consumer — the
offline CLI was wrong too, and any future caller would inherit the same noise:

| Change | Where | Why |
|--------|-------|-----|
| R1 keys on the **arriving** event being an egress | `tool_anomaly.py` `_rule_sensitive_read_then_egress` | Only the egress half of the pair can *create* the finding. Matches `_rule_bursts`, which already keyed on arrival |
| `_dedupe()` correlation cache | `tool_anomaly.py` | `rule` + `window_s` + member `event_id`s. Belt-and-braces for any rule that re-fires on the same incident |
| `event_id` redelivery guard in `feed()` | `tool_anomaly.py` | JetStream is at-least-once. A redelivery counted twice inflates R2/R3/R4 and manufactures a burst from four real calls |
| `_prune_emitted()` on every event | `tool_anomaly.py` | Correlation state is windowed, not a lifetime leak. Pruned on benign events too, not just when a finding fires |

Sequence behavior after the fix: **12 events → 1 finding**, batch and streaming
alike, while a second genuine incident still fires its own finding.

## Decisions

**Fix R1 in the detector, not in the consumer.** The offline CLI had the same
defect. Deduplicating downstream would leave every future caller broken and
keep the library's contract surprising.

**At-most-once core-NATS subscription, not a durable JetStream pull consumer.**
Matches `AuditEventConsumer` and `FleetOverviewProducer`, which are what a
reviewer will compare against. Costs a gap across restarts; buys a path that is
hermetically testable without a live broker. Recorded as the top residual in
ADR-0007 and the threat model rather than hidden.

**`aspen.sentinel.tools.anomaly`, no ACL change.** The subject is a child of the
existing `aspen.sentinel.>` grant on `STARSHIP_OPS` (publish, subscribe, and
JetStream export) and of `STARSHIP_EDGE`'s import. Verified by test against
`nats/fleet-accounts.conf.tmpl`, not assumed.

**`finding_id` is a content hash, not random.** `Nats-Msg-Id` dedup means a
replayed finding after a restart or journal re-scan collapses onto one message
instead of paging twice. A random id would defeat the entire reason for
publishing to a durable stream.

**Own JSONL, do not reuse the audit journal.** Findings are derived data; mixing
them into the audit trail would corrupt forensic replay and the `H-015` trail.

## Changes

| File | Change |
|------|--------|
| `src/python/sentinel/tool_anomaly.py` | Arrival-keyed R1, `_dedupe()`, `event_id` redelivery guard, `_prune_emitted()` |
| `src/python/sentinel/anomaly_consumer.py` | **New** `AnomalyConsumer` — subscribe, ingest, journal (fsync), publish, `scan`/`scan_journal`/`tail`/`check` |
| `scripts/sentinel-tool-anomaly.py` | **New** CLI: `daemon` / `scan` / `tail` / `check` |
| `src/python/sentinel/__init__.py` | Export `AnomalyConsumer`, `SUBJECT_TOOLS_ANOMALY`, `build_finding_envelope`, `finding_id` |
| `nats/subjects.yaml` | Register `tools_anomaly` |
| `tests/test_tool_anomaly.py` | +12 tests: emit-once regressions, second-incident-still-fires, out-of-order arrival, per-actor isolation, redelivery-vs-burst, window expiry, missing-`event_id` limits |
| `tests/test_sentinel_anomaly.py` | **New**, 39 tests: envelope shape, `finding_id` stability/differentiation, journal durability, offline `scan` parity with `ingest`, `tail`/`check`, mocked JetStream publish + `Nats-Msg-Id` header, subscription wiring, ACL coverage, and fail-open paths (no broker, missing `nats`, refused connection, detector raising, unwritable journal, malformed JSON) |
| `docs/adr/ADR-0007-nats-subject-contracts-sentinel-c2.md` | Subject-table row, "Wired so far" entry, updated **Next** |
| `docs/SECURITY_THREAT_MODEL_v2.2.md` | F-015 mitigation + residual status; new coverage row; summary table |
| `docs/ops/FLEET_SUBJECT_PUBLISHERS.md` | Publisher + subscriber inventory rows |
| `docs/solutions/asp-379-tool-anomaly.md` | Follow-up checked off; remaining work listed |

## Verification

- `python3 -m pytest -q` → **518 passed, 4 skipped** (baseline at `origin/master`
  was 470 passed, 4 skipped — no regressions)
- `tests/test_tool_anomaly.py` + `tests/test_sentinel_anomaly.py` → **60 passed**
- CLI end-to-end offline: `scan` over a 9-event audit journal → `1 finding(s)
  journaled`; `tail -n 2`; `check`; `daemon` with no broker → reports
  `journal-only` and stays up; no args → usage error
- **Mutation-tested the fix**, since a dedupe guard that nothing kills is not
  verified:
  - restore original set-state R1 → 12-event probe yields **11** findings (must be 1)
  - disable the `event_id` guard → 4 shells + 1 redelivery yields **1** burst (must be 0)
  - disable `_prune_emitted()` at both call sites → 2 tests fail
  - file restored byte-identical afterwards (`diff -q` clean)
- `python3 -m py_compile` on the new module and CLI
- ACL claim is a test, not a comment: `test_findings_subject_falls_under_existing_ops_acl`
  parses `STARSHIP_OPS` out of the template and asserts publish, subscribe, and
  the JetStream export

## Residuals (deliberate, documented)

1. **At-most-once delivery.** A restart loses the window it was down for. A
   durable pull consumer is the fix and the top item in ADR-0007 **Next**.
2. **No paging consumer.** `aspen.sentinel.tools.anomaly` is published but
   nothing subscribes yet, so R1 findings currently land in the journal and the
   stream, not in a pager.
3. **Blocking path still deferred.** Unchanged from ASP-379 and still the
   right call: an anomaly is an investigation lead, not a stop signal.
4. **`event_id` is required for redelivery dedup.** Events without one cannot be
   distinguished from a redelivery; pinned by
   `test_duplicate_event_without_id_is_counted_twice` so the limit is visible.

## Out of scope

- A nightly verification section — the blocked ASP-701 branch claims the next
  free number, and Section 13 already runs `pytest tests/`, which includes every
  test added here. A new section would duplicate existing coverage.
- Dashboard Sentinel endpoints for findings.
- Any change to deny semantics or `propose_act`.