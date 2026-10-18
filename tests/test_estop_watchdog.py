"""
Independent hardware estop watchdog (H-023 / ASP-433).

A watchdog whose trip state lives outside agent-controlled memory/processes is
the fail-closed backstop when the software estop latch or gatekeeper is
compromised or dead.

Covered here:

- trip on missed heartbeat (and persistence of that latch)
- no trip while ticks arrive inside the deadline
- explicit ``force_trip``
- clear refused with fewer than two distinct authorizers (estop dual-clear)
- clear accepted only with two distinct authorizers, and re-arm semantics
- fail-closed on backend read/write errors, invalid config, never-ticked
- durable trip latch survives process re-instance (file-backed)
- observe mode reports but does not persist (optional sim profile)

All tests are hermetic: explicit ``now`` timestamps (no sleeping), in-process
or tmp-file backends, no hardware, no NATS.
"""

import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_PYTHON = os.path.join(REPO_ROOT, "src", "python")
sys.path.insert(0, SRC_PYTHON)

from safety.estop_watchdog import (  # noqa: E402
    EVT_CLEAR,
    EVT_MISS,
    EVT_TRIP,
    FilePulseBackend,
    SimBackend,
    WatchdogBackend,
    EstopWatchdog,
)

DEADLINE = 100


def make_watchdog(backend=None, mode="enforce", deadline_ms=DEADLINE):
    return EstopWatchdog(
        name="test-cell",
        deadline_ms=deadline_ms,
        backend=backend,
        mode=mode,
    )


def events(state):
    return [entry["event"] for entry in state["audit_log"]]


class RaisingBackend(WatchdogBackend):
    """Backend that fails on every read or write, per configuration."""

    def __init__(self, fail_read=False, fail_write=False):
        self.fail_read = fail_read
        self.fail_write = fail_write

    def read(self):
        if self.fail_read:
            raise OSError("boom")
        return {}

    def write(self, state):
        if self.fail_write:
            raise OSError("boom")


class TestHeartbeatLiveness:
    def test_trip_on_missed_heartbeat(self):
        wd = make_watchdog()
        wd.tick("edge-01", now=1000.0)
        status = wd.check(now=1000.0 + (DEADLINE / 1000.0) + 0.5)
        assert status["tripped"] is True
        assert status["trip_reason"] == "heartbeat_missed"
        assert EVT_MISS in events(status)
        assert EVT_TRIP in events(status)

    def test_no_trip_while_ticks_arrive(self):
        wd = make_watchdog()
        now = 1000.0
        for step in range(10):
            wd.tick("edge-01", now=now)
            assert wd.is_tripped(now=now) is False
            now += DEADLINE / 1000.0 / 2.0

    def test_missed_heartbeat_latches_until_clear(self):
        wd = make_watchdog()
        wd.tick("edge-01", now=0.0)
        assert wd.is_tripped(now=0.0 + (DEADLINE / 1000.0) / 2.0) is False
        assert wd.is_tripped(now=0.0 + (DEADLINE / 1000.0) + 0.1) is True
        # Resuming ticks must NOT self-clear: the trip needs humans.
        wd.tick("edge-01", now=5.0)
        assert wd.is_tripped(now=5.0) is True


class TestForceTrip:
    def test_force_trip(self):
        wd = make_watchdog()
        status = wd.force_trip("operator", now=1.0)
        assert status["tripped"] is True
        assert status["trip_reason"] == "operator"
        assert wd.is_tripped(now=1.0) is True
        assert EVT_TRIP in events(wd.state)


class TestClearDualAuthorize:
    def test_clear_refused_with_single_authorizer(self):
        wd = make_watchdog()
        wd.force_trip("operator", now=1.0)
        result = wd.clear(["alice"], now=1.5)
        assert result["accepted"] is False
        assert result["reason"] == "requires_two_distinct_authorizers"
        assert wd.is_tripped(now=1.5) is True

    def test_clear_refused_with_duplicate_authorizer(self):
        wd = make_watchdog()
        wd.force_trip("operator", now=1.0)
        result = wd.clear(["alice", "alice"], now=1.5)
        assert result["accepted"] is False
        assert result["reason"] == "requires_two_distinct_authorizers"
        assert wd.is_tripped(now=1.5) is True

    def test_clear_accepted_with_two_distinct_authorizers(self):
        wd = make_watchdog()
        wd.force_trip("operator", now=1.0)
        result = wd.clear(["alice", "bob"], now=1.5)
        assert result["accepted"] is True
        assert result["tripped"] is False
        assert set(result["state"]["cleared_by"]) == {"alice", "bob"}
        assert EVT_CLEAR in events(result["state"])

    def test_clear_is_not_a_free_pass(self):
        wd = make_watchdog()
        wd.force_trip("operator", now=1.0)
        assert wd.clear(["alice", "bob"], now=1.5)["accepted"] is True
        # Re-armed at clear time; without ticks it trips again at the deadline.
        inside = 1.5 + (DEADLINE / 1000.0) / 2.0
        assert wd.is_tripped(now=inside) is False
        overdue = 1.5 + (DEADLINE / 1000.0) + 0.1
        assert wd.is_tripped(now=overdue) is True
        assert wd.state["trip_reason"] == "heartbeat_missed"


