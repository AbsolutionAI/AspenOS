"""CI contract: nightly check sections and CI job wiring must not regress."""
import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# pip distribution name for a module whose name differs from it
DIST_ALIASES = {
    "yaml": "pyyaml",
    "PIL": "pillow",
    "cv2": "opencv-python",
    "sklearn": "scikit-learn",
    "dotenv": "python-dotenv",
    "bs4": "beautifulsoup4",
    "dateutil": "python-dateutil",
    "jwt": "pyjwt",
    "serial": "pyserial",
    "Crypto": "pycryptodome",
    "OpenSSL": "pyopenssl",
    "zmq": "pyzmq",
    "attr": "attrs",
}


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

def _ci_jobs() -> dict:
    """Split .github/workflows/ci.yml into {job_name: [step lines]}."""
    jobs: dict = {}
    name = None
    for line in _ci().splitlines():
        m = re.match(r"^  ([A-Za-z0-9_-]+):\s*$", line)
        if m and line not in jobs:
            name = m.group(1)
            jobs.setdefault(name, [])
            continue
        if name:
            jobs[name].append(line)
    return jobs


def _conftest_deps() -> set:
    """Third-party top-level modules tests/conftest.py imports at collection."""
    tree = ast.parse((ROOT / "tests" / "conftest.py").read_text())
    mods = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            mods.add(node.module.split(".")[0])
    return {m for m in mods if m not in sys.stdlib_module_names}


def _pip_installed(lines) -> set:
    """Distribution names installed by `pip install` anywhere in a job."""
    found = set()
    for line in lines:
        m = re.search(r"pip install ([^\n#]+)", line)
        if m:
            for token in m.group(1).split():
                if not token.startswith("-"):
                    found.add(token.lower())
    return found


def test_conftest_deps_discovered():
    """The contract below is only meaningful if conftest really imports these."""
    deps = _conftest_deps()
    assert {"pytest", "yaml"} <= deps, deps


def test_ci_jobs_running_tests_install_conftest_deps():
    """F-014/ASP-693: a CI job running `pytest tests/` must install conftest deps.

    pytest loads tests/conftest.py for every module under tests/, so a missing
    conftest dependency kills collection for the whole job. When that job is a
    security gate, it fails open: a green check that verified nothing.
    """
    jobs = _ci_jobs()
    required = _conftest_deps()
    offenders = {}
    for name, lines in jobs.items():
        if not any(re.search(r"pytest [^|]*tests/", ln) for ln in lines):
            continue
        installed = _pip_installed(lines)
        missing = sorted(
            mod for mod in required
            if mod.lower() not in installed
            and DIST_ALIASES.get(mod, mod).lower() not in installed
        )
        if missing:
            offenders[name] = missing
    assert not offenders, (
        f"CI jobs running `pytest tests/` without installing {sorted(required)}: {offenders}"
    )
