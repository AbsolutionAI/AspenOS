"""H-024 P0-2: NATS TLS-by-default contract for ops/edge cells.

Covers three layers:
  * TLS mode resolution (firstboot defaults ops/edge on, server off, explicit wins)
  * generator behavior (mutual flag, mode re-issue on an existing cell)
  * gate wiring (gate exists, runs clean, is wired into CI and nightly)
"""

import os
import re
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIRSTBOOT = ROOT / "scripts" / "starship-firstboot.sh"
TLS_GEN = ROOT / "scripts" / "gen-nats-tls.sh"
GATE = ROOT / "scripts" / "check-nats-tls-default.sh"


def _run(cmd, env=None, cwd=None):
    full_env = dict(os.environ)
    if env:
        full_env.update(env)
    return subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        text=True,
        env=full_env,
        cwd=cwd or ROOT,
        timeout=180,
    )


# ─── TLS mode resolution ───────────────────────────────────────────────

# Extracted from firstboot so the assertions test the real resolver rather
# than a Python re-implementation of it (which would pass even if bash broke).
_RESOLVER = re.compile(
    r"_resolve_tls_mode\(\)\s*\{(.*?)\n\}", re.DOTALL
)


def _resolve_tls_mode(profile: str, env_value: str | None) -> str:
    """Run the real bash resolver in isolation and return its stdout."""
    m = _RESOLVER.search(FIRSTBOOT.read_text())
    assert m, "firstboot has no _resolve_tls_mode resolver"
    script = (
        "set -euo pipefail\n"
        'PROFILE="$1"; STARSHIP_NATS_TLS="$2"\n'
        f"{m.group(1)}\n"
        "_resolve_tls_mode\n"
    )
    return _run(["bash", "-c", script, "_", profile, env_value or ""]).stdout.strip()


def test_ops_profile_defaults_tls_on():
    assert _resolve_tls_mode("ops", None) == "on"


def test_edge_profile_defaults_tls_on():
    assert _resolve_tls_mode("edge", None) == "on"


def test_server_profile_defaults_tls_off():
    # server/dev is loopback agent-bus; forcing TLS there breaks dev boxes.
    assert _resolve_tls_mode("server", None) == "off"


def test_explicit_off_overrides_profile_default():
    for value in ("0", "false", "off", "no"):
        assert _resolve_tls_mode("ops", value) == "off", value
        assert _resolve_tls_mode("edge", value) == "off", value


def test_explicit_on_overrides_profile_default():
    for value in ("1", "true", "on", "yes"):
        assert _resolve_tls_mode("server", value) == "on", value


def test_invalid_explicit_value_falls_back_to_profile_default():
    # Warns, then defers to the profile default rather than guessing.
    assert _resolve_tls_mode("ops", "maybe") == "on"
    assert _resolve_tls_mode("server", "maybe") == "off"


def test_resolver_matrix_is_complete():
    """8 combinations: {ops,edge,server,other} x {unset, explicit}."""
    expected = {
        ("ops", None): "on",
        ("edge", None): "on",
        ("server", None): "off",
        ("other", None): "off",
        ("ops", "1"): "on",
        ("edge", "0"): "off",
        ("server", "0"): "off",
        ("other", "1"): "on",
    }
    for (profile, value), want in expected.items():
        got = _resolve_tls_mode(profile, value)
        assert got == want, f"{profile=} {value=} → {got}, want {want}"


# ─── firstboot structure ───────────────────────────────────────────────


def test_tls_runs_after_bus_selection():
    """active.conf is created by bus selection; TLS must not run before it."""
    src = FIRSTBOOT.read_text()
    tls_call = src.index('if [[ "$TLS_MODE" == "on" ]]')
    selection = src.index("# Bus selection:")
    assert tls_call > selection, "TLS must be applied after bus selection"


def test_tls_path_is_bus_agnostic():
    """Resolves active.conf rather than hardcoding one bus conf."""
    src = FIRSTBOOT.read_text()
    assert "readlink -f /etc/starship/nats/active.conf" in src


def test_firstboot_fails_closed_when_tls_required():
    src = FIRSTBOOT.read_text()
    assert "STARSHIP_NATS_TLS_BEST_EFFORT" in src
    # The opt-out message must tell the operator how to fix it.
    assert "STARSHIP_NATS_TLS=0" in src
    assert "openssl is installed" in src


