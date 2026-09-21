"""H-015 / F-015 (ASP-379): tool-execution behavioral anomaly detector.

Hermetic unit tests for sentinel.tool_anomaly. Never touches NATS, a live
journal, or propose_act. Uses fixture event sequences (ADR-0007 dicts) that are
clearly benign vs clearly anomalous, and asserts the detector is fail-open.
"""
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_PYTHON = REPO_ROOT / "src" / "python"
sys.path.insert(0, str(SRC_PYTHON))

from sentinel.tool_anomaly import (
    ToolAnomalyDetector,
    read_jsonl,
)

# Fixed epoch base for deterministic windows (2026-09-20T00:00:00Z)
BASE_TS = 1789948800.0


def _event(
    actor: str,
    action: str,
    target: str = "",
    result: str = "ok",
    ts: float = 0.0,
) -> dict:
    return {
        "event_id": f"{actor}-{action}-{ts}".replace("/", "_"),
        "actor": actor,
        "action": action,
        "target": target,
        "result": result,
        "ts": ts,
    }


def _events_from(actor: str, actions, *, dt=10.0, result="ok", target=""):
    return [
        _event(actor, action, target=target, result=result, ts=BASE_TS + i * dt)
        for i, action in enumerate(actions)
    ]


# ---------------------------------------------------------------------------
# Benign vs anomalous
# ---------------------------------------------------------------------------


def test_benign_sequence_no_findings():
    """Normal ops work — reads, searches, plain shells — must not flag."""
    events = _events_from(
        "ops-agent",
        [
            "tool.read_file", "tool.search_files", "tool.shell",
            "tool.list_dir", "tool.memory_note", "tool.shell",
            "tool.read_file", "tool.temporal_snapshot",
        ],
        target="/var/log/app.log",
    )
    findings = ToolAnomalyDetector().scan(events)
    assert findings == []


def test_sensitive_read_then_egress_flagged():
    """R1: reading /etc/shadow then http_post within the window is HIGH."""
    events = [
        _event("proxy", "tool.list_dir", target="/etc", ts=BASE_TS),
        _event("proxy", "tool.read_file", target="/etc/shadow", ts=BASE_TS + 1),
        _event("proxy", "tool.http_post", target="https://c2.example.invalid/collect",
               ts=BASE_TS + 5),
    ]
    findings = ToolAnomalyDetector().scan(events)
    r1 = [f for f in findings if f.rule == "sensitive_read_then_egress"]
    assert len(r1) == 1
    assert r1[0].severity == "high"


def test_sensitive_read_then_plain_shell_not_egress():
    """A shell without a network target is not an egress for R1."""
    events = [
        _event("proxy", "tool.read_file", target=".env.credentials.txt", ts=BASE_TS),
        _event("proxy", "tool.shell", target="ls -la", ts=BASE_TS + 3),
    ]
    findings = ToolAnomalyDetector().scan(events)
    assert [f for f in findings if f.rule == "sensitive_read_then_egress"] == []


def test_egress_outside_window_not_flagged():
    """Same pair far beyond the window must not flag (windowed)."""
    events = [
        _event("proxy", "tool.read_file", target="nkey.seed", ts=BASE_TS),
        _event("proxy", "tool.http_post", target="https://x/collect",
               ts=BASE_TS + 600),
    ]
    findings = ToolAnomalyDetector().scan(events)
    assert [f for f in findings if f.rule == "sensitive_read_then_egress"] == []


def test_high_risk_burst_flagged():
    """R2: 6 high-risk calls inside the window."""
    events = _events_from(
        "proxy",
        ["tool.shell"] * 6,
        target="ls",
    )
    findings = ToolAnomalyDetector().scan(events)
    r2 = [f for f in findings if f.rule == "high_risk_burst"]
    assert len(r2) == 1
    assert r2[0].severity == "medium"


def test_denial_probe_flagged():
    """R3: same active-action denied repeatedly inside the window."""
    events = _events_from(
        "red",
        ["tool.shell"] * 4,
        result="deny",
        target="opencode --run",
    )
    findings = ToolAnomalyDetector().scan(events)
    r3 = [f for f in findings if f.rule == "denial_probe"]
    assert len(r3) == 1
    assert r3[0].severity == "medium"


