import sys
import json
import pytest

pytest.importorskip("aiohttp", reason="aiohttp package not installed")

from aiohttp import web
from unittest.mock import patch, AsyncMock, MagicMock

import server as srv


@pytest.fixture
def mock_gpu_state(tmp_path, monkeypatch):
    gpu_file = tmp_path / "gpu-state.json"
    gpu_file.write_text(json.dumps({"vendor": "nvidia", "model": "RTX 4090"}))
    monkeypatch.setattr(srv, "GPU_STATE", gpu_file)
    return gpu_file


@pytest.fixture
def mock_status_file(tmp_path, monkeypatch):
    status_file = tmp_path / "status.json"
    status_file.write_text(json.dumps({
        "agents": {"proxy": {"status": "online"}},
        "telemetry": {"cpu": 45.2, "mem_used": 4096000000, "mem_total": 8192000000},
        "messages": [],
    }))
    monkeypatch.setattr(srv, "STATUS_FILE", status_file)
    return status_file


def create_app():
    app = web.Application()
    app.router.add_get("/api/health", srv.handle_health)
    app.router.add_post("/api/send", srv.handle_send)
    app.router.add_get("/api/ollama/models", srv.handle_api_ollama_models)
    app.router.add_get("/api/logs/search", srv.handle_log_search)
    app.router.add_get("/api/dashboard", srv.handle_api_dashboard)
    return app


@pytest.mark.asyncio
async def test_health_endpoint(aiohttp_client, mock_gpu_state, mock_status_file, monkeypatch):
    monkeypatch.setattr(srv, "nc", None)

    async def mock_get_nats():
        mock = AsyncMock()
        mock.is_connected = False
        return mock

    monkeypatch.setattr(srv, "get_nats", mock_get_nats)

    app = create_app()
    client = await aiohttp_client(app)
    resp = await client.get("/api/health")
    assert resp.status == 200
    data = await resp.json()
    assert data["status"] == "degraded"
    assert "timestamp" in data
    assert "agents_running" in data


@pytest.mark.asyncio
async def test_send_endpoint(aiohttp_client, mock_gpu_state, mock_status_file, monkeypatch):
    async def mock_get_nats():
        mock_nc = AsyncMock()
        mock_nc.is_connected = True
        mock_nc.publish = AsyncMock()
        sub = AsyncMock()
        msg = MagicMock()
        msg.data = json.dumps({"agent": "proxy", "response": "pong"}).encode()
        sub.next_msg = AsyncMock(return_value=msg)
        mock_nc.subscribe = AsyncMock(return_value=sub)
        return mock_nc

    monkeypatch.setattr(srv, "get_nats", mock_get_nats)

    app = create_app()
    client = await aiohttp_client(app)
    resp = await client.post("/api/send", json={
        "agent": "proxy",
        "command": "ping",
        "args": {},
    })
    assert resp.status == 200
    data = await resp.json()
    assert data["agent"] == "proxy"
    assert data["response"] == "pong"


@pytest.mark.asyncio
async def test_ollama_models_endpoint(aiohttp_client, mock_gpu_state, mock_status_file, monkeypatch):
    async def mock_get_ollama_models():
        return [{"name": "qwen2.5:7b", "size": 4700000000}]

    monkeypatch.setattr(srv, "get_ollama_models", mock_get_ollama_models)

    app = create_app()
    client = await aiohttp_client(app)
    resp = await client.get("/api/ollama/models")
    assert resp.status == 200
    data = await resp.json()
    assert "models" in data
    assert len(data["models"]) == 1
    assert data["models"][0]["name"] == "qwen2.5:7b"


@pytest.mark.asyncio
async def test_logs_search_endpoint(aiohttp_client, mock_gpu_state, mock_status_file, monkeypatch):
    class FakeLogAgg:
        @staticmethod
        def search(**kwargs):
            return [{"message": "test log entry", "level": "INFO", "source": "proxy"}]

    monkeypatch.setitem(sys.modules, "log_aggregator", FakeLogAgg())

    app = create_app()
    client = await aiohttp_client(app)
    resp = await client.get("/api/logs/search?q=error&source=proxy")
    assert resp.status == 200
    data = await resp.json()
    assert "results" in data
    assert "total" in data



