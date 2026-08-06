# ASP-56 — BEL-154 MCP server (`aspen-memory-mcp`)

Minimal PEP 621 packaging for the Starship OS memory-layer MCP server.

```bash
pip install -e ./mcp/aspen-memory-mcp

aspen-memory-mcp --db /tmp/agnetic-data/memory.db
```

The server wraps the canonical `aspen_memory.MemoryClient` (which itself wraps
`services/memory.py`) — no parallel store, no schema drift.
