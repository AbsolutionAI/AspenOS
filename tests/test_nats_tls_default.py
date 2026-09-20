"""H-006 (ASP-174): NATS TLS is on by default; mTLS with per-node certs
signed by the fleet CA; clients fail closed without a CA."""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(PROJECT_ROOT / "agents"))

import nats_connect  # noqa: E402

requires_openssl = pytest.mark.skipif(
    shutil.which("openssl") is None, reason="openssl not available"
)


@pytest.fixture(autouse=True)
def clean_nats_env(monkeypatch):
    for var in (
        "NATS_URL",
        "STARSHIP_NATS_TLS",
        "STARSHIP_NATS_CA",
        "STARSHIP_NATS_CERT",
        "STARSHIP_NATS_KEY",
        "STARSHIP_NATS_TLS_INSECURE",
    ):
        monkeypatch.delenv(var, raising=False)


def _gen_tls(tmp_path, *extra):
    out = tmp_path / "tls"
    result = subprocess.run(
        ["bash", str(PROJECT_ROOT / "scripts" / "gen-nats-tls.sh"),
         "--out", str(out), "--host", "nattest.local", *extra],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT),
    )
    assert result.returncode == 0, result.stderr
    return out


# ─── server side: mTLS snippet ──────────────────────────────────────

@requires_openssl
def test_gen_nats_tls_materializes_server_and_ca(tmp_path):
    out = _gen_tls(tmp_path)
    for name in ("ca.pem", "ca-key.pem", "server-cert.pem", "server-key.pem"):
        assert (out / name).exists(), name
    assert (out / "server-key.pem").read_bytes().startswith(b"-----BEGIN")


@requires_openssl
def test_tls_snippet_requires_and_verifies_client_certs(tmp_path):
    out = _gen_tls(tmp_path)
    body = (out / "tls.conf.snippet").read_text()
    assert "tls {" in body
    assert "verify: true" in body
    assert "verify: false" not in body
    assert "ca_file:" in body
    assert f'cert_file: "{out}/server-cert.pem"' in body


# ─── per-node identities signed by the fleet CA ─────────────────────

@requires_openssl
def test_node_cert_issued_and_signed_by_fleet_ca(tmp_path):
    out = _gen_tls(tmp_path)
    result = subprocess.run(
        ["bash", str(PROJECT_ROOT / "scripts" / "gen-nats-tls.sh"),
         "--out", str(out), "--node", "plant-edge-01"],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT),
    )
    assert result.returncode == 0, result.stderr
    cert = out / "node-plant-edge-01-cert.pem"
    key = out / "node-plant-edge-01-key.pem"
    assert cert.exists() and key.exists()
    verify = subprocess.run(
        ["openssl", "verify", "-CAfile", str(out / "ca.pem"), str(cert)],
        capture_output=True, text=True,
    )
    assert verify.returncode == 0, verify.stderr
    assert "OK" in verify.stdout


@requires_openssl
def test_node_cert_rejected_without_fleet_ca(tmp_path):
    out = _gen_tls(tmp_path)
    other = tmp_path / "other-ca"
    subprocess.run(
        ["bash", str(PROJECT_ROOT / "scripts" / "gen-nats-tls.sh"),
         "--out", str(other)],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT),
        check=True,
    )
    verify = subprocess.run(
        ["openssl", "verify", "-CAfile", str(other / "ca.pem"),
         str(out / "node-plant-edge-01-cert.pem")],
        capture_output=True, text=True,
    )
    assert verify.returncode != 0, "rogue CA must not validate node certs"


@requires_openssl
def test_node_env_carries_mtls_identity(tmp_path):
    out = _gen_tls(tmp_path)
    result = subprocess.run(
        ["bash", str(PROJECT_ROOT / "scripts" / "gen-nats-tls.sh"),
         "--out", str(out), "--node", "plant-edge-01"],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT),
    )
    assert result.returncode == 0, result.stderr
    env_text = (out / "node-plant-edge-01.env").read_text()
    assert "STARSHIP_NATS_TLS=1" in env_text
    assert f"STARSHIP_NATS_CERT={out}/node-plant-edge-01-cert.pem" in env_text
    assert f"STARSHIP_NATS_KEY={out}/node-plant-edge-01-key.pem" in env_text
    assert env_text.startswith("tls://") or "NATS_URL=tls://" in env_text


def test_gen_nats_tls_refuses_unknown_args(tmp_path):
    result = subprocess.run(
        ["bash", str(PROJECT_ROOT / "scripts" / "gen-nats-tls.sh"),
         "--out", str(tmp_path / "x"), "--bogus"],
        capture_output=True, text=True,
    )
    assert result.returncode != 0


