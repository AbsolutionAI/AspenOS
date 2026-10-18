# ASP-433 / H-023: Independent hardware estop watchdog (design/sim)

**Status:** READY_FOR_AIDER_QA
**Mode:** IMPLEMENTATION
**Source:** Security Threat Model v2.2 (ASP-431 / F-009 ampliation) — H-023
**Parent issue:** ASP-433
**Plan:** `docs/plans/ASP-433.md`
**Updated:** 2026-09-23

## Summary

The software estop latch and the gatekeeper dual-human path live inside
agent-controlled processes. If the agent runtime or gatekeeper is compromised
or dead, the cell still needs a **fail-closed** path to the safe state that
does **not** trust agent software. ASP-433 lands that watchdog contract as
`src/python/safety/estop_watchdog.py` — a pure-stdlib module with no new deps,
no live hardware, and a durable trip latch that survives process restarts.

## What was built

| Piece | File | Purpose |
|-------|------|---------|
| `WatchdogBackend` (ABC) | `safety/estop_watchdog.py` | The only place trip state lives; swapping the backend is what moves the latch outside agent memory (independence). |
| `SimBackend` | same | In-process dict, default for tests/CI. |
| `FilePulseBackend` | same | Durable JSON file, atomic `os.replace`; the reference stand-in for future GPIO storage. |
| `EstopWatchdog` | same | Fail-closed watchdog: `tick(source)` heartbeat, `check()`/`is_tripped()` deadline gate, `force_trip(reason)`, `clear(authorizers)` dual-authorize, `mode="observe"` opt-in for sim profiles. |
| Tests | `tests/test_estop_watchdog.py` | 18 hermetic tests, all deterministic via injected timestamps. |

## Key semantics (decision, recorded)

1. **Ticks never clear.** A heartbeat only refreshes `last_tick_at`. A trip
   leaves the durable latch alone until `clear` presents **two distinct**
   authorizers — mirroring the existing `aspen.safety.estop` dual-clear. Never
   single-clear. Duplicate principals don't count (`set` over IDs).
2. **Fail closed everywhere.** `check()` trips on: missed heartbeat,
   `force_trip`, backend read/write error, invalid deadline config, and
   never-ticked. A resume of ticks after a `heartbeat_missed` trip does *not*
   self-clear — resuming ticks is exactly what a compromised agent would do.
3. **`never_ticked` is transient, not a latch.** Before the first heartbeat the
   watchdog reads as tripped (safe) but does not persist a latch, so a first
   boot that arms within the deadline needs no operator clear.
4. **Clear re-arms the deadline.** `clear` sets `last_tick_at = now`, so the
   software path has a fresh deadline to prove liveness; a cleared watchdog
   that stays silent re-trips. Clear is an ack, not a free pass.
5. **Independence invariant.** Ceasing `tick` (simulated agent death) trips the
   watchdog through `check()` alone — no gatekeeper, NATS, LLM, or agent call
   in the detection path.
6. **Audit trail is durable and non-gating.** `safety.watchdog.trip`,
   `safety.watchdog.clear`, `safety.watchdog.tick_miss` append to the backend
   state log (bounded) and fire an optional `emit` hook; the hook never gates
   the trip decision.
7. **Sim profile `light-cell` may run observe-only** (`mode="observe"`), which
   computes but never persists trips. Plant-range default stays `enforce`.

## Scope guard

- **No live GPIO / relay / physical loop wiring** this ticket — per Captain
  constraint, that requires Aspen START on this issue (separate comment).
- No change to existing `aspen-edge-rrm` estop dual-clear semantics; the
  watchdog adds an independent layer.
- No new dependencies; module imports stdlib only.

## Verification

- `python3 -m pytest tests/test_estop_watchdog.py` → **18 passed** in 0.07s.
- Full suite `python3 -m pytest tests/` → **466 passed, 4 skipped** (gatekeeper
  suites incl. H-022 vault-gate remain green).
- No hardware touched; all timing via injected monotonic timestamps.

## Residual / follow-up

- **Live hardware wire** (GPIO/relay + `GpioPulseBackend` contract) — gated on
  Aspen START for ASP-433.
- Gatekeeper daemon tick emission points remain a documentation-only surface
  this ticket (module docstring shows the intended wiring).