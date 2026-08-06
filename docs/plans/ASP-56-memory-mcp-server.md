# ASP-56 — BEL-154 MCP Server (`mcp/aspen-memory-mcp`)

**Status:** Plan → Implement → QA → Compound
**Sweep:** Hourly implementation sweep (ASP-56)
**Area:** Long-term memory service — access layer Component 4.2
**CE-GATE:** `discovery` → `plan` → `implement` → `qa` → `compound`
**Pipeline:** Discovery → Plan (docs/plans/<issue>.md) → Implement → QA → Compound

## Discovery

BEL-154's design (`docs/architecture/MEMORY_LAYER.md`) Component 4.2 specifies an
MCP server exposing the memory store to agents (Hermes, OpenCode, Aider,
Paperclip, ABS stack) over the Model Context Protocol. ASP-52 landed the
semantic layer, ASP-53 the access layer, ASP-54 the promotion pipeline, and
ASP-55 the `aspen_memory.MemoryClient` library. The MCP server was explicitly
deferred in the ASP-55 disposition ("MCP server (Component 4.2) — separate
cycle"). This sweep lands Component 4.2.

The design doc's target interface:

```bash
cd /home/tech/aspen-dev/repos/aspen-os/mcp/aspen-memory-mcp
pip install -e .

aspen-memory-mcp --db /home/tech/.aspen/memory/facts/facts.sqlite \
                 --vectors /home/tech/.aspen/memory/vectors
```

**Tools exposed (from design doc):**
- `memory_search(query, k=5, min_confidence=0.7)`
- `memory_get_by_linear(linear_id)`
- `memory_get_by_paperclip(paperclip_id)`
- `memory_get_by_tags(tags)`
- `memory_add_fact(type, content, tags, linear_refs, paperclip_refs, confidence)`

## Objective

Create `mcp/aspen-memory-mcp/` as an installable Python package that starts an
MCP server over stdio. The server wraps the canonical
`aspen_memory.MemoryClient` (which itself wraps `services/memory.py`) — no
parallel store, no schema drift (the ASP-52/53/54/55 pattern).

## Changes

### 1. `mcp/aspen-memory-mcp/pyproject.toml`

Minimal PEP 621 metadata: name `aspen-memory-mcp`, package `aspen_memory_mcp`,
console script `aspen-memory-mcp = aspen_memory_mcp.server:main`. Runtime deps:
`mcp>=1.0`, `aspen-memory` (installed from `memory_pkg/`) or a path dependency
on the repo. Requires-python `>=3.10`.

### 2. `mcp/aspen-memory-mcp/src/aspen_memory_mcp/server.py`

- `main(argv=None)` parses `--db` (default `$AGNETIC_MEMORY_DB` or
  `/tmp/agnetic-data/memory.db`) and `--vectors` (accepted, reserved for the
  future semantic override; currently unused by `MemoryClient`).
- Builds a `MCPServer` named `aspen-memory-mcp`.
- Registers the five tools from the design doc, each delegating to
  `MemoryClient`:
  - `memory_search(query, k=5, min_confidence=0.7)` → `client.search()`
  - `memory_get_by_linear(linear_id)` → `client.get_by_linear()`
  - `memory_get_by_paperclip(paperclip_id)` → `client.get_by_paperclip()`
  - `memory_get_by_tags(tags)` → `client.get_by_tags()`
  - `memory_add_fact(type, content, tags, linear_refs, paperclip_refs,
    confidence=0.95)` → `client.add_fact()`; returns the new id.
- Runs via stdio transport (`asyncio.run(server.run_stdio_async())`).
- Locates `memory_pkg/` via `sys.path` insert relative to the package file (the
  established pattern) so it works editable-installed and from the repo.
- Handles `MemoryType` validation errors from `add_fact` by returning a clean
  error string rather than raising (MCP tool contract: return value, not crash).

### 3. Tests

`tests/test_memory_mcp.py` (canonical pytest style, temp `--db`):
- Tools list contains the five expected tool names.
- `memory_add_fact` returns an id; `memory_get_by_linear` / `memory_search`
  round-trip it.
- `memory_get_by_tags` respects `match_all` semantics.
- Invalid fact `type` returns an error string, not a crash.
- Direct `MemoryClient` integration asserts the server uses the canonical store
  (a fact added via the tool is visible to a fresh `MemoryClient` on the same
  db path).

### 4. Docs

- `docs/ARCHITECTURE_COMPLETE.md`: mark the MCP server row under the Memory
  Layer section as Implemented.
- `docs/architecture/MEMORY_LAYER.md`: flip the MCP server component status
  from `🔄 Design` to `✅ Implemented`.

## QA

- `python3 -m py_compile mcp/aspen-memory-mcp/src/aspen_memory_mcp/server.py`
- `pytest tests/test_memory_mcp.py tests/test_memory_client.py -q`
- Existing tracked memory tests still pass (no behavior change to the store).

## Compound

Record `docs/solutions/asp-56-memory-mcp-server.md`: MCP SDK v2 API notes
(`MCPServer.tool()` decorator, `run_stdio_async()`), the thin-wrapper-over-
`MemoryClient` decision, argument-marshalling pitfalls, and how to register the
server with OpenCode/Aider.

## Out of scope / escalated

- AppFlowy bidirectional sync (Component 5) — larger scope, future cycle.
- `ProspectiveMemoryManager` — architect decision pending (escalated ASP-53).
- ABS mirror deliverables owned by [ASP-36](/ASP/issues/ASP-36) — left
  uncommitted.
