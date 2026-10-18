"""ASP-780: tool-anomaly consumer against a real nats-server (TLS + creds).

The hermetic suite (``test_tool_anomaly_consumer.py``) mocks NATS, which is how
the PR #76 connection/stream/slow-consumer issues slipped past CI. This module
spins up a throwaway ``nats-server`` with JetStream, TLS (self-signed CA) and
user/password auth, then checks:

* the consumer connects only through the shared TLS/creds helper,
* it uses a **pre-existing** operator stream and never changes its settings,
* a burst of audit events is processed without the subscription being dropped
  as a slow consumer,
* replaying the same events does not publish duplicate findings (in-process
  seen-set *and* JetStream ``Nats-Msg-Id`` dedupe).

Skips cleanly when ``nats-server``, ``nats-py`` or ``openssl`` is unavailable,
so the default CI suite (pytest + pytest-asyncio only) is unaffected.
"""
import asyncio
import json
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "python"))

nats = pytest.importorskip("nats")
if not hasattr(nats, "connect"):  # repo-local ``nats/`` config dir, not nats-py
    pytest.skip("nats-py not installed", allow_module_level=True)

NATS_SERVER = os.environ.get("NATS_SERVER_BIN") or shutil.which("nats-server")
OPENSSL = shutil.which("openssl")
pytestmark = pytest.mark.skipif(
    not (NATS_SERVER and OPENSSL),
    reason="needs nats-server and openssl on PATH (or NATS_SERVER_BIN)",
)

from sentinel.audit import SUBJECT_AUDIT_EVENT  # noqa: E402
from sentinel.tool_anomaly_consumer import (  # noqa: E402
    SUBJECT_TOOL_ANOMALY,
    ToolAnomalyConsumer,
)

USER, PASSWORD = "sentinel", "test-only-password"
STREAM = "ASPEN_SENTINEL"
BASE_TS = 1789948800.0


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _openssl(*args, cwd):
    subprocess.run([OPENSSL, *args], cwd=cwd, check=True, capture_output=True)


def _make_certs(d: Path) -> dict:
    _openssl("req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1",
             "-keyout", "ca.key", "-out", "ca.pem", "-subj", "/CN=aspen-test-ca",
             "-addext", "basicConstraints=critical,CA:TRUE",
             "-addext", "keyUsage=critical,keyCertSign,cRLSign",
             cwd=d)
    # Python 3.13 enables VERIFY_X509_STRICT: leaf needs SAN, key usage, AKI.
    (d / "san.cnf").write_text(
        "subjectAltName=DNS:localhost,IP:127.0.0.1\n"
        "keyUsage=critical,digitalSignature,keyEncipherment\n"
        "extendedKeyUsage=serverAuth\n"
        "authorityKeyIdentifier=keyid\n"
        "subjectKeyIdentifier=hash\n"
    )
    _openssl("req", "-newkey", "rsa:2048", "-nodes", "-keyout", "server.key",
             "-out", "server.csr", "-subj", "/CN=localhost", cwd=d)
    _openssl("x509", "-req", "-in", "server.csr", "-CA", "ca.pem", "-CAkey",
             "ca.key", "-CAcreateserial", "-out", "server.pem", "-days", "1",
             "-extfile", "san.cnf", cwd=d)
    return {k: str(d / v) for k, v in
            {"ca": "ca.pem", "cert": "server.pem", "key": "server.key"}.items()}


