"""H-003 (ASP-171): native C11 sandbox/policy enforcement is mandatory, fail closed."""

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

AGENTS_DIR = Path(__file__).resolve().parent.parent / "agents"
sys.path.insert(0, str(AGENTS_DIR))

import native_check  # noqa: E402
import policy_native  # noqa: E402
import sandbox_native  # noqa: E402


FAKE_SANDBOX = "/tmp/fake-sandbox_run"
FAKE_POLICYEXEC = "/tmp/fake-policyexec"


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for var in (
        "STARSHIP_SANDBOX_NATIVE",
        "STARSHIP_POLICY_NATIVE",
        "STARSHIP_SANDBOX_RUN",
        "STARSHIP_POLICYEXEC",
    ):
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def fake_binaries(monkeypatch):
    for p in (FAKE_SANDBOX, FAKE_POLICYEXEC):
        Path(p).write_text("#!/bin/sh\nexit 0\n")
        os.chmod(p, 0o755)
    monkeypatch.setenv("STARSHIP_SANDBOX_RUN", FAKE_SANDBOX)
    monkeypatch.setenv("STARSHIP_POLICYEXEC", FAKE_POLICYEXEC)


# ─── default-on semantics ───────────────────────────────────────────

def test_native_enabled_by_default():
    assert sandbox_native.native_enabled() is True
    assert policy_native.native_enabled() is True


def test_explicit_opt_out_disables_native(monkeypatch):
    monkeypatch.setenv("STARSHIP_SANDBOX_NATIVE", "0")
    monkeypatch.setenv("STARSHIP_POLICY_NATIVE", "false")
    assert sandbox_native.native_enabled() is False
    assert policy_native.native_enabled() is False


# ─── fail closed: missing binaries ──────────────────────────────────

@pytest.fixture
def no_binaries(monkeypatch, tmp_path):
    """Hide repo-local and PATH binaries so lookups fail."""
    monkeypatch.setenv("STARSHIP_ROOT", str(tmp_path))
    monkeypatch.setattr(sandbox_native.shutil, "which", lambda name: None)
    monkeypatch.setattr(policy_native.shutil, "which", lambda name: None)
    real_file = Path.is_file

    def hidden(self):
        s = str(self)
        if s.endswith(("sandbox_spike/sandbox_run", "policyexec/policyexec")):
            return False
        return real_file(self)

    monkeypatch.setattr(Path, "is_file", hidden)


def test_require_sandbox_binary_raises_when_missing(no_binaries):
    with pytest.raises(RuntimeError, match="sandbox_run"):
        sandbox_native.require_native()


def test_require_policyexec_raises_when_missing(no_binaries):
    with pytest.raises(RuntimeError, match="policyexec"):
        policy_native.require_native()


def test_require_binaries_pass_with_fake_binaries(fake_binaries):
    assert sandbox_native.require_native() == FAKE_SANDBOX
    assert policy_native.require_native() == FAKE_POLICYEXEC


# ─── startup gate module ────────────────────────────────────────────

def test_native_check_fails_closed_without_binaries(no_binaries, capsys):
    assert native_check.main() == 1
    out = capsys.readouterr()
    assert "FATAL" in out.err


def test_native_check_passes_with_binaries(fake_binaries):
    assert native_check.main() == 0


# ─── CommandExecutor fails closed without Python fallback ──────────

def _run(coro):
    import asyncio

    return asyncio.run(coro)


def test_executor_fails_closed_when_native_bridge_broken():
    from tools import CommandExecutor, SandboxError

    executor = CommandExecutor(sandbox=True)
    with patch.dict(sys.modules, {"sandbox_native": None}):
        with pytest.raises(SandboxError):
            _run(executor.execute("echo hello"))


def test_executor_uses_python_fallback_only_on_explicit_opt_out():
    from tools import CommandExecutor

    monkey_env = {"STARSHIP_SANDBOX_NATIVE": "0"}
    executor = CommandExecutor(sandbox=True)
    with patch.dict(os.environ, monkey_env), patch.object(sandbox_native, "native_enabled", lambda: False):
        result = _run(executor.execute("echo hello"))
    assert result.success
    assert "hello" in result.stdout
