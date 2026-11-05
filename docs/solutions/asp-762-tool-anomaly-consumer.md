# ASP-762 / ASP-687: Wire Behavioral Anomaly Detector to Live Audit Stream

## Summary

Wired the ASP-379 `ToolAnomalyDetector` (R1–R4 rules, fail-open, log-only) to
the live ADR-0007 tool-audit JetStream subject. A new `ToolAnomalyConsumer`
module subscribes to the audit event stream, feeds every event through the
detector, journals findings to a durable JSONL log, and mirrors them to a
`sentinel.tools.anomaly` subject for ops paging. Delivered under the ASP-762
daily implementation sweep, merged via PR #76 (`5dea57b`), with a follow-up
hardening pass via PR #79 (ASP-780, `7a9f45f`).

## Changes

| Area | Files | Lines | Description |
|------|-------|-------|-------------|
| **Consumer** | `src/python/sentinel/tool_anomaly_consumer.py` | 376 (new) | `ToolAnomalyConsumer`: subscribe audit → feed → journal + publish |
| **CLI** | `scripts/tool-anomaly.py` | 158 (extended) | Added `watch` subcommand with `--once` offline replay |
| **Tests** | `tests/test_tool_anomaly_consumer.py` | 340 (new) | 16 hermetic tests: detection→emit, journal, NATS mocks, fail-open |
| **Hardening** | `src/python/sentinel/tool_anomaly_consumer.py` | +39/-9 (PR #79) | ASP-780: `window_executor` guard, `assertion_before_capture` hardening, `_on_message` trust-boundary logging |
| **Plan** | `docs/plans/ASP-762.md` | 71 (new) | CE plan before code |

## Result

- 28 tests pass (12 detector + 16 consumer), 0 failures.
- Full suite: 516 passed, 4 skipped (optional deps), 0 failures.
- Commits `f6ef0d7` + `7a9f45f` both ancestors of `origin/master`.
- CLI: `scripts/tool-anomaly.py watch --once` replays audit journal offline.

## What was learned

- **Subject naming under the `aspen.sentinel.` namespace** — The threat model
  names the finding subject `sentinel.tools.anomaly`, but the durable
  `ASPEN_SENTINEL` JetStream stream binds `aspen.sentinel.>`, so the concrete
  subject must be `aspen.sentinel.tools.anomaly`. The short form in the threat
  model is the conceptual name; the consumer resolves it to the namespaced form.
  The `ASPEN_TOOLS_ANOMALY_SUBJECT` env var allows override.

- **Local-first write topology (journal + JetStream)** — Mirrors
  `sentinel.audit` and `sentinel.fleet_overview`: findings are always written to
  a durable JSONL journal with `flush + fsync`, then best-effort published to
  JetStream with `Nats-Msg-Id: finding_id` for idempotent replay. A missing
  broker never drops a finding, and a publish failure is logged + swallowed.

- **Fail-open at every layer** — The detector never raises on malformed input.
  The consumer wraps every callback in try/except. The `handle_event` method
  catches detector exceptions. The `_on_message` callback catches JSON decode
  errors. The publish path journals first (always durable) then tries JetStream.
  Nothing blocks `propose_act`.

- **Paging vs. templating separation** — The `_is_page` check maps severity to a
  `notify` boolean in the finding envelope. R1 (high severity) is `notify: true`,
  the rest are informational. Ops can filter on `notify` without understanding
  detection rules, and can template different sinks per rule.

- **No durable subscription for the consumer** — The audit subscription uses
  `nc.subscribe` (non-durable) rather than `js.subscribe` with a durable name.
  The detector holds an in-memory sliding window; replaying a durable backlog
  into a fresh process would re-window stale events as if live. The audit JSONL
  journal is the durable source for offline replay via `ingest_journal()`.

- **ASP-780 hardening patterns** — The first production-hardening pass added:
  - `window_executor` guard: prevent concurrent `feed()` calls from corrupting
    the in-memory sliding window (a Python list append is thread-safe but a
    concurrent `feed` + prune + check sequence is not; the async event loop
    serialises them under asyncio, but `ingest_journal` runs synchronously).
  - `assertion_before_capture`: validate invariants before writing findings
    (e.g. that `finding_id` is non-empty, that the journal line round-trips).
  - Trust-boundary logging in `_on_message`: log the source subject and event_id
    when a message fails to decode, so an operator can trace which publisher
    sent the malformed data.

- **CI-independence** — The consumer tests mock NATS at the `sys.modules` level
  (via `patch.dict("sys.modules", {"nats": mock_mod})`) and never touch a real
  broker. The `tmp_path` fixture isolates journal I/O. The test collection is
  fast (0.07s) and requires no external services — it passes in any CI
  environment.