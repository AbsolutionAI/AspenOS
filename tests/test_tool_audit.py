import asyncio
import json
import os
import time
from pathlib import Path

import pytest

import tool_audit
import tools


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture(autouse=True)
def audit_env(tmp_path, monkeypatch):
    audit_dir = tmp_path / "audit"
    monkeypatch.setenv("STARSHIP_AUDIT_DIR", str(audit_dir))
    monkeypatch.setattr(tool_audit, "AUDIT_DIR", audit_dir)
    monkeypatch.setattr(tool_audit, "_last_prune_day", None)
    monkeypatch.delenv("STARSHIP_AGENT_NAME", raising=False)
    return audit_dir


def _read_lines(audit_dir: Path, agent: str = "proxy"):
    path = audit_dir / f"{agent}-{time.strftime('%Y%m%d')}.jsonl"
    assert path.exists(), f"missing audit file {path}"
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


class TestArgsHash:
    def test_stable_and_truncated(self):
        h1 = tool_audit.args_hash({"command": "ls -la"})
        h2 = tool_audit.args_hash({"command": "ls -la"})
        assert h1 == h2
        assert len(h1) == 16

    def test_key_order_insensitive(self):
        assert tool_audit.args_hash({"a": 1, "b": 2}) == tool_audit.args_hash({"b": 2, "a": 1})

    def test_distinct_arguments_differ(self):
        assert tool_audit.args_hash({"command": "ls"}) != tool_audit.args_hash({"command": "pwd"})


class TestAgentId:
    def test_defaults_to_unknown(self):
        assert tool_audit.agent_id() == "unknown"

    def test_reads_env_and_sanitizes(self, monkeypatch):
        monkeypatch.setenv("STARSHIP_AGENT_NAME", "evil agent/x")
        assert tool_audit.agent_id() == "evil_agent_x"


class TestAuditToolCall:
    def test_writes_required_fields(self):
        ok = tool_audit.audit_tool_call(
            "shell", {"command": "ls"}, agent="romi", duration_ms=12, exit_code=0, status="ok"
        )
        assert ok is True
        (record,) = _read_lines(tool_audit.AUDIT_DIR, "romi")
        for field in ("agent_id", "tool_name", "args_hash", "timestamp_ms",
                      "duration_ms", "exit_code", "status", "redacted"):
            assert field in record
        assert record["tool_name"] == "shell"
        assert record["agent_id"] == "romi"
        assert record["duration_ms"] == 12
        assert record["exit_code"] == 0
        assert record["status"] == "ok"
        assert record["redacted"] is True

    def test_raw_arguments_never_written(self):
        secret_args = {"path": "/tmp/x", "content": "hunter2-password"}
        tool_audit.audit_tool_call("write_file", secret_args, agent="romi")
        (record,) = _read_lines(tool_audit.AUDIT_DIR, "romi")
        raw = json.dumps(record)
        assert "hunter2" not in raw
        assert record["args_hash"] == tool_audit.args_hash(secret_args)

    def test_enforces_file_mode_640(self):
        tool_audit.audit_tool_call("read_file", {"path": "/etc/hostname"}, agent="ops1")
        f = next(tool_audit.AUDIT_DIR.glob("ops1-*.jsonl"))
        assert (f.stat().st_mode & 0o777) == 0o640

    def test_denied_call_exit_code_none(self):
        tool_audit.audit_tool_call("shell", {}, agent="x", duration_ms=1,
                                   exit_code=None, status="denied")
        (record,) = _read_lines(tool_audit.AUDIT_DIR, "x")
        assert record["status"] == "denied"
        assert record["exit_code"] is None

    def test_failure_isolated(self, monkeypatch):
        monkeypatch.setattr(
            tool_audit.Path, "mkdir",
            lambda *a, **k: (_ for _ in ()).throw(OSError("disk full")),
        )
        assert tool_audit.audit_tool_call("shell", {}) is False


class TestRetention:
    def test_prune_old_logs_keeps_fresh(self):
        tool_audit.AUDIT_DIR.mkdir(parents=True, exist_ok=True)
        old_file = tool_audit._audit_path("old-agent", __import__("datetime").datetime(2000, 1, 1))
        old_file.write_text("{}\n")
        fresh = tool_audit._audit_path("new-agent", __import__("datetime").datetime.now())
        fresh.write_text("{}\n")
        removed = tool_audit.prune_old_logs()
        assert removed == 1
        assert not old_file.exists()
        assert fresh.exists()

    def test_maybe_prune_runs_once_per_day(self):
        tool_audit.AUDIT_DIR.mkdir(parents=True, exist_ok=True)
        old_file = tool_audit._audit_path("old", __import__("datetime").datetime(2000, 1, 1))
        old_file.write_text("{}\n")
        assert tool_audit.maybe_prune() == 1
        another = tool_audit._audit_path("old2", __import__("datetime").datetime(2000, 1, 2))
        another.write_text("{}\n")
        assert tool_audit.maybe_prune() == 0  # same-day no-op


class TestExecuteToolIntegration:
    def test_success_call_audited(self):
        target = os.path.join(str(tool_audit.AUDIT_DIR.parent), "t.txt")
        with open(target, "w") as fh:
            fh.write("hi")
        result = _run(tools.execute_tool("read_file", {"path": target}))
        assert result["error"] is False
        (record,) = _read_lines(tool_audit.AUDIT_DIR, "unknown")
        assert record["status"] == "ok"
        assert record["exit_code"] == 0

    def test_error_call_marked_error(self):
        result = _run(tools.execute_tool("nope_not_a_tool", {}))
        assert result["error"] is True
        (record,) = _read_lines(tool_audit.AUDIT_DIR, "unknown")
        assert record["status"] == "error"
        assert record["exit_code"] == 1

    def test_policy_denial_marked_denied(self):
        import fleet_policy
        with __import__("unittest").mock.patch.object(
            fleet_policy, "check_tool", return_value="denied by fleet ACL"
        ):
            result = _run(tools.execute_tool("opencode", {}))
        assert result["policy"] == "fleet"
        (record,) = _read_lines(tool_audit.AUDIT_DIR, "unknown")
        assert record["status"] == "denied"
