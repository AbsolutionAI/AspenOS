"""H-HOST-01 / ASP-370: AUDITOR_BASELINE SSH+UFW apply script (hermetic).

Verifies scripts/apply-auditor-baseline.sh without applying anything:

- the script exists, is executable, and defaults to --dry-run
- dry-run exits 0, prints the planned ruleset + evidence template, touches nothing
- --apply refuses when not root (skipped when the test runs as root)
- the allowlist gate fails closed when a lockout port is missing from the rules
- the rendered sshd drop-in contains the required hardening directives
- the rendered UFW ruleset has default-deny incoming + default-allow outgoing
  and every allowlist port, and never contains secrets

Tests never call live `ufw`/`sshd` and never run --apply with root privileges.
"""
import os
import re
import stat
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "apply-auditor-baseline.sh"

REQUIRED_SSHD = [
    "PermitRootLogin no",
    "PasswordAuthentication no",
    "PubkeyAuthentication yes",
    "AllowUsers",
]

ALLOWLIST_PORTS = [22, 443, 3100, 8788, 3000]


def run_script(*args, check: bool = True, input_env: dict | None = None):
    env = dict(os.environ)
    if input_env:
        env.update(input_env)
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        capture_output=True,
        text=True,
        check=check,
        env=env,
        timeout=60,
    )


def test_script_exists_and_executable():
    assert SCRIPT.is_file(), f"missing {SCRIPT.name}"
    st = SCRIPT.stat()
    assert st.st_mode & stat.S_IXUSR, f"{SCRIPT.name} is not executable"
    head = SCRIPT.read_text(encoding="utf-8").splitlines()[0]
    assert head.startswith("#!/usr/bin/env bash"), "missing bash shebang"


def test_dry_run_default_exits_zero_and_prints_plan():
    res = run_script()
    assert res.returncode == 0, f"dry-run failed: {res.stdout}\n{res.stderr}"
    assert "mode=dry-run" in res.stdout
    assert "no changes will be made" in res.stdout
    assert "planned UFW rules:" in res.stdout
    assert "default deny incoming" in res.stdout
    assert "=== BEFORE (evidence template, no secrets) ===" in res.stdout
    assert "No changes were made." in res.stdout


def test_dry_run_contains_all_allowlist_ports():
    res = run_script()
    for port in ALLOWLIST_PORTS:
        assert re.search(rf"\b{port}/tcp\b|\bport {port}\b", res.stdout), (
            f"allowlist port {port}/tcp missing from planned UFW rules"
        )


def test_dry_run_prints_sshd_dropin_with_required_directives():
    res = run_script()
    for directive in REQUIRED_SSHD:
        assert directive in res.stdout, (
            f"sshd drop-in missing required directive {directive!r}"
        )


@pytest.mark.skipif(os.geteuid() == 0, reason="must not run --apply as root")
def test_apply_refuses_without_root():
    res = run_script("--apply", check=False)
    assert res.returncode != 0, "--apply as non-root should fail"
    assert "root required" in res.stderr


def test_allowlist_gate_fails_closed():
    # Simulate an outdated allowlist entry that is not in the ruleset.
    env_src = (
        f'source {SCRIPT} >/dev/null 2>&1\n'
        'ALLOWLIST=( "tcp 9999 not in ruleset" )\n'
        'if check_allowlist_in_rules; then echo VALIDATE_PASS; '
        'else echo VALIDATE_FAIL; fi\n'
    )
    res = subprocess.run(["bash", "-c", env_src], capture_output=True, text=True)
    assert "VALIDATE_FAIL" in res.stdout, "gate must fail when a port is missing"


def test_allowlist_gate_passes_full_ruleset():
    env_src = (
        f'source {SCRIPT} >/dev/null 2>&1\n'
        'if check_allowlist_in_rules; then echo VALIDATE_PASS; '
        'else echo VALIDATE_FAIL; fi\n'
    )
    res = subprocess.run(["bash", "-c", env_src], capture_output=True, text=True)
    assert "VALIDATE_PASS" in res.stdout, "gate must pass for the full ruleset"


def test_sshd_conf_allowusers_uses_override_env():
    res = run_script(input_env={"ASPEN_SSH_ALLOW_USERS": "aspen robot-ops"})
    assert "AllowUsers aspen robot-ops" in res.stdout


def test_ufw_default_policies():
    res = run_script()
    assert re.search(r"ufw default deny incoming", res.stdout)
    assert re.search(r"ufw default allow outgoing", res.stdout)


def test_evidence_template_has_no_secrets():
    res = run_script()
    out = res.stdout
    for needle in ("BEGIN OPENSSH PRIVATE KEY", "BEGIN PRIVATE KEY",
                   "ssh-rsa ", "ssh-ed25519", "-----BEGIN"):
        assert needle not in out, f"evidence/plan output leaked secret-like {needle!r}"


def test_dry_run_touches_no_sshd_dropin():
    dropin = "/etc/ssh/sshd_config.d/99-aspen-baseline.conf"
    before = Path(dropin).read_text(encoding="utf-8") if Path(dropin).exists() else None
    run_script()
    after = Path(dropin).read_text(encoding="utf-8") if Path(dropin).exists() else None
    assert after == before, "dry-run must not modify the sshd drop-in"