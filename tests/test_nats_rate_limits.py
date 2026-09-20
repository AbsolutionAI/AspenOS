import os
import re
import shutil
import subprocess
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ASP-375 / F-011: NATS rate limiting + tighter connection limits.
# Every NATS server config must carry per-connection hardening and the
# fleet bus / accounts mode must carry auth-failure + per-account limits.
CONFIGS = [
    os.path.join(REPO_ROOT, "nats", "agent-bus.conf"),
    os.path.join(REPO_ROOT, "nats", "fleet-bus.conf"),
    os.path.join(REPO_ROOT, "nats", "fleet-accounts.conf.tmpl"),
]

# Keys that must be present with a value in every config.
HARDENED_KEYS = [
    "max_pending",
    "max_control_line",
    "max_subscriptions",
    "max_closed_clients",
    "max_traced_msg_len",
    "write_deadline",
    "ping_interval",
    "ping_max",
]

ACCOUNTS = ["SYS", "STARSHIP_OPS", "STARSHIP_EDGE", "STARSHIP_RANGE", "STARSHIP_TELEM"]


def _read(rel):
    with open(os.path.join(REPO_ROOT, rel)) as f:
        return f.read()


def _value(text, key):
    m = re.search(rf"^{re.escape(key)}:\s*(\S+)", text, re.MULTILINE)
    assert m, f"{key} not set"
    return m.group(1)


def test_every_config_carries_hardened_limits():
    for path in CONFIGS:
        text = open(path).read()
        for key in HARDENED_KEYS:
            m = re.search(rf"^{re.escape(key)}:\s*\S+", text, re.MULTILINE)
            assert m, f"{path}: missing {key}"
        payload = _value(text, "max_payload")
        pending = _value(text, "max_pending")
        assert _bytes(pending) >= _bytes(payload), (
            f"{path}: max_pending ({pending}) must be >= max_payload ({payload})"
        )


def _bytes(size):
    match = re.fullmatch(r"(\d+)(MB|KB)?", size)
    assert match, f"unparseable size {size!r}"
    value, unit = match.group(1), match.group(2)
    return int(value) * {"MB": 1024 * 1024, "KB": 1024}.get(unit, 1)


def test_fleet_bus_auth_timeout_is_hardened():
    text = _read("nats/fleet-bus.conf")
    m = re.search(r"timeout:\s*([\d.]+)", text)
    assert m, "fleet-bus.conf missing authorization timeout"
    assert float(m.group(1)) <= 2.0, "auth timeout must be <= 2.0s (was 5.0)"


def test_fleet_accounts_limits_per_account():
    text = _read("nats/fleet-accounts.conf.tmpl")
    for account in ACCOUNTS:
        block = re.search(rf"^\s*{account} \{{(.*?)^  \}}", text, re.MULTILINE | re.DOTALL)
        assert block, f"{account} block missing in fleet-accounts template"
        assert "limits {" in block.group(1), f"{account} missing limits block"
        assert re.search(r"max_connections:\s*\d+", block.group(1)), (
            f"{account} missing max_connections limit"
        )
        assert re.search(r"max_subscriptions:\s*\d+", block.group(1)), (
            f"{account} missing max_subscriptions limit"
        )


def _nats_server():
    return shutil.which("nats-server")


def test_configs_parse_with_nats_server():
    nats = _nats_server()
    if nats is None:
        return  # runtime parse check requires nats-server; static checks above still run
    for rel in ("nats/agent-bus.conf", "nats/fleet-bus.conf"):
        result = subprocess.run(
            [nats, "-c", os.path.join(REPO_ROOT, rel), "-t"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, f"{rel}: {result.stderr}"


def test_materialized_accounts_conf_parses_with_nats_server():
    nats = _nats_server()
    gen = os.path.join(REPO_ROOT, "scripts", "gen-nats-accounts.sh")
    if nats is None:
        return
    if shutil.which("bash") is None:
        return
    out = tempfile.mkdtemp(prefix="nats-rate-limits-")
    try:
        result = subprocess.run(
            ["bash", gen, "--out", out, "--port", "14222", "--no-nkeys"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, result.stderr
        conf = os.path.join(out, "fleet-accounts.conf")
        text = open(conf).read()
        for account in ACCOUNTS:
            assert re.search(rf"{account} \{{.*?limits \{{", text, re.DOTALL), (
                f"materialized {account} lost its limits block"
            )
        check = subprocess.run(
            [nats, "-c", conf, "-t"], capture_output=True, text=True,
        )
        assert check.returncode == 0, check.stderr
    finally:
        subprocess.run(["rm", "-rf", out], capture_output=True)