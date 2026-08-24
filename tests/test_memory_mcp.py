"""ASP-56 — BEL-154 MCP server tests.

Verifies the ``aspen-memory-mcp`` server exposes the five design-doc tools and
that they operate on the canonical ``MemoryClient`` store (no parallel store).
"""

import asyncio
import json
import sys
from pathlib import Path

import pytest

pytest.importorskip("mcp.server", reason="mcp SDK not installed (pip install 'mcp>=1.0')")

REPO_ROOT = Path(__file__).resolve().parent.parent
MCP_SRC = REPO_ROOT / "mcp" / "aspen-memory-mcp" / "src"
if str(MCP_SRC) not in sys.path:
    sys.path.insert(0, str(MCP_SRC))

from aspen_memory_mcp.server import _valid_types, build_server  # noqa: E402

EXPECTED_TOOLS = {
    "memory_search",
    "memory_get_by_linear",
    "memory_get_by_paperclip",
    "memory_get_by_tags",
    "memory_add_fact",
}


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture
def server(tmp_path):
    return build_server(str(tmp_path / "mcp-test.db"))


@pytest.fixture
def tools(server):
    return _run(server.list_tools())


def test_tool_list_has_design_doc_tools(tools):
    names = {t.name for t in tools}
    assert EXPECTED_TOOLS <= names


def test_add_fact_roundtrip_via_linear(server):
    result = _run(
        server.call_tool(
            "memory_add_fact",
            {
                "type": "decision",
                "content": "Use DeepSeek V4-Flash for ABS agents",
                "tags": ["model-routing"],
                "linear_refs": ["BEL-154"],
                "confidence": 0.95,
            },
        )
    )
    mem_id = result.structured_content["result"]
    assert mem_id

    found = _run(
        server.call_tool("memory_get_by_linear", {"linear_id": "BEL-154"})
    )
    facts = json.loads(found.structured_content["result"])
    assert len(facts) == 1
    assert facts[0]["id"] == mem_id
    assert facts[0]["type"] == "decision"


def test_get_by_tags_match_all_semantics(server):
    _run(
        server.call_tool(
            "memory_add_fact",
            {
                "type": "semantic",
                "content": "UFW hardened on all nodes",
                "tags": ["security", "ufw"],
                "confidence": 0.9,
            },
        )
    )
    _run(
        server.call_tool(
            "memory_add_fact",
            {
                "type": "semantic",
                "content": "Port 22 policy",
                "tags": ["security"],
                "confidence": 0.8,
            },
        )
    )

    found = _run(
        server.call_tool("memory_get_by_tags", {"tags": ["security", "ufw"]})
    )
    facts = json.loads(found.structured_content["result"])
    assert len(facts) == 1
    assert facts[0]["content"].startswith("UFW")


def test_get_by_paperclip_unknown_returns_empty(server):
    found = _run(
        server.call_tool(
            "memory_get_by_paperclip", {"paperclip_id": "ABS-999"}
        )
    )
    assert json.loads(found.structured_content["result"]) == []


def test_search_finds_added_fact(server):
    _run(
        server.call_tool(
            "memory_add_fact",
            {
                "type": "semantic",
                "content": "NATS cluster uses JetStream persistence",
                "tags": ["nats"],
                "confidence": 0.9,
            },
        )
    )
    found = _run(
        server.call_tool(
            "memory_search", {"query": "JetStream", "k": 5, "min_confidence": 0.5}
        )
    )
    facts = json.loads(found.structured_content["result"])
    assert any("JetStream" in f["content"] for f in facts)


def test_invalid_type_returns_error_not_crash(server):
    result = _run(
        server.call_tool(
            "memory_add_fact", {"type": "bogus", "content": "x"}
        )
    )
    text = result.structured_content["result"]
    assert text.startswith("error: invalid type 'bogus'")
    assert all(t in text for t in _valid_types())


def test_server_uses_canonical_store(tmp_path):
    """A fact added via the tool must be visible to a fresh MemoryClient."""
    db = str(tmp_path / "canonical.db")

    from aspen_memory import MemoryClient

    server = build_server(db)
    _run(
        server.call_tool(
            "memory_add_fact",
            {
                "type": "decision",
                "content": "Canonical store round-trip",
                "paperclip_refs": ["ABS-10"],
                "confidence": 0.95,
            },
        )
    )

    with MemoryClient(db) as client:
        facts = client.get_by_paperclip("ABS-10")
    assert len(facts) == 1
    assert facts[0]["content"] == "Canonical store round-trip"
