"""F-015 / ASP-687: live tool-audit anomaly consumer (ASP-379 detector wiring).

Hermetic tests for ``sentinel.tool_anomaly_consumer``. Never touches a live
broker: NATS is mocked, journals are ``tmp_path``. Asserts the wiring feeds the
detector, journals findings, publishes to the findings subject with an
idempotency header, and stays fail-open on bad input and publish failures.
"""
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_PYTHON = REPO_ROOT / "src" / "python"
sys.path.insert(0, str(SRC_PYTHON))

from sentinel.audit import SUBJECT_AUDIT_EVENT
from sentinel.tool_anomaly_consumer import (
    SUBJECT_TOOL_ANOMALY,
    ToolAnomalyConsumer,
)

# Fixed epoch base for deterministic windows (2026-09-20T00:00:00Z)
BASE_TS = 1789948800.0


def _event(actor: str, action: str, target: str = "", result: str = "ok",
           ts: float = BASE_TS) -> dict:
    return {
        "event_id": f"{actor}-{action}-{ts}".replace("/", "_"),
        "actor": actor,
        "action": action,
        "target": target,
        "result": result,
        "ts": ts,
    }


def _sensitive_then_egress(actor: str = "proxy") -> list:
    return [
        _event(actor, "tool.read_file", target="/etc/shadow", ts=BASE_TS),
        _event(actor, "tool.http_post", target="https://c2.example.invalid/x",
               ts=BASE_TS + 2),
    ]


def _consumer(tmp_path, **kwargs) -> ToolAnomalyConsumer:
    kwargs.setdefault("audit_log", str(tmp_path / "sentinel" / "audit.jsonl"))
    kwargs.setdefault("anomaly_log", str(tmp_path / "sentinel" / "tool-anomaly.jsonl"))
    return ToolAnomalyConsumer(**kwargs)


def _read_journal(consumer: ToolAnomalyConsumer) -> list:
    path = consumer.anomaly_log_path
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


# ---------------------------------------------------------------------------
# Detection -> emit
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_event_detects_and_journals(tmp_path):
    consumer = _consumer(tmp_path)
    emitted = []
    for event in _sensitive_then_egress():
        emitted.extend(await consumer.handle_event(event))

    r1 = [f for f in emitted if f["rule"] == "sensitive_read_then_egress"]
    assert len(r1) == 1
    assert r1[0]["severity"] == "high"
    assert consumer.findings_emitted == 1

    journal = _read_journal(consumer)
    assert len(journal) == 1
    assert journal[0]["rule"] == "sensitive_read_then_egress"


@pytest.mark.asyncio
async def test_benign_sequence_emits_nothing(tmp_path):
    consumer = _consumer(tmp_path)
    emitted = []
    for action, target in (
        ("tool.read_file", "/var/log/app.log"),
        ("tool.shell", "ls -la"),
        ("tool.search_files", "/var/log"),
    ):
        emitted.extend(await consumer.handle_event(_event("ops", action, target)))
    assert emitted == []
    assert _read_journal(consumer) == []


@pytest.mark.asyncio
async def test_fail_open_on_garbage(tmp_path):
    consumer = _consumer(tmp_path)
    for garbage in (None, "nope", 42, {"king": "midas"}, {}):
        emitted = await consumer.handle_event(garbage)  # must not raise
        assert emitted == []
    assert consumer.findings_emitted == 0


# ---------------------------------------------------------------------------
# Finding envelope
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_envelope_fields_and_paging_flag(tmp_path):
    consumer = _consumer(tmp_path)
    emitted = []
    for event in _sensitive_then_egress():
        emitted.extend(await consumer.handle_event(event))
    finding = emitted[0]
    assert set(finding) >= {
        "finding_id", "ts", "source", "notify", "rule", "severity",
        "actor", "message", "fail_open", "action_required",
    }
    assert finding["source"] == "sentinel.tool_anomaly_consumer"
    assert finding["fail_open"] is True
    assert finding["action_required"] == "investigate"
    assert finding["notify"] is True  # R1 is high -> page
    assert len(finding["finding_id"]) == 32