# ─── firstboot defaults TLS on ──────────────────────────────────────

def test_firstboot_defaults_tls_on():
    text = (PROJECT_ROOT / "scripts" / "starship-firstboot.sh").read_text()
    # Default value is on; only an explicit opt-out disables it.
    assert 'STARSHIP_NATS_TLS:-1}' in text
    disabled_values = ("0|false|off|no",)
    assert any(v in text for v in disabled_values)


def _shell_fn(text: str, fn_name: str) -> str:
    """Extract a bash function body (from its first line to the closing brace).

    Stops at the first line that is exactly '}' at column 0 — good enough for
    helpers without heredocs; use exact-call assertions for heredoc-heavy fns.
    """
    lines = text.split(f"{fn_name}() {{", 1)[1].splitlines()
    body = []
    for line in lines:
        if line == "}":
            break
        body.append(line)
    return "\n".join(body)


def test_firstboot_wires_tls_into_both_bus_modes():
    text = (PROJECT_ROOT / "scripts" / "starship-firstboot.sh").read_text()
    assert "_setup_nats_tls" in text
    assert "_setup_nats_tls /etc/starship/nats/fleet-bus.active.conf" in text
    assert '_setup_nats_tls "$out/fleet-accounts.conf"' in text


def test_firstboot_appends_tls_block_to_active_conf():
    text = (PROJECT_ROOT / "scripts" / "starship-firstboot.sh").read_text()
    helper = _shell_fn(text, "_setup_nats_tls")
    assert "tls.conf.snippet" in helper
    assert "grep -q '^tls {'" in helper


# ─── client side: fail closed without CA ────────────────────────────

def test_tls_context_none_when_flag_unset():
    assert nats_connect.tls_context() is None


def test_tls_context_fails_closed_without_ca(monkeypatch):
    monkeypatch.setenv("STARSHIP_NATS_TLS", "1")
    with pytest.raises(RuntimeError, match="H-006"):
        nats_connect.tls_context()


def test_tls_context_fails_closed_when_ca_missing_on_disk(monkeypatch, tmp_path):
    monkeypatch.setenv("STARSHIP_NATS_TLS", "1")
    monkeypatch.setenv("STARSHIP_NATS_CA", str(tmp_path / "nope.pem"))
    with pytest.raises(RuntimeError, match="H-006"):
        nats_connect.tls_context()


def test_tls_context_insecure_escape_hatch(monkeypatch):
    monkeypatch.setenv("STARSHIP_NATS_TLS", "1")
    monkeypatch.setenv("STARSHIP_NATS_TLS_INSECURE", "1")
    import ssl
    ctx = nats_connect.tls_context()
    assert ctx.verify_mode == ssl.CERT_NONE


@requires_openssl
def test_tls_context_loads_ca_and_node_identity(monkeypatch, tmp_path):
    import ssl

    out = _gen_tls(tmp_path)
    subprocess.run(
        ["bash", str(PROJECT_ROOT / "scripts" / "gen-nats-tls.sh"),
         "--out", str(out), "--node", "plant-edge-01"],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT), check=True,
    )
    monkeypatch.setenv("STARSHIP_NATS_TLS", "1")
    monkeypatch.setenv("STARSHIP_NATS_CA", str(out / "ca.pem"))
    monkeypatch.setenv("STARSHIP_NATS_CERT", str(out / "node-plant-edge-01-cert.pem"))
    monkeypatch.setenv("STARSHIP_NATS_KEY", str(out / "node-plant-edge-01-key.pem"))
    ctx = nats_connect.tls_context()
    assert ctx is not None
    assert ctx.verify_mode == ssl.CERT_REQUIRED
    assert ctx.check_hostname is True


def test_build_nats_url_upgrades_scheme_when_tls_requested(monkeypatch):
    monkeypatch.setenv("NATS_URL", "nats://127.0.0.1:4222")
    monkeypatch.setenv("STARSHIP_NATS_TLS", "1")
    assert nats_connect.build_nats_url().startswith("tls://127.0.0.1:4222")


# ─── hub services pass the TLS context through ──────────────────────

def test_fleet_service_uses_connect_kwargs():
    text = (PROJECT_ROOT / "services" / "fleet.py").read_text()
    assert "connect_kwargs()" in text
    for call in (
        "nc = await nats_connect(_nats_url(), **connect_kwargs())",
        "nc = await nats_connect(url, **connect_kwargs())",
    ):
        assert call in text
    assert "nc = await nats_connect(url)" not in text
