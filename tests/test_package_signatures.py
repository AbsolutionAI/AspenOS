"""F-014 / ASP-378: signed package + update integrity checks.

Hermetic tests for scripts/verify-deb-signature.sh and scripts/sign-deb.sh:
an unsigned / tampered / unknown-key artifact must be rejected; an artifact
signed by a trusted key must verify. Throwaway GPG keys are generated at run
time in a temp GNUPGHOME — no private key material is committed.
"""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
VERIFY = ROOT / "scripts" / "verify-deb-signature.sh"
DEFAULT_KEYRING = ROOT / "security" / "packages" / "starship-release.gpg"

pytestmark = pytest.mark.skipif(
    not shutil.which("gpg") or not shutil.which("gpgv"),
    reason="gnupg2 (gpg/gpgv) required for signature fixture tests",
)


def _run(args, cwd=None, check=False):
    r = subprocess.run(args, capture_output=True, text=True, cwd=cwd, check=False)
    if check:
        assert r.returncode == 0, r.stderr
    return r


def _make_gpghome(tmp_path, name="Starship OS Test <test@starship.os>", subdir="gnupghome"):
    home = tmp_path / subdir
    home.mkdir(mode=0o700)
    r = _run(
        [
            "gpg", "--homedir", str(home), "--batch", "--no-tty",
            "--pinentry-mode", "loopback", "--passphrase", "",
            "--quick-generate-key", name, "ed25519", "sign", "0",
        ]
    )
    assert r.returncode == 0, r.stderr
    r = _run(["gpg", "--homedir", str(home), "--list-keys", "--with-colons"])
    keyid = None
    for line in r.stdout.splitlines():
        if line.startswith("pub:"):
            keyid = line.split(":")[4]
            break
    assert keyid, "no public key generated"
    return str(home), keyid


def _export_keyring(tmp_path, gh, keyid):
    out = tmp_path / "trusted.gpg"
    r = subprocess.run(
        ["gpg", "--homedir", gh, "--batch", "--yes",
         "--export-options", "export-minimal", "--export", keyid],
        capture_output=True, check=False,
    )
    assert r.returncode == 0, r.stderr
    out.write_bytes(r.stdout)
    return str(out)


def _sign(tmp_path, gh, keyid, artifact):
    sig = Path(str(artifact) + ".asc")
    r = _run(
        ["gpg", "--homedir", gh, "--batch", "--no-tty", "--pinentry-mode",
         "loopback", "--passphrase", "", "--armor", "--detach-sign",
         "--local-user", keyid, "--output", str(sig), str(artifact)]
    )
    assert r.returncode == 0, r.stderr
    return sig


def _make_artifact(tmp_path):
    """A minimal but real .deb fixture when dpkg-deb works; bytes otherwise.

    The signature covers the artifact bytes, so either fixture exercises the
    same integrity contract. LD_LIBRARY_PATH is stripped (an agent env leaks an
    older liblzma that breaks dpkg-deb — same workaround as scripts/build-deb.sh).
    """
    if shutil.which("dpkg-deb"):
        tree = tmp_path / "tree"
        (tree / "DEBIAN").mkdir(parents=True)
        (tree / "DEBIAN" / "control").write_text(
            "Package: starship-os-fixture\nVersion: 9.9.9\n"
            "Architecture: all\nMaintainer: Test <test@starship.os>\n"
            "Description: signature fixture\n"
        )
        usr = tree / "usr"
        usr.mkdir()
        (usr / "dummy.txt").write_text("fixture data\n")
        deb = tmp_path / "fixture.deb"
        env = dict(os.environ)
        env.pop("LD_LIBRARY_PATH", None)
        r = subprocess.run(
            ["dpkg-deb", "--build", str(tree), str(deb)],
            capture_output=True, text=True, env=env, check=False,
        )
        if r.returncode == 0:
            return deb
    artifact = tmp_path / "fixture.bin"
    artifact.write_bytes(b"starship-os fake artifact bytes for signature testing\n" * 4)
    return artifact


