import json
import os
import sys
import threading
import importlib.util
from http.client import HTTPConnection
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "services"))

_spec = importlib.util.spec_from_file_location(
    "memory_api", PROJECT_ROOT / "services" / "memory-api.py"
)
memory_api = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(memory_api)  # noqa: E402


@pytest.fixture
def server(tmp_path):
    db = tmp_path / "api_test.db"
    old_db = os.environ.get("ABS_MEMORY_DB")
    old_port = os.environ.get("PORT")
    os.environ["ABS_MEMORY_DB"] = str(db)
    os.environ["PORT"] = "18099"

    from http.server import HTTPServer

    httpd = HTTPServer(("127.0.0.1", 18099), memory_api.MemoryAPIHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    yield

    httpd.shutdown()
    httpd.server_close()
    thread.join(timeout=5)
    if old_db is None:
        os.environ.pop("ABS_MEMORY_DB", None)
    else:
        os.environ["ABS_MEMORY_DB"] = old_db
    if old_port is None:
        os.environ.pop("PORT", None)
    else:
        os.environ["PORT"] = old_port


def _request(method, path, body=None):
    conn = HTTPConnection("127.0.0.1", 18099, timeout=10)
    raw = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"} if body is not None else {}
    conn.request(method, path, body=raw, headers=headers)
    resp = conn.getresponse()
    payload = resp.read().decode()
    conn.close()
    return resp.status, json.loads(payload) if payload else None


def test_health(server):
    status, data = _request("GET", "/api/health")
    assert status == 200
    assert data["status"] == "ok"


def test_store_then_search_round_trip(server):
    status, data = _request(
        "POST",
        "/api/memory/store",
        {"agent": "agent-a", "type": "episodic", "content": "CI runs on GitHub Actions"},
    )
    assert status == 201
    mid = data["id"]
    assert mid

    status, data = _request("GET", "/api/memory/search?q=CI+build&agent=agent-a")
    assert status == 200
    results = data["results"]
    assert any(r["id"] == mid for r in results)


def test_search_returns_serializable_dicts(server):
    _request(
        "POST",
        "/api/memory/store",
        {"agent": "agent-a", "type": "semantic", "content": "Embeddings are vectors"},
    )
    status, data = _request("GET", "/api/memory/search?q=embeddings&agent=agent-a")
    assert status == 200
    for r in data["results"]:
        assert "id" in r and "content" in r and "type" in r


def test_recall_returns_serializable_dict(server):
    _, store = _request(
        "POST",
        "/api/memory/store",
        {"agent": "agent-a", "type": "decision", "content": "Decision: keep SQLite fallback"},
    )
    status, data = _request("GET", f"/api/memory/recall/{store['id']}")
    assert status == 200
    assert data["content"].startswith("Decision:")


def test_store_invalid_type_returns_400(server):
    status, data = _request(
        "POST",
        "/api/memory/store",
        {"agent": "agent-a", "type": "bogus", "content": "x"},
    )
    assert status == 400
    assert "Invalid memory type" in data["error"]


def test_search_invalid_type_returns_400(server):
    status, data = _request("GET", "/api/memory/search?q=x&type=bogus")
    assert status == 400
    assert "Invalid memory type" in data["error"]


def test_forget_and_recall_404(server):
    _, store = _request(
        "POST",
        "/api/memory/store",
        {"agent": "agent-a", "type": "episodic", "content": "Temporary fact"},
    )
    status, data = _request("DELETE", f"/api/memory/forget/{store['id']}")
    assert status == 200
    assert data["deleted"] is True

    status, _ = _request("GET", f"/api/memory/recall/{store['id']}")
    assert status == 404


def test_unknown_route_404(server):
    status, _ = _request("GET", "/api/nope")
    assert status == 404
