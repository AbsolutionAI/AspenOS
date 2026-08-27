# Runbook — plant-range estop latch + audit drill (G7)

**Trackers:** ASP-417 · ASP-381 · BEL-192  
**Co-owners:** robotics (execute) · auditor (chain / refuse review)  
**Profile:** `config/cells/plant-range-d1.yaml`  
**Test card:** G5 §4–6

## Intent

Prove that an estop **latches**, freezes safety-adjacent acts, requires an authorized clear, and leaves a **verifiable hash-chained audit** trail. Sim drill is acceptable before live hardware.

## Preconditions

- [ ] G6 profile artifacts present (`config/cells/plant-range-d1.yaml` + hold-to-enable runbook)
- [ ] Edge RRM (or lab stand-in) can subscribe to `aspen.safety.estop` / `aspen.safety.clear`
- [ ] Audit path writable (`ASPEN_AUDIT_PATH` or profile default)
- [ ] Dual-human sim still green
- [ ] **Live drivers / free motion still forbidden** until this drill green + dual-auth usable + captain ceiling for any PO

## Drill procedure

### 1. Baseline

1. Start cell stack in **sim** (or dry-run) mode with audit path set.
2. Confirm no latched estop; optional health/status shows safe.
3. Note audit file path and baseline line count / head hash if available.

### 2. Press estop (latch)

1. Publish / inject `aspen.safety.estop` for the cell node.
2. **Expect:** estop latched; new `propose_act` / act attempts **held or refused**.
3. Record audit events: estop received + latch.

### 3. Refuse path under latch

1. Attempt a safety-adjacent propose_act (sim).
2. **Expect:** refuse or hold with reason tied to estop/unsafe — never silent execute.
3. Single-principal authorize must still refuse per G3 even if latch were clear.

### 4. Unauthorized clear attempt

1. Attempt clear without authorized procedure / dual principals as required by policy.
2. **Expect:** latch remains; clear refused; audit records refusal.

### 5. Authorized clear

1. Follow clear procedure (named operator; dual auth if policy requires for clear).
2. Publish `aspen.safety.clear` only after checks.
3. **Expect:** latch clears; system returns to propose_act hold (not free motion).

### 6. Verify audit chain

```bash
# Package path varies by install; edge-rrm smoke exposes verify_audit()
# Lab stand-in via fleet bus smoke:
ASPEN_SIM=1 python3 scripts/smoke-fleet-bus.py
# Prefer package:
#   cd aspen-edge-rrm && make smoke
```

**Expect:** `verify_audit()` passes; tamper of any mid-file line fails verification in unit/smoke coverage.

## Pass criteria

| # | Check | Pass |
|---|-------|------|
| 1 | Estop latches | Yes |
| 2 | Acts refused/held while latched | Yes |
| 3 | Unauthorized clear fails | Yes |
| 4 | Authorized clear restores propose_act hold only | Yes |
| 5 | Audit hash chain verifies | Yes |
| 6 | No joint motion occurred during drill | Yes |

## Evidence to attach

- Comment on ASP-417 with command transcripts + audit path (redact secrets)
- Link verify output / smoke exit codes
- Auditor note: chain integrity + refuse path review

## Explicit non-goals

- Free-space slow move (needs dual-auth usable path after G7)
- Production plant-alpha cutover
- Skipping dual-auth because “estop works”