def test_firstboot_does_not_swallow_tls_failure():
    """The generator must run failure-checked, never under a bare `|| true`."""
    src = FIRSTBOOT.read_text()
    body = src[src.index("_enable_nats_tls() {"):src.index("TLS_MODE=")]
    call = [line for line in body.splitlines() if 'bash "$tls_gen"' in line]
    assert call, "generator is never invoked"
    assert "|| true" not in call[0], f"generator failure is swallowed: {call[0]}"
    # and the caller must branch on its return status
    assert 'if ! _enable_nats_tls; then' in src


# ─── generator behavior ────────────────────────────────────────────────


def _gen(args, out_dir):
    return _run(["bash", str(TLS_GEN), "--out", str(out_dir), *args])


def test_generator_emits_server_auth_by_default(tmp_path):
    out = tmp_path / "tls"
    result = _gen(["--host", "cell-1.local"], out)
    assert result.returncode == 0, result.stderr
    snippet = (out / "tls.conf.snippet").read_text()
    assert "verify: false" in snippet
    assert "verify: true" not in snippet


def test_generator_mutual_flag_sets_verify_true(tmp_path):
    out = tmp_path / "tls"
    result = _gen(["--host", "cell-1.local", "--mutual"], out)
    assert result.returncode == 0, result.stderr
    snippet = (out / "tls.conf.snippet").read_text()
    assert "verify: true" in snippet
    assert "verify_and_map: false" in snippet
    assert "verify: false" not in snippet


def test_generator_rejects_invalid_mutual_value(tmp_path):
    """Env-var path is validated too, not just the CLI flag."""
    out = tmp_path / "tls"
    result = _run(
        ["bash", str(TLS_GEN), "--out", str(out)],
        env={"STARSHIP_NATS_TLS_MUTUAL": "not-a-bool"},
    )
    assert result.returncode != 0
    assert "invalid --mutual value" in result.stderr


def test_generator_is_idempotent_in_same_mode(tmp_path):
    out = tmp_path / "tls"
    first = _gen(["--host", "cell-1.local"], out)
    assert first.returncode == 0, first.stderr
    fingerprint = (out / "server-cert.pem").read_bytes()
    second = _gen(["--host", "cell-1.local"], out)
    assert second.returncode == 0, second.stderr
    assert "already present" in second.stdout
    assert (out / "server-cert.pem").read_bytes() == fingerprint


def test_upgrading_to_mutual_reissues_snippet_without_rotating_certs(tmp_path):
    """--mutual on an existing cell must not silently no-op (H-024)."""
    out = tmp_path / "tls"
    assert _gen(["--host", "cell-1.local"], out).returncode == 0
    fingerprint = (out / "server-cert.pem").read_bytes()

    upgrade = _gen(["--host", "cell-1.local", "--mutual"], out)
    assert upgrade.returncode == 0, upgrade.stderr
    assert "mode differs" in upgrade.stdout
    snippet = (out / "tls.conf.snippet").read_text()
    assert "verify: true" in snippet
    # Certs must survive — re-issuing is a config change, not a key rotation.
    assert (out / "server-cert.pem").read_bytes() == fingerprint


def test_generator_locks_private_keys(tmp_path):
    out = tmp_path / "tls"
    assert _gen(["--host", "cell-1.local"], out).returncode == 0
    for name in ("server-key.pem", "client-key.pem"):
        mode = stat.S_IMODE(os.stat(out / name).st_mode)
        assert mode == 0o600, f"{name} is {oct(mode)}, expected 600"
    assert stat.S_IMODE(os.stat(out).st_mode) == 0o700


def test_generator_creates_usable_cert_chain(tmp_path):
    out = tmp_path / "tls"
    assert _gen(["--host", "cell-1.local"], out).returncode == 0
    verify = _run(
        [
            "openssl", "verify", "-CAfile", str(out / "ca.pem"),
            str(out / "server-cert.pem"),
        ]
    )
    assert verify.returncode == 0, verify.stdout + verify.stderr


