"""aspen-memory-mcp — BEL-154 MCP server (Component 4.2).

Exposes the Starship OS long-term memory store to MCP clients (Hermes,
OpenCode, Aider, Paperclip, ABS stack) over stdio. Thin wrapper over the
canonical ``aspen_memory.MemoryClient`` — no parallel store, no schema drift.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

# Make the repo's packages importable whether this package is installed
# (editable) or run straight from the source tree.
_REPO_ROOT = Path(__file__).resolve().parents[4]  # mcp/aspen-memory-mcp/src/aspen_memory_mcp -> repo root
_MEMORY_PKG = _REPO_ROOT / "memory_pkg"
for _path in (_MEMORY_PKG,):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from aspen_memory import MemoryClient  # noqa: E402

try:
    from mcp.server.mcpserver import MCPServer
except ImportError:  # older mcp SDK layout
    from mcp.server import Server as MCPServer  # type: ignore

DEFAULT_DB = os.environ.get("AGNETIC_MEMORY_DB", "/tmp/agnetic-data/memory.db")


def _valid_types() -> list[str]:
    from memory import MemoryType

    return [t.value for t in MemoryType]


def build_server(db_path: str) -> MCPServer:
    """Construct an MCP server bound to the given SQLite memory db."""
    server = MCPServer("aspen-memory-mcp", version="0.1.0")

    @server.tool()
    def memory_search(
        query: str,
        k: int = 5,
        min_confidence: float = 0.7,
    ) -> str:
        """Semantic search over long-term memory. Returns JSON facts."""
        with MemoryClient(db_path) as client:
            return _dump(client.search(query, k=k, min_confidence=min_confidence))

    @server.tool()
    def memory_get_by_linear(linear_id: str) -> str:
        """Return memories referencing a Linear ticket id."""
        with MemoryClient(db_path) as client:
            return _dump(client.get_by_linear(linear_id))

    @server.tool()
    def memory_get_by_paperclip(paperclip_id: str) -> str:
        """Return memories referencing a Paperclip issue id."""
        with MemoryClient(db_path) as client:
            return _dump(client.get_by_paperclip(paperclip_id))

    @server.tool()
    def memory_get_by_tags(tags: list[str]) -> str:
        """Return memories carrying *all* the given tags."""
        with MemoryClient(db_path) as client:
            return _dump(client.get_by_tags(tags))

    @server.tool()
    def memory_add_fact(
        type: str,
        content: str,
        tags: list[str] | None = None,
        linear_refs: list[str] | None = None,
        paperclip_refs: list[str] | None = None,
        confidence: float = 0.95,
    ) -> str:
        """Persist a fact to long-term memory. Returns the new memory id."""
        if type not in _valid_types():
            return (
                f"error: invalid type {type!r}; valid types: {', '.join(_valid_types())}"
            )
        with MemoryClient(db_path) as client:
            return client.add_fact(
                type=type,
                content=content,
                tags=tags,
                linear_refs=linear_refs,
                paperclip_refs=paperclip_refs,
                confidence=confidence,
            )

    return server


def _dump(results: Any) -> str:
    import json

    return json.dumps(results, default=str)


def main(argv: list[str] | None = None) -> None:
    """CLI entry point: parse flags, start the stdio MCP server."""
    parser = argparse.ArgumentParser(prog="aspen-memory-mcp")
    parser.add_argument("--db", default=DEFAULT_DB, help="SQLite memory db path")
    parser.add_argument(
        "--vectors",
        default=None,
        help="Reserved: LanceDB vector store path (unused by MemoryClient today)",
    )
    args = parser.parse_args(argv)

    import asyncio

    server = build_server(args.db)
    asyncio.run(server.run_stdio_async())


if __name__ == "__main__":
    main()
