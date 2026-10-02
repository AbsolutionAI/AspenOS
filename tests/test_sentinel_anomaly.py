"""
Tests for the Aspen Sentinel tool-anomaly consumer (ADR-0007 / ASP-687).

Covers the wiring ASP-379 deferred: audit events reach ``ToolAnomalyDetector``,
findings reach the JSONL journal and ``aspen.sentinel.tools.anomaly``.

- Envelope shape and content-derived ``finding_id`` (``Nats-Msg-Id`` dedup)
- ``ingest()`` feeds the detector and journals only what actually fired
- Offline ``scan()`` / ``scan_journal()`` produce the same findings, no broker
- ``tail()`` / ``check()`` read the journal
- Best-effort JetStream publish (mocked) with the dedup header
- Fail-open: broker down, malformed message, detector raising, unwritable path
- Regression: one incident emits one finding, not one per later event (R1)
- Regression: a redelivered ``event_id`` cannot manufacture a burst (R2)
"""

import asyncio
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_PYTHON = os.path.join(REPO_ROOT, "src", "python")
sys.path.insert(0, SRC_PYTHON)

from sentinel.anomaly_consumer import (
    DEFAULT_ANOMALY_LOG,
    SUBJECT_AUDIT_EVENT,
    SUBJECT_TOOLS_ANOMALY,
    AnomalyConsumer,
    build_finding_envelope,
    finding_id,
)
from sentinel.tool_anomaly import Finding, ToolAnomalyDetector


BASE = datetime(2026, 10, 2, 12, 0, 0, tzinfo=timezone.utc)


def _ts(offset_s):
    return (BASE + timedelta(seconds=offset_s)).isoformat().replace("+00:00", "Z")


def _event(i, action, target, actor="agent-1", result="ok"):
    return {
        "event_id": f"evt-{i:04d}",
        "ts": _ts(i),
        "actor": actor,
        "action": action,
        "target": target,
        "result": result,
    }


def _exfil_events(count=2, actor="agent-1", start=0):
    """A sensitive read, an egress, then benign filler — exactly `count` events."""
    assert count >= 2, "an exfiltration incident needs the read and the egress"
    events = [
        _event(start, "tool.read_file", "/etc/shadow", actor=actor),
        _event(start + 1, "tool.http_post", "https://exfil.example/collect", actor=actor),
    ]
    for i in range(2, count):
        events.append(
            _event(start + i, "tool.search_files", "docs/readme.md", actor=actor)
        )
    return events


def _ingest_incident(consumer, count=6, **kwargs):
    """Feed a whole incident; return the finding envelopes it produced."""
    emitted = []
    for e in _exfil_events(count=count, **kwargs):
        emitted.extend(_ingest(consumer, e))
    return emitted


def _consumer(tmp_path, **kwargs):
    kwargs.setdefault("anomaly_log", str(tmp_path / "anomaly.jsonl"))
    kwargs.setdefault("audit_log", str(tmp_path / "audit.jsonl"))
    return AnomalyConsumer(**kwargs)


