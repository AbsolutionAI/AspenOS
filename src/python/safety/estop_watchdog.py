"""Independent hardware estop watchdog (H-023 / ASP-433).

The software estop latch and the gatekeeper dual-human path live inside
agent-controlled processes. If the agent runtime or gatekeeper is compromised
or dead, the cell must still have a *fail-closed* path to the safe state that
does not trust agent software. This module is that watchdog contract:

- ``tick(source[, now])`` — the only software-path heartbeat. A heartbeat sets
  the durable ``last_tick_at`` in the backend; it NEVER clears a trip. A trip
  can only be removed via ``clear(authorizers)`` with **two distinct**
  authorizers (mirrors the existing estop dual-clear; never single-clear).
- ``check([now])`` — evaluates trip state on demand. Tripped when:
    * an explicit ``force_trip`` latched the backend, OR
    * the watchdog never received a heartbeat (``never_ticked``), OR
    * the last heartbeat is older than ``deadline_ms`` (``heartbeat_missed``),
    * a backend read/write failed (``backend_error``), OR
    * the deadline config is invalid (``invalid_config``).
- Backends isolate the durable latch from the agent process whenever the
  backend storage lives outside agent code:

    * ``SimBackend`` — in-process dict, the default for tests/CI.
    * ``FilePulseBackend`` — JSON file written atomically; the reference
      durable backend. A file on a write-protected/independent mount is the
      documented future ``GpioPulseBackend`` stand-in (no live GPIO this
      ticket; live hardware wire requires Aspen START per ASP-433 plan).

Independence invariant: ceasing ``tick`` (the simulated "agent killed") trips
the watchdog through ``check()`` alone — no gatekeeper, LLM, or agent call is
involved. ``emit`` callbacks (audit events ``safety.watchdog.*``) default to
the logger and never gate the watchdog decision.

Fail-closed paddles every way the software path can try to unbind the
watchdog: invalid config, unknown clock, backend read/write errors, and any
state that does not prove a recent independent heartbeat.
"""

import json
import logging
import os
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Callable, Dict, List, Optional

logger = logging.getLogger("safety.watchdog")

#: Canonical persisted state. All timestamps are seconds (monotonic when
#: injected, wall otherwise); audit events are the durable event trail.
DEFAULT_STATE: Dict[str, object] = {
    "tripped": False,
    "trip_reason": None,
    "trip_at": None,
    "last_tick_at": None,
    "last_tick_source": None,
    "cleared_at": None,
    "cleared_by": [],
    "audit_log": [],
}

AUDIT_MAX_EVENTS = 200

EVT_TRIP = "safety.watchdog.trip"
EVT_CLEAR = "safety.watchdog.clear"
EVT_MISS = "safety.watchdog.tick_miss"


class WatchdogBackend(ABC):
    """Persistent side of the watchdog.

    The backend is the only place trip state is stored, so choosing a backend
    whose storage is outside the agent process (e.g. ``FilePulseBackend`` on an
    independent mount, later GPIO-backed logic) is what makes the watchdog
    *independent* of agent software. Implementations must be thread-safe enough
    for the gatekeeper loop (single writer today).
    """

    @abstractmethod
    def read(self) -> Dict[str, object]:
        """Return the persisted state dict (may be empty on first use)."""

    @abstractmethod
    def write(self, state: Dict[str, object]) -> None:
        """Persist the state dict atomically enough to survive process death."""


class SimBackend(WatchdogBackend):
    """In-process backend for unit tests / CI. Does NOT survive restarts."""

    def __init__(self) -> None:
        self._data: Dict[str, object] = {}

    def read(self) -> Dict[str, object]:
        return dict(self._data)

    def write(self, state: Dict[str, object]) -> None:
        self._data = dict(state)


