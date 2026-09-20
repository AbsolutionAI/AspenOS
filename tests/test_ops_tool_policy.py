"""H-005 (ASP-173): ops role minimum-necessary tool allowlist.

Validates the shared policy contract change against the real C11
policyexec binary and the Python bridge, proving:

- ops role has an explicit allowlist (empty allow no longer means allow-all)
- non-essential system tools are denied by the expanded blocklist
- existing agent capabilities (red-team, no-role) are unchanged
"""

import os
import sys
from pathlib import Path

import pytest

AGENTS_DIR = Path(__file__).resolve().parent.parent / "agents"
sys.path.insert(0, str(AGENTS_DIR))

import policy_native  # noqa: E402

REPO_ROOT = AGENTS_DIR.parent
POLICY = REPO_ROOT / "config" / "policy.default.json"


def _policyexec():
    binary = policy_native.policyexec_binary()
    assert binary, "policyexec binary must be built for H-005 policy tests"
    return binary


@pytest.fixture(autouse=True)
def clean_role_env(monkeypatch):
    monkeypatch.delenv("STARSHIP_FLEET_ROLES", raising=False)
    monkeypatch.delenv("STARSHIP_FLEET_TEAM", raising=False)


def _check(policyexec_args):
    import subprocess

    proc = subprocess.run(
        [_policyexec(), "--policy", str(POLICY)] + policyexec_args,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return proc.returncode


# ─── ops role: explicit allowlist (criterion 1) ─────────────────────

OPS_ALLOWED = [
    "read_file",
    "write_file",
    "list_dir",
    "search_files",
    "shell",
    "http_get",
    "http_post",
    "delegate_to_agent",
    "delegate",
    "memory_note",
    "user_profile",
    "archive_search",
    "temporal_graph",
    "temporal_chain",
    "temporal_snapshot",
    "kg_query",
    "kg_store",
    "preference_note",
    "preference_query",
    "create_schedule",
    "list_schedules",
    "remove_schedule",
    "goal_create",
    "goal_list",
    "goal_update",
    "mission_create",
    "mission_list",
    "task_create",
    "task_list",
    "task_complete",
]


@pytest.mark.parametrize("tool", OPS_ALLOWED)
def test_ops_allows_declared_capabilities(tool):
    assert _check(["--role", "ops", "check-tool", tool]) == 0


OPS_DENIED = [
    # expansion/design is not an operations capability
    "opencode",
    "opendesign",
    # HITL vault decisions are human-only
    "vault_approve",
    "vault_deny",
    # not in allowlist → fail closed even without explicit deny entry
    "vault_sync",
    "vault_note",
]


@pytest.mark.parametrize("tool", OPS_DENIED)
def test_ops_denies_non_essential_tools(tool):
    assert _check(["--role", "ops", "check-tool", tool]) == 1


# ─── existing capabilities unchanged (criterion 3) ──────────────────

def test_red_team_behavior_unchanged():
    assert _check(["--role", "red-team", "check-tool", "read_file"]) == 0
    assert _check(["--role", "red-team", "check-tool", "shell"]) == 1
    assert _check(["--role", "red-team", "check-tool", "opencode"]) == 1


def test_no_role_behavior_unchanged():
    assert _check(["check-tool", "shell"]) == 0
    assert _check(["check-tool", "opencode"]) == 1


# ─── expanded command blocklist (criterion 2) ───────────────────────

BLOCKED = [
    # pre-existing entries — regression guard
    "mount",
    "dd",
    "iptables",
    # H-005 additions
    "fdisk",
    "parted",
    "modprobe",
    "kexec",
    "useradd",
    "passwd",
    "visudo",
    "crontab",
]


@pytest.mark.parametrize("cmd", BLOCKED)
def test_blocklist_denies_system_tools(cmd):
    assert _check(["check-command", cmd]) == 1


def test_blocklist_does_not_break_operational_commands():
    assert _check(["check-command", "/bin/echo"]) == 0
    assert _check(["check-command", "systemctl"]) == 0


# ─── python bridge end-to-end ────────────────────────────────────────

def test_python_bridge_enforces_ops_role(monkeypatch):
    monkeypatch.setenv("STARSHIP_POLICYEXEC", _policyexec())
    monkeypatch.setenv("STARSHIP_POLICY", str(POLICY))
    monkeypatch.setenv("STARSHIP_FLEET_ROLES", "ops")
    assert policy_native.check_tool("shell") is None
    reason = policy_native.check_tool("vault_approve")
    assert reason is not None
    assert "vault_approve" in reason
