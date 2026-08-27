"""H-001 (ASP-169): NATS defaults to multi-tenant accounts auth; no-auth
agent-bus mode removed and the bus fails closed without credentials."""

import os
import stat
import sys
from pathlib import Path

import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(PROJECT_ROOT / "agents"))

import nats_connect  # noqa: E402


# ─── no-auth config is gone ─────────────────────────────────────────

def test_agent_bus_conf_removed():
    assert not (PROJECT_ROOT / "nats" / "agent-bus.conf").exists()


@pytest.mark.parametrize(
    "relpath",
    [
        "scripts/starship-firstboot.sh",
        "scripts/start-agents.sh",
        "src/python/lib/scripts/start-agents.sh",
        "scripts/install-daemon.sh",
        "src/python/lib/scripts/install-daemon.sh",
        "scripts/build-deb.sh",
        "src/python/lib/scripts/build-deb.sh",
        "debian/DEBIAN/postinst",
        "Makefile",
    ],
)
def test_no_functional_agent_bus_references(relpath):
    text = (PROJECT_ROOT / relpath).read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.lstrip().startswith("#"):
            continue
        assert "agent-bus" not in line, f"{relpath}: {line.strip()}"


def test_firstboot_has_no_agent_bus_fallback():
    text = (PROJECT_ROOT / "scripts" / "starship-firstboot.sh").read_text()
    assert "_enable_agent_bus" not in text


def test_firstboot_accounts_is_default_path():
    text = (PROJECT_ROOT / "scripts" / "starship-firstboot.sh").read_text()
    # Selection: fleet token only when explicitly forced; otherwise accounts.
    assert 'STARSHIP_NATS_MODE:-}" == "fleet"' in text or '"${STARSHIP_NATS_MODE:-}" == "fleet"' in text
    else_branch = text.split("if [[ \"${STARSHIP_NATS_MODE:-}\"", 1)[1]
    else_branch = else_branch.split("else", 1)[1].split("fi", 1)[0]
    assert "_enable_accounts_bus" in else_branch
    assert "_enable_fleet_bus" not in else_branch


# ─── firstboot generates multi-tenant accounts with nkeys ───────────

def test_accounts_template_defines_all_tenants():
    tmpl = (PROJECT_ROOT / "nats" / "fleet-accounts.conf.tmpl").read_text()
    for account in ("SYS", "STARSHIP_OPS", "STARSHIP_EDGE", "STARSHIP_RANGE", "STARSHIP_TELEM"):
        assert account in tmpl, account
    assert "system_account: SYS" in tmpl
    # nkey sibling-user placeholders survive materialization
    for marker in ("__OPS_NKEY_LINE__", "__EDGE_NKEY_LINE__", "__TELEM_NKEY_LINE__"):
        assert marker in tmpl, marker


def test_profiles_default_to_accounts_mode():
    profiles = yaml.safe_load((PROJECT_ROOT / "config" / "profiles.yaml").read_text())["profiles"]
    for name, cfg in profiles.items():
        mode = cfg.get("nats_mode")
        assert mode == "accounts", f"profile {name}: nats_mode={mode}"


def test_gen_nats_accounts_materializes_conf_and_creds(tmp_path):
    import subprocess

    out = tmp_path / "nats"
    result = subprocess.run(
        ["bash", str(PROJECT_ROOT / "scripts" / "gen-nats-accounts.sh"),
         "--out", str(out), "--no-nkeys"],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT),
    )
    assert result.returncode == 0, result.stderr

    conf = out / "fleet-accounts.conf"
    assert conf.exists()
    assert stat.S_IMODE(conf.stat().st_mode) & 0o077 == 0, "conf must not be group/world readable"
    body = conf.read_text()
    for account in ("STARSHIP_OPS", "STARSHIP_EDGE", "STARSHIP_RANGE", "STARSHIP_TELEM"):
        assert account in body
    assert "__OPS_PASS__" not in body, "placeholder secrets must be replaced"

    ops_env = out / "creds" / "ops.env"
    assert ops_env.exists()
    env_values = {}
    for line in ops_env.read_text().splitlines():
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env_values[k] = v
    assert env_values["NATS_USER"] == "ops"
    assert len(env_values["NATS_PASSWORD"]) >= 16
    assert env_values["STARSHIP_NATS_MODE"] == "accounts"
    assert f"{env_values['NATS_USER']}:{env_values['NATS_PASSWORD']}@" in env_values["NATS_URL"]

    manifest = (out / "creds" / "manifest.json")
    assert manifest.exists()
    manifest_text = manifest.read_text().lower()
    for role_pass_key in ("password", "nats_password"):
        assert role_pass_key not in manifest_text, "manifest must not contain secrets"


