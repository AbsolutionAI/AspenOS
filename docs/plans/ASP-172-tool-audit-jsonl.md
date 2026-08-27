# ASP-172 / H-004 — Per-agent tool audit log (JSONL)

Status: implemented
Priority: HIGH (Security Threat Model v2.1, finding F-006)

## Problem

No audit trail of tool execution exists. Every tool call should be logged
with agent identity, tool name, argument hash, timestamp, duration, and
result status.

## Approach

Single chokepoint: `execute_tool()` in `agents/tools.py` — every tool call
(direct tools, policy denials, unknown tools) already funnels through it.

New module `agents/tool_audit.py`:

- Appends one JSON line per tool call to
  `/var/log/starship/audit/<agent_id>-<YYYYMMDD>.jsonl`
  (override with `STARSHIP_AUDIT_DIR` for dev/tests).
- Fields per acceptance criteria: `agent_id`, `tool_name`, `args_hash`,
  `timestamp_ms`, `duration_ms`, `exit_code`, plus `status`
  (`ok` | `error` | `denied`) and `redacted: true`.
- Arguments are never written raw — only a SHA-256 hash of their canonical
  JSON (first 16 hex chars), so no secret material lands in the log.
- File mode `640`, dir mode `750` (best-effort chmod; failure to enforce is
  logged at debug and never breaks execution).
- Rotation: date-stamped files give daily segmentation; opportunistic
  retention sweep deletes files older than
  `STARSHIP_AUDIT_RETENTION_DAYS` (default 30) at most once per day.
- Failure-isolated: any audit error is swallowed (debug log). Auditing must
  never break tool execution — same principle as memory ingestion.

Agent identity: `agent_daemon.run_agent()` exports `STARSHIP_AGENT_NAME`;
the audit module reads it (`unknown` fallback for out-of-band use).

## Acceptance criteria mapping

| Criterion | Where |
| --- | --- |
| JSONL at `/var/log/starship/audit/<agent>-<date>.jsonl` | `tool_audit._audit_path` |
| Fields agent_id/tool_name/args_hash/timestamp_ms/duration_ms/exit_code/redacted | `tool_audit.audit_tool_call` |
| Rotation | date-stamped files + `prune_old_logs` retention |
| Readable only by ops team (mode 640) | best-effort chmod on file + dir |

## Tests

`tests/test_tool_audit.py`: field completeness, args-hash stability +
no-raw-args, mode enforcement, retention pruning, and an `execute_tool`
integration case proving one line per call including error paths.

## Disposition

**COMPLETED** (ASP-482 sweep — 2026-08-26) — Tool audit JSONL landed. `agents/tool_audit.py` with JSONL audit at `/var/log/starship/audit/`. Fields: agent_id, tool_name, args_hash, timestamps, duration, exit_code, redacted. Rotation via date-stamped files + `prune_old_logs`. Mode 640 enforcement. `tests/test_tool_audit.py` green.
