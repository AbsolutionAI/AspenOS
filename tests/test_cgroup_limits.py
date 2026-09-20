"""ASP-376 / H-012: cgroups per-agent CPU/memory/PID limits.

Verifies every systemd agent unit carries a cgroup-limit drop-in with
the required resource-control properties.
"""
import os
import re

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYSTEMD_DIR = os.path.join(REPO_ROOT, "systemd")

# All agent units that should carry cgroup-limit drop-ins.
# Excludes agnetic-mesh.target (meta-target, no runtime).
AGENT_UNITS = [
    "agnetic-agent@.service",
    "agnetic-staragent.service",
    "agnetic-dashboard.service",
    "agnetic-status-bridge.service",
    "agnetic-message-history.service",
    "starship-fleet.service",
    "starship-health-checker.service",
    "agnetic-nats.service",
]

# Keys that each drop-in *must* set in the [Service] section.
REQUIRED_KEYS = {
    "CPUAccounting": r"yes|true",
    "MemoryAccounting": r"yes|true",
    "TasksAccounting": r"yes|true",
    "CPUQuota": r"\d+%",
    "MemoryMax": r"\d+[KMG]",
    "TasksMax": r"\d+",
}

# Units whose IOAccounting=cgroup-v1 fallback is acceptable (or not needed).
# NATS, message-history, fleet are I/O-intensive.
IO_INTENSIVE = {"agnetic-nats.service", "agnetic-message-history.service", "starship-fleet.service"}


def _dropin_path(unit):
    """Return the cgroup drop-in path for *unit*, or None."""
    d = os.path.join(SYSTEMD_DIR, f"{unit}.d")
    if not os.path.isdir(d):
        return None
    for fn in sorted(os.listdir(d)):
        if fn.endswith(".conf"):
            return os.path.join(d, fn)
    return None


def _read(rel):
    with open(os.path.join(REPO_ROOT, rel)) as f:
        return f.read()


def test_every_agent_unit_has_cgroup_dropin():
    for unit in AGENT_UNITS:
        path = _dropin_path(unit)
        assert path is not None, f"{unit}: missing .d/ directory or *.conf"
        assert os.path.isfile(path), f"{unit}: drop-in {path} not a file"
        text = open(path).read()
        assert text.strip(), f"{unit}: drop-in is empty"


def test_dropin_has_valid_service_section():
    for unit in AGENT_UNITS:
        path = _dropin_path(unit)
        if path is None:
            continue
        text = open(path).read()
        assert re.search(r"^\[Service\]", text, re.MULTILINE), (
            f"{unit}: drop-in missing [Service] section"
        )
        # Must not contain bare [Unit] or [Install] — drop-ins only extend [Service]
        assert not re.search(r"^\[(Unit|Install)\]", text, re.MULTILINE), (
            f"{unit}: drop-in has disallowed section"
        )


def test_dropin_has_all_required_keys():
    for unit in AGENT_UNITS:
        path = _dropin_path(unit)
        if path is None:
            continue
        text = open(path).read()
        for key, value_pattern in REQUIRED_KEYS.items():
            m = re.search(
                rf"^{re.escape(key)}=(?:{value_pattern})",
                text,
                re.MULTILINE,
            )
            assert m, f"{unit}: missing or malformed {key} (expected {key}=<{value_pattern}>)"


def test_io_intensive_units_have_io_accounting():
    for unit in AGENT_UNITS:
        path = _dropin_path(unit)
        if path is None:
            continue
        text = open(path).read()
        has_io = re.search(r"^IOAccounting=yes", text, re.MULTILINE)
        if unit in IO_INTENSIVE and not has_io:
            # Hard requirement for these units
            assert has_io, f"{unit}: I/O-intensive unit missing IOAccounting=yes"
        elif unit not in IO_INTENSIVE and has_io:
            # Non-I/O-intensive units MAY have it, no assertion needed
            pass


def test_memory_high_is_below_max():
    for unit in AGENT_UNITS:
        path = _dropin_path(unit)
        if path is None:
            continue
        text = open(path).read()
        m_max = re.search(r"^MemoryMax=(\S+)", text, re.MULTILINE)
        m_high = re.search(r"^MemoryHigh=(\S+)", text, re.MULTILINE)
        if m_max and m_high:
            # Simple numeric comparison (same unit assumed)
            max_val = _parse_size(m_max.group(1))
            high_val = _parse_size(m_high.group(1))
            assert high_val <= max_val, (
                f"{unit}: MemoryHigh ({m_high.group(1)}) > MemoryMax ({m_max.group(1)})"
            )


def _parse_size(size):
    match = re.fullmatch(r"(\d+)([KMG])", size)
    if not match:
        return 0
    scale = {"K": 1024, "M": 1024**2, "G": 1024**3}
    return int(match.group(1)) * scale[match.group(2)]


def test_starship_fleet_and_agent_have_same_limits():
    """Fleet and agent share the Python agent daemon pattern — identical caps."""
    fleet = open(_dropin_path("starship-fleet.service")).read()
    agent = open(_dropin_path("agnetic-agent@.service")).read()
    for key in ("CPUQuota", "CPUWeight", "MemoryMax", "MemoryHigh", "TasksMax"):
        v_fleet = re.search(rf"^{key}=(\S+)", fleet, re.MULTILINE)
        v_agent = re.search(rf"^{key}=(\S+)", agent, re.MULTILINE)
        assert v_fleet and v_agent, f"{key}: missing in one of fleet/agent drop-ins"
        assert v_fleet.group(1) == v_agent.group(1), (
            f"{key}: fleet={v_fleet.group(1)} != agent={v_agent.group(1)}"
        )
