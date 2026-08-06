"""aspen_memory — BEL-154 access-layer Python library.

Thin wrapper over the canonical ``services.memory.MemoryManager`` (single
source of truth). No parallel store, no schema drift.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

# Make the canonical service importable whether the package is installed
# (editable) or run straight from the repo.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_SERVICES = _REPO_ROOT / "services"
if str(_SERVICES) not in sys.path:
    sys.path.insert(0, str(_SERVICES))

from memory import MemoryManager, MemoryType  # noqa: E402

DEFAULT_DB = os.environ.get("AGNETIC_MEMORY_DB", "/tmp/agnetic-data/memory.db")


class MemoryClient:
    """Access-layer client for the Starship OS long-term memory store.

    API matches the BEL-154 design doc Component 4.1. Can be used directly or
    as a context manager (the underlying ``MemoryManager`` is closed on exit).
    """

    def __init__(self, db_path: str | None = None):
        self._db_path = db_path or DEFAULT_DB
        self._manager = MemoryManager(self._db_path)

    # -- lifecycle ----------------------------------------------------------

    def close(self) -> None:
        """Close the underlying SQLite connection."""
        self._manager.close()

    def __enter__(self) -> "MemoryClient":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    # -- query --------------------------------------------------------------

    def search(
        self,
        query: str,
        k: int = 5,
        min_confidence: float = 0.7,
        agent: str | None = None,
    ) -> list[dict]:
        """Semantic search. Returns JSON-friendly memory dicts."""
        return self._manager.retrieve(
            query, agent=agent, limit=k, min_importance=min_confidence
        )

    def get_by_linear(self, linear_id: str) -> list[dict]:
        """Return memories referencing a Linear ticket id."""
        return self._manager.get_by_metadata("linear_refs", [linear_id])

    def get_by_paperclip(self, paperclip_id: str) -> list[dict]:
        """Return memories referencing a Paperclip issue id."""
        return self._manager.get_by_metadata("paperclip_refs", [paperclip_id])

    def get_by_tags(self, tags: list[str]) -> list[dict]:
        """Return memories carrying *all* the given tags."""
        return self._manager.get_by_metadata("tags", tags, match_all=True)

    # -- write --------------------------------------------------------------

    def add_fact(
        self,
        type: str,
        content: str,
        tags: list[str] | None = None,
        linear_refs: list[str] | None = None,
        paperclip_refs: list[str] | None = None,
        confidence: float = 0.95,
        agent: str = "aspen",
        summary: str = "",
    ) -> str:
        """Persist a fact with the BEL-154 metadata shape. Returns the id."""
        mem_type = MemoryType(type)
        metadata = {
            "tags": tags or [],
            "linear_refs": linear_refs or [],
            "paperclip_refs": paperclip_refs or [],
        }
        return self._manager.ingest(
            agent=agent,
            content=content,
            mem_type=mem_type,
            importance=confidence,
            summary=summary,
            metadata=metadata,
        )


__all__ = ["MemoryClient", "DEFAULT_DB"]
