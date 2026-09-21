# ASP-379 / H-015 / F-015: Behavioral anomaly detection over tool execution

**Status:** READY_FOR_AIDER_QA
**Mode:** IMPLEMENTATION
**Source:** Sentinel Threat Model / H-015 / F-015 — LOW
**Plan:** `docs/plans/ASP-379.md`
**Updated:** 2026-09-20

## Summary

A fail-open behavioral anomaly detector over tool-audit events (ADR-0007,
`{event_id, actor, action, target, result, ts}`). The detector is a pure
Python library + CLI (`scripts/tool-anomaly.py`) that flags unusual tool
sequences with four explicit rules — one temporal sequence rule (R1) and three
sliding-window statistical rules (R2–R4). It is **observation-only**: it logs
findings tagged `fail_open: True` / `action_required: "investigate"` and never
blocks `propose_act` (or any call path).

## Decision (recorded)

**Fail-open, log-only detector. No blocking path in v1.**

| Concern | Decision | Why |
|---------|----------|-----|
| Blocking verdicts | None | Prevent a detector false-positive from breaking legitimate ops; an anomaly is an investigation lead, not a stop signal (cf. sensor-trigger guard, which does have real deny semantics) |
| Detect window | 120s default | Compact enough to catch a burst/pivot corridor, wide enough for normal work |
| Emit-once per burst | R2/R3/R4 fire at exact threshold crossing (`== min`) | One finding per burst, no spam as the window slides |
| Malformed input | Never raises; events without `actor`/`action`/`ts` are skipped | Fail-open by construction; `read_jsonl` skips corrupt lines |
| Time ordering | `scan()` sorts events; each event is evaluated against its own window | Shuffled journal input still yields the same findings |

## Rules

| Rule | Severity | Threshold | Suspicion |
|------|----------|-----------|-----------|
| `sensitive_read_then_egress` (R1) | high | sensitive read (credential/secret-adjacent target) then egress (`http_post` / `delegate_to_agent` / networked `shell`) within the window | data exfiltration / pivot after compromise |
| `high_risk_burst` (R2) | medium | 5+ high-risk tools (shell/http/write/delegate/opencode/…) inside the window | automated attack or runaway agent |
| `denial_probe` (R3) | medium | same high-risk action denied 4+ times inside the window | probing the guard |
| `error_storm` (R4) | low | same tool fails 6+ times inside the window | broken/poisoned tool or supply-chain failure |

## Threat-model checklist — H-015 marked

- [x] **H-015 / F-015:** behavioral anomaly detection over tool execution —
      **detector implemented (ASP-379)**. Batch + incremental API, hermetic
      fixtures for benign vs anomalous sequences, fail-open contract,
      detection-library plus CLI. Cheap enough to run on every audit event;
      deliberately NOT wired to any deny path yet (follow-up task, see below).
- [ ] Live consumption hook-up (JetStream consumer → detector → findings
      journal/table) — deferred; a follow-up issue tracks the wiring.

## Changes

| File | Change |
|------|--------|
| `src/python/sentinel/tool_anomaly.py` | `ToolAnomalyDetector` (windowed R1–R4), `Finding` (fail-open), `read_jsonl`, `read_audit_logger` (services.audit fallback), `default_journal` |
| `scripts/tool-anomaly.py` | CLI: `scan` subcommand (`--jsonl` / `-` stdin / `--from-audit-db` / `--window`, human + `--json` output) |
| `tests/test_tool_anomaly.py` | Hermetic suite: benign vs anomalous per rule, window boundaries, fail-open/garbage inputs, time-order independence, loaders, CLI end-to-end |

## Verification

- `.venv/bin/pytest tests/test_tool_anomaly.py -q` → **12 passed**
- CLI on mixed fixture: benign ops lines → no finding; `/etc/shadow` read then
  `http_post` → exactly one `HIGH sensitive_read_then_egress`
- No NATS, journal, or `propose_act` touched by tests (hermetic)

## Out of scope

- Dual-human `authorize_clear` (ASP-364 / ASP-538)
- ASP-370 (aa-enforce) / production deny-by-default
- Live consumer wiring into a JetStream subject `sentinel.tools.anomaly`

## Follow-up

Live wiring: subscribe a consumer to the tool-audit subject (ADR-0007), feed
each event through `ToolAnomalyDetector.feed()`, and publish any findings to a
`sentinel.tools.anomaly` subject / audit table so ops can page on R1 (high)
and template on R2–R4.