class TestFailClosed:
    def test_fail_closed_on_backend_read_error(self):
        wd = make_watchdog(backend=RaisingBackend(fail_read=True))
        status = wd.check(now=1.0)
        assert status["tripped"] is True
        assert status["trip_reason"] == "backend_error"

    def test_fail_closed_on_backend_write_error(self):
        wd = make_watchdog(backend=RaisingBackend(fail_write=True))
        wd.tick("edge-01", now=1.0)
        status = wd.tick("edge-01", now=1.1)
        assert status["tripped"] is True
        assert status["trip_reason"] == "backend_error"

    def test_fail_closed_on_never_ticked(self):
        wd = make_watchdog()
        status = wd.check(now=0.0)
        assert status["tripped"] is True
        assert status["trip_reason"] == "never_ticked"
        # A heartbeat arms it; the transient report did not latch a trip.
        wd.tick("edge-01", now=0.0)
        assert wd.is_tripped(now=0.0) is False
        assert wd.state["tripped"] is False

    def test_fail_closed_on_invalid_config(self):
        with pytest.raises(ValueError):
            EstopWatchdog("cell", deadline_ms=0)

    def test_observe_mode_reports_without_persisting(self):
        wd = make_watchdog(mode="observe")
        wd.tick("edge-01", now=0.0)
        assert wd.is_tripped(now=0.0 + (DEADLINE / 1000.0) + 0.1) is True
        assert wd.state["tripped"] is False  # not persisted
        wd.tick("edge-01", now=1.0)
        assert wd.is_tripped(now=1.0) is False  # recovered without clear


class TestDurableLatch:
    def test_durable_trip_survives_restart(self, tmp_path):
        pulse = tmp_path / "pulse.json"
        first = EstopWatchdog(
            "cell-01", deadline_ms=DEADLINE, backend=FilePulseBackend(pulse)
        )
        first.force_trip("operator", now=1.0)

        restarted = EstopWatchdog(
            "cell-01", deadline_ms=DEADLINE, backend=FilePulseBackend(pulse)
        )
        assert restarted.is_tripped(now=2.0) is True
        assert restarted.state["trip_reason"] == "operator"

    def test_durable_clear_survives_restart(self, tmp_path):
        pulse = tmp_path / "pulse.json"
        first = EstopWatchdog(
            "cell-01", deadline_ms=DEADLINE, backend=FilePulseBackend(pulse)
        )
        first.force_trip("operator", now=1.0)
        assert first.clear(["alice", "bob"], now=1.5)["accepted"] is True

        restarted = EstopWatchdog(
            "cell-01", deadline_ms=DEADLINE, backend=FilePulseBackend(pulse)
        )
        # Clear re-armed the deadline at 1.5; checking inside it proves the
        # cleared latch survived restart without re-tripping.
        assert restarted.is_tripped(now=1.55) is False
        assert restarted.state["tripped"] is False

    def test_missed_heartbeat_latch_survives_restart(self, tmp_path):
        pulse = tmp_path / "pulse.json"
        first = EstopWatchdog(
            "cell-01", deadline_ms=DEADLINE, backend=FilePulseBackend(pulse)
        )
        first.tick("edge-01", now=0.0)
        assert first.is_tripped(now=0.0 + (DEADLINE / 1000.0) + 0.1) is True

        restarted = EstopWatchdog(
            "cell-01", deadline_ms=DEADLINE, backend=FilePulseBackend(pulse)
        )
        assert restarted.is_tripped(now=5.0) is True


class TestIndependence:
    def test_agent_death_trips_watchdog_via_check_alone(self):
        """Killing the agent side = ceasing ``tick``.

        Only the watchdog's own ``check`` (no gatekeeper/agent call) may be
        involved in detection. Here the watchdog object is ticked once like a
        fresh agent startup, then the agent is gone; detection is a pure
        ``check``.
        """
        wd = make_watchdog()
        last_tick = 1000.0
        wd.tick("edge-01", now=last_tick)
        # Agent is now dead — no gatekeeper, NATS, LLM, or other agent code
        # runs below; only the watchdog's independent deadline gate decides.
        assert wd.check(now=last_tick + (DEADLINE / 1000.0) + 0.5)["tripped"] is True

    def test_watchdog_is_stdlib_backend_driven(self):
        """No cloud/hardware deps: pure stdlib + pathlib state files."""
        import inspect

        source = inspect.getsource(FilePulseBackend)
        for banned in ("requests", "nats", "GPIO", "subprocess", "asyncio"):
            assert banned not in source