@pytest.mark.skipif(
    shutil.which("nats-server") is None, reason="nats-server not on PATH"
)
@pytest.mark.parametrize("mode", ["server-auth", "mutual"])
def test_real_nats_server_parses_the_generated_snippet(tmp_path, mode):
    """Append the snippet the way firstboot does and let nats-server parse it.

    A snippet that nats-server rejects takes the whole cell down, so this is
    the check that actually matters for the control.
    """
    out = tmp_path / mode
    args = ["--host", "cell-alpha.example.com"] + (["--mutual"] if mode == "mutual" else [])
    assert _gen(args, out).returncode == 0

    conf = tmp_path / f"{mode}.conf"
    conf.write_text(
        'port: 4222\n'
        'authorization {\n'
        '  token: "x"\n'
        '  timeout: 2.0\n'
        '}\n' + (out / "tls.conf.snippet").read_text()
    )
    result = _run(["nats-server", "-t", "-c", str(conf)])
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.skipif(
    shutil.which("nats-server") is None, reason="nats-server not on PATH"
)
def test_real_nats_server_parses_shipped_fleet_bus_with_mutual_snippet(tmp_path):
    """The conf an ops cell actually runs must survive the snippet append."""
    out = tmp_path / "tls"
    assert _gen(["--host", "cell-alpha.example.com", "--mutual"], out).returncode == 0

    shipped = (ROOT / "nats" / "fleet-bus.conf").read_text().replace(
        "__STARSHIP_NATS_TOKEN__", "realtoken"
    )
    conf = tmp_path / "fleet-bus.conf"
    conf.write_text(shipped + (out / "tls.conf.snippet").read_text())
    result = _run(["nats-server", "-t", "-c", str(conf)])
    assert result.returncode == 0, result.stdout + result.stderr


# ─── gate wiring ───────────────────────────────────────────────────────


def test_gate_passes_on_real_tree():
    result = _run(["bash", str(GATE)])
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS" in result.stdout


def test_gate_self_test_proves_itself():
    result = _run(["bash", str(GATE), "--self-test"])
    assert result.returncode == 0, result.stdout + result.stderr
    assert "load-bearing" in result.stdout
    assert "positive control" in result.stdout


def test_gate_catches_a_reverted_firstboot(tmp_path):
    """Mutation test: strip the resolver and confirm the gate turns red."""
    work = tmp_path / "tree"
    (work / "scripts").mkdir(parents=True)
    (work / "nats").mkdir(parents=True)
    for name in ("starship-firstboot.sh", "gen-nats-tls.sh", "check-nats-tls-default.sh"):
        shutil.copy(ROOT / "scripts" / name, work / "scripts" / name)
    shutil.copy(ROOT / "nats" / "fleet-bus.conf", work / "nats" / "fleet-bus.conf")

    src = (work / "scripts" / "starship-firstboot.sh").read_text()
    src = src.replace("ops|edge) echo on", "ops|edge) echo off")
    (work / "scripts" / "starship-firstboot.sh").write_text(src)

    result = _run(["bash", str(work / "scripts" / "check-nats-tls-default.sh")], cwd=work)
    assert result.returncode != 0
    assert "has_resolver" in result.stdout


def test_gate_has_no_false_positive_on_clean_copy(tmp_path):
    """A clean copy must still pass — guards against an over-strict gate."""
    work = tmp_path / "tree"
    (work / "scripts").mkdir(parents=True)
    (work / "nats").mkdir(parents=True)
    for name in ("starship-firstboot.sh", "gen-nats-tls.sh", "check-nats-tls-default.sh"):
        shutil.copy(ROOT / "scripts" / name, work / "scripts" / name)
    for conf in (ROOT / "nats").glob("*.conf"):
        shutil.copy(conf, work / "nats" / conf.name)

    result = _run(["bash", str(work / "scripts" / "check-nats-tls-default.sh")], cwd=work)
    assert result.returncode == 0, result.stdout + result.stderr


def test_shipped_nats_confs_have_no_hardcoded_verify_false():
    for conf in (ROOT / "nats").glob("*.conf"):
        text = conf.read_text()
        assert not re.search(r"^\s*verify:\s*false", text, re.MULTILINE), conf.name


# ─── CI + nightly wiring ───────────────────────────────────────────────


def test_ci_runs_the_tls_gate():
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text()
    assert "security-nats-tls" in ci
    assert "check-nats-tls-default.sh" in ci
    assert "test_nats_tls_default.py" in ci


def test_nightly_runs_the_tls_gate():
    nightly = (ROOT / "scripts" / "check-nightly.sh").read_text()
    assert "check-nats-tls-default.sh" in nightly
    assert "test_nats_tls_default.py" in nightly
    assert "H-024" in nightly


def test_firstboot_script_is_syntactically_valid():
    result = _run(["bash", "-n", str(FIRSTBOOT)])
    assert result.returncode == 0, result.stderr
    result = _run(["bash", "-n", str(TLS_GEN)])
    assert result.returncode == 0, result.stderr