"""Behavioral anomaly detection over sentinel tool-audit events (F-015 / ASP-379).

Consumes ADR-0007 audit events (``{event_id, actor, action, target, result, ts}``
plus any ``tool`` extra field) and flags *unusual tool sequences* with a small
set of explicit rules: one temporal sequence rule plus three sliding-window
statistical rules. It is a **fail-open, log-only detector** — it never blocks
``propose_act`` (or any other call path) and never raises on bad input.

Rules:

* ``sensitive_read_then_egress`` (R1, high) — same actor performs a sensitive
  read (credential/secret-adjacent target) and then an egress tool
  (``http_post`` / ``delegate_to_agent`` / networked ``shell``) inside the
  window. Suspicion: data exfiltration / pivot after compromise.
* ``high_risk_burst`` (R2, medium) — same actor runs ``n``+ high-risk tools
  inside the window. Suspicion: automated attack or runaway agent.
* ``denial_probe`` (R3, medium) — same actor gets the *same* high-risk action
  denied ``n``+ times inside the window. Suspicion: probing the guard.
* ``error_storm`` (R4, low) — same actor+tool fails ``n``+ times inside the
  window. Suspicion: broken/poisoned tool or supply-chain failure.

Every finding carries ``fail_open: True`` and ``action_required: "investigate"``
so consumers know the detector observed something worth a human look, never a
hard stop.

Usage::

    from sentinel.tool_anomaly import ToolAnomalyDetector

    det = ToolAnomalyDetector()
    findings = det.scan(events)   # batch: list[dict] -> list[Finding]
    # or
    for event in stream:
        for finding in det.feed(event):   # incremental
            ...

CLI: ``scripts/tool-anomaly.py scan --jsonl <journal>``.
"""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

# ---------------------------------------------------------------------------
# Event schema / classification helpers
# ---------------------------------------------------------------------------

SENSITIVE_TARGET_TOKENS = (
    "credential",
    "credentials",
    "secret",
    "password",
    "passwd",
    "shadow",
    "key",
    "private_key",
    "token",
    ".env",
    "api_key",
    "auth",
    "nkey",
)

SENSITIVE_READ_ACTIONS = (
    "tool.read_file",
    "tool.search_files",
    "tool.list_dir",
    "tool.kg_query",
    "tool.vault_list",
    "tool.archive_search",
    "read_file",
    "search_files",
    "kg_query",
    "vault_list",
    "archive_search",
)

EGRESS_ACTIONS = (
    "tool.http_post",
    "tool.delegate_to_agent",
    "tool.delegate",
    "http_post",
    "delegate_to_agent",
    "delegate",
)

HIGH_RISK_ACTIONS = (
    "tool.shell",
    "tool.http_post",
    "tool.http_get",
    "tool.write_file",
    "tool.delegate_to_agent",
    "tool.delegate",
    "tool.opencode",
    "tool.opendesign",
    "tool.policyexec",
    "shell",
    "http_post",
    "http_get",
    "write_file",
    "delegate_to_agent",
    "delegate",
    "opencode",
    "opendesign",
    "policyexec",
)

DENY_RESULTS = ("deny", "denied", "blocked", "refused", "gate.deny")
FAIL_RESULTS = ("failed", "error", "exception")


def _ts_epoch(ts: Any) -> float:
    """Coerce a naive/aware ISO ts (or raw epoch) to epoch seconds."""
    if ts is None:
        return float("inf")
    if isinstance(ts, (int, float)):
        return float(ts)
    try:
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except ValueError:
        return float("inf")


def _is_sensitive_target(target: Any) -> bool:
    text = str(target or "").lower()
    if not text:
        return False
    return any(tok in text for tok in SENSITIVE_TARGET_TOKENS)


def _action_name(action: Any) -> str:
    return str(action or "").lower()


def _has_shell_network_target(target: Any) -> bool:
    text = str(target or "").lower()
    return any(
        frag in text
        for frag in ("http://", "https://", "nc ", "netcat", "curl ",
                     "wget ", "ssh ", "telnet ")
    )


def _is_sensitive_read(action: Any, target: Any) -> bool:
    return _action_name(action) in SENSITIVE_READ_ACTIONS and _is_sensitive_target(target)


def _is_egress(action: Any, target: Any) -> bool:
    name = _action_name(action)
    if name in EGRESS_ACTIONS:
        return True
    if name in ("tool.shell", "shell"):
        return _has_shell_network_target(target)
    return False


