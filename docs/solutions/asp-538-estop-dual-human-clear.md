# ASP-538: Estop dual-human clear gate

## Problem

The EdgeRRM's `_on_clear` handler unlatched the estop unconditionally on any
`aspen.safety.clear` message. A single human could clear a safety stop without
any authorization check — violating ADR-0003 §Safety (dual-human clear required)
and leaving H-007 (CVSS 9.0) unmitigated.

## Solution

### Implementation (`aspen_edge/rrm.py`)

Added a `_clear_auths: dict[str, float]` field to `EdgeRRM` tracking distinct
human IDs and their authorization timestamps:

- **`aspen.safety.authorize_clear`** subscription — extracts `human_id` from
  envelope data, prunes stale entries (5-minute window `CLEAR_AUTH_WINDOW`),
  records the human ID in the dict, emits `authorize_clear` audit event.

- **`_on_clear` gate** — prunes stale auths, then checks `len(_clear_auths) >= 2`.
  Surfaces `clear_refused_insufficient_auths` audit event instead of unlatching
  when fewer than 2 distinct humans have authorized.

- **`_on_estop`** now also clears `_clear_auths` — a new estop invalidates any
  prior authorization set.

- **Auth window pruning** — stale entries older than 300 seconds are dropped on
  each `authorize_clear` or `clear` event.

### Tests (`tests/test_rrm.py`)

| Test | What it verifies |
|------|-----------------|
| `test_clear_alone_never_unlatches` | bare `clear` → estop stays True, audit has `clear_refused_insufficient_auths` |
| `test_single_auth_never_unlatches` | 1 `authorize_clear` + `clear` → estop stays True |
| `test_dual_auth_then_clear_unlatches` | 2 distinct humans + `clear` → estop becomes False |
| `test_same_human_twice_equals_one` | same `human_id` twice + `clear` → estop stays True |
| `test_estop_resets_clear_auths` | new estop clears auth set, preventing stale auths |
| `test_audit_records_authorize_clear` | each `authorize_clear` produces audit record with `human_id` and `auth_count` |

## Key design decisions

1. **Dict (not set)** for `_clear_auths` — value stores timestamp for window
   pruning; key deduplicates by `human_id` for free.

2. **5-minute auth window** — limits reuse of stale authorizations; can be
   tuned via `CLEAR_AUTH_WINDOW` module constant.

3. **Estop clears auth set** — a new safety stop must get fresh authorizations
   before it can be cleared.

4. **Audit on refused clear** — `clear_refused_insufficient_auths` provides
   observability into denied attempts.