@pytest.mark.asyncio
async def test_medium_finding_not_paging(tmp_path):
    """R2 (medium) emits findings but does not set the paging flag."""
    consumer = _consumer(tmp_path)
    emitted = []
    for _ in range(6):  # burst_high_risk_min == 5, fires once at 5
        emitted.extend(await consumer.handle_event(
            _event("bot", "tool.shell", target="ls", ts=BASE_TS + _ * 1.0)
        ))
    r2 = [f for f in emitted if f["rule"] == "high_risk_burst"]
    assert len(r2) == 1
    assert r2[0]["severity"] == "medium"
    assert r2[0]["notify"] is False


# ---------------------------------------------------------------------------
# Subject resolution
# ---------------------------------------------------------------------------


def test_subject_default():
    consumer = ToolAnomalyConsumer(anomaly_log="/tmp/does-not-matter.jsonl")
    assert consumer.subject == SUBJECT_TOOL_ANOMALY
    assert consumer.subject == "aspen.sentinel.tools.anomaly"


def test_subject_env_override(monkeypatch, tmp_path):
    monkeypatch.setenv("ASPEN_TOOLS_ANOMALY_SUBJECT", "aspen.sentinel.custom.anomaly")
    consumer = _consumer(tmp_path)
    assert consumer.subject == "aspen.sentinel.custom.anomaly"


# ---------------------------------------------------------------------------
# NATS lifecycle (mocked)
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_nats():
    mock_mod = MagicMock()
    mock_conn = AsyncMock()
    mock_conn.is_connected = True
    mock_conn.drain = AsyncMock()
    mock_conn.close = AsyncMock()

    mock_js = MagicMock()
    mock_js.add_stream = AsyncMock()
    mock_js.publish = AsyncMock()
    # ASP-780: the consumer verifies (never creates) the operator's stream.
    stream_info = MagicMock()
    stream_info.config.subjects = ["aspen.sentinel.>"]
    mock_js.stream_info = AsyncMock(return_value=stream_info)
    mock_conn.jetstream = MagicMock(return_value=mock_js)

    mock_sub = MagicMock()
    mock_sub.unsubscribe = AsyncMock()
    mock_conn.subscribe = AsyncMock(return_value=mock_sub)

    mock_mod.connect = AsyncMock(return_value=mock_conn)
    return mock_mod, mock_conn, mock_js, mock_sub


@pytest.mark.asyncio
async def test_start_offline_no_url(tmp_path):
    consumer = _consumer(tmp_path)
    assert await consumer.start() is False
    assert consumer.is_online is False


@pytest.mark.asyncio
async def test_start_subscribes_to_audit_subject(tmp_path, mock_nats):
    mock_mod, mock_conn, _, _ = mock_nats
    consumer = _consumer(tmp_path, nats_url="nats://localhost:4222")
    with patch.dict("sys.modules", {"nats": mock_mod}):
        assert await consumer.start() is True
    assert consumer.is_online is True
    subjects = [c.args[0] for c in mock_conn.subscribe.call_args_list]
    assert SUBJECT_AUDIT_EVENT in subjects
    await consumer.close()


@pytest.mark.asyncio
async def test_live_message_feed_and_publish(tmp_path, mock_nats):
    mock_mod, mock_conn, mock_js, _ = mock_nats

    captured: dict = {}

    async def _capture_sub(subject, cb=None):
        captured[subject] = cb
        return MagicMock(unsubscribe=AsyncMock())

    mock_conn.subscribe = _capture_sub

    consumer = _consumer(tmp_path, nats_url="nats://localhost:4222")
    with patch.dict("sys.modules", {"nats": mock_mod}):
        await consumer.start()

    cb = captured[SUBJECT_AUDIT_EVENT]
    for event in _sensitive_then_egress():
        msg = MagicMock()
        msg.data = json.dumps(event).encode()
        await cb(msg)

    assert mock_js.publish.await_count == 1
    call = mock_js.publish.await_args
    assert call.args[0] == SUBJECT_TOOL_ANOMALY
    published = json.loads(call.args[1].decode())
    assert published["rule"] == "sensitive_read_then_egress"
    assert call.kwargs["headers"]["Nats-Msg-Id"] == published["finding_id"]
    assert _read_journal(consumer)[0]["finding_id"] == published["finding_id"]
    await consumer.close()