@pytest.fixture
def fixture_env(tmp_path):
    gh, keyid = _make_gpghome(tmp_path)
    keyring = _export_keyring(tmp_path, gh, keyid)
    artifact = _make_artifact(tmp_path)
    return {"gh": gh, "keyid": keyid, "keyring": keyring, "artifact": artifact}


def test_unsigned_artifact_rejected(fixture_env):
    """F-014: an artifact with no .asc must not install (verify must FAIL)."""
    e = fixture_env
    r = _run(["bash", str(VERIFY), "--keyring", e["keyring"], str(e["artifact"])])
    assert r.returncode != 0, r.stdout
    assert "UNSIGNED" in r.stderr


def test_valid_signature_accepted(fixture_env, tmp_path):
    """F-014: an artifact signed by a trusted key verifies (exit 0)."""
    e = fixture_env
    _sign(tmp_path, e["gh"], e["keyid"], e["artifact"])
    r = _run(["bash", str(VERIFY), "--keyring", e["keyring"], str(e["artifact"])])
    assert r.returncode == 0, r.stdout + r.stderr
    assert "OK" in r.stdout


def test_tampered_artifact_rejected(fixture_env, tmp_path):
    """F-014: flipping a byte after signing must fail verification."""
    e = fixture_env
    _sign(tmp_path, e["gh"], e["keyid"], e["artifact"])
    data = bytearray(e["artifact"].read_bytes())
    data[len(data) // 2] ^= 0xFF
    e["artifact"].write_bytes(bytes(data))
    r = _run(["bash", str(VERIFY), "--keyring", e["keyring"], str(e["artifact"])])
    assert r.returncode != 0, r.stdout
    assert "FAIL" in r.stderr


def test_unknown_key_rejected(fixture_env, tmp_path):
    """F-014: signature by a key NOT in the pinned keyring must fail."""
    e = fixture_env
    _sign(tmp_path, e["gh"], e["keyid"], e["artifact"])  # sign with trusted key
    other_home, other_keyid = _make_gpghome(
        tmp_path, name="Attacker <evil@example.org>", subdir="gnupghome-other")
    other_keyring = _export_keyring(tmp_path, other_home, other_keyid)
    r = _run(["bash", str(VERIFY), "--keyring", other_keyring, str(e["artifact"])])
    assert r.returncode != 0, r.stdout
    assert "FAIL" in r.stderr


def test_missing_signature_is_environment_error(fixture_env):
    """F-014: absent signature maps to exit 3 (env/missing) before any install."""
    e = fixture_env
    r = _run(["bash", str(VERIFY), "--keyring", e["keyring"], str(e["artifact"])])
    assert r.returncode == 3, r.stdout + r.stderr


def test_committed_trust_anchor_is_a_valid_public_keyring():
    """F-014: the default trust anchor is a real, importable public keyring."""
    r = _run(["gpg", "--list-packets", str(DEFAULT_KEYRING)])
    assert r.returncode == 0, r.stderr
    assert "public key packet" in r.stdout
    assert DEFAULT_KEYRING.stat().st_size > 100


def test_update_sh_supports_verify_signature():
    """F-014: the update chain exposes the opt-in signature gate."""
    text = (ROOT / "scripts" / "update.sh").read_text()
    assert "--verify-signature" in text
    assert "verify-deb-signature.sh" in text


def test_ci_runs_signature_gate():
    """F-014: CI must run the package-signature pytest suite."""
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text()
    assert "verify-package-signature" in ci
    assert "test_package_signatures.py" in ci


def test_nightly_gates_package_signatures():
    """F-014: nightly asserts the tooling + fixture tests exist."""
    nightly = (ROOT / "scripts" / "check-nightly.sh").read_text()
    assert "Section 21: Package signature gate (ASP-378/F-014)" in nightly
    assert "verify-deb-signature.sh" in nightly or "sign-deb.sh" in nightly
    assert "test_package_signatures.py" in nightly