def test_error_storm_flagged():
    """R4: same tool failing repeatedly inside the window."""
    events = _events_from(
        "proxy",
        ["tool.read_file"] * 6,
        result="failed",
        target="/proc/kcore",
    )
    findings = ToolAnomalyDetector().scan(events)
    r4 = [f for f in findings if f.rule == "error_storm"]
    assert len(r4) == 1
    assert r4[0].severity == "low"


# ---------------------------------------------------------------------------
# Fail-open contract
# ---------------------------------------------------------------------------


def test_fail_open_never_raises_on_garbage():
    det = ToolAnomalyDetector()
    garbage = [
        None,
        "not-a-dict",
        42,
        {"king": "midas"},           # no actor/action/ts
        {"actor": "x", "action": ["weird"]},  # non-str action + no ts
    ]
    findings = det.scan(garbage)          # must not raise
    assert isinstance(findings, list)


def test_findings_are_fail_open_log_only():
    events = [
        _event("proxy", "tool.read_file", target="tokens.json", ts=BASE_TS),
        _event("proxy", "tool.http_post", target="https://x/collect", ts=BASE_TS + 2),
    ]
    findings = ToolAnomalyDetector().scan(events)
    assert findings  # at least R1
    for f in findings:
        payload = f.to_dict()
        assert f.fail_open is True
        assert payload["action_required"] == "investigate"
        assert "deny" not in payload["action_required"]  # never a blocking verdict


def test_scan_is_time_order_independent():
    """The batch API sorts events, so shuffled input matches ordered input."""
    ordered = [
        _event("proxy", "tool.read_file", target="id_rsa", ts=BASE_TS),
        _event("proxy", "tool.http_post", target="https://x/collect", ts=BASE_TS + 2),
    ]
    shuffled = [ordered[1], ordered[0]]
    assert (len(ToolAnomalyDetector().scan(ordered))
            == len(ToolAnomalyDetector().scan(shuffled)))


# ---------------------------------------------------------------------------
# Source loaders
# ---------------------------------------------------------------------------


def test_read_jsonl_skips_malformed_lines(tmp_path):
    log = tmp_path / "audit.jsonl"
    log.write_text(
        '{"actor":"a","action":"tool.shell","target":"ls","result":"ok","ts":1}\n'
        "this is not json\n"
        '{"actor":"b","action":"tool.http_post",\n',  # truncated
        encoding="utf-8",
    )
    events = read_jsonl(str(log))
    assert len(events) == 1
    assert events[0]["actor"] == "a"


def test_cli_scan_reports_and_never_errors(tmp_path):
    """CLI end-to-end: benign journal prints no anomaly; anomalous prints a finding."""
    benign = [
        _event("ops-agent", "tool.read_file", target="/var/log/app.log", ts=BASE_TS),
        _event("ops-agent", "tool.shell", target="ls", ts=BASE_TS + 5),
    ]
    anomalous = [
        _event("proxy", "tool.read_file", target="/etc/shadow", ts=BASE_TS),
        _event("proxy", "tool.http_post", target="https://c2.invalid/x",
               ts=BASE_TS + 3),
    ]

    for name, events, expect_finding in (
        ("benign", benign, False),
        ("anomalous", anomalous, True),
    ):
        journal = tmp_path / f"{name}.jsonl"
        journal.write_text(
            "".join(json.dumps(e) + "\n" for e in events), encoding="utf-8"
        )
        proc = subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "tool-anomaly.py"),
             "scan", "--jsonl", str(journal)],
            capture_output=True, text=True, timeout=60, check=False,
        )
        assert proc.returncode == 0, proc.stderr
        outcome = proc.stdout
        if expect_finding:
            assert "finding(s)" in outcome and "0 finding" not in outcome
            assert "sensitive_read_then_egress" in outcome
        else:
            assert "no anomalies" in outcome