@pytest.mark.asyncio
async def test_invalid_json_message_ignored(tmp_path, mock_nats):
    mock_mod, mock_conn, mock_js, _ = mock_nats

    captured: dict = {}

    async def _capture_sub(subject, cb=None):
        captured[subject] = cb
        return MagicMock(unsubscribe=AsyncMock())

    mock_conn.subscribe = _capture_sub
    consumer = _consumer(tmp_path, nats_url="nats://localhost:4222")
    with patch.dict("sys.modules", {"nats": mock_mod}):
        await consumer.start()

    msg = MagicMock()
    msg.data = b"not-json"
    await captured[SUBJECT_AUDIT_EVENT](msg)  # must not raise
    assert mock_js.publish.await_count == 0
    assert consumer.findings_emitted == 0
    await consumer.close()


@pytest.mark.asyncio
async def test_publish_failure_still_journals(tmp_path, mock_nats):
    mock_mod, mock_conn, mock_js, _ = mock_nats
    mock_js.publish = AsyncMock(side_effect=RuntimeError("broker down"))

    consumer = _consumer(tmp_path, nats_url="nats://localhost:4222")
    with patch.dict("sys.modules", {"nats": mock_mod}):
        await consumer.start()

    emitted = []
    for event in _sensitive_then_egress():
        emitted.extend(await consumer.handle_event(event))

    assert len(emitted) == 1  # journal durable even when publish fails
    assert _read_journal(consumer)[0]["rule"] == "sensitive_read_then_egress"
    await consumer.close()


# ---------------------------------------------------------------------------
# Offline replay
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ingest_journal_replays_findings(tmp_path):
    audit = tmp_path / "sentinel" / "audit.jsonl"
    audit.parent.mkdir(parents=True, exist_ok=True)
    audit.write_text(
        "".join(json.dumps(e) + "\n" for e in _sensitive_then_egress()),
        encoding="utf-8",
    )
    consumer = _consumer(tmp_path, audit_log=str(audit))
    findings = await consumer.ingest_journal()
    assert [f["rule"] for f in findings] == ["sensitive_read_then_egress"]
    assert _read_journal(consumer)[0]["notify"] is True


@pytest.mark.asyncio
async def test_ingest_missing_journal_is_empty(tmp_path):
    consumer = _consumer(tmp_path)
    assert await consumer.ingest_journal() == []


def test_tail_reads_newest_first(tmp_path):
    consumer = _consumer(tmp_path)
    path = consumer.anomaly_log_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        '{"finding_id":"a","rule":"r1"}\n{"finding_id":"b","rule":"r2"}\n',
        encoding="utf-8",
    )
    tail = consumer.tail(5)
    assert [t["finding_id"] for t in tail] == ["b", "a"]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def test_cli_watch_once_replays_journal(tmp_path):
    audit = tmp_path / "audit.jsonl"
    audit.write_text(
        "".join(json.dumps(e) + "\n" for e in _sensitive_then_egress()),
        encoding="utf-8",
    )
    anomaly = tmp_path / "tool-anomaly.jsonl"
    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "tool-anomaly.py"),
         "watch", "--once", "--journal", str(audit),
         "--anomaly-log", str(anomaly)],
        capture_output=True, text=True, timeout=60, check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert "sensitive_read_then_egress" in proc.stdout
    assert "PAGE" in proc.stdout
    assert anomaly.exists()


# ---------------------------------------------------------------------------
# ASP-780 hardening (PR #76 follow-ups)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_start_does_not_create_stream(tmp_path, mock_nats):
    """Item 2: production consumer checks the stream; it never add_stream()s."""
    mock_mod, _, mock_js, _ = mock_nats
    consumer = _consumer(tmp_path, nats_url="nats://localhost:4222")
    with patch.dict("sys.modules", {"nats": mock_mod}):
        assert await consumer.start() is True
    mock_js.stream_info.assert_awaited()
    mock_js.add_stream.assert_not_awaited()
    assert consumer.stream_ok is True
    await consumer.close()