def _run(coro):
    """Run a coroutine on a fresh loop, off the caller's event loop."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _ingest(consumer, event):
    return _run(consumer.ingest(event))


def _findings_on_disk(path):
    if not os.path.exists(path):
        return []
    return [json.loads(l) for l in open(path).read().splitlines() if l.strip()]


# --------------------------------------------------------------------------
# finding_id / envelope
# --------------------------------------------------------------------------


def test_finding_id_is_stable_for_same_incident():
    finding = Finding(
        rule="sensitive_read_then_egress",
        severity="high",
        actor="agent-1",
        message="sensitive read then egress",
        window_s=600.0,
        events=[_event(0, "tool.read_file", "/etc/shadow")],
    )
    assert finding_id(finding) == finding_id(finding)


def test_finding_id_differs_across_incidents():
    events = _exfil_events(count=3)
    findings = ToolAnomalyDetector().scan(events)
    assert len(findings) == 1
    other = ToolAnomalyDetector().scan(_exfil_events(count=3, start=100_000))
    assert finding_id(findings[0]) != finding_id(other[0])


def test_finding_id_includes_event_id():
    finding = Finding(
        rule="error_storm",
        severity="low",
        actor="agent-1",
        message="repeated failures",
        window_s=300.0,
        events=[],
    )
    assert finding_id(finding, "evt-1") != finding_id(finding, "evt-2")


def test_envelope_shape_matches_adr0007():
    finding = Finding(
        rule="sensitive_read_then_egress",
        severity="high",
        actor="agent-1",
        message="sensitive read then egress",
        window_s=600.0,
        events=[_event(0, "tool.read_file", "/etc/shadow")],
    )
    env = build_finding_envelope(finding, event_id="evt-0001")
    for key in ("rule", "severity", "actor", "message", "window_s", "events",
                "finding_id", "ts", "source", "event_id"):
        assert key in env, f"envelope missing {key}"
    assert env["event_id"] == "evt-0001"
    assert env["source"] == "sentinel-tool-anomaly"
    assert env["ts"].endswith("Z")


def test_subject_contracts():
    assert SUBJECT_AUDIT_EVENT == "aspen.sentinel.audit.event"
    assert SUBJECT_TOOLS_ANOMALY == "aspen.sentinel.tools.anomaly"


def test_default_log_path_is_documented_location():
    assert DEFAULT_ANOMALY_LOG == "/var/lib/aspen/sentinel/anomaly.jsonl"


# --------------------------------------------------------------------------
# ingest(): the live path minus the subscription
# --------------------------------------------------------------------------


def test_ingest_journals_and_returns_finding(tmp_path):
    consumer = _consumer(tmp_path)
    events = _exfil_events(count=6)

    assert _ingest(consumer, events[0]) == []
    envelopes = _ingest(consumer, events[1])

    assert len(envelopes) == 1
    assert envelopes[0]["rule"] == "sensitive_read_then_egress"
    assert envelopes[0]["severity"] == "high"
    assert envelopes[0]["actor"] == "agent-1"
    on_disk = _findings_on_disk(tmp_path / "anomaly.jsonl")
    assert len(on_disk) == 1
    assert on_disk[0]["finding_id"] == envelopes[0]["finding_id"]


def test_ingest_counts_events_and_findings(tmp_path):
    consumer = _consumer(tmp_path)
    _ingest_incident(consumer, count=5)
    stats = consumer.stats
    assert stats["events_seen"] == 5
    assert stats["findings_emitted"] == 1
    assert stats["findings_published"] == 0  # offline


def test_ingest_regression_one_incident_one_finding(tmp_path):
    """R1 is a set-state predicate; it used to re-emit per subsequent event."""
    consumer = _consumer(tmp_path)
    emitted = [_ingest(consumer, e) for e in _exfil_events(count=12)]
    assert sum(len(e) for e in emitted) == 1
    assert len(_findings_on_disk(tmp_path / "anomaly.jsonl")) == 1


def test_ingest_regression_second_incident_still_fires(tmp_path):
    """Dedupe must not swallow a genuinely new incident for the same actor."""
    consumer = _consumer(tmp_path)
    _ingest_incident(consumer, count=2)
    # Push the first incident out of the window before the second one.
    emitted = _ingest_incident(consumer, count=2, start=100_000)
    assert len(emitted) == 1


def test_ingest_regression_redelivery_cannot_make_a_burst(tmp_path):
    """At-least-once redelivery must not inflate the R2 count."""
    consumer = _consumer(tmp_path)
    shells = [_event(i, "tool.shell", "ls") for i in range(4)]
    emitted = [_ingest(consumer, e) for e in shells]
    assert sum(len(e) for e in emitted) == 0
    redelivered = _ingest(consumer, shells[-1])
    assert redelivered == []
    fifth = _ingest(consumer, _event(4, "tool.shell", "ls"))
    assert len(fifth) == 1
    assert fifth[0]["rule"] == "high_risk_burst"


def test_ingest_is_per_actor(tmp_path):
    consumer = _consumer(tmp_path)
    _ingest_incident(consumer, count=2, actor="agent-1")
    _ingest_incident(consumer, count=2, actor="agent-2")
    rules = [f["rule"] for f in _findings_on_disk(tmp_path / "anomaly.jsonl")]
    assert rules.count("sensitive_read_then_egress") == 2
    assert {f["actor"] for f in _findings_on_disk(tmp_path / "anomaly.jsonl")} == {
        "agent-1",
        "agent-2",
    }


def test_ingest_creates_parent_directory(tmp_path):
    consumer = _consumer(tmp_path, anomaly_log=str(tmp_path / "deep" / "a" / "anomaly.jsonl"))
    _ingest_incident(consumer)
    assert (tmp_path / "deep" / "a" / "anomaly.jsonl").exists()


# --------------------------------------------------------------------------
# offline scan
# --------------------------------------------------------------------------


def test_scan_matches_ingest_and_needs_no_broker(tmp_path):
    live = _consumer(tmp_path, anomaly_log=str(tmp_path / "live.jsonl"))
    batch = _consumer(tmp_path, anomaly_log=str(tmp_path / "batch.jsonl"))
    events = _exfil_events(count=8)

    for e in events:
        _ingest(live, e)
    batch.scan(events)

    live_rules = [f["rule"] for f in _findings_on_disk(tmp_path / "live.jsonl")]
    batch_rules = [f["rule"] for f in _findings_on_disk(tmp_path / "batch.jsonl")]
    assert live_rules == batch_rules == ["sensitive_read_then_egress"]


def test_scan_accepts_unordered_events(tmp_path):
    consumer = _consumer(tmp_path)
    events = _exfil_events(count=5)
    envelopes = consumer.scan(list(reversed(events)))
    assert len(envelopes) == 1


def test_scan_journal_reads_audit_log(tmp_path):
    audit = tmp_path / "audit.jsonl"
    audit.write_text(
        "\n".join(json.dumps(e) for e in _exfil_events(count=6)) + "\n",
        encoding="utf-8",
    )
    consumer = _consumer(tmp_path)
    envelopes = consumer.scan_journal()
    assert len(envelopes) == 1
    assert consumer.stats["events_seen"] == 6


def test_scan_journal_skips_malformed_lines(tmp_path):
    audit = tmp_path / "audit.jsonl"
    good = [json.dumps(e) for e in _exfil_events(count=6)]
    audit.write_text("\n".join(good[:2] + ["{not json"] + good[2:]) + "\n", encoding="utf-8")
    consumer = _consumer(tmp_path)
    assert len(consumer.scan_journal()) == 1


def test_scan_journal_missing_file_is_empty(tmp_path):
    consumer = _consumer(tmp_path)
    assert consumer.scan_journal() == []


# --------------------------------------------------------------------------
# tail / findings / check
# --------------------------------------------------------------------------


def test_tail_returns_newest_first(tmp_path):
    consumer = _consumer(tmp_path)
    consumer._append_journal({"ts": _ts(1), "rule": "a", "severity": "low"})
    consumer._append_journal({"ts": _ts(2), "rule": "b", "severity": "high"})
    consumer._append_journal({"ts": _ts(3), "rule": "c", "severity": "medium"})
    assert [f["rule"] for f in consumer.tail(2)] == ["c", "b"]
    assert [f["rule"] for f in consumer.tail(10)] == ["c", "b", "a"]
    assert consumer.tail(0) == []


def test_findings_reads_whole_journal(tmp_path):
    consumer = _consumer(tmp_path)
    consumer._append_journal({"ts": _ts(1), "rule": "a"})
    consumer._append_journal({"ts": _ts(2), "rule": "b"})
    assert [f["rule"] for f in consumer.findings()] == ["a", "b"]


def test_check_reports_journal_and_subjects(tmp_path):
    consumer = _consumer(tmp_path)
    for e in _exfil_events(count=6):
        _ingest(consumer, e)
    report = _run(
        consumer.check()
    )
    assert report["findings_on_disk"] == 1
    assert report["by_rule"] == {"sensitive_read_then_egress": 1}
    assert report["by_severity"] == {"high": 1}
    assert report["source_subject"] == "aspen.sentinel.audit.event"
    assert report["findings_subject"] == "aspen.sentinel.tools.anomaly"
    assert report["online"] is False
    assert report["stream"] == "ASPEN_SENTINEL"
    assert report["first_ts"] and report["last_ts"]


# --------------------------------------------------------------------------
# JetStream publish (mocked)
# --------------------------------------------------------------------------


def _online_consumer(tmp_path):
    consumer = _consumer(tmp_path)
    js = MagicMock()
    js.add_stream = AsyncMock()
    js.publish = AsyncMock()
    stream_state = MagicMock()
    stream_state.messages = 4
    stream_state.bytes = 512
    js.stream_info = AsyncMock(return_value=MagicMock(state=stream_state))
    nc = MagicMock()
    nc.is_connected = True
    nc.jetstream = MagicMock(return_value=js)
    nc.subscribe = AsyncMock(return_value=MagicMock())
    nc.drain = AsyncMock()
    nc.close = AsyncMock()
    consumer._nc = nc
    consumer._js = js
    consumer._connected = True
    return consumer, js


def test_publish_uses_findings_subject_and_msg_id_header(tmp_path):
    consumer, js = _online_consumer(tmp_path)
    envelopes = _ingest_incident(consumer)

    subject, payload = js.publish.call_args[0]
    assert subject == "aspen.sentinel.tools.anomaly"
    assert js.publish.call_args[1]["headers"] == {
        "Nats-Msg-Id": envelopes[0]["finding_id"]
    }
    assert json.loads(payload.decode())["rule"] == "sensitive_read_then_egress"
    assert consumer.stats["findings_published"] == 1


def test_publish_failure_does_not_lose_the_finding(tmp_path):
    consumer, js = _online_consumer(tmp_path)
    js.publish = AsyncMock(side_effect=RuntimeError("no stream"))
    envelopes = _ingest_incident(consumer)
    assert len(envelopes) == 1
    assert len(_findings_on_disk(tmp_path / "anomaly.jsonl")) == 1
    assert consumer.stats["findings_published"] == 0


def test_check_includes_jetstream_state_when_online(tmp_path):
    consumer, _ = _online_consumer(tmp_path)
    report = _run(
        consumer.check()
    )
    assert report["online"] is True
    assert report["jetstream"] == {"messages": 4, "bytes": 512}


def test_ensure_stream_uses_existing_sentinel_subjects(tmp_path):
    consumer, js = _online_consumer(tmp_path)
    consumer._stream_subjects = ["aspen.sentinel.>"]
    _run(
        consumer._ensure_stream()
    )
    kwargs = js.add_stream.call_args[1]
    assert kwargs["name"] == "ASPEN_SENTINEL"
    assert kwargs["subjects"] == ["aspen.sentinel.>"]


# --------------------------------------------------------------------------
# subscription
# --------------------------------------------------------------------------


def test_subscribe_registers_callback_on_audit_subject(tmp_path):
    consumer, _ = _online_consumer(tmp_path)
    _run(
        consumer._subscribe()
    )
    subject = consumer._nc.subscribe.call_args[0][0]
    assert subject == "aspen.sentinel.audit.event"
    assert consumer._nc.subscribe.call_args[1]["cb"] == consumer._on_audit


def test_on_audit_parses_json_payload(tmp_path):
    consumer, _ = _online_consumer(tmp_path)
    events = _exfil_events(count=6)
    msg = MagicMock()
    msg.data = json.dumps(events[0]).encode()
    msg.subject = SUBJECT_AUDIT_EVENT

    async def run():
        await consumer._on_audit(msg)
        await consumer._on_audit(msg)

    _run(run())
    assert consumer.stats["events_seen"] == 2  # no duplicate finding


def test_on_audit_rejects_garbage(tmp_path):
    consumer, _ = _online_consumer(tmp_path)
    bad = MagicMock()
    bad.data = b"{not json"
    non_dict = MagicMock()
    non_dict.data = b"[1,2,3]"

    async def run():
        await consumer._on_audit(bad)
        await consumer._on_audit(non_dict)
        await consumer._on_audit(MagicMock(data=None))

    _run(run())
    assert consumer.stats["events_rejected"] == 3
    assert consumer.stats["events_seen"] == 0


# --------------------------------------------------------------------------
# fail-open
# --------------------------------------------------------------------------


def test_start_without_url_is_journal_only(tmp_path):
    consumer = _consumer(tmp_path)
    assert _run(
        consumer.start()
    ) is False
    assert consumer.is_online is False


def test_start_survives_missing_nats_library(tmp_path):
    consumer = _consumer(tmp_path, nats_url="nats://127.0.0.1:4222")
    with patch.dict(sys.modules, {"nats": None}):
        assert _run(
            consumer.start()
        ) is False
    assert consumer.is_online is False
    # Still usable as journal-only.
    assert len(_ingest_incident(consumer)) == 1


def test_start_survives_broker_refused(tmp_path):
    consumer = _consumer(tmp_path, nats_url="nats://127.0.0.1:4222")
    fake_nats = MagicMock()
    fake_nats.connect = AsyncMock(side_effect=OSError("connection refused"))
    with patch.dict(sys.modules, {"nats": fake_nats}):
        assert _run(
            consumer.start()
        ) is False
    assert consumer.is_online is False


def test_detector_failure_is_counted_not_raised(tmp_path):
    consumer = _consumer(tmp_path)
    boom = MagicMock()
    boom.feed.side_effect = RuntimeError("detector exploded")
    consumer._detector = boom
    assert _ingest(consumer, _event(0, "tool.shell", "ls")) == []
    assert consumer.stats["events_rejected"] == 1


def test_unwritable_journal_does_not_raise(tmp_path):
    consumer = _consumer(tmp_path, anomaly_log="/proc/definitely/not/writable.jsonl")
    # Finding is produced but cannot be recorded; must not propagate.
    assert _ingest_incident(consumer) == []


def test_close_is_idempotent(tmp_path):
    consumer, _ = _online_consumer(tmp_path)
    _run(consumer.close())
    _run(consumer.close())
    assert consumer.is_online is False

# --------------------------------------------------------------------------
# ACL coverage — the findings subject must be reachable by the ops account
# --------------------------------------------------------------------------

REPO_ROOT_NATS = os.path.join(REPO_ROOT, "nats")


def _conf_text(name):
    with open(os.path.join(REPO_ROOT_NATS, name), encoding="utf-8") as fh:
        return fh.read()


def test_findings_subject_falls_under_existing_ops_acl():
    """`aspen.sentinel.>` already grants publish+subscribe — no ACL change needed.

    Verified rather than assumed: if this ever fails, the new subject needs an
    entry in `nats/fleet-accounts.conf.tmpl`.
    """
    text = _conf_text("fleet-accounts.conf.tmpl")
    block = re.search(
        r"^\s*STARSHIP_OPS \{(.*?)^\s{2}\}", text, re.MULTILINE | re.DOTALL
    )
    assert block, "STARSHIP_OPS block missing from fleet-accounts template"
    ops = block.group(1)
    publish = re.search(r"publish:\s*\{(.*?)\}", ops, re.DOTALL)
    subscribe = re.search(r"subscribe:\s*\{(.*?)\}", ops, re.DOTALL)
    assert publish and '"aspen.sentinel.>"' in publish.group(1), (
        "ops account cannot publish to aspen.sentinel.>"
    )
    assert subscribe and '"aspen.sentinel.>"' in subscribe.group(1), (
        "ops account cannot subscribe to aspen.sentinel.>"
    )
    exports = re.search(r"exports:\s*\[(.*?)\]", ops, re.DOTALL)
    assert exports and '"aspen.sentinel.>"' in exports.group(1), (
        "ops account lost its aspen.sentinel JetStream export"
    )
    # The new subject is a child of that wildcard.
    assert SUBJECT_TOOLS_ANOMALY.startswith("aspen.sentinel.")


def test_subjects_manifest_registers_findings_subject():
    """`nats/subjects.yaml` is the machine-readable contract list."""
    with open(os.path.join(REPO_ROOT_NATS, "subjects.yaml"), encoding="utf-8") as fh:
        assert "tools_anomaly" in fh.read()
    with open(os.path.join(REPO_ROOT_NATS, "subjects.yaml"), encoding="utf-8") as fh:
        assert SUBJECT_TOOLS_ANOMALY in fh.read()


def test_subjects_manifest_is_valid_yaml():
    try:
        import yaml
    except ImportError:
        pytest.skip("PyYAML not installed")
    with open(os.path.join(REPO_ROOT_NATS, "subjects.yaml"), encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    assert data["aspen"]["sentinel"]["tools_anomaly"] == SUBJECT_TOOLS_ANOMALY
