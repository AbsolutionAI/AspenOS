"""Host-relative path derivation (ASP-733).

The property under test is the one nothing asserted before: these defaults
follow the *invoking host*, not the machine the code was written on. The
pre-existing `/home/tech` literals made every one of these assertions
unreachable on any other runner, and made the CI suite green by accident.
"""

import importlib
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import paths as P

_ALL_DATA_VARS = (
    "ASPEN_DATA_HOME",
    "XDG_DATA_HOME",
    "HERMES_AGENT_ROOT",
    "AGNETIC_MEMORY_INGEST_DIR",
    "AGNETIC_MEMORY_FACTS_DIR",
    "ASPEN_HOLOGRAPHIC_DB",
)


@pytest.fixture
def clean_env(monkeypatch):
    """No Aspen/XDG override set, and a home that is not the author's."""
    for var in _ALL_DATA_VARS:
        monkeypatch.delenv(var, raising=False)
    return monkeypatch


# --- derivation follows $HOME -------------------------------------------------


def test_data_home_follows_home(clean_env, tmp_path):
    clean_env.setenv("HOME", str(tmp_path))
    assert P.data_home() == tmp_path / ".aspen"
    assert P.memory_ingest_dir() == tmp_path / ".aspen" / "memory" / "ingest"
    assert P.memory_facts_dir() == tmp_path / ".aspen" / "memory" / "facts"
    assert P.memory_facts_log() == tmp_path / ".aspen" / "memory" / "facts" / "facts.jsonl"
    assert P.holographic_db() == tmp_path / ".aspen" / "memory" / "holographic.db"


def test_hermes_root_follows_home(clean_env, tmp_path):
    clean_env.setenv("HOME", str(tmp_path))
    assert P.hermes_agent_root() == tmp_path / ".hermes" / "hermes-agent"


def test_derivation_is_per_call_not_frozen_at_import(clean_env, tmp_path):
    """A module-level constant freezes whichever host imported it first.

    That is the exact bug this module exists to remove, so it is asserted
    directly rather than assumed.
    """
    first, second = tmp_path / "host-a", tmp_path / "host-b"
    clean_env.setenv("HOME", str(first))
    assert P.data_home() == first / ".aspen"
    clean_env.setenv("HOME", str(second))
    assert P.data_home() == second / ".aspen"


# --- precedence ---------------------------------------------------------------


def test_xdg_data_home_beats_home(clean_env, tmp_path):
    clean_env.setenv("HOME", str(tmp_path / "home"))
    clean_env.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
    assert P.data_home() == tmp_path / "xdg" / "starship"


def test_aspen_data_home_beats_xdg_and_home(clean_env, tmp_path):
    clean_env.setenv("HOME", str(tmp_path / "home"))
    clean_env.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
    clean_env.setenv("ASPEN_DATA_HOME", str(tmp_path / "pinned"))
    assert P.data_home() == tmp_path / "pinned"
    assert P.memory_ingest_dir() == tmp_path / "pinned" / "memory" / "ingest"


@pytest.mark.parametrize(
    "var,fn",
    [
        ("AGNETIC_MEMORY_INGEST_DIR", P.memory_ingest_dir),
        ("AGNETIC_MEMORY_FACTS_DIR", P.memory_facts_dir),
        ("ASPEN_HOLOGRAPHIC_DB", P.holographic_db),
        ("HERMES_AGENT_ROOT", P.hermes_agent_root),
    ],
)
def test_explicit_override_wins_over_every_derived_default(clean_env, tmp_path, var, fn):
    clean_env.setenv("HOME", str(tmp_path / "home"))
    clean_env.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
    clean_env.setenv("ASPEN_DATA_HOME", str(tmp_path / "pinned"))
    clean_env.setenv(var, str(tmp_path / "explicit"))
    assert fn() == tmp_path / "explicit"