@pytest.mark.asyncio
async def test_missing_stream_is_loud_and_journal_only(tmp_path, mock_nats, caplog):
    mock_mod, _, mock_js, _ = mock_nats
    mock_js.stream_info = AsyncMock(side_effect=RuntimeError("stream not found"))
    consumer = _consumer(tmp_path, nats_url="nats://localhost:4222")
    with caplog.at_level("ERROR", logger="sentinel.tool_anomaly_consumer"), \
            patch.dict("sys.modules", {"nats": mock_mod}):
        assert await consumer.start() is True
    assert consumer.stream_ok is False
    assert any("not found" in r.getMessage() for r in caplog.records
               if r.levelname == "ERROR")
    for event in _sensitive_then_egress():
        await consumer.handle_event(event)
    mock_js.publish.assert_not_awaited()  # journal-only
    mock_js.add_stream.assert_not_awaited()
    assert len(_read_journal(consumer)) == 1
    await consumer.close()


@pytest.mark.asyncio
async def test_stream_not_binding_subject_is_journal_only(tmp_path, mock_nats):
    mock_mod, _, mock_js, _ = mock_nats
    info = MagicMock()
    info.config.subjects = ["aspen.other.>"]
    mock_js.stream_info = AsyncMock(return_value=info)
    consumer = _consumer(tmp_path, nats_url="nats://localhost:4222")
    with patch.dict("sys.modules", {"nats": mock_mod}):
        await consumer.start()
    assert consumer.stream_ok is False
    await consumer.close()


@pytest.mark.asyncio
async def test_create_stream_opt_in_for_dev(tmp_path, mock_nats):
    mock_mod, _, mock_js, _ = mock_nats
    mock_js.stream_info = AsyncMock(side_effect=RuntimeError("stream not found"))
    consumer = _consumer(tmp_path, nats_url="nats://localhost:4222",
                         create_stream=True)
    with patch.dict("sys.modules", {"nats": mock_mod}):
        await consumer.start()
    mock_js.add_stream.assert_awaited_once()
    assert consumer.stream_ok is True
    await consumer.close()


def test_connect_options_reuse_shared_helper(monkeypatch):
    """Item 1: env creds + TLS flow through agents/nats_connect.py."""
    from sentinel.tool_anomaly_consumer import nats_connect_options

    monkeypatch.setenv("NATS_USER", "sentinel")
    monkeypatch.setenv("NATS_PASSWORD", "s3cret")
    monkeypatch.setenv("STARSHIP_NATS_TLS", "1")
    monkeypatch.delenv("STARSHIP_NATS_CA", raising=False)
    monkeypatch.delenv("STARSHIP_NATS_NKEY_SEED", raising=False)
    monkeypatch.delenv("STARSHIP_NATS_NKEY_SEED_FILE", raising=False)
    url, kwargs, redacted = nats_connect_options("nats://bus.example:4222")
    assert url == "tls://sentinel:s3cret@bus.example:4222"
    assert kwargs.get("tls") is not None
    assert "s3cret" not in redacted


def test_connect_options_creds_file(monkeypatch, tmp_path):
    from sentinel.tool_anomaly_consumer import nats_connect_options

    for var in ("NATS_USER", "NATS_PASSWORD", "STARSHIP_NATS_TOKEN",
                "STARSHIP_NATS_TLS", "STARSHIP_NATS_NKEY_SEED",
                "STARSHIP_NATS_NKEY_SEED_FILE"):
        monkeypatch.delenv(var, raising=False)
    creds = tmp_path / "sentinel.creds"
    creds.write_text("placeholder")
    monkeypatch.setenv("ASPEN_NATS_CREDS", str(creds))
    _, kwargs, _ = nats_connect_options("nats://127.0.0.1:4222")
    assert kwargs["user_credentials"] == str(creds)


