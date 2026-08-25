# Per-agent JSONL tool audit log (ASP-172 / H-004)

**Date:** 2026-08-24
**Tickets:** ASP-172 (H-004)

## Problem

No audit trail of tool execution existed. Every tool call should be logged with
agent identity, tool name, argument hash, timestamp, duration, and result status.

## Solution

Single chokepoint instrumentation in `agents/tool_audit.py`:

1. **`audit_tool_call()`** appends one JSONL line per tool call to
   `/var/log/starship/audit/<agent>-<YYYYMMDD>.jsonl` with fields `agent_id`,
   `tool_name`, `args_hash`, `timestamp_ms`, `duration_ms`, `exit_code`,
   `status` (`ok`|`error`|`denied`), and `redacted: true`.
2. **Arguments are never written raw** — only a SHA-256 hash of canonical JSON
   (first 16 hex chars), so no secret material lands in the log.
3. **`_call()` wrapper in tools.py** calls `audit_tool_call()` on every `execute_tool`
   path including error and policy-denial paths.
4. **File mode 640** (best-effort chmod, failure debug-logged and non-blocking).
5. **Daily segmentation** via date-stamped filenames; `prune_old_logs()`
   deletes files older than `STARSHIP_AUDIT_RETENTION_DAYS` (default 30).
6. **Failure isolation** — any audit error is swallowed (debug log). Auditing
   never breaks tool execution.

## Patterns to reuse

1. **Instrument the chokepoint, not every caller.** `execute_tool()` is the
   single funnel for all tool calls (direct, policy denials, unknown tools).
   One wrapper covers everything.
2. **Hash, don't store.** Arguments are the highest-value signal and the
   highest-risk content. Hashing preserves forensic value without exposing
   secrets.
3. **Fail-isolated by default.** If the audit log is unwritable, the system
   keeps running. This matches the memory-ingestion failure isolation pattern.
4. **Lazy import in tools.py** to avoid circular dependency at module load time.
   `audit_tool_call()` is imported inside the wrapper function body.

## Verification

- `tests/test_tool_audit.py` — 15 tests covering field completeness, args-hash
  stability + no-raw-args, mode enforcement, retention pruning, and
  `execute_tool` integration for ok/error/denied paths.

## Remaining

- Audit log rotation is simple date-stamped file + retention sweep. Production
  deployments may want logrotate or external shipping (syslog/fluentd).
