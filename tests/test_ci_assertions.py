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


def _smoke_job() -> str:
    m = re.search(r"^  smoke:.*?(?=^  [a-z0-9-]+:)", _ci(), re.S | re.M)
    assert m, "missing smoke job in ci.yml"
    return m.group(0)


def test_ci_nats_install_is_guarded():
    """ASP-721: the smoke job's nats-server install fails closed on a broken download."""
    smoke = _smoke_job()
    assert "set -euo pipefail" in smoke
    assert "if ! command -v nats-server >/dev/null 2>&1; then" in smoke
    assert smoke.index("set -euo pipefail") < smoke.index("nats-server")
    assert "v2.14.5" in smoke
    assert "v2.14.3" not in smoke


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


def test_nightly_section_16_devonly_gate_present():
    nightly = _nightly()
    assert "Section 16: Dev-only package isolation" in nightly
    assert "no Dev-only in production paths" in nightly


def _build_deb() -> str:
    return (ROOT / "scripts" / "build-deb.sh").read_text()


def _postinst() -> str:
    return (ROOT / "debian" / "DEBIAN" / "postinst").read_text()


def test_build_deb_stages_apparmor_profiles():
    """H-010: the .deb build must stage AppArmor profiles (ASP-374)."""
    deb = _build_deb()
    assert "etc/apparmor.d" in deb
    assert "security/apparmor" in deb
    for profile in ("agnetic-agent", "nats", "ollama"):
        assert profile in deb, f"build-deb.sh missing profile {profile}"
    # Layout validation must enforce profiles ship in the .deb
    assert 'etc/apparmor.d/agnetic-agent"' in deb
    assert 'etc/apparmor.d/nats"' in deb
    # Parser load belongs to postinst on the installed target, not the build
    assert "apparmor_parser" not in deb


def test_postinst_loads_apparmor_without_enforce():
    """H-010: postinst parses each profile, never enforces (ASP-374)."""
    inst = _postinst()
    for profile in ("agnetic-agent", "nats", "ollama"):
        assert profile in inst
    assert "apparmor_parser -r" in inst
    assert "aa-enforce" not in inst


def test_nightly_section_17_apparmor_deb_shipped():
    """H-010: nightly asserts profiles stage, postinst parses, no enforce."""
    nightly = _nightly()
    assert "Section 17: AppArmor profiles in deb (H-010)" in nightly
    assert "apparmor profiles in security/apparmor" in nightly
    assert "build-deb stages apparmor profiles" in nightly
    assert "postinst has apparmor_parser" in nightly
    assert "apparmor_parser -r" in nightly
    assert "postinst avoids aa-enforce" in nightly


def test_nightly_section_19_nats_rate_limits_present():
    """F-011: nightly asserts NATS rate limits + per-account connection caps."""
    nightly = _nightly()
    assert "Section 19: NATS rate limits & connection caps" in nightly
    assert "max_pending: 16MB" in nightly
    assert "max_closed_clients: 4096" in nightly
    assert "fleet-bus auth timeout hardened" in nightly
    assert "accounts template per-account limits" in nightly
    assert "test_nats_rate_limits.py" in nightly


def test_nightly_section_20_cgroup_limits_present():
    """F-012: nightly asserts cgroup per-agent resource limit drop-ins."""
    nightly = _nightly()
    assert "Section 20: cgroup per-agent resource limits" in nightly
    assert "cgroup drop-ins exist for every unit" in nightly
    assert "agent drop-in carries cgroup keys" in nightly
    assert "build-deb stages service.d drop-in dirs" in nightly
    assert "install-systemd installs drop-ins to /etc" in nightly
    assert "test_cgroup_limits.py" in nightly


def _ci_job(name: str) -> str:
    """Return the raw YAML body of one job in ci.yml.

    Job bodies are two-space indented; a line that is indented exactly two spaces
    and then non-space starts the next job, so that is where this one ends.
    """
    ci = _ci()
    start = ci.index(f"\n  {name}:\n") + 1
    rest = ci[start:]
    nxt = re.search(r"^  \S", rest[1:], re.MULTILINE)
    return rest if nxt is None else rest[: nxt.start() + 1]


def test_ci_runs_full_python_suite():
    """ASP-730: CI must run tests/ wholesale, not named files only.

    The named-file-only gate let origin/master go red (ASP-706) with every required
    check green, so the failure only surfaced in nightly section 13 and QA preflight.
    """
    ci = _ci()
    assert "python -m pytest tests/" in ci, "ci.yml must run the full tests/ suite"
    assert "python-test-suite:" in ci, "ci.yml must define the python-test-suite job"


def test_ci_full_suite_job_is_not_a_soft_gate():
    """ASP-730: the full-suite check is required, not continue-on-error.

    A silently-optional job recreates the blind spot it was added to close.
    """
    job = _ci_job("python-test-suite")
    assert "continue-on-error" not in job, "python-test-suite must not be continue-on-error"
    assert "always()" not in job, "python-test-suite must not be gated by always()"


def test_ci_full_suite_job_matches_nightly_interpreter():
    """ASP-730: the CI gate runs the same Python as the nightly host.

    The suite had never been executed on the CI interpreter, which is how a real bug
    (services/hitl.py unimportable without aiohttp on Python < 3.14) stayed green
    here and red in nightly section 13.
    """
    job = _ci_job("python-test-suite")
    assert "python-version: '3.12'" in job, "python-test-suite must use the nightly Python"
    installs = [ln for ln in job.splitlines() if "pip install" in ln]
    assert installs, "python-test-suite must install the suite deps"
    joined = " ".join(installs)
    for dep in ("pytest", "pytest-asyncio", "pyyaml"):
        assert dep in joined, f"python-test-suite must install {dep}"
    # Optional deps stay out so their documented skips keep skipping.
    for optional in ("aiohttp", "nats-py", "mcp", "httpx"):
        assert optional not in joined, (
            f"{optional} must stay optional: installing it deletes a documented skip "
            f"and changes the gate's baseline"
        )


def test_guarded_optional_imports_defer_annotations():
    """ASP-730: `web = None` must be survivable at import time.

    These modules guard `from aiohttp import web` with `except ImportError`, then
    annotate module-level defs `-> web.Response`. Without PEP 563 that annotation is
    evaluated at def time, so the module cannot be imported at all when aiohttp is
    absent -- defeating the guard and failing the suite on any Python < 3.14.
    """
    guarded = sorted(
        p for p in (ROOT / "services").glob("*.py")
        if "from aiohttp import web" in p.read_text()
    )
    assert len(guarded) >= 7, f"expected the guarded service modules, found {guarded}"
    for path in guarded:
        text = path.read_text()
        assert "from __future__ import annotations" in text, (
            f"{path.name} guards its aiohttp import but still evaluates web.Response "
            f"annotations at import time"
        )
        assert "web = None" in text, f"{path.name} must keep the optional-import guard"
