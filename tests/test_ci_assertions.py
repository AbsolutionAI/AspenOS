"""CI contract: nightly check sections must not regress."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _smoke() -> str:
    return (ROOT / "scripts" / "smoke-test.sh").read_text()


def _ci() -> str:
    return (ROOT / ".github" / "workflows" / "ci.yml").read_text()


def _nightly() -> str:
    return (ROOT / "scripts" / "check-nightly.sh").read_text()


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


def test_nightly_section_13_python_test_suite_present():
    nightly = _nightly()
    assert "Section 13: Python test suite" in nightly
    assert "pytest importable" in nightly
    assert "python test suite" in nightly
    assert "pytest pass count >= 150" in nightly
    assert "no pytest failures" in nightly


def test_nightly_section_14_iso_structure_present():
    nightly = _nightly()
    assert "Section 14: ISO build structure" in nightly
    assert "iso/autoinstall dir exists" in nightly
    assert "edge profile exists" in nightly
    assert "server profile exists" in nightly
    assert "ops profile exists" in nightly
    assert "iso config hooks dir exists" in nightly
    assert "iso chroot hook exists" in nightly
    assert "iso package lists exist" in nightly
    assert "iso package list non-empty" in nightly


def test_nightly_section_15_dashboard_assets_present():
    nightly = _nightly()
    assert "Section 15: Dashboard static assets" in nightly
    for asset in ("style.css", "ui.js", "dashboard.js", "agents.js",
                  "chat.js", "panels.js", "incidents.js", "boot.js"):
        assert f"dashboard {asset}" in nightly, f"missing check for {asset}"


def test_nightly_python_test_uses_failed_not_error():
    nightly = _nightly()
    assert "grep -q 'FAILED'" in nightly
    assert "grep -q 'error'" not in nightly