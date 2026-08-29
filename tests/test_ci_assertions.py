"""CI contract: NATS PATH + C11 help must not be brittle string/PATH traps."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _smoke() -> str:
    return (ROOT / "scripts" / "smoke-test.sh").read_text()


def _ci() -> str:
    return (ROOT / ".github" / "workflows" / "ci.yml").read_text()


def _gen_accounts_line() -> str:
    m = re.search(r'check "gen accounts conf valid".*', _smoke())
    assert m, "missing gen accounts conf valid check"
    return m.group(0)


def test_gen_accounts_path_includes_usr_local_bin():
    line = _gen_accounts_line()
    assert "/usr/local/bin" in line, line


def test_gen_accounts_skips_when_nats_server_missing():
    line = _gen_accounts_line()
    assert "command -v nats-server" in line, line


def test_smoke_c11_help_is_not_coupled_to_builtin_string():
    smoke = _smoke()
    assert "grep -q built-in" not in smoke
    assert "sandbox_run --help" in smoke


def test_ci_c11_help_is_not_coupled_to_builtin_string():
    ci = _ci()
    assert "grep -q built-in" not in ci
    assert "sandbox_run --help" in ci