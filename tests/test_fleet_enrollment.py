"""H-002 (ASP-170): fleet node enrollment with signed identity tokens.

Protocol (scripts/fleet-enroll.sh):
  issue-token -> request -> sign -> install
Tokens are RSA-SHA256 signed by the fleet CA key, bound to one node name +
expiry. Revocation is enforced at signing, in nats_connect (self), and by
the fleet daemon (peers).
"""

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
        "STARSHIP_NATS_REVOCATIONS",
    ):
        monkeypatch.delenv(var, raising=False)


def _run(*args, env_out=None):
    return subprocess.run(
        ["bash", str(PROJECT_ROOT / "scripts" / "fleet-enroll.sh"), *args],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
        env={"PATH": "/usr/bin:/bin:/usr/local/bin", "HOME": str(env_out or "/tmp")},
    )


def _gen_ca(tmp_path):
    out = tmp_path / "tls"
    result = subprocess.run(
        ["bash", str(PROJECT_ROOT / "scripts" / "gen-nats-tls.sh"),
         "--out", str(out), "--host", "nattest.local"],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT),
    )
    assert result.returncode == 0, result.stderr
    return out


def _issue_token(out, node, days="7"):
    result = _run("issue-token", "--node", node, "--days", days, "--out", str(out))
    assert result.returncode == 0, result.stderr
    return result.stdout.strip().splitlines()[-1]


def _enroll(tmp_path, out, node):
    """Happy-path enroll helper: returns (request_dir, cert_path)."""
    token = _issue_token(out, node)
    req = tmp_path / f"req-{node}"
    result = _run("request", "--node", node, "--token", token,
                  "--dir", str(req), "--out", str(out))
    assert result.returncode == 0, result.stderr
    result = _run("sign", "--request", str(req), "--out", str(out))
    assert result.returncode == 0, result.stderr
    cert = out / f"node-{node}-cert.pem"
    assert cert.exists()
    return req, cert


# ── end-to-end enrollment ────────────────────────────────────────────

@requires_openssl
def test_full_enrollment_produces_valid_fleet_identity(tmp_path):
    out = _gen_ca(tmp_path)
    _, cert = _enroll(tmp_path, out, "cell-7")
    verify = subprocess.run(
        ["openssl", "verify", "-CAfile", str(out / "ca.pem"), str(cert)],
        capture_output=True, text=True,
    )
    assert verify.returncode == 0, verify.stderr
    subject = subprocess.run(
        ["openssl", "x509", "-in", str(cert), "-noout", "-subject",
         "-nameopt", "RFC2253"],
        capture_output=True, text=True,
    )
    assert "CN=cell-7" in subject.stdout


@requires_openssl
def test_node_private_key_never_leaves_request_dir(tmp_path):
    out = _gen_ca(tmp_path)
    req, _ = _enroll(tmp_path, out, "cell-7")
    assert (req / "node-cell-7-key.pem").exists()
    assert not (out / "node-cell-7-key.pem").exists()


@requires_openssl
def test_sign_consumes_token_and_csr(tmp_path):
    out = _gen_ca(tmp_path)
    req, _ = _enroll(tmp_path, out, "cell-7")
    assert not (req / "enrollment-token").exists()
    assert not list(req.glob("*.csr"))


@requires_openssl
def test_signed_env_binds_starship_node_id(tmp_path):
    out = _gen_ca(tmp_path)
    _enroll(tmp_path, out, "cell-7")
    env_text = (out / "node-cell-7.env").read_text()
    assert "STARSHIP_NODE_ID=cell-7" in env_text
    assert f"STARSHIP_NATS_CERT={out}/node-cell-7-cert.pem" in env_text


# ── rogue nodes cannot join without a valid signed token ─────────────

@requires_openssl
def test_tampered_token_rejected(tmp_path):
    out = _gen_ca(tmp_path)
    token = _issue_token(out, "cell-8")
    payload, sig = token.rsplit(".", 1)
    tampered = payload[:-1] + ("9" if payload[-1] != "9" else "7") + "." + sig
    result = _run("request", "--node", "cell-8", "--token", tampered,
                  "--dir", str(tmp_path / "r"), "--out", str(out))
    assert result.returncode != 0
    assert "signature invalid" in result.stderr


@requires_openssl
def test_token_bound_to_requested_node(tmp_path):
    out = _gen_ca(tmp_path)
    token = _issue_token(out, "cell-8")
    result = _run("request", "--node", "cell-99", "--token", token,
                  "--dir", str(tmp_path / "r"), "--out", str(out))
    assert result.returncode != 0
    assert "not 'cell-99'" in result.stderr


@requires_openssl
def test_expired_token_rejected(tmp_path):
    out = _gen_ca(tmp_path)
    token = _issue_token(out, "cell-8", days="-1")
    result = _run("request", "--node", "cell-8", "--token", token,
                  "--dir", str(tmp_path / "r"), "--out", str(out))
    assert result.returncode != 0
    assert "expired" in result.stderr


