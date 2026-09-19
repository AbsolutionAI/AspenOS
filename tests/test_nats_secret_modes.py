import os
import shutil
import stat
import subprocess
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXER = os.path.join(REPO_ROOT, "scripts", "fix-nats-secret-modes.sh")
FIRSTBOOT = os.path.join(REPO_ROOT, "scripts", "starship-firstboot.sh")
POSTINST = os.path.join(REPO_ROOT, "debian", "DEBIAN", "postinst")
BUILD_DEB = os.path.join(REPO_ROOT, "scripts", "build-deb.sh")
INSTALL_AGENT = os.path.join(REPO_ROOT, "scripts", "install-agent-linux.sh")

# ASP-373 / F-009: NATS creds & secret paths must be 600 (dirs 700), never 644/640.
SECRET_PATHS_600 = [
    "etc/starship/nats.env",
    "etc/starship/nats-token",
    "etc/starship/nats/fleet-accounts.conf",
    "etc/starship/nats/fleet-bus.active.conf",
    "etc/starship/nats/server.conf",
]


def _build_fixture(base):
    """Create a fake /etc tree with secret files left at world/group-readable modes."""
    secret_files = list(SECRET_PATHS_600) + [
        "etc/starship/nats/creds/ops.env",
        "etc/starship/nats/creds/edge.nk",
        "etc/starship/nats/tls/X-client-key.pem",
    ]
    for rel in secret_files:
        path = os.path.join(base, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write("fixture")
        os.chmod(path, 0o644)
    os.chmod(os.path.join(base, "etc/starship/nats/creds"), 0o755)
    os.chmod(os.path.join(base, "etc/starship/nats/tls"), 0o755)


def test_fixer_locks_secret_paths_600():
    base = tempfile.mkdtemp(prefix="nats-secret-modes-")
    try:
        _build_fixture(base)
        result = subprocess.run(
            ["bash", FIXER, base],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
        for rel in SECRET_PATHS_600:
            mode = stat.S_IMODE(os.stat(os.path.join(base, rel)).st_mode)
            assert mode == 0o600, f"{rel} is {oct(mode)}, expected 600"
        creds_dir = os.path.join(base, "etc/starship/nats/creds")
        tls_dir = os.path.join(base, "etc/starship/nats/tls")
        assert stat.S_IMODE(os.stat(creds_dir).st_mode) == 0o700
        for d in (creds_dir, tls_dir):
            for name in os.listdir(d):
                mode = stat.S_IMODE(os.stat(os.path.join(d, name)).st_mode)
                assert mode == 0o600, f"{name} is {oct(mode)}, expected 600"
    finally:
        shutil.rmtree(base, ignore_errors=True)


def test_firstboot_writes_secret_paths_as_600():
    with open(FIRSTBOOT) as f:
        src = f.read()
    for path in ("/etc/starship/nats-token", "/etc/starship/nats.env"):
        assert f"chmod 600 {path}" in src, f"firstboot does not chmod 600 {path}"
    assert "chmod 640 /etc/starship/nats-token" not in src
    assert "chmod 640 /etc/starship/nats.env" not in src
    assert "chmod 644 /etc/starship/nats.env" not in src
    assert "fix-nats-secret-modes.sh" in src


def test_packaging_enforces_secret_modes():
    with open(POSTINST) as f:
        postinst = f.read()
    assert "fix-nats-secret-modes.sh" in postinst or "chmod 600" in postinst

    with open(BUILD_DEB) as f:
        build = f.read()
    assert "fix-nats-secret-modes.sh" in build
    assert "PKG_ROOT" in build
    assert 'mode != 600' in build

    with open(INSTALL_AGENT) as f:
        installer = f.read()
    assert "chmod 600 \"$CONFIG_DIR/staragent.yaml\"" in installer