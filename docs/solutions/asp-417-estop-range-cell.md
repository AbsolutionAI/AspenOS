# Estop latch + audit hash chain on the range cell (ASP-417 / G7)

**Date:** 2026-08-24
**Tickets:** ASP-417 (G7), ASP-384 (dual-human gate), BEL-192 (Phase D)

## Problem

An emergency-stop press must be latched and tamper-evidently audited. Single-
principal clear and audit forgery were the primary failure modes.

## Solution

Two-layer safety mechanism for the plant-range-cell:

1. **Estop latch (three states)** — `armed` (normal), `latched` (estop pressed,
   refuses everything with `refused: estop_latched`), and `clearing` (authorized
   clear initiated). The latch cannot be toggled off by a plain flag write; only
   the authorized-clear path (two distinct human principals) returns to `armed`.
2. **Audit hash chain** — every lifecycle event appended to
   `/tmp/aspen-audit-<node>.jsonl` as a hash-chained `AuditLog` record. Records
   carry `ts`, `event`, `data`, `prev` (prior record hash), and `hash` = SHA-256
   over the canonical body. `verify_audit()` detects insertion, deletion,
   reordering, or content edit.

The refuse-path proofs cover:
- act refused while latched (`estop_latched`)
- single-principal clear refused (`insufficient_principals`)
- duplicate-principal clear refused (`duplicate_principal`)
- tampered audit line detected by `verify_audit()`

## Patterns to reuse

1. **Latch, don't debounce.** A safety stop must be latched until an explicit
   authorized clearance. Soft debouncing or auto-clear creates unsafe race
   conditions.
2. **Dual-principal clear mirrors the act gate.** The same two-principal model
   (ASP-384) applies to clearing a safety stop: the person who caused the stop
   cannot be one of the authorizers.
3. **Hash chain for audit integrity.** Individual record signing (PKI) is
   overkill for internal audit; a SHA-256 hash chain over canonical JSON bodies
   makes tampering detectable at zero key-management cost.
4. **Sim drill before live wiring.** The simulation (`scripts/sim_estop_range_cell.py`)
   proves the full press→latch→refuse→dual_clear→armed cycle plus all refuse
   paths before any physical wiring.

## Verification

```
python3 scripts/sim_estop_range_cell.py
```

Exit 0 = full drill passes + `verify_audit()` confirms chain integrity.
Output: JSONL audit evidence + final proof line.

## Remaining

- Live wiring into Hermes `propose_act`→`act` path (gated on ASP-384 G6
  profile lock + captain $ ceiling + dual-auth path).
- No physical motion until G6 profile lock is deployed.