@pytest.mark.asyncio
async def test_journal_fsync_runs_off_event_loop(tmp_path):
    """Item 3: the blocking append+fsync happens in a worker thread."""
    import threading

    consumer = _consumer(tmp_path)
    loop_thread = threading.get_ident()
    seen = []
    real = consumer._append_journal

    def _spy(payload):
        seen.append(threading.get_ident())
        real(payload)

    consumer._append_journal = _spy
    for event in _sensitive_then_egress():
        await consumer.handle_event(event)
    assert seen and all(t != loop_thread for t in seen)


@pytest.mark.asyncio
async def test_journal_oserror_still_publishes(tmp_path, mock_nats):
    """Item 6: a failed journal write no longer skips the JetStream publish."""
    mock_mod, _, mock_js, _ = mock_nats
    consumer = _consumer(tmp_path, nats_url="nats://localhost:4222")
    with patch.dict("sys.modules", {"nats": mock_mod}):
        await consumer.start()

    def _boom(payload):
        raise OSError("disk full")

    consumer._append_journal = _boom
    emitted = []
    for event in _sensitive_then_egress():
        emitted.extend(await consumer.handle_event(event))
    assert len(emitted) == 1
    assert mock_js.publish.await_count == 1
    await consumer.close()


def test_finding_id_is_deterministic():
    """Item 5: same rule/actor/events -> same id, independent of event order."""
    from sentinel.tool_anomaly import Finding
    from sentinel.tool_anomaly_consumer import finding_id_for

    a, b = _sensitive_then_egress()
    f1 = Finding(rule="sensitive_read_then_egress", severity="high",
                 actor="proxy", message="m", window_s=120, events=[a, b])
    f2 = Finding(rule="sensitive_read_then_egress", severity="high",
                 actor="proxy", message="other text", window_s=120, events=[b, a])
    f3 = Finding(rule="sensitive_read_then_egress", severity="high",
                 actor="other", message="m", window_s=120, events=[a, b])
    assert finding_id_for(f1) == finding_id_for(f2)
    assert finding_id_for(f1) != finding_id_for(f3)
    assert len(finding_id_for(f1)) == 32


@pytest.mark.asyncio
async def test_replay_dedupes_findings(tmp_path):
    """Item 5: replaying the same journal does not re-emit/re-page."""
    audit = tmp_path / "sentinel" / "audit.jsonl"
    audit.parent.mkdir(parents=True, exist_ok=True)
    audit.write_text(
        "".join(json.dumps(e) + "\n" for e in _sensitive_then_egress()),
        encoding="utf-8",
    )
    first = await _consumer(tmp_path, audit_log=str(audit)).ingest_journal()
    assert len(first) == 1
    # Fresh process (new consumer + detector) over the same journals.
    second = await _consumer(tmp_path, audit_log=str(audit)).ingest_journal()
    assert second == []
    assert len(_read_journal(_consumer(tmp_path))) == 1


@pytest.mark.asyncio
async def test_repeated_r1_hit_not_reemitted(tmp_path):
    """R1 re-evaluates on every event in the window; same pair = one finding."""
    consumer = _consumer(tmp_path)
    emitted = []
    events = _sensitive_then_egress() + [
        _event("proxy", "tool.list_dir", target="/tmp", ts=BASE_TS + 3),
    ]
    for event in events:
        emitted.extend(await consumer.handle_event(event))
    assert [f["rule"] for f in emitted] == ["sensitive_read_then_egress"]


def test_tail_bounded_and_skips_garbage(tmp_path):
    consumer = _consumer(tmp_path)
    path = consumer.anomaly_log_path
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps({"finding_id": str(i)}) for i in range(1000)]
    lines.insert(500, "not json")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert [t["finding_id"] for t in consumer.tail(3)] == ["999", "998", "997"]
    assert consumer.tail(0) == []


def test_unused_env_int_helper_removed():
    import sentinel.tool_anomaly_consumer as mod

    assert not hasattr(mod, "_env_int")