# ─── clients fail closed without account credentials ────────────────

@pytest.fixture(autouse=True)
def clean_nats_env(monkeypatch):
    for var in (
        "NATS_URL", "NATS_USER", "NATS_PASSWORD",
        "STARSHIP_NATS_TOKEN", "STARSHIP_NATS_MODE",
        "STARSHIP_NATS_NKEY_SEED", "STARSHIP_NATS_NKEY_SEED_FILE",
        "STARSHIP_NATS_TLS",
    ):
        monkeypatch.delenv(var, raising=False)


def test_require_credentials_noop_when_mode_unset():
    nats_connect.require_account_credentials()


def test_require_credentials_raises_anonymous_in_accounts_mode(monkeypatch):
    monkeypatch.setenv("STARSHIP_NATS_MODE", "accounts")
    monkeypatch.setenv("NATS_URL", "nats://127.0.0.1:4222")
    with pytest.raises(RuntimeError, match="H-001"):
        nats_connect.require_account_credentials()


def test_require_credentials_raises_bare_token_in_accounts_mode(monkeypatch):
    monkeypatch.setenv("STARSHIP_NATS_MODE", "accounts")
    monkeypatch.setenv("NATS_URL", "nats://127.0.0.1:4222")
    monkeypatch.setenv("STARSHIP_NATS_TOKEN", "sometoken")
    with pytest.raises(RuntimeError, match="H-001"):
        nats_connect.require_account_credentials()


def test_require_credentials_ok_with_user_pass(monkeypatch):
    monkeypatch.setenv("STARSHIP_NATS_MODE", "accounts")
    monkeypatch.setenv("NATS_USER", "ops")
    monkeypatch.setenv("NATS_PASSWORD", "x" * 32)
    nats_connect.require_account_credentials()


def test_require_credentials_ok_with_url_embedded_creds(monkeypatch):
    monkeypatch.setenv("STARSHIP_NATS_MODE", "accounts")
    monkeypatch.setenv("NATS_URL", "nats://ops:secret@127.0.0.1:4222")
    nats_connect.require_account_credentials()


def test_require_credentials_ok_with_nkey_seed_file(monkeypatch, tmp_path):
    seed = tmp_path / "ops.nk"
    seed.write_text("SUACSSL3UAHUDXKFSNYUUIUTFXCXWUHFJ6UVKXBWSAK2DOYSD4UB52ZC7Q\n")
    monkeypatch.setenv("STARSHIP_NATS_MODE", "accounts")
    monkeypatch.setenv("NATS_URL", "nats://127.0.0.1:4222")
    monkeypatch.setenv("STARSHIP_NATS_NKEY_SEED_FILE", str(seed))
    nats_connect.require_account_credentials()


def test_build_nats_url_embeds_user_pass(monkeypatch):
    monkeypatch.setenv("NATS_URL", "nats://127.0.0.1:4222")
    monkeypatch.setenv("NATS_USER", "edge user")
    monkeypatch.setenv("NATS_PASSWORD", "p@ss word")
    url = nats_connect.build_nats_url()
    assert url.startswith("nats://edge%20user:p%40ss%20word@127.0.0.1:4222")


def test_safe_url_redacts_password():
    assert "***" in nats_connect.safe_url("nats://ops:hunter2@127.0.0.1:4222")
    assert "hunter2" not in nats_connect.safe_url("nats://ops:hunter2@127.0.0.1:4222")


