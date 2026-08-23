"""ASP-98 — ProspectiveMemoryManager on canonical services/memory.py."""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "services"))

from memory import (  # noqa: E402
    MEMORY_DESCRIPTIONS,
    MemoryManager,
    MemoryType,
    ProspectiveMemoryManager,
    get_memory_manager,
    get_prospective_memory,
)


@pytest.fixture
def mgr(tmp_path):
    m = MemoryManager(str(tmp_path / "prospective.db"))
    yield m
    m.close()


@pytest.fixture
def pm(mgr):
    return ProspectiveMemoryManager(mgr)


def test_exports_exist():
    assert ProspectiveMemoryManager is not None
    assert callable(get_memory_manager)
    assert callable(get_prospective_memory)
    assert MemoryType.PROSPECTIVE.value == "prospective"
    assert MemoryType.PROSPECTIVE in MEMORY_DESCRIPTIONS


def test_stresstest_type_names_present():
    names = {t.value for t in MemoryType}
    for required in (
        "working",
        "semantic",
        "episodic",
        "procedural",
        "retrieval",
        "parametric",
        "prospective",
    ):
        assert required in names


def test_create_list_complete_sync(pm, mgr):
    created = pm.create_intention_sync(
        "aspen",
        "Ship ASP-98 prospective memory",
        due_at=(datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(),
        priority=0.9,
        goal_id="ASP-98",
    )
    assert created["id"]
    assert created["status"] == "pending"

    pending = pm.get_pending_sync(agent="aspen")
    assert any(m.id == created["id"] for m in pending)
    mem = next(m for m in pending if m.id == created["id"])
    assert mem.type == MemoryType.PROSPECTIVE
    assert mem.status == "pending"
    assert mem.due_at
    assert mem.to_dict()["status"] == "pending"

    listed = mgr.prospective_search(status="pending", agent="aspen")
    assert any(m.id == created["id"] for m in listed)

    assert pm.complete_sync(created["id"], outcome="done") is True
    assert pm.get_pending_sync(agent="aspen") == []


def test_overdue_and_upcoming_and_defer(pm):
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    near = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    far = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()

    overdue_id = pm.create_intention_sync("r", "overdue task", due_at=past)["id"]
    upcoming_id = pm.create_intention_sync("r", "soon task", due_at=near)["id"]
    later_id = pm.create_intention_sync("r", "later task", due_at=far)["id"]

    overdue = pm.get_overdue_sync(agent="r")
    assert {m.id for m in overdue} == {overdue_id}

    upcoming = pm.get_upcoming_sync(horizon_hours=24, agent="r")
    ids = {m.id for m in upcoming}
    assert overdue_id in ids
    assert upcoming_id in ids
    assert later_id not in ids

    assert pm.defer_sync(upcoming_id, far) is True
    deferred = [
        m
        for m in pm.mem.prospective_search(status="deferred", agent="r")
        if m.id == upcoming_id
    ]
    assert len(deferred) == 1
    assert deferred[0].due_at == far


def test_async_surface_matches_tools(pm):
    async def _run():
        created = await pm.create_intention(
            "daemon", "async intention", due_at=None, priority=0.4
        )
        pending = await pm.get_pending(agent="daemon")
        assert any(m.id == created["id"] for m in pending)
        ok = await pm.complete(created["id"], outcome="ok")
        assert ok is True

    asyncio.run(_run())


def test_schema_migration_adds_columns(tmp_path):
    """Existing DBs without due_at/status still open and gain columns."""
    import sqlite3

    db = tmp_path / "legacy.db"
    conn = sqlite3.connect(db)
    conn.executescript(
        """
        CREATE TABLE memories (
            id TEXT PRIMARY KEY,
            agent TEXT NOT NULL,
            type TEXT NOT NULL,
            content TEXT NOT NULL,
            summary TEXT NOT NULL,
            embedding TEXT,
            metadata TEXT,
            importance REAL DEFAULT 0.5,
            created_at TEXT NOT NULL,
            accessed_at TEXT NOT NULL,
            access_count INTEGER DEFAULT 0,
            decay REAL DEFAULT 1.0
        );
        """
    )
    conn.commit()
    conn.close()

    mgr = MemoryManager(str(db))
    try:
        cols = {r[1] for r in mgr.db.execute("PRAGMA table_info(memories)").fetchall()}
        assert "due_at" in cols
        assert "status" in cols
        mid = mgr.store(
            "a",
            MemoryType.PROSPECTIVE,
            "migrated intention",
            due_at="2099-01-01T00:00:00+00:00",
            status="pending",
        )
        row = mgr.db.execute("SELECT due_at, status FROM memories WHERE id=?", (mid,)).fetchone()
        assert row["due_at"].startswith("2099")
        assert row["status"] == "pending"
    finally:
        mgr.close()