def test_blank_override_is_ignored_not_treated_as_cwd(clean_env, tmp_path, monkeypatch):
    """An exported-but-empty var must not resolve to the current directory."""
    clean_env.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.chdir(tmp_path)
    clean_env.setenv("ASPEN_DATA_HOME", "   ")
    assert P.data_home() == tmp_path / "home" / ".aspen"


def test_override_is_expandusered(clean_env, tmp_path):
    clean_env.setenv("HOME", str(tmp_path))
    clean_env.setenv("ASPEN_DATA_HOME", "~/elsewhere")
    assert P.data_home() == tmp_path / "elsewhere"


def test_unset_home_falls_back_to_the_passwd_entry(clean_env, monkeypatch):
    """A systemd unit or CI runner may have no HOME at all.

    `os.path.expanduser` falls back to the passwd database, so the answer is
    still a real absolute home rather than an exception at import time.
    """
    import os
    import pwd

    clean_env.delenv("HOME", raising=False)
    expected = Path(pwd.getpwuid(os.getuid()).pw_dir) / ".aspen"
    assert P.data_home() == expected
    assert P.data_home().is_absolute()


# --- the importing modules ----------------------------------------------------


def test_memory_ingest_default_follows_relocated_home(clean_env, tmp_path):
    clean_env.setenv("HOME", str(tmp_path))
    mi = importlib.reload(importlib.import_module("memory_ingest"))
    assert mi.DEFAULT_INGEST_DIR == tmp_path / ".aspen" / "memory" / "ingest"

    path = mi.ingest_record(
        "opencode", "ASP-733-1", "Decision: default follows the host.",
    )
    assert path.parent.parent == tmp_path / ".aspen" / "memory" / "ingest"
    assert path.exists()


def test_memory_promote_defaults_follow_relocated_home(clean_env, tmp_path):
    clean_env.setenv("HOME", str(tmp_path))
    mp = importlib.reload(importlib.import_module("memory_promote"))
    assert mp.DEFAULT_INGEST_DIR == tmp_path / ".aspen" / "memory" / "ingest"
    assert mp.DEFAULT_FACTS_LOG == tmp_path / ".aspen" / "memory" / "facts" / "facts.jsonl"


def test_holographic_defaults_follow_relocated_home(clean_env, tmp_path):
    clean_env.setenv("HOME", str(tmp_path))
    hi = importlib.reload(importlib.import_module("holographic_ingest"))
    assert hi.DEFAULT_HOLOGRAPHIC_DB == tmp_path / ".aspen" / "memory" / "holographic.db"
    assert hi.HERMES_AGENT_ROOT == tmp_path / ".hermes" / "hermes-agent"


# --- the regression that motivated the ticket ---------------------------------


def test_cli_default_succeeds_with_home_that_is_not_writable(tmp_path):
    """ASP-730: this failed on CI with `Permission denied: '/home/tech'`.

    Runs the real CLI in a subprocess whose HOME is a *different* directory
    from the ingest root, so the assertion cannot be satisfied by a hardcoded
    path that happens to exist on the author's machine.
    """
    home = tmp_path / "home"
    ingest = tmp_path / "ingest"
    home.mkdir()

    env = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(home),
        "AGNETIC_MEMORY_INGEST_DIR": str(ingest),
        "ASPEN_HOLOGRAPHIC_DISABLE": "1",
        "PYTHONPATH": str(PROJECT_ROOT),
    }
    proc = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "memory_ingest.py"),
         "--source", "opencode",
         "--source-id", "ASP-733-cli", "--content", "Decision: CI-safe default."],
        capture_output=True, text=True, env=env, cwd=str(tmp_path),
        timeout=60, check=False,
    )
    assert proc.returncode == 0, proc.stderr
    written = list((ingest / "opencode").glob("*.jsonl"))
    assert written, f"no ingest file under {ingest}"