# ─── packaging ships authenticated configs only ─────────────────────

def test_deb_packages_ship_accounts_template_not_agent_bus():
    build = (PROJECT_ROOT / "scripts" / "build-deb.sh").read_text()
    assert "fleet-accounts.conf.tmpl" in build
    assert 'cp "$REPO_DIR/nats/agent-bus.conf"' not in build


# ─── H-017: no live NATS secrets committed ──────────────────────────

# Lab values historically committed in nats/server.conf (F-016). Burned;
# must never reappear in tracked sources (see docs/SECURITY.md rotation).
_BURNED_NATS_LAB_SECRETS = (
    "agnetic_s3cr3t_t0k3n",
    "agnetic_admin_2026",
    "agnetic_user_2026",
)

_TRACKED_SCAN_GLOBS = (
    "nats/**",
    "scripts/**",
    "src/**",
    "docs/**",
    "config/**",
    "agents/**",
    "services/**",
    "dashboard/**",
    "systemd/**",
    "debian/**",
    "README.md",
    "SECURITY.md",
    "Makefile",
)


def _iter_tracked_text_files():
    import subprocess

    result = subprocess.run(
        ["git", "ls-files", "--", *_TRACKED_SCAN_GLOBS],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        check=True,
    )
    for rel in result.stdout.splitlines():
        path = PROJECT_ROOT / rel
        if not path.is_file():
            continue
        # Skip binary-ish
        if path.suffix in {".png", ".jpg", ".jpeg", ".gif", ".wasm", ".so", ".o"}:
            continue
        yield path


def test_server_conf_is_placeholder_only():
    conf = (PROJECT_ROOT / "nats" / "server.conf").read_text(encoding="utf-8")
    assert "DEPRECATED" in conf or "H-017" in conf
    assert "__STARSHIP_NATS_TOKEN__" in conf
    assert "__SYS_PASS__" in conf or "__OPS_PASS__" in conf
    for secret in _BURNED_NATS_LAB_SECRETS:
        assert secret not in conf, f"live secret still in nats/server.conf: {secret}"
    # Must not look like a ready-to-run production secret store
    assert 'token: "agnetic_' not in conf
    assert "password: \"agnetic_" not in conf


def test_repo_has_no_burned_nats_lab_secrets():
    offenders = []
    for path in _iter_tracked_text_files():
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for secret in _BURNED_NATS_LAB_SECRETS:
            if secret in text:
                # Allow the regression suite + smoke negative-grep only
                if path.name in {
                    "test_nats_accounts_default.py",
                    "smoke-test.sh",
                }:
                    continue
                offenders.append(f"{path.relative_to(PROJECT_ROOT)}:{secret}")
    assert not offenders, "burned lab NATS secrets still present:\n" + "\n".join(offenders)


def test_setup_nats_auth_uses_generator_not_hardcoded_passwords():
    for rel in (
        "scripts/setup-nats-auth.sh",
        "src/python/lib/scripts/setup-nats-auth.sh",
    ):
        text = (PROJECT_ROOT / rel).read_text(encoding="utf-8")
        assert "gen-nats-accounts.sh" in text, rel
        for secret in _BURNED_NATS_LAB_SECRETS:
            assert secret not in text, f"{rel} still references {secret}"
        assert "Credentials:" not in text or "do not commit" in text.lower()


def test_packaging_does_not_install_server_conf_as_active():
    for rel in (
        "scripts/install-daemon.sh",
        "scripts/build-deb.sh",
        "src/python/lib/scripts/install-daemon.sh",
        "src/python/lib/scripts/build-deb.sh",
    ):
        text = (PROJECT_ROOT / rel).read_text(encoding="utf-8")
        # Must not copy server.conf to a live path without .deprecated suffix
        for line in text.splitlines():
            if "server.conf" not in line or line.lstrip().startswith("#"):
                continue
            if "cp " in line and "server.conf" in line:
                assert "server.conf.deprecated" in line, f"{rel}: {line.strip()}"
