# ASP-369 / F-022 / H-021: Remove plant-edge→plant-alpha ACL (pivot risk)

**Status:** READY_FOR_AIDER_QA
**Mode:** IMPLEMENTATION
**Source:** Security Threat Model v2.2 (ASP-298) — HIGH finding F-022
**Parent issue:** ASP-298
**Plan:** `docs/plans/ASP-369.md`
**Updated:** 2026-09-20

## Summary

`config/fleet.yaml` shipped a **bidirectional** cross-plant ACL:

```yaml
acl:
  allow:
    plant-alpha: [plant-edge]   # ops → edge
    plant-edge: [plant-alpha]   # edge → ops  ← removed
```

`plant-edge: [plant-alpha]` gave an edge node an allow-list path into the ops
plant. If an edge host was compromised (RCE, tool escape, poisoned skill), the
attacker could pivot into `plant-alpha` through `delegate_to_agent` /
`http_post` / `http_get` cross-plant checks — despite the v2.2 zone model
treating EDGE as a limited subject set with "no mission/write subjects"
(ASP-298, §3.1).

## Decision (recorded)

**Remove `edge → alpha`. Keep `alpha → edge` (ops-initiated).**

| Direction | After | Rationale |
|-----------|-------|-----------|
| `plant-alpha → plant-edge` | **Allowed** | Ops must still manage/reach edge nodes; brokered operator-side (ops plant initiates) |
| `plant-edge → plant-alpha` | **Denied** (fail-closed default) | Edge compromise must not pivot to ops; least privilege |
| `plant-range → *` / `* → plant-range` | **Denied** | Isolation + empty allow list unchanged |

Removing the edge entry means any edge-initiated cross-plant request now falls
through `fleet_policy.check_cross_plant` to the `same_plant_only` default →
denied. Ops→edge management is preserved via the explicit alpha allow list.

## Threat-model checklist — H-021 marked

- [x] **H-021 / F-022:** plant-edge→plant-alpha ACL pivot — **closed (ASP-369)**.
      `plant-edge: [plant-alpha]` removed from `config/fleet.yaml`; edge
      cross-plant now fails closed at the ACL layer. Ops→edge retained for
      ops-initiated management. Verified by `tests/test_fleet_policy.py` and
      `scripts/smoke-test.sh` (`cross-plant ACL denies edge→alpha (F-022)`).

## Changes

| File | Change |
|------|--------|
| `config/fleet.yaml` | Removed `plant-edge: [plant-alpha]`; comment records the direction rule |
| `docs/FLEET.md` | ACL example block mirrored + direction note added |
| `tests/test_fleet_policy.py` | New hermetic suite pinning the shipped ACL: edge→alpha denied, alpha→edge allowed, range isolation, same-plant, red-team exercise deny, `delegate_to_agent` parity |
| `scripts/smoke-test.sh` | Added `cross-plant ACL denies edge→alpha (F-022)` check |

## Verification

- `pytest tests/test_fleet_policy.py -q` → all pass
- Cross-plant smoke checks: alpha→edge allowed, edge→alpha denied, alpha→range denied
- Runtime behavior unchanged: same-plant and range isolation logic untouched

## Out of scope

- Live NATS restart / ACL apply on any cell
- NATS account-level subject ACL (`fleet-accounts.conf.tmpl`) — ASP-536 covers it
- ASP-370 (aa-enforce), ASP-379