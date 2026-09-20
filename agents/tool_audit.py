#!/usr/bin/env python3
"""
Starship OS — Per-agent tool audit log (H-004 / ASP-172).

Every agent tool call is appended as a single JSON line to
/var/log/starship/audit/<agent_id>-<YYYYMMDD>.jsonl with fields:

    agent_id     tool-calling agent (STARSHIP_AGENT_NAME, else "unknown")
    tool_name    name of the executed tool
    args_hash    sha256 of canonical JSON arguments (first 16 hex chars)
    timestamp_ms wall-clock epoch milliseconds
    duration_ms  execution duration in milliseconds
    exit_code    0 ok, 1 error, None for pre-execution denials
    status       "ok" | "error" | "denied"
    redacted     always true — raw arguments are never written

Rotation: date-stamped files segment per day; prune_old_logs() deletes
files older than STARSHIP_AUDIT_RETENTION_DAYS (default 30) and is run
opportunistically at most once per process-day.

Failure-isolated by design: audit write errors are logged at debug and
never propagate into the tool path.
"""

import hashlib
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

AUDIT_DIR = Path(os.getenv("STARSHIP_AUDIT_DIR", "/var/log/starship/audit"))
RETENTION_DAYS = int(os.getenv("STARSHIP_AUDIT_RETENTION_DAYS", "30"))

DIR_MODE = 0o750
FILE_MODE = 0o640
_ARGS_HASH_MAX_INPUT = 64 * 1024
_FILENAME_RE = re.compile(r"^(?P<agent>[A-Za-z0-9._-]+)-(?P<date>\d{8})\.jsonl$")

_last_prune_day: Optional[str] = None

log = None


def _logger():
    global log
    if log is None:
        log = __import__("logging").getLogger("tool-audit")
    return log


def agent_id() -> str:
    """Best-effort agent identity from the environment."""
    raw = os.getenv("STARSHIP_AGENT_NAME", "").strip()
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", raw)
    return cleaned or "unknown"


def args_hash(arguments: Any = None) -> str:
    """Stable short hash of tool arguments. Raw values are never stored."""
    try:
        canonical = json.dumps(arguments if arguments is not None else {},
                               sort_keys=True, default=str)
    except (TypeError, ValueError):
        canonical = repr(arguments)
    return hashlib.sha256(canonical.encode()[:_ARGS_HASH_MAX_INPUT]).hexdigest()[:16]


def _audit_path(agent: str, when: datetime) -> Path:
    return AUDIT_DIR / f"{agent}-{when.strftime('%Y%m%d')}.jsonl"


def audit_tool_call(
    tool_name: str,
    arguments: Any = None,
    *,
    agent: str = "",
    duration_ms: int = 0,
    exit_code: Optional[int] = 0,
    status: str = "ok",
) -> bool:
    """Append one JSONL audit record. Returns True on successful write.

    Never raises: callers must not let auditing break tool execution.
    """
    try:
        now = datetime.now(timezone.utc)
        who = agent or agent_id()
        record = {
            "agent_id": who,
            "tool_name": tool_name,
            "args_hash": args_hash(arguments),
            "timestamp_ms": int(now.timestamp() * 1000),
            "duration_ms": int(duration_ms),
            "exit_code": exit_code,
            "status": status,
            "redacted": True,
        }
        AUDIT_DIR.mkdir(parents=True, exist_ok=True)
        try:
            AUDIT_DIR.chmod(DIR_MODE)
        except OSError:
            pass
        path = _audit_path(who, now)
        line = json.dumps(record, separators=(",", ":")) + "\n"
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(line)
            fh.flush()
        try:
            path.chmod(FILE_MODE)
        except OSError:
            pass
        maybe_prune()
        return True
    except Exception as exc:  # failure-isolated
        _logger().debug("tool audit write skipped for '%s': %s", tool_name, exc)
        return False


def maybe_prune(now: Optional[datetime] = None) -> int:
    """Prune stale audit files at most once per day. Returns files removed."""
    global _last_prune_day
    try:
        now = now or datetime.now(timezone.utc)
        today = now.strftime("%Y%m%d")
        if _last_prune_day == today:
            return 0
        removed = prune_old_logs(now=now)
        _last_prune_day = today
        return removed
    except Exception as exc:
        _logger().debug("audit retention sweep skipped: %s", exc)
        return 0


def prune_old_logs(*, now: Optional[datetime] = None) -> int:
    """Delete <agent>-<date>.jsonl files older than RETENTION_DAYS."""
    now = now or datetime.now(timezone.utc)
    if not AUDIT_DIR.is_dir():
        return 0
    cutoff = now.timestamp() - RETENTION_DAYS * 86400
    removed = 0
    for entry in AUDIT_DIR.iterdir():
        m = _FILENAME_RE.match(entry.name)
        if not m or not entry.is_file():
            continue
        try:
            file_day = datetime.strptime(m.group("date"), "%Y%m%d").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if file_day.timestamp() < cutoff:
            entry.unlink(missing_ok=True)
            removed += 1
    return removed