@requires_openssl
def test_garbage_and_missing_tokens_rejected(tmp_path):
    out = _gen_ca(tmp_path)
    for bad in ("garbage", "ENROLL-v1:x:y.deadbeef", ""):
        result = _run("request", "--node", "cell-x", "--token", bad,
                      "--dir", str(tmp_path / "r"), "--out", str(out))
        assert result.returncode != 0, repr(bad)


# ── revocation ───────────────────────────────────────────────────────

@requires_openssl
def test_revoked_node_cannot_be_signed_or_issued(tmp_path):
    out = _gen_ca(tmp_path)
    _enroll(tmp_path, out, "cell-7")
    result = _run("revoke", "--node", "cell-7", "--reason", "stolen", "--out", str(out))
    assert result.returncode == 0, result.stderr
    result = _run("issue-token", "--node", "cell-7", "--out", str(out))
    assert result.returncode != 0, "revoked node must not get new tokens"


@requires_openssl
def test_revocation_blocks_pre_token_request_at_sign_time(tmp_path):
    out = _gen_ca(tmp_path)
    token = _issue_token(out, "cell-9")
    req = tmp_path / "req-9"
    assert _run("request", "--node", "cell-9", "--token", token,
                "--dir", str(req), "--out", str(out)).returncode == 0
    # revoke after the request was created but before it was signed
    _run("revoke", "--node", "cell-9", "--out", str(out))
    result = _run("sign", "--request", str(req), "--out", str(out))
    assert result.returncode != 0
    assert "revocation list" in result.stderr


@requires_openssl
def test_revoke_list_roundtrip(tmp_path):
    out = _gen_ca(tmp_path)
    assert _run("revoke", "--list", "--out", str(out)).returncode == 0
    _run("revoke", "--node", "bad-node", "--reason", "test", "--out", str(out))
    listing = _run("revoke", "--list", "--out", str(out))
    assert "bad-node" in listing.stdout


# ── client-side fail closed on revoked self identity ─────────────────

@requires_openssl
def test_nats_connect_detects_local_identity_cn(monkeypatch, tmp_path):
    out = _gen_ca(tmp_path)
    _, cert = _enroll(tmp_path, out, "cell-7")
    monkeypatch.setenv("STARSHIP_NATS_CERT", str(cert))
    assert nats_connect.local_identity_cn() == "cell-7"


@requires_openssl
def test_check_local_identity_fails_closed_when_revoked(monkeypatch, tmp_path):
    out = _gen_ca(tmp_path)
    _, cert = _enroll(tmp_path, out, "cell-7")
    monkeypatch.setenv("STARSHIP_NATS_CA", str(out / "ca.pem"))
    monkeypatch.setenv("STARSHIP_NATS_CERT", str(cert))
    assert nats_connect.check_local_identity() is None
    _run("revoke", "--node", "cell-7", "--out", str(out))
    with pytest.raises(RuntimeError, match="H-002"):
        nats_connect.check_local_identity()


def test_is_revoked_reads_override_list(monkeypatch, tmp_path):
    rev = tmp_path / "revocations.list"
    rev.write_text("# revoked earlier\nold-node\n\nnew-node extra-field\n")
    monkeypatch.setenv("STARSHIP_NATS_REVOCATIONS", str(rev))
    assert nats_connect.is_revoked("old-node")
    assert nats_connect.is_revoked("new-node")
    assert not nats_connect.is_revoked("fine-node")
    assert not nats_connect.is_revoked(None)


def test_is_revoked_false_without_list(monkeypatch):
    monkeypatch.delenv("STARSHIP_NATS_REVOCATIONS", raising=False)
    monkeypatch.setenv("STARSHIP_NATS_CA", "/nonexistent/ca.pem")
    assert nats_connect.is_revoked("any-node") is False


def test_revocations_default_next_to_ca(monkeypatch):
    monkeypatch.delenv("STARSHIP_NATS_REVOCATIONS", raising=False)
    monkeypatch.setenv("STARSHIP_NATS_CA", "/etc/starship/nats/tls/ca.pem")
    assert nats_connect.revocations_path() == "/etc/starship/nats/tls/revocations.list"


# ── fleet daemon drops revoked peers ─────────────────────────────────

sys.path.insert(0, str(PROJECT_ROOT / "services"))


def test_fleet_service_enforces_revocation():
    import fleet  # noqa: E402

    assert fleet.identity_revoked(None) is False
    text = (PROJECT_ROOT / "services" / "fleet.py").read_text()
    assert "identity_revoked(nid)" in text
    assert "rejected register from revoked node" in text
    assert "rejected heartbeat from revoked node" in text


# ── fail closed without CA material ──────────────────────────────────

def test_all_commands_fail_closed_without_ca(tmp_path):
    missing = tmp_path / "empty"
    r1 = _run("issue-token", "--node", "cell-1", "--out", str(missing))
    assert r1.returncode != 0
    assert "fleet CA missing" in r1.stderr
    r2 = _run("sign", "--request", str(missing), "--out", str(missing))
    assert r2.returncode != 0
