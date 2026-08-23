"""ASP-98: ProspectiveMemoryManager on canonical services/memory.py."""

from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from services.memory import (
    MEMORY_DESCRIPTIONS,
    MemoryType,
    ProspectiveMemoryManager,
    get_memory_manager,
    get_prospective_memory,
)


class ProspectiveMemoryTests(unittest.TestCase):
    def setUp(self) -> None:
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.mgr = get_memory_manager(self.db_path)
        self.pm = ProspectiveMemoryManager(self.mgr)

    def tearDown(self) -> None:
        self.mgr.close()
        try:
            os.unlink(self.db_path)
        except OSError:
            pass

    def test_exports(self) -> None:
        self.assertEqual(MemoryType.PROSPECTIVE.value, "prospective")
        self.assertIn(MemoryType.PROSPECTIVE, MEMORY_DESCRIPTIONS)
        self.assertIsInstance(get_prospective_memory(self.mgr), ProspectiveMemoryManager)

    def test_intention_lifecycle(self) -> None:
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        future = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()

        a = self.pm.create_intention(
            "aspen", "ship ASP-98", due_at=past, priority=0.9, goal_id="ASP-98"
        )
        b = self.pm.create_intention("aspen", "later task", due_at=future, priority=0.4)

        pending = self.pm.get_pending(agent="aspen")
        self.assertEqual(len(pending), 2)

        overdue = self.pm.get_overdue(agent="aspen")
        self.assertEqual(len(overdue), 1)
        self.assertEqual(overdue[0].id, a["id"])

        upcoming = self.pm.get_upcoming(horizon_hours=3, agent="aspen")
        self.assertEqual({m.id for m in upcoming}, {a["id"], b["id"]})

        self.assertTrue(self.pm.defer(b["id"], future))
        deferred = self.mgr.prospective_search(agent="aspen", status="deferred")
        self.assertEqual(len(deferred), 1)
        self.assertEqual(deferred[0].id, b["id"])

        self.assertTrue(self.pm.complete(a["id"], outcome="landed"))
        self.assertFalse(any(m.id == a["id"] for m in self.pm.get_pending()))


if __name__ == "__main__":
    unittest.main()
