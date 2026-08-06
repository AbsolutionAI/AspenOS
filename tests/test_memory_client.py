import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "memory_pkg"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "services"))

from aspen_memory import MemoryClient  # noqa: E402


@pytest.fixture
def client(tmp_path):
    db = tmp_path / "client_test.db"
    c = MemoryClient(str(db))
    yield c
    c.close()


def test_add_fact_round_trips_via_search(client):
    mid = client.add_fact(
        type="decision",
        content="Decision: use DeepSeek V4-Flash for all ABS agents",
        tags=["model-routing", "fiscal-freeze"],
        linear_refs=["BEL-154"],
        paperclip_refs=["ABS-10"],
        confidence=0.95,
    )
    assert mid

    hits = client.search("DeepSeek V4-Flash", k=5, min_confidence=0.0)
    assert any(h["id"] == mid for h in hits)


def test_get_by_linear(client):
    client.add_fact(
        type="decision",
        content="Decision: UFW hardening baseline",
        linear_refs=["BEL-114"],
        paperclip_refs=["ABS-9"],
        confidence=0.9,
    )
    client.add_fact(
        type="semantic",
        content="Fact about embeddings",
        tags=["memory"],
        confidence=0.8,
    )

    hits = client.get_by_linear("BEL-114")
    assert len(hits) == 1
    assert hits[0]["metadata"]["linear_refs"] == ["BEL-114"]

    assert client.get_by_linear("NOPE-999") == []


def test_get_by_paperclip(client):
    client.add_fact(
        type="decision",
        content="Decision: use LanceDB for vectors",
        linear_refs=["BEL-153"],
        paperclip_refs=["ABS-7"],
        confidence=0.9,
    )
    hits = client.get_by_paperclip("ABS-7")
    assert len(hits) == 1
    assert hits[0]["metadata"]["paperclip_refs"] == ["ABS-7"]

    assert client.get_by_paperclip("ABS-12345") == []


def test_get_by_tags_match_all(client):
    client.add_fact(
        type="semantic",
        content="Security auditor baseline",
        tags=["security", "ufw"],
        confidence=0.85,
    )
    client.add_fact(
        type="semantic",
        content="Model routing table",
        tags=["model-routing"],
        confidence=0.8,
    )

    both = client.get_by_tags(["security", "ufw"])
    assert len(both) == 1
    assert both[0]["content"].startswith("Security")

    partial = client.get_by_tags(["security", "missing"])
    assert partial == []


def test_client_context_manager(tmp_path):
    db = tmp_path / "cm_test.db"
    with MemoryClient(str(db)) as c:
        mid = c.add_fact(
            type="decision",
            content="Decision: promote >=0.7 facts",
            tags=["memory", "promotion"],
            linear_refs=["BEL-154"],
            confidence=0.95,
        )
        assert mid


def test_memory_manager_get_by_metadata_match_all_false(tmp_path):
    from memory import MemoryManager, MemoryType  # noqa: E402

    mgr = MemoryManager(str(tmp_path / "meta.db"))
    try:
        mgr.store(
            "agent-a",
            MemoryType.SEMANTIC,
            "One tag fact",
            metadata={"tags": ["alpha"], "linear_refs": ["BEL-1"]},
        )
        mgr.store(
            "agent-a",
            MemoryType.SEMANTIC,
            "Two tag fact",
            metadata={"tags": ["alpha", "beta"], "linear_refs": ["BEL-2"]},
        )
        any_hit = mgr.get_by_metadata("tags", ["beta"])
        assert len(any_hit) == 1
        all_hit = mgr.get_by_metadata("tags", ["alpha", "beta"], match_all=True)
        assert len(all_hit) == 1
        none_hit = mgr.get_by_metadata("tags", [])
        assert none_hit == []
    finally:
        mgr.close()
