# ASP-845: Biweekly Security Threat-Model Refresh — Follow-up Hardening Tasks

**Generated:** 2026-11-10
**Source:** docs/SECURITY_THREAT_MODEL_v2.2.md (v2.5)
**Commit:** f8b68bb on ASP-845-biweekly-security-threat-model-refresh

---

## P0 — Unblock the merge pipeline (structural risk)

The v2.5 refresh identifies that multiple security-relevant branches have not landed on origin/master. §5 lists 7 branches spanning ~1-2 cycles. While the merge pipeline was partially cleared by edbc440 (PR 78, 2026-10-12), the velocity has not kept pace with security branch creation.

### Task 1: Land anomaly consumer hardening
- Branch: ASP-780 (PR 83)
- Changes: TLS-aware NATS connect, bounded actor map, dedupe seen-set, 16 new + 1 live-module tests
- Required before: systemd enablement of anomaly feed
- Age: ~1 cycle (since 2026-10-26)

### Task 2: Land NATS legacy credential scrub
- Branch: ASP-365 (PR 82)
- Changes: Replace literal creds in `nats/server.conf` with placeholders; hermetic test prevents recurrence
- Security impact: Attack surface reduction + partial H-017 progress
- Age: ~1 cycle

### Task 3: Land D1 cell profile and baseline
- Branches: ASP-796 (PR 85) — cell profile, ASP-820 (on ASP-819 branch) — security baseline
- Both required before D1 physical cell deployment
- F-023 opened; baseline defined but not on origin/master

---

## P1 — Persistent hardening (carried from v2.4)

### Task 4: NATS credential rotation cadence (H-017)
- Open for 6+ cycles (since ASP-536)
- Define 90-day cadence with dry-run rotation procedure
- Sibling: ASP-365 (cred scrub) should land first
- No ticket exists; suggest creating one

### Task 5: Fleet heartbeat node fingerprint (F-017)
- Design doc `docs/security/f-017-fleet-node-fingerprint.md` on origin/master
- No implementation exists. ASP-804 suggested but not linked.
- Add fingerprint field to register/heartbeat payload; ops-manager validates against allowlist

### Task 6: ADR-0012 operator binding (H-024 P0-1)
- Bind `human_id` to a persistent operator registry before non-sim actuator arm
- ADR-0012 stays Proposed; do not implement from this refresh alone
- ASP-777 suggested

### Task 7: NACL drift fixture (ASP-805)
- Compare config/fleet.yaml to committed baseline
- Print audit-shaped report
- No host cron

### Task 8: Bandit CI report job (ASP-806)
- High-severity bandit on src/python
- Report-only; not a required check

---

## P2 — Carry-forward (v2.6 planning)

### Task 9: NATS nkey migration (continued)
- Residual from ASP-536: nkey-only CI enforcement, SYS account migration, nk binary availability

### Task 10: H-HOST-04 (master password in env)
- Replace AGENTIC_MASTER_PASSWORD env var with keyring, prompt, or TPM-backed secret
- Env fallback must warn

### Task 11: Gatekeeper SPOF (H-020)
- Redundancy plan still design-only
- Phase 2 (ASP-564) landed; full fail-over architecture not designed

### Task 12: Land remaining backlog branches
- ASP-782 (PR 79): Holographic MemoryStore loader — no security credit but blocks other work
- ASP-800/818 (PRs 84/87): Weekly architecture reviews — documentation

---

## Appendix: Unmerged security branches (at 2026-11-10)

| Branch | Topic | PR | Security Impact | Age |
|--------|-------|----|-----------------|-----|
| ASP-365 | Scrub literal NATS creds from legacy config | 82 | Attack surface + partial H-017 | ~1 cycle |
| ASP-780 | Anomaly consumer hardening (TLS-aware connect, bounded map) | 83 | Pre-service-enable hardening | ~1 cycle |
| ASP-782 | Holographic catalog MemoryStore loader | 79 | No security impact | ~1 cycle |
| ASP-796 | D1 plant-range cell profile, sim-only | 85 | F-023 opened | ~1 cycle |
| ASP-800 | Weekly architecture review 2026-10-19 | 84 | Documentation | ~1 cycle |
| ASP-774 | H-024 cell assessment document | 44 | Certification baseline | ~2 cycles |
| ASP-819/820 | v2.4 threat model + F-023 D1 baseline | — | Superseded by v2.5 | ~1 cycle |

**Total: 7 unmerged branches. 3 carry open security changes (ASP-365, ASP-780, ASP-774). ASP-796 and ASP-820 are security-adjacent (cell deployment baseline). None are on origin/master.**

---

*Written by Auditor at f8b68bb. Branch: ASP-845-biweekly-security-threat-model-refresh.*