def _is_high_risk(action: Any) -> bool:
    return _action_name(action) in HIGH_RISK_ACTIONS


# ---------------------------------------------------------------------------
# Finding / detector
# ---------------------------------------------------------------------------


@dataclass
class Finding:
    """One observed anomaly. Always fail-open — informational, never blocking."""

    rule: str
    severity: str
    actor: str
    message: str
    window_s: float
    events: list[dict] = field(default_factory=list)
    fail_open: bool = True
    action_required: str = "investigate"

    def to_dict(self) -> dict:
        return {
            "rule": self.rule,
            "severity": self.severity,
            "actor": self.actor,
            "message": self.message,
            "window_s": self.window_s,
            "events": self.events,
            "fail_open": self.fail_open,
            "action_required": self.action_required,
        }


class ToolAnomalyDetector:
    """Windowed behavioral rule engine over sentinel tool-audit events.

    Fail-open by construction: ``feed``/``scan`` never raise on malformed
    events and never return a blocking verdict.
    """

    def __init__(
        self,
        *,
        window_s: float = 120.0,
        burst_high_risk_min: int = 5,
        denial_min: int = 4,
        error_min: int = 6,
        sensitive_read_egress_window_s: float | None = None,
        window_events_cap: int = 2000,
    ) -> None:
        self.window_s = float(window_s)
        self.burst_high_risk_min = burst_high_risk_min
        self.denial_min = denial_min
        self.error_min = error_min
        self.sensitive_read_egress_window_s = float(
            sensitive_read_egress_window_s or window_s
        )
        self._window_events_cap = int(window_events_cap)
        # actor -> list[(ts_epoch, event)]
        self._history: dict[str, list[tuple]] = {}

    # -- ingestion ----------------------------------------------------------

    def feed(self, event: dict) -> list[Finding]:
        """Ingest one event, returning any findings it triggers."""
        if not isinstance(event, dict):
            return []
        actor = str(event.get("actor") or event.get("agent") or "unknown")
        ts = _ts_epoch(event.get("ts") or event.get("ts_epoch"))
        if ts != float("inf"):
            history = self._history.setdefault(actor, [])
            history.append((ts, event))
            cutoff = ts - self.window_s
            history[:] = [(t, e) for t, e in history if t >= cutoff]
            if len(history) > self._window_events_cap:
                self._history[actor] = history[-self._window_events_cap:]
        return self._check_actor(actor)

    def scan(self, events: Iterable[dict]) -> list[Finding]:
        """Batch ingest: run a sliding detector over the given events.

        Events do not need to be time-ordered; each event is evaluated against
        the window that exists at its own timestamp.
        """
        findings: list[Finding] = []

        def _ordered(events: Iterable[dict]) -> list[dict]:
            return sorted(
                [e for e in events if isinstance(e, dict)],
                key=lambda e: _ts_epoch(e.get("ts") or e.get("ts_epoch")),
            )

        findings = [
            finding
            for event in _ordered(events)
            for finding in self.feed(event)
        ]
        return findings

    # -- rule evaluation ----------------------------------------------------

    def _check_actor(self, actor: str) -> list[Finding]:
        history = self._history.get(actor) or []
        if not history:
            return []
        findings: list[Finding] = []
        rule_r1 = self._rule_sensitive_read_then_egress(actor, history)
        if rule_r1:
            findings.append(rule_r1)
        findings.extend(self._rule_bursts(actor, history))
        return findings

    def _rule_sensitive_read_then_egress(self, actor: str, history: list) -> Finding | None:
        """R1 — sensitive read followed by egress within the R1 window."""
        latency = self.sensitive_read_egress_window_s
        events = sorted([e for _, e in history], key=lambda e: _ts_epoch(e.get("ts")))
        for i, event in enumerate(events):
            if not _is_sensitive_read(event.get("action"), event.get("target")):
                continue
            ts_i = _ts_epoch(event.get("ts"))
            for other in events[i + 1:]:
                ts_j = _ts_epoch(other.get("ts"))
                if ts_j - ts_i > latency:
                    break  # window closed for this read
                if _is_egress(other.get("action"), other.get("target")):
                    return Finding(
                        rule="sensitive_read_then_egress",
                        severity="high",
                        actor=actor,
                        message=(
                            f"sensitive read '{event.get('action')}' on "
                            f"'{event.get('target')}' followed by egress "
                            f"'{other.get('action')}' within {latency:g}s"
                        ),
                        window_s=latency,
                        events=[event, other],
                    )
        return None

    def _rule_bursts(self, actor: str, history: list) -> list[Finding]:
        """R2/R3/R4 — sliding-window statistical rules over recent events.

        Streaming semantics: only the *newest* event (the one just arrived)
        drives evaluation, and the window ends at its timestamp. A rule fires
        when its count hits the threshold exactly, so each burst yields exactly
        one finding.
        """
        if not history:
            return []
        findings: list[Finding] = []
        event = history[-1][1]
        ts = float(_ts_epoch(event.get("ts")))
        local = [
            e for t, e in history
            if 0 <= ts - float(_ts_epoch(e.get("ts"))) <= self.window_s
        ]
        local.sort(key=lambda e: _ts_epoch(e.get("ts")))

        # R2 high-risk burst — fire at exact threshold crossing
        if _is_high_risk(event.get("action")):
            high_risk = [e for e in local if _is_high_risk(e.get("action"))]
            if len(high_risk) == self.burst_high_risk_min:
                findings.append(
                    Finding(
                        rule="high_risk_burst",
                        severity="medium",
                        actor=actor,
                        message=(
                            f"{len(high_risk)} high-risk tool calls in "
                            f"{self.window_s:g}s window "
                            f"(min {self.burst_high_risk_min})"
                        ),
                        window_s=self.window_s,
                        events=high_risk[-self.burst_high_risk_min:],
                    )
                )

        # R3 denial probe — repeated denial of the SAME high-risk action
        action = _action_name(event.get("action"))
        if (
            action
            and _is_high_risk(event.get("action"))
            and str(event.get("result") or "").lower() in DENY_RESULTS
        ):
            denies = [
                e for e in local
                if _action_name(e.get("action")) == action
                and str(e.get("result") or "").lower() in DENY_RESULTS
            ]
            if len(denies) == self.denial_min:
                findings.append(
                    Finding(
                        rule="denial_probe",
                        severity="medium",
                        actor=actor,
                        message=(
                            f"action '{action}' denied {len(denies)} times "
                            f"in {self.window_s:g}s window "
                            f"(min {self.denial_min})"
                        ),
                        window_s=self.window_s,
                        events=denies,
                    )
                )

        # R4 error storm — repeated failures of the same tool
        if action and str(event.get("result") or "").lower() in FAIL_RESULTS:
            fails = [
                e for e in local
                if _action_name(e.get("action")) == action
                and str(e.get("result") or "").lower() in FAIL_RESULTS
            ]
            if len(fails) == self.error_min:
                findings.append(
                    Finding(
                        rule="error_storm",
                        severity="low",
                        actor=actor,
                        message=(
                            f"tool/action '{action}' failed {len(fails)} times "
                            f"in {self.window_s:g}s window (min {self.error_min})"
                        ),
                        window_s=self.window_s,
                        events=fails,
                    )
                )
        return findings


