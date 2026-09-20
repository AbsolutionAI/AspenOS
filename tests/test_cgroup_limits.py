import os
import re

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ASP-376 / F-012: cgroup v2 resource limits shipped as systemd drop-ins.
# Plan values from docs/plans/ASP-376.md; bound checks guard against drift.
UNITS = {
    # unit file        : (CPUQuota, MemoryHigh, MemoryMax, TasksMax)
    "agnetic-agent@.service": ("150%", "768M", "1G", 128),
    "agnetic-message-history.service": ("100%", "384M", "512M", 64),
    "agnetic-nats.service": ("100%", "384M", "512M", 128),
    "agnetic-dashboard.service": ("100%", "384M", "512M", 128),
    "agnetic-staragent.service": ("50%", "192M", "256M", 64),
    "agnetic-status-bridge.service": ("50%", "192M", "256M", 64),
    "starship-fleet.service": ("100%", "384M", "512M", 128),
    "starship-health-checker.service": ("25%", "96M", "128M", 32),
}

ACCOUNTING = ["CPUAccounting=yes", "MemoryAccounting=yes", "TasksAccounting=yes"]


def _dropin(unit):
    return os.path.join(REPO_ROOT, "systemd", f"{unit}.d", "10-cgroup-limits.conf")


def _mb(size):
    match = re.fullmatch(r"(\d+)([MG])(B)?", size)
    assert match, f"unparseable size {size!r}"
    value, unit = match.group(1), match.group(2)
    return int(value) * {"M": 1024 * 1024, "G": 1024 * 1024 * 1024}[unit]


def test_every_unit_has_a_cgroup_limits_dropin():
    for unit, _ in UNITS.items():
        path = _dropin(unit)
        assert os.path.isfile(path), f"missing drop-in {path}"
        text = open(path).read()
        assert "[Service]" in text, f"{unit} drop-in missing [Service] section"


def test_dropin_keys_and_bounds():
    for unit, (quota, high, max_, tasks) in UNITS.items():
        lines = open(_dropin(unit)).read().splitlines()
        for key in ACCOUNTING + [
            f"CPUQuota={quota}",
            f"MemoryHigh={high}",
            f"MemoryMax={max_}",
            f"TasksMax={tasks}",
        ]:
            assert key in lines, f"{unit} drop-in missing {key}"
        allowed_quotas = {"25%", "50%", "100%", "150%"}
        assert quota in allowed_quotas, f"{unit}: unexpected CPUQuota {quota}"
        assert tasks >= 32, f"{unit}: TasksMax must be >= 32"
        assert _mb(high) < _mb(max_), f"{unit}: MemoryHigh must be < MemoryMax"


def test_build_deb_stages_dropin_dirs():
    text = open(os.path.join(REPO_ROOT, "scripts", "build-deb.sh")).read()
    assert "systemd/*.service.d" in text, "build-deb must stage *.service.d dirs"
    assert "lib/systemd/system/" in text
    assert "10-cgroup-limits.conf" in text
    assert "agnetic-agent@.service.d/10-cgroup-limits.conf" in text


def test_install_systemd_installs_dropins():
    text = open(os.path.join(REPO_ROOT, "scripts", "install-systemd.sh")).read()
    assert ".service.d" in text, "install-systemd must install drop-in dirs"
    assert "${svc}.service.d" in text, "drop-in dir must key off unit name"
    assert "systemctl daemon-reload" in text


def test_ops_doc_documents_knobs():
    text = open(os.path.join(REPO_ROOT, "docs", "ops", "CGROUPS_RESOURCE_LIMITS.md")).read()
    for knob in ("MemoryMax=", "MemoryHigh=", "CPUQuota=", "TasksMax="):
        assert knob in text, f"ops doc missing knob {knob}"
    assert "bt-asp-srv" not in text, "ops doc must not instruct live application on bt-asp-srv"