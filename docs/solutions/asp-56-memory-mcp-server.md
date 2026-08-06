# ASP-56 — BEL-154 MCP server (`mcp/aspen-memory-mcp`)

## Problem

BEL-154 Component 4.2 (MCP server) existed only as a design snippet
(`docs/architecture/MEMORY_LAYER.md`). Agents wanting to query the memory store
from an MCP client (Hermes, OpenCode, Aider, Paperclip, ABS stack) had to shell
out to `scripts/memory_promote.py` or hand-write a client — there was no stdio
MCP endpoint.

## Root cause

The access layer stopped at the Python `MemoryClient` (ASP-55). Exposing the
same five operations over the Model Context Protocol was an explicit
"separate cycle" deferral in the ASP-55 disposition, so no MCP transport
existed in-repo.

## Fix

- **`mcp/aspen-memory-mcp/`** — installable package (PEP 621, console script
  `aspen-memory-mcp`) that starts an MCP server over stdio.
- **`server.py`** — builds an `MCPServer` and registers the five design-doc
  tools, each delegating to `MemoryClient` (which wraps `MemoryManager` — the
  canonical store, no parallel copy):
  - `memory_search(query, k=5, min_confidence=0.7)` → `client.search()`
  - `memory_get_by_linear(linear_id)` → `client.get_by_linear()`
  - `memory_get_by_paperclip(paperclip_id)` → `client.get_by_paperclip()`
  - `memory_get_by_tags(tags)` → `client.get_by_tags()`
  - `memory_add_fact(type, content, tags, linear_refs, paperclip_refs,
    confidence=0.95)` → `client.add_fact()`, returns the new id
- **Argument marshalling** — `list[str]` args (tags, refs) are pydantic-typed
  through the tool function signature, so the SDK validates them; a
  `memory_add_fact` tool uses the SDK's tool **return value contract** and
  returns a plain error string for an invalid `MemoryType` instead of raising
  (the `MCPServer` would otherwise surface a tool-level exception to the
  client).
- **Path strategy** — the package inserts `memory_pkg/` (and relies on
  `aspen_memory` inserting `services/`) into `sys.path` relative to the source
  file, so it runs both editable-installed and straight from the tree — the
  ASP-53/54/55 pattern.
- **Tests** — `tests/test_memory_mcp.py`: 7 tests covering the tool list,
  add-fact round-trips through linear/tags/search, unknown-ref empty results,
  invalid-type error strings, and a canonical-store check (a fact written via
  the tool is visible to a fresh `MemoryClient` on the same db).
- **Docs** — `ARCHITECTURE_COMPLETE.md` 3.2a + `MEMORY_LAYER.md` status flipped
  to Implemented.

## Lessons

- **MCP SDK v2 API surface.** The modern layout is
  `mcp.server.mcpserver.MCPServer` with a `@server.tool()` decorator, an async
  `list_tools()`/`call_tool()` for tests, and `run_stdio_async()` for the
  transport. It auto-generates JSON schemas from the function signature, so
  keep tool params plain-typed (`list[str]`, `float`, `int`).
- **Tools should return values, not raise.** `call_tool` wraps exceptions as
  tool errors; a cleanly-worded error string is friendlier to agents and still
  `is_error=False`. Validation of enums belongs at the boundary.
- **Thin wrapper over the canonical client, again.** The server adds zero
  state; `MemoryClient` (canonical `MemoryManager`) stays the single source of
  truth. A temp db per test keeps tests isolated.
- **Test the transport once.** One stdio round-trip via `ClientSession` proves
  the `__main__`/console-script path; the unit tests hit `call_tool` directly.

## Verification

- `python3 -m py_compile mcp/aspen-memory-mcp/src/aspen_memory_mcp/server.py` OK.
- `tests/test_memory_mcp.py` + `tests/test_memory_client.py`: **13/13 pass**.
- End-to-end stdio: `ClientSession` lists the five tools and round-trips an
  add-fact + `memory_get_by_paperclip` through the installed `aspen-memory-mcp`
  console script.

## Follow-ups

- AppFlowy bidirectional sync (Component 5) — larger scope, future cycle.
- `ProspectiveMemoryManager` — architect decision pending (escalated ASP-53).
- Register the server with OpenCode/Aider (`opencode --plugin` /
  `aider --read-hook`) once agent-side integration is in scope.