@pytest.fixture
def nats_tls_server(tmp_path, monkeypatch):
    certs = _make_certs(tmp_path)
    port = _free_port()
    conf = tmp_path / "nats.conf"
    conf.write_text(f"""
listen: 127.0.0.1:{port}
jetstream {{ store_dir: "{tmp_path / 'js'}" }}
tls {{
  cert_file: "{certs['cert']}"
  key_file: "{certs['key']}"
}}
authorization {{
  users = [ {{ user: "{USER}", password: "{PASSWORD}" }} ]
}}
""")
    proc = subprocess.Popen([NATS_SERVER, "-c", str(conf)],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
            break
        except OSError:
            time.sleep(0.1)
    else:  # pragma: no cover
        proc.kill()
        pytest.skip("nats-server did not start")
    # Credentials and TLS only via the env the shared helper reads.
    for var in ("STARSHIP_NATS_TOKEN", "STARSHIP_NATS_NKEY_SEED",
                "STARSHIP_NATS_NKEY_SEED_FILE", "ASPEN_NATS_CREDS",
                "STARSHIP_NATS_CERT", "STARSHIP_NATS_KEY"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("NATS_USER", USER)
    monkeypatch.setenv("NATS_PASSWORD", PASSWORD)
    monkeypatch.setenv("STARSHIP_NATS_TLS", "1")
    monkeypatch.setenv("STARSHIP_NATS_CA", certs["ca"])
    yield {"url": f"nats://127.0.0.1:{port}", "certs": certs, "port": port}
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:  # pragma: no cover
        proc.kill()


async def _admin(server):
    """Independent client (same TLS/creds) for provisioning and assertions."""
    import ssl

    ctx = ssl.create_default_context(cafile=server["certs"]["ca"])
    return await asyncio.wait_for(
        nats.connect(f"tls://127.0.0.1:{server['port']}", tls=ctx,
                     user=USER, password=PASSWORD, max_reconnect_attempts=1),
        timeout=10,
    )


def _r1_pair(actor="proxy", ts=BASE_TS):
    return [
        {"event_id": f"{actor}-read-{ts}", "actor": actor,
         "action": "tool.read_file", "target": "/etc/shadow", "result": "ok",
         "ts": ts},
        {"event_id": f"{actor}-post-{ts}", "actor": actor,
         "action": "tool.http_post", "target": "https://c2.example.invalid/x",
         "result": "ok", "ts": ts + 2},
    ]


async def _finding_count(js) -> int:
    info = await js.stream_info(STREAM, subjects_filter=SUBJECT_TOOL_ANOMALY)
    return sum((info.state.subjects or {}).values())


async def _wait_for(pred, timeout=10.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if await pred():
            return True
        await asyncio.sleep(0.05)
    return False


@pytest.mark.asyncio
async def test_plain_unauthenticated_connect_is_rejected(nats_tls_server, tmp_path,
                                                         monkeypatch):
    """Sanity: without the helper's creds/TLS the broker refuses us."""
    monkeypatch.delenv("NATS_USER")
    monkeypatch.delenv("NATS_PASSWORD")
    monkeypatch.delenv("STARSHIP_NATS_TLS")
    import sentinel.tool_anomaly_consumer as mod

    monkeypatch.setattr(mod, "_CONNECT_DEADLINE_S", 5.0)
    consumer = ToolAnomalyConsumer(nats_url=nats_tls_server["url"],
                                   anomaly_log=str(tmp_path / "a.jsonl"))
    assert await consumer.start() is False
    assert consumer.is_online is False


@pytest.mark.asyncio
async def test_live_tls_creds_preexisting_stream_burst_and_dedupe(
        nats_tls_server, tmp_path):
    admin = await _admin(nats_tls_server)
    js = admin.jetstream()
    # Operator-provisioned stream with *its own* retention settings.
    await js.add_stream(name=STREAM, subjects=["aspen.sentinel.>"],
                        storage="file", max_age=3600, duplicate_window=300)
    before = (await js.stream_info(STREAM)).config

    journal = tmp_path / "tool-anomaly.jsonl"
    consumer = ToolAnomalyConsumer(nats_url=nats_tls_server["url"],
                                   anomaly_log=str(journal))
    assert await consumer.start() is True
    assert consumer.is_online and consumer.stream_ok

    # Stream settings untouched by the consumer (no add_stream/update).
    after = (await js.stream_info(STREAM)).config
    assert after.max_age == before.max_age == 3600
    assert after.duplicate_window == before.duplicate_window

    # Burst: 3000 benign events across many actors + one R1 pair.
    for i in range(3000):
        await admin.publish(SUBJECT_AUDIT_EVENT, json.dumps({
            "event_id": f"b-{i}", "actor": f"bulk-{i % 300}",
            "action": "tool.list_dir", "target": "/tmp", "result": "ok",
            "ts": BASE_TS + i * 0.001,
        }).encode())
    for event in _r1_pair():
        await admin.publish(SUBJECT_AUDIT_EVENT, json.dumps(event).encode())
    await admin.flush()

    assert await _wait_for(lambda: _async_true(consumer.findings_emitted >= 1))
    assert await _wait_for(lambda: _finding_count_eq(js, 1))
    # Subscription survived the burst (no slow-consumer drop).
    assert consumer.is_online
    sub = consumer._subs[0]
    assert sub.pending_msgs == 0 or await _wait_for(
        lambda: _async_true(sub.pending_msgs == 0))

    # Replay the same R1 events: in-process dedupe -> no new finding.
    for event in _r1_pair():
        await admin.publish(SUBJECT_AUDIT_EVENT, json.dumps(event).encode())
    await admin.flush()
    await asyncio.sleep(0.5)
    assert consumer.findings_emitted == 1
    assert await _finding_count(js) == 1
    await consumer.close()

    # New process with an empty journal (no seen-set): JetStream Nats-Msg-Id
    # dedupe still collapses the identical finding.
    fresh = ToolAnomalyConsumer(nats_url=nats_tls_server["url"],
                                anomaly_log=str(tmp_path / "fresh.jsonl"))
    assert await fresh.start() is True
    for event in _r1_pair():
        await fresh.handle_event(event)
    assert fresh.findings_emitted == 1  # journaled locally
    await asyncio.sleep(0.3)
    assert await _finding_count(js) == 1  # but not re-published to the stream
    await fresh.close()

    lines = [json.loads(x) for x in journal.read_text().splitlines() if x.strip()]
    assert [x["rule"] for x in lines] == ["sensitive_read_then_egress"]
    await admin.close()


@pytest.mark.asyncio
async def test_live_missing_stream_runs_journal_only(nats_tls_server, tmp_path):
    consumer = ToolAnomalyConsumer(nats_url=nats_tls_server["url"],
                                   anomaly_log=str(tmp_path / "j.jsonl"))
    assert await consumer.start() is True
    assert consumer.stream_ok is False
    admin = await _admin(nats_tls_server)
    js = admin.jetstream()
    from nats.js.errors import NotFoundError

    with pytest.raises(NotFoundError):
        await js.stream_info(STREAM)  # consumer did not create it
    for event in _r1_pair():
        await consumer.handle_event(event)
    assert consumer.findings_emitted == 1
    await consumer.close()
    await admin.close()


async def _async_true(value):
    return bool(value)


async def _finding_count_eq(js, n):
    try:
        return await _finding_count(js) == n
    except Exception:  # noqa: BLE001 - stream may not exist yet while polling
        return False