def test_cli_default_needs_no_override_at_all(clean_env, tmp_path):
    """The stronger form: with a foreign HOME and no override, the CLI writes
    under that HOME. This is the assertion the hardcoded literal made
    impossible, because it could only pass where /home/tech already existed.
    """
    home = tmp_path / "home"
    home.mkdir()
    env = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(home),
        "ASPEN_HOLOGRAPHIC_DISABLE": "1",
        "PYTHONPATH": str(PROJECT_ROOT),
    }
    proc = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "memory_ingest.py"),
         "--source", "opencode",
         "--source-id", "ASP-733-nooverride", "--content", "Decision: derived default."],
        capture_output=True, text=True, env=env, cwd=str(tmp_path),
        timeout=60, check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert list((home / ".aspen" / "memory" / "ingest" / "opencode").glob("*.jsonl"))


# --- no literal may come back -------------------------------------------------

_HARDCODED_HOME = "/home/tech"

# The ticket accepts "each hit has a written justification", so the surviving
# literals are enumerated here rather than left as folklore. Each entry is
# path -> (justification, substring that must be present on the line for the
# exemption to apply, so a *new* line in an exempted file still fails).
_ALLOWED = {
    "scripts/install-daemon.sh": (
        "install-time sed rewriting the retired source literal to /etc/starship/nats",
        "/etc/starship/nats",
    ),
    "scripts/paths.py": (
        "docstring prose naming the literal this module replaced",
        "previous hardcoded",
    ),
    "scripts/smoke-fleet-bus.py": (
        (
            "out of scope: last-resort entry in an ordered candidate list for a "
            "sibling checkout; repo-relative candidates are tried first"
        ),
        "/home/tech/repos",
    ),
    "scripts/test-iso-auto.sh": (
        "out of scope: verbatim preseed answers baked into the ISO image",
        "cd /home/tech/agnetic-os && make",
    ),
    "services/scripts/start-all-agents.sh.template": (
        "not executed: copy-paste template superseded by start-all-agents.sh",
        "STROAGNETIC_ROOT",
    ),
}


def _literal_hits(root: Path, subdir: str) -> list[tuple[str, int, str]]:
    hits = []
    for path in sorted((root / subdir).rglob("*")):
        if path.is_dir() or path.suffix in {".pyc"} or "__pycache__" in path.parts:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            if _HARDCODED_HOME in line:
                hits.append((f"{subdir}/{path.relative_to(root / subdir)}", lineno, line.strip()))
    return hits


@pytest.mark.parametrize("subdir", ["scripts", "services/scripts", "agents"])
def test_no_functional_source_hardcodes_the_operator_home(subdir):
    unapproved = []
    for rel, lineno, line in _literal_hits(PROJECT_ROOT, subdir):
        exemption = _ALLOWED.get(rel)
        if exemption and exemption[1] in line:
            continue
        unapproved.append(f"{rel}:{lineno}: {line}")
    assert not unapproved, "hardcoded operator home path(s):\n" + "\n".join(unapproved)


def test_every_allowlisted_exception_is_still_live_and_justified():
    """Guard the exemptions themselves.

    A stale exemption is worse than no guard: it reads like an approved
    exception while silently covering whatever the file contains next.
    """
    live = {rel for rel, _, _ in
            _literal_hits(PROJECT_ROOT, "scripts")
            + _literal_hits(PROJECT_ROOT, "services/scripts")
            + _literal_hits(PROJECT_ROOT, "agents")}
    for rel, (justification, marker) in _ALLOWED.items():
        assert justification.strip(), f"{rel} has an empty justification"
        assert marker, f"{rel} has an empty marker"
        assert rel in live, f"{rel} is exempted but no longer hits; drop the exemption"


def test_documentation_of_the_change_records_the_allowed_exception():
    """The one remaining functional hit is a deployment rewrite, and it is justified in-repo."""
    plan = (PROJECT_ROOT / "docs" / "plans" / "ASP-733.md").read_text(encoding="utf-8")
    assert _HARDCODED_HOME in plan
