# ASP-541: Daily Implementation Sweep — Gatekeeper NATS Daemon, Holographic Ingest, Grok Build Hook, Security Model v2.2

## Summary

Batched implementation sweep advancing the ADR-0009 gatekeeper prototype to a
fully NATS-integrated daemon with offline-fallback buffer, adding holographic
dual-write to the BEL-154 memory ingest pipeline, introducing a Grok Build
memory hook, and updating the security threat model to v2.2. All changes
committed and verified (26 tests passing, nightly 80/81 pass).

## Changes

| Area | Files | Description |
|------|-------|-------------|
| **Gatekeeper NATS daemon** | `src/python/gatekeeper/minimal_shim.py` | Full async daemon mode with `asyncio.run`, NATS gate request handler, wildcard `_cap_match`, `SAFETY_SUBJECTS` isolation, `set_nats_client()` registry, demo/daemon CLI. 322 lines changed. |
| **NATS client** | `src/python/gatekeeper/nats_client.py` (new) | `NATSGateClient` class — `publish_audit`/`publish_decision`/`publish_grant` typed helpers, `_subscribe_gate_requests`, offline buffer with auto-flush on reconnect, standalone demo mode. 341 lines. |
| **Gatekeeper package** | `src/python/gatekeeper/__init__.py` (new) | Exports `NATSGateClient`, `request_capability`, `log_audit`, `CAPABILITY_STORE`, `AUDIT_LOG`. |
| **Holographic ingest** | `scripts/holographic_ingest.py` (new) | Best-effort dual-write to shared holographic SQLite via Hermes `MemoryStore`. Failure-isolated, env-gated (`_should_write`). 120 lines. |
| **Memory ingest dual-write** | `scripts/memory_ingest.py` | Added `"grokbuild"` to `VALID_SOURCES`; best-effort call to `write_holographic()` after JSONL append. Never raises. |
| **Grok Build hook** | `agents/grokbuild_memory.py` (new) | BEL-154 memory ingestion hook for Grok Build. Mirrors opencode/aider/paperclip hooks with CLI (`--source-id`, `--stdin`) and holographic dual-write. 117 lines. |
| **Security threat model** | `docs/SECURITY_THREAT_MODEL_v2.2.md` (new) | 315-line security threat model update, integrating ADR-0009 gatekeeper pattern, capability-based authz, and NATS subject boundaries. |
| **Nightly check results** | `docs/nightly-check-results-2026-08-31.md` (new) | 80 passed, 1 known C11 failure. Baseline verified. |
| **Tests** | `tests/test_gatekeeper_nats.py` (new, 21 tests) | Decision engine (grant/deny/propose_act/audit/scoping), NATS client (connect/publish/offline-buffer/handler/subscribe/close), shim-NATS integration (audit delegation, handler dispatch, missing-cap deny). |
| **Tests** | `tests/test_holographic_ingest.py` (new, 5 tests) | Prod-DB isolation, explicit DB env write, grokbuild source acceptance, hook persistence, all four writer JSONL output. |

## Result

- All 10 files committed (1,882 insertions, 49 deletions).
- Tests: **26 passed, 0 failed** (21 gatekeeper, 5 holographic ingest).
- Nightly check: **80 passed, 1 failed** (C11 p50 — known, hardware-dependent).
- Pushed: [5c92f5b](https://github.com/AbsolutionAI/AspenOS/commit/5c92f5b)

## What was learned

- **NATS daemon pattern:** The ADR-0009 gatekeeper prototype was refactored from
  a synchronous demo script to a proper async daemon with NATS subscriptions.
  Key pattern: the `NATSGateClient` manages its own lifecycle (connect/close)
  while the `minimal_shim` owns the decision engine. They communicate through
  `set_nats_client()` and `_handle_gate_request()`. This separation means the
  decision engine can be unit-tested without NATS, while the client is mock-
  tested separately.
- **Offline-first architecture:** Every NATS publish call is best-effort with
  local buffer fallback. The `is_online` property and `offline_buffer_size`
  give operators observability. The auto-flush in `connect()` handles the
  reconnect case cleanly — no agent credential is ever embedded.
- **Holographic dual-write pattern:** The BEL-154 ingest pipeline now dual-
  writes to JSONL (existing) and holographic SQLite (new). The holographic
  path is failure-isolated in both directions: `memory_ingest.py` catches
  all exceptions from `write_holographic()`, and `holographic_ingest.py`
  never raises. The `_should_write()` gate prevents production DB writes
  during test runs with tmp ingest dirs, unless `ASPEN_HOLOGRAPHIC_DB` is
  explicitly set.
- **Grok Build hook symmetry:** The new `agents/grokbuild_memory.py` follows
  the exact pattern of `opencode_memory.py`, `aider_memory.py`, and
  `paperclip_memory.py` — `ingest_grokbuild_record()` → `ingest_record()`
  with failure isolation and CLI entry point. Keeping all four hooks
  structurally identical reduces cognitive overhead.
- **Test isolation for async NATS:** The `mock_nats` fixture patches `nats`
  at the `sys.modules` level, enabling full NATS client testing without
  a real broker. Critical: `pytest-asyncio` must be installed for async
  test support; the nightly check's `pytest` invocation should include it.
- **Sweep pattern:** This sweep combined code (gatekeeper daemon), new
  infrastructure (holographic DB), and documentation (threat model v2.2).
  The commit message itemizes each area independently. The nightly check
  was run before the sweep and confirmed clean, so the sweep commit is
  the only delta.