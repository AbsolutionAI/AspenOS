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

# ---------------------------------------------------------------------------
# Emit-once semantics (ASP-687)
#
# Every rule here is re-evaluated on each arrival, and the consumer feeds events
# one at a time. Without a correlation guard the detector re-emits the *same*
# incident once per subsequent event: 12 events containing one read+egress pair
# produced 11 identical R1 findings. These tests pin one incident -> one finding.
# ---------------------------------------------------------------------------


def test_r1_emits_once_not_once_per_later_event():
    """The R1 regression: 12 events, one exfil pair, exactly one finding."""
    events = [
        _event("proxy", "tool.read_file", target="/etc/shadow", ts=BASE_TS),
        _event("proxy", "tool.http_post", target="https://c2.invalid/x",
               ts=BASE_TS + 3),
    ] + [
        _event("proxy", "tool.search_files", target="docs/readme.md",
               ts=BASE_TS + 10 * (i + 1))
        for i in range(10)
    ]

    findings = ToolAnomalyDetector().scan(events)

    r1 = [f for f in findings if f.rule == "sensitive_read_then_egress"]
    assert len(r1) == 1, [f.message for f in r1]
    assert len(findings) == 1, [f.rule for f in findings]


def test_r1_emits_once_when_fed_one_event_at_a_time():
    """Streaming is the live path, and it was the worse case: 11 findings."""
    events = [
        _event("proxy", "tool.read_file", target="/etc/shadow", ts=BASE_TS),
        _event("proxy", "tool.http_post", target="https://c2.invalid/x",
               ts=BASE_TS + 3),
    ] + [
        _event("proxy", "tool.search_files", target="docs/readme.md",
               ts=BASE_TS + 10 * (i + 1))
        for i in range(10)
    ]

    detector = ToolAnomalyDetector()
    emitted = [f for event in events for f in detector.feed(event)]

    assert len(emitted) == 1, [f.message for f in emitted]


def test_r1_dedupe_does_not_swallow_a_second_incident():
    """Two separate exfil attempts by the same actor are two findings."""
    detector = ToolAnomalyDetector()
    for i in range(3):
        assert detector.feed(
            _event("proxy", "tool.read_file", target="/etc/shadow",
                   ts=BASE_TS + i * 10_000)
        ) == []
    assert len(detector.feed(
        _event("proxy", "tool.http_post", target="https://c2.invalid/x",
               ts=BASE_TS + 3)
    )) == 1
    assert len(detector.feed(
        _event("proxy", "tool.read_file", target="/etc/shadow", ts=BASE_TS + 10_000)
    )) == 0
    assert len(detector.feed(
        _event("proxy", "tool.http_post", target="https://c2.invalid/y",
               ts=BASE_TS + 10_003)
    )) == 1


def test_r1_out_of_order_arrival_does_not_refire():
    """A late-arriving older event must not resurrect a reported incident."""
    detector = ToolAnomalyDetector()
    assert len(detector.feed(
        _event("proxy", "tool.read_file", target="/etc/shadow", ts=BASE_TS)
    )) == 0
    assert len(detector.feed(
        _event("proxy", "tool.http_post", target="https://c2.invalid/x",
               ts=BASE_TS + 3)
    )) == 1
    # Lands *after* the egress in the window, so the pair is unchanged.
    assert detector.feed(
        _event("proxy", "tool.read_file", target="/etc/shadow", ts=BASE_TS + 1)
    ) == []


def test_r1_actors_are_independent():
    """Correlation state is per actor, not global."""
    detector = ToolAnomalyDetector()
    for actor in ("agent-a", "agent-b"):
        assert detector.feed(
            _event(actor, "tool.read_file", target="/etc/shadow", ts=BASE_TS)
        ) == []
        assert len(detector.feed(
            _event(actor, "tool.http_post", target="https://c2.invalid/x",
                   ts=BASE_TS + 3)
        )) == 1
    assert len(detector._emitted["agent-a"]) == 1
    assert len(detector._emitted["agent-b"]) == 1


def test_redelivered_event_id_cannot_manufacture_a_burst():
    """JetStream is at-least-once; a redelivery must not inflate the R2 count."""
    detector = ToolAnomalyDetector()
    for i in range(4):
        assert detector.feed(
            _event("ops", "tool.shell", target="ls", ts=BASE_TS + i * 2)
        ) == []
    assert detector.feed(
        _event("ops", "tool.shell", target="ls", ts=BASE_TS + 6)
    ) == [], "5th shell fires the burst"
    assert len(detector.feed(
        _event("ops", "tool.shell", target="ls", ts=BASE_TS + 8)
    )) == 1
    # Same message again — a redelivery, not a 6th call.
    assert detector.feed(
        _event("ops", "tool.shell", target="ls", ts=BASE_TS + 8)
    ) == []


def test_burst_still_fires_without_redelivery():
    """The dedupe guard must not suppress the genuine threshold crossing."""
    detector = ToolAnomalyDetector()
    emitted = [
        f
        for i in range(5)
        for f in detector.feed(
            _event("ops", "tool.shell", target="ls", ts=BASE_TS + i * 2)
        )
    ]
    assert [f.rule for f in emitted] == ["high_risk_burst"]


def test_dedupe_state_expires_with_the_window():
    """The correlation cache is bounded, not a permanent leak."""
    detector = ToolAnomalyDetector(window_s=100.0)
    assert len(detector.feed(
        _event("proxy", "tool.read_file", target="/etc/shadow", ts=BASE_TS)
    )) == 0
    assert len(detector.feed(
        _event("proxy", "tool.http_post", target="https://c2.invalid/x",
               ts=BASE_TS + 3)
    )) == 1
    # Far outside the window: the old key is pruned.
    detector.feed(_event("proxy", "tool.search_files", target="x", ts=BASE_TS + 10_000))
    assert detector._emitted["proxy"] == {}


def test_dedupe_state_pruned_by_a_quiet_actor():
    """A benign event must still release correlation state (leak guard)."""
    detector = ToolAnomalyDetector(window_s=100.0)
    assert len(detector.feed(
        _event("proxy", "tool.read_file", target="/etc/shadow", ts=BASE_TS)
    )) == 0
    assert len(detector.feed(
        _event("proxy", "tool.http_post", target="https://c2.invalid/x",
               ts=BASE_TS + 3)
    )) == 1
    assert len(detector._emitted["proxy"]) == 1
    # No finding fires here, yet the key must still age out.
    assert detector.feed(
        _event("proxy", "tool.search_files", target="docs/readme.md",
               ts=BASE_TS + 500)
    ) == []
    assert detector._emitted["proxy"] == {}


def test_events_without_event_id_still_detect():
    """Guard is opt-in on the id: legacy events with no id must still work."""
    events = [
        _event("proxy", "tool.read_file", target="/etc/shadow", ts=BASE_TS),
        _event("proxy", "tool.http_post", target="https://c2.invalid/x",
               ts=BASE_TS + 3),
    ]
    for event in events:
        event.pop("event_id")
    assert len(ToolAnomalyDetector().scan(events)) == 1


def test_duplicate_event_without_id_is_counted_twice():
    """Documents the limit: no id means no way to tell a redelivery apart."""
    events = [
        _event("ops", "tool.shell", target="ls", ts=BASE_TS + i * 2)
        for i in range(4)
    ]
    dup = dict(events[-1])
    dup.pop("event_id")
    events[-1].pop("event_id")

    findings = ToolAnomalyDetector().scan(events + [dup])
    assert [f.rule for f in findings] == ["high_risk_burst"]