# ---------------------------------------------------------------------------
# Source loaders
# ---------------------------------------------------------------------------


def read_jsonl(path: str) -> list[dict]:
    """Read ADR-0007 events from a JSONL file (or via ``-`` for stdin)."""
    events: list[dict] = []
    if path == "-":
        lines = sys.stdin
    else:
        with open(path, "r", encoding="utf-8") as fh:
            lines = fh.readlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def read_audit_logger() -> list[dict]:
    """Load events from the legacy services.audit SQLite trail (H-004 fallback).

    Returns ADR-0007-shaped dicts. Fails open: any DB error yields [].
    """
    try:
        from services.audit import get_logger  # type: ignore
    except Exception:  # noqa: BLE001 - intentionally fail-open
        return []
    try:
        entries = get_logger().query(limit=100000)
    except Exception:  # noqa: BLE001 - intentionally fail-open
        return []
    out: list[dict] = []
    for e in entries:
        out.append({
            "event_id": e.id,
            "actor": e.agent,
            "action": f"tool.{e.tool}" if e.tool else e.action,
            "target": str(e.arguments or "")[:256],
            "result": "ok" if e.risk_level != "high" else "deny",
            "ts": datetime.fromtimestamp(e.ts_epoch, tz=timezone.utc).isoformat(),
            "tool": e.tool,
            "risk_level": e.risk_level,
            "approval_status": e.approval_status,
            "session_id": e.session_id,
        })
    return out


def default_journal() -> str:
    return os.environ.get(
        "ASPEN_AUDIT_LOG", "/var/lib/aspen/sentinel/audit.jsonl"
    )