class FilePulseBackend(WatchdogBackend):
    """Durable JSON-file backend with atomic replace (survives restarts)."""

    def __init__(self, path: Path) -> None:
        self._path = Path(path)

    def read(self) -> Dict[str, object]:
        try:
            loaded = json.loads(self._path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {}
        if not isinstance(loaded, dict):
            raise OSError(f"corrupt watchdog state (not a dict): {self._path}")
        return loaded

    def write(self, state: Dict[str, object]) -> None:
        data = json.dumps(state, indent=2, sort_keys=True)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_name(self._path.name + ".tmp")
        tmp.write_text(data, encoding="utf-8")
        os.replace(tmp, self._path)


class EstopWatchdog:
    """Fail-closed estop watchdog independent of agent software.

    Args:
        name: Watchdog identity (e.g. ``aspen-edge-cell-01``).
        deadline_ms: Heartbeat deadline in milliseconds. Default 500ms (cell
            class). A value <= 0 is treated as invalid config and trips.
        backend: ``WatchdogBackend``; defaults to ``SimBackend``.
        now_fn: Callable returning current seconds; injectable for hermetic
            tests (defaults to ``time.monotonic``).
        mode: ``"enforce"`` (default) persists trip latches; ``"observe"``
            computes but does not persist trips (optional sim-profile mode,
            only when explicitly configured — plant-range stays enforce).
        emit: Optional ``Callable[[str, str], None]`` audit hook receiving
            ``(event, detail)``. Never gates the watchdog decision.
    """

    def __init__(
        self,
        name: str,
        deadline_ms: int = 500,
        backend: Optional[WatchdogBackend] = None,
        now_fn: Callable[[], float] = time.monotonic,
        mode: str = "enforce",
        emit: Optional[Callable[[str, str], None]] = None,
    ) -> None:
        if mode not in ("enforce", "observe"):
            raise ValueError(f"mode must be 'enforce' or 'observe', got {mode!r}")
        if deadline_ms is not None and int(deadline_ms) <= 0:
            raise ValueError("deadline_ms must be strictly positive")
        self.name = name
        self.deadline_ms = int(deadline_ms)
        self._deadline_s = self.deadline_ms / 1000.0
        self._backend = backend if backend is not None else SimBackend()
        self._now_fn = now_fn
        self.mode = mode
        self._emit = emit

    # -- public API ---------------------------------------------------------

    def tick(self, source: str, now: Optional[float] = None) -> Dict[str, object]:
        """Record the software-path heartbeat from ``source``.

        Never clears a trip — a trip stays latched until ``clear`` with two
        distinct authorizers. Persistence failures fail closed (trip).
        """
        ts = self._now_fn() if now is None else float(now)
        try:
            state = self._load()
        except Exception as exc:  # pragma: no cover - defensive fail-closed
            return self._fail_closed("backend_error", ts, detail=f"read failed: {exc}")
        state["last_tick_at"] = ts
        state["last_tick_source"] = source
        try:
            self._save(state)
        except Exception as exc:
            return self._fail_closed("backend_error", ts, detail=f"write failed: {exc}")
        return state

    def check(self, now: Optional[float] = None) -> Dict[str, object]:
        """Evaluate and return the current trip state (may latch a trip)."""
        ts = self._now_fn() if now is None else float(now)
        try:
            state = self._load()
        except Exception:
            return self._fail_closed("backend_error", ts)
        if state["tripped"]:
            return state
        if self.deadline_ms <= 0:
            return self._trip(state, "invalid_config", ts)
        last = state["last_tick_at"]
        if last is None:
            # Unarmed (no heartbeat ever): report the safe state but do NOT
            # latch a persistent trip — the first tick arms the watchdog and
            # a stale ``never_ticked`` latch would demand an operator clear
            # on every first boot.
            return self._report_trip(state, "never_ticked", ts)
        if (ts - float(last)) > self._deadline_s:
            return self._trip(state, "heartbeat_missed", ts, miss=True)
        return state

    def is_tripped(self, now: Optional[float] = None) -> bool:
        """Convenience wrapper over ``check``."""
        return bool(self.check(now=now)["tripped"])

    @property
    def state(self) -> Dict[str, object]:
        """Read-only snapshot of the current backend state."""
        return dict(self._load_safe())

    def force_trip(
        self, reason: str = "manual", now: Optional[float] = None
    ) -> Dict[str, object]:
        """Explicitly latch the trip (operator, hardware, or supervisor)."""
        ts = self._now_fn() if now is None else float(now)
        try:
            state = self._load()
        except Exception as exc:
            return self._fail_closed("backend_error", ts, detail=f"read failed: {exc}")
        return self._trip(state, reason, ts)

    def clear(
        self, authorizers: List[str], now: Optional[float] = None
    ) -> Dict[str, object]:
        """Dual-authorize clear: requires two *distinct* authorizers.

        Mirrors ``aspen.safety.estop`` dual-clear — a single principal can
        never un-latch. On acceptance the watchdog re-arms ``last_tick_at`` so
        the software path has a fresh deadline to prove liveness before the
        next check.
        """
        ts = self._now_fn() if now is None else float(now)
        distinct = {a for a in (authorizers or []) if a is not None and a != ""}
        if len(distinct) < 2:
            return {
                "accepted": False,
                "reason": "requires_two_distinct_authorizers",
                "tripped": True,
                "state": dict(self._load_safe()),
            }
        if self.mode == "observe":
            return {"accepted": False, "reason": "observe_only", "tripped": True,
                    "state": dict(self._load_safe())}
        try:
            state = self._load()
        except Exception as exc:
            return self._fail_closed("backend_error", ts, detail=f"read failed: {exc}")
        state["tripped"] = False
        state["trip_reason"] = None
        state["trip_at"] = None
        state["cleared_at"] = ts
        state["cleared_by"] = sorted(distinct)
        state["last_tick_at"] = ts
        self._audit(state, EVT_CLEAR, f"cleared by {sorted(distinct)}")
        try:
            self._save(state)
        except Exception as exc:
            return self._fail_closed("backend_error", ts, detail=f"write failed: {exc}")
        return {"accepted": True, "reason": None, "tripped": False, "state": state}

    # -- internals ----------------------------------------------------------

    def _load(self) -> Dict[str, object]:
        raw = self._backend.read()
        merged = dict(DEFAULT_STATE)
        merged.update(raw)
        merged["cleared_by"] = list(merged.get("cleared_by") or [])
        return merged

    def _load_safe(self) -> Dict[str, object]:
        try:
            return self._load()
        except Exception:
            return dict(DEFAULT_STATE)

    def _save(self, state: Dict[str, object]) -> None:
        state["audit_log"] = list(state.get("audit_log") or [])[-AUDIT_MAX_EVENTS:]
        self._backend.write(state)

    def _audit(self, state: Dict[str, object], event: str, detail: str) -> None:
        entry = {"ts": self._now_fn(), "event": event, "detail": detail}
        log = list(state.get("audit_log") or [])[-AUDIT_MAX_EVENTS:]
        log.append(entry)
        state["audit_log"] = log
        if self._emit is not None:
            try:
                self._emit(event, detail)
            except Exception:  # pragma: no cover - audit never gates safety
                logger.warning("audit emit failed for %s", event, exc_info=True)
        else:
            logger.info("watchdog audit %s: %s", event, detail)

    def _report_trip(
        self,
        state: Dict[str, object],
        reason: str,
        ts: float,
    ) -> Dict[str, object]:
        """Mark tripped in the returned dict WITHOUT persisting a latch.

        Used for transient conditions (e.g. never heartbeated) that must read
        as safe but must not lock the cell down until a dual-clear; the next
        successful check re-evaluates liveness.
        """
        state["tripped"] = True
        state["trip_reason"] = reason
        state["trip_at"] = ts
        return state

    def _trip(
        self,
        state: Dict[str, object],
        reason: str,
        ts: float,
        miss: bool = False,
    ) -> Dict[str, object]:
        already = bool(state["tripped"])
        state["tripped"] = True
        state["trip_reason"] = reason
        state["trip_at"] = ts if not already else state.get("trip_at")
        if not already:
            if miss:
                self._audit(state, EVT_MISS, f"{self.name} heartbeat overdue")
            self._audit(state, EVT_TRIP, f"{self.name} -> {reason}")
        try:
            if self.mode == "enforce":
                self._save(state)
        except Exception:
            state["trip_reason"] = "backend_error"
        return state

    def _fail_closed(
        self, reason: str, ts: float, detail: Optional[str] = None
    ) -> Dict[str, object]:
        state = dict(DEFAULT_STATE)
        state["tripped"] = True
        state["trip_reason"] = reason
        state["trip_at"] = ts
        self._audit(state, EVT_TRIP, f"{self.name} -> {reason}" + (f" ({detail})" if detail else ""))
        return state