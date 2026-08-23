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
