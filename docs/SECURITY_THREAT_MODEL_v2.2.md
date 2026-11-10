# Security Threat Model — AspenOS v2.5

**Version:** 2.5 · **Refresh:** 2026-11-02 (Biweekly)
**Author:** Auditor (Paperclip agent 4203b00e)
**Previous baseline:** origin/master held v2.2 (ASP-629, 2026-09-21). The v2.3 draft (ASP-741, local commit 44f5730) was never pushed to origin. The v2.4 draft (ASP-819, commit 86caa33) was authored on a branch and never merged to origin/master. This v2.5 incorporates both and adds this cycle's delta.
**This cycle:** ASP-845 — incorporate unmerged v2.4 analysis from ASP-819 branch. On the tree: TLS default (ASP-684), anomaly live consumer (ASP-687), branch protection (10 contexts), Python CI test suite gate (ASP-730). Not on the tree: H-024 cell assessment (PR 44, ASP-774), D1 sim-only cell profile (ASP-796, PR 85), anomaly consumer hardening (ASP-780, PR 83), NATS cred scrub (ASP-365, PR 82), weekly arch review 2026-10-19 (PR 84), D1 cell security baseline (ASP-820, on ASP-819 branch).
**Filename:** stable path `docs/SECURITY_THREAT_MODEL_v2.2.md`. The version in this header is canonical. Do not rename the file.
**SoR:** `docs/SECURITY.md` · `docs/FLEET.md` · `docs/adr/ADR-0003` · `docs/adr/ADR-0007` · `docs/adr/ADR-0009` · `docs/security/H-024-wan-mtls-deployment.md` · `docs/security/ACT_GATE_CONTRACT.md`
**IEC 62443 mapping:** §5.2 (zones/conduits), §3.3 (SLT), §5.3 (defence-in-depth). Cell assessment draft is PR 44 (ASP-774), not this file's §4.

---

## 1. Architecture Zones

```
┌──────────────────────────────────────────────────────────────────┐
│  ZONE 0 — Internet / WAN                                          │
│  ┌────────────────────────┐  ┌──────────────────────────────┐   │
│  │ Hermes agent (cloud)   │  │ OpenRouter / Ollama API       │   │
│  └────────┬───────────────┘  └──────────────────────────────┘   │
│           │                                                      │
│     ╔═════╩══════════════════════════════════════════════════╗   │
│     ║  ZONE 1 — Fleet Bus (NATS)                             ║   │
│     ║  JetStream store, subject routing, auth (accts/TLS)    ║   │
│     ╚═════╤══════════════════════╤══════════╤═══════════════╝   │
│           │                      │          │                    │
│  ┌────────┴──────┐   ┌──────────┴──────┐   ┌┴──────────────┐   │
│  │ ZONE 2        │   │ ZONE 3          │   │ ZONE 4        │   │
│  │ Ops Plant     │   │ Edge Plant      │   │ Range Plant   │   │
│  │ (plant-alpha) │   │ (plant-edge)    │   │ (plant-range) │   │
│  │ Full tools    │   │ Limited tools   │   │ Red/Blue/D1   │   │
│  │ All agents    │   │ Proxy + ctrlr   │   │ Isolated/sim  │   │
│  └───────────────┘   └─────────────────┘   └───────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

### Zone boundaries

| Boundary | Conduit | Auth | Notes |
|----------|---------|------|-------|
| Z0 → Z1 | NATS client/TLS or localhost | Token / accounts / TLS | Ops/edge: TLS on by default; server: plaintext loopback |
| Z2 ↔ Z1 | NATS `starship.*` / `aspen.*` | OPS account, full mesh | TLS on by default on ops cells |
| Z3 → Z1 | NATS heartbeat + proxy only | EDGE account, limited subjects | TLS on by default on edge cells |
| Z4 ↔ Z1 | NATS range subjects only | RANGE account, isolated | No imports from OPS/EDGE |
| Agent ↔ Host | Systemd unit / AppArmor | User=agnetic, NoNewPrivileges | Optional sandbox_run + policyexec |

---

## 2. Threat Register

### 2.1 Core threats (carried from v2.1 baseline)

| ID | Threat | Asset | Risk (CVSS) | Mitigation | Status |
|----|--------|-------|-------------|------------|--------|
| H-001 | Agent RCE via tool execution | Shell/host | 8.5 (AV:N/AC:L) | Sandbox blocklists, C11 seccomp, path allowlists, 50KB output limit, 30s timeout | Active |
| H-002 | Lateral movement via red-team agent | Fleet nodes | 7.5 (AV:A/AC:L) | Fleet ACL, tool allowlists, `plant-range` isolation, RED_TEAM_ALLOWED only | Active |
| H-003 | NATS bus spoofed commands | Message bus | 8.0 (AV:N/AC:L) | Accounts/nkeys, token auth, per-subject permissions, TLS default on ops/edge | Active |
| H-004 | Credential leak in logs/LLM context | Secrets | 6.5 (AV:N/AC:H) | Redaction patterns (password/token/secret/key), SecretsManager AES-256-GCM | Active |
| H-005 | Abliterated local model refusal bypass | Model safety | 7.0 (AV:L/AC:L) | Mandatory policy + sandbox + Droid Shield, never trust model alone | Active |
| H-006 | Cross-plant privilege escalation | Plant isolation | 7.0 (AV:N/AC:M) | `same_plant_only` default ACL, `check_cross_plant()` fail-closed | Active |

### 2.2 v2.5 refresh threats (updated 2026-11-02)

| ID | Threat | Asset | Risk (CVSS) | Mitigation | Status |
|----|--------|-------|-------------|------------|--------|
| H-007 | **EStop bypass — single-human clear** | Safety | **9.0** (AV:N/AC:L) | Dual-human `authorize_clear` before `clear` fires; `clear` alone never unlatches | **Covered (ASP-573)** — dedicated negative-case integration test in `scripts/smoke-fleet-bus.py`; pinned `aspen-edge-rrm` gate |
| H-008 | **Propose_act self-authorization** | Actuation | **8.5** (AV:N/AC:L) | Gate must reject single-principal and self-approval; stable audited reasons | **Phase 1+2 (ASP-540/564)** — dual-human enforced, token lifecycle, credential-strip proxy |
| H-009 | **Dual-human collision — same principal counted twice** | Authorization | 7.5 (AV:N/AC:M) | Verify distinct `human_id` records in-window; duplicate-principal refuse with reason | **Satisfied (ASP-540)** — `authorize_gate_request` dedupes by `human_id`; duplicate ignored + `gate.authorize.duplicate` audited |
| H-010 | **Stale capability tokens post-expiry** | Gatekeeper | 6.0 (AV:N/AC:L) | Short TTL + NATS auth time window; refuse if expired | **Implemented (ASP-564)** — short-TTL tokens (15 min) with active/consumed/expired lifecycle, refuse-if-expired on consume/refresh, stale cleanup |
| H-011 | **NATS plaintext credentials on disk** | Secrets | 7.5 (AV:L/AC:L) | nkey-only generator (ASP-536): `gen-nats-accounts.sh` emits `{nkey}` entries and drops plaintext when `nk` present; fallback password on missing `nk`; SYS account excluded | **Partial (ASP-536)** — nkey-only gen mode; residual: `nk` binary required at gen time, SYS account always password. ASP-365 (branch, not on origin/master) scrubbed literal creds from legacy `nats/server.conf` |
| H-012 | **scheduler.py hardcoded NATS URL** | Bus | 5.5 (AV:L/AC:H) | Hardcoded `nats://[IP_ADDRESS]:4222` — replaced with config/env | **Closed** (ASP-539) |
| H-013 | **No aspen.* subject ACL in NATS config** | Bus | 7.0 (AV:N/AC:L) | Per-role `aspen.*` ACLs committed in template (ASP-536): ops=sentinel+authz+fleet+safety, edge=fleet+edge+estop+clear, range=scoped fleet/heartbeat; cross-account imports/exports wired | **CLOSED (ASP-536)** — template ACLs for all roles; residual: clients still dual-publish `starship.*` during migration |
| H-014 | **Missing AppArmor profiles in deployment** | Host | 6.5 (AV:L/AC:M) | Profiles exist in `security/apparmor/`; deb postinst loads them (ASP-374); nightly Section 17 verifies wiring; verified in ASP-575 | **Satisfied (ASP-374/575)** — profiles staged + loaded via `postinst` (`apparmor_parser -r`, no enforce) |
| H-015 | **Audit trail not yet connected to aspen.sentinel.audit.event** | Forensics | 6.0 (AV:N/AC:L) | Subject defined (ADR-0007); publisher wired (ASP-537); Sentinel-dashboard consumer added; offline-capable JSONL journal + JetStream durable trail | **CLOSED (ASP-537)** — publisher + consumer both wired; gateway-agnostic design |
| H-016 | **LangGraph worker emit-side guard** | Mission subjects | 8.0 (AV:N/AC:L) | `aspen_lgw/guard.py`: blocks mission publish; `SwarmManager._busy_plants` prevents dual arm | **CLOSED** (ASP-533) |
| H-017 | **NATS credential rotation — no automatic rotation** | Credentials | 5.5 (AV:A/AC:H) | Manual `gen-nats-accounts.sh` only; no expiry enforcement | **Open** — No rotation procedure, no expiry enforcement, no cadence. ASP-365 (branch) scrubbed literal creds from legacy config. Open for 6+ cycles. |
| H-018 | **Single-plant dual-arm prevention** | Scheduler | 8.0 (AV:N/AC:M) | Dual guard layers: emit-side + scheduler-side | **CLOSED** (ASP-533) |
| H-019 | **Package classification bypass — Dev-only in production** | Supply chain | 6.0 (AV:N/AC:H) | ADR-0008 declares tiers; CI gate `check-no-devonly-in-prod.sh` wired in CI + nightly Section 16 (ASP-574) | **CLOSED (ASP-574)** — gate script committed; CI + nightly wired; verified clean |
| H-020 | **Gatekeeper single point of failure** | Availability | 7.0 (AV:N/AC:H) | Mitigate with local fallback + redundant instances (ADR-0009) | **Design only** — Phase 2 (ASP-564) done; redundancy plan separate |
| H-021 | **No dual-publish on aspen.sentinel.* subjects yet** | Observability | 5.0 (AV:N/AC:L) | Migration incomplete; `starship.*` still primary | **Closed (ASP-369)** — edge→alpha ACL pivot removed |
| H-022 | **Physical cell act requires HITL vault approval** | Actuation / Safety | **8.5** (AV:N/AC:L) | Gatekeeper shim vault-gate: physical cell act subjects require durable HITL vault approval record before authorize grants | **Implemented (ASP-432)** — 19/19 vault-gate tests + 99/99 phase2 pass; fail-closed on every vault failure path |
| H-023 | **Software estop latch is agent-dependent — no independent hardware watchdog** | Safety | **9.0** (AV:L/AC:H) | Independent `EstopWatchdog` (design/sim): software-path `tick` heartbeat, fail-closed open-loop trip, dual-authorize clear | **Implemented (ASP-433)** — 18/18 watchdog tests; 466-test suite green; residual: live GPIO/relay wire = Aspen START |
| H-024 | **No formal IEC 62443-4-2 / NIST CSF baseline for cell deployment** | Certification / Cell readiness | 6.5 (AV:N/AC:H) | Baseline gap analysis for CR 2.1–4.3; identity-to-IEC role map; production cell readiness verdict. **P0-1:** ADR-0012 operator binding (open, ASP-777). **P0-2:** TLS default on cell firstboot (on origin/master via ASP-684) | **P0-2 Implemented (ASP-684)** — TLS default on ops/edge. P0-1 remains open. Cell assessment document (PR 44, ASP-774) not on origin/master. WAN mTLS guide `docs/security/H-024-wan-mtls-deployment.md` on tree. |

### 2.3 Fleet-specific threats (F- series)

| ID | Threat | Asset | Risk (CVSS) | Mitigation | Status |
|----|--------|-------|-------------|------------|--------|
| F-015 | **Red-team lateral from range to ops** | Plant isolation | 8.0 (AV:A/AC:L) | `check_cross_plant()` rule 3/4: isolation deny; RANGE no import from OPS; tool-anomaly detector (ASP-379) adds behavioral detection | **Active** — anomaly detector live consumer wired (ASP-687); hardening (ASP-780, branch) adds TLS-aware NATS connect, bounded actor map, dedupe; blocking path still deferred |
| F-016 | **Plant ACL misconfiguration opens cross-plant** | ACL | 6.5 (AV:N/AC:L) | Default `same_plant_only` fail-closed; explicit allow list; F-022 removed edge→alpha pivot | **Active** — F-022 closed (ASP-369) |
| F-017 | **Fleet heartbeat spoofing (register fake node)** | Identity | 7.5 (AV:N/AC:L) | NATS accounts + token; no PKI/fingerprint yet | **Open** — design doc `docs/security/f-017-fleet-node-fingerprint.md` on origin/master. No implementation. |
| F-018 | **Exercise state race — start/stop collision** | Exercise | 5.0 (AV:N/AC:H) | Atomic file write; poll-based check in fleet_policy.py | **Open** |
| F-019 | **Delegated agent without plant tag** | Cross-plant | 6.0 (AV:N/AC:M) | `delegate_to_agent` accepts `plant`/`target_plant`; missing tag defaults no ACL | Informational |
| F-013 | **Unpinned model digests — tag-only ollama pull** | Supply chain / Model integrity | 6.0 (AV:N/AC:H) | Pin model digests (`config/models-digests.yaml`); verify-after-pull fail-hard | **Implemented (ASP-377)** — CI + nightly Section 22 |
| F-020 | **Software data-diode missing for OSINT/ingest** | OSINT domain | 6.5 (AV:N/AC:M) | nftables/iptables one-way rules + process isolation + restricted NATS account | **Recipe complete** — [Recipe](solutions/asp-368-data-diode-recipe.md) reviewed (AUDITOR_APPROVE); awaiting captain proof |
| F-011 | **NATS bus resource exhaustion — flood connections / subscriptions** | Bus availability | 6.5 (AV:N/AC:L) | `max_pending` 16MB, `max_control_line` 4KB, `max_subscriptions` 512, `write_deadline` 5s, `ping_interval` 30s/3, auth timeout 2.0s | **Implemented (ASP-375)** — per-account limits; Section 19 nightly gate |
| F-012 | **Agent resource exhaustion — runaway agent DoS** | Host / Agent availability | 6.0 (AV:L/AC:L) | systemd cgroup drop-ins (`CPUQuota`, `MemoryMax`, `MemoryHigh`, `TasksMax`) bound each agent unit | **Implemented (ASP-376)** — 8 unit profiles staged; 6 fixture tests; git-only (no live systemd applied) |
| F-014 | **Unsigned package substitution in update chain** | Supply chain / Package integrity | 6.5 (AV:N/AC:M) | `gpgv` detached-signature verify gate before `dpkg -i`; CI job `verify-package-signature` fails on unsigned/tampered | **Implemented (ASP-378)** — verify path ships; placeholder dev key; ceremony (real key signing) is deferred human action |
| F-022 | **Edge-initiated cross-plant pivot into ops** | Plant isolation | **8.0 (AV:A/AC:L)** | `plant-edge: [plant-alpha]` removed from `config/fleet.yaml` ACL; edge cross-plant fails to `same_plant_only` default (deny) | **Closed (ASP-369)** — 11 ACL fixture tests; smoke-test cross-plant check |
| F-023 | **D1 range cell has no security baseline — sim-only profile may skip hardening** | Cell isolation | 5.5 (AV:L/AC:H) | `config/cells/plant-range-d1.sim.yaml` (ASP-796, not on origin/master) defines `sim_only: true`. Baseline defined in `docs/security/F-023-d1-cell-security-baseline.md` (ASP-820, on ASP-819 branch, not on origin/master). | **Baseline defined but NOT on origin/master** — Both ASP-796 (cell profile) and ASP-820 (security baseline) are on the unmerged ASP-819 branch. Neither has been merged to origin/master. |

### 2.4 Host-level threats

| ID | Threat | Asset | Risk (CVSS) | Mitigation | Status |
|----|--------|-------|-------------|------------|--------|
| H-HOST-01 | **Unprivileged user access to NATS store** | JetStream data | 6.0 (AV:L/AC:L) | systemd `ProtectSystem=strict`, `User=agnetic`, `ProtectHome=true` | Active |
| H-HOST-02 | **Embedding model path traversal** | Model files | 4.0 (AV:L/AC:L) | Path allowlists in sandbox; Ollama runs under AppArmor | Active |
| H-HOST-03 | **Stale systemd units without hardening flags** | Systemd | 5.5 (AV:L/AC:L) | Units use NoNewPrivileges, ProtectSystem, etc. | Check gap |
| H-HOST-04 | **SecretsManager master password in env** | Secrets | 6.5 (AV:L/AC:L) | `AGENTIC_MASTER_PASSWORD` env var; recommend prompt or keyring | Open |

---

## 3. ACL and Zero-Trust Posture

### 3.1 Subject-level NATS permissions (accounts mode)

| Role | Account | Publish allow | Subscribe allow | Cross-account import |
|------|---------|---------------|-----------------|---------------------|
| sys | SYS | (system) | (system) | — |
| ops | STARSHIP_OPS | `starship.>` · `agnetic.>` | `starship.>` · `agnetic.>` | Imports: EDGE fleet + TELEM telemetry |
| edge | STARSHIP_EDGE | heartbeat, register, status, proxy.>, telemetry.> | fleet.>, ops.>, proxy.> | Exports: fleet subjects to OPS |
| red | STARSHIP_RANGE | proxy.>, fleet.heartbeat | proxy.>, fleet.exercise | **No imports** — isolated |
| blue | STARSHIP_RANGE | agent.>, fleet.heartbeat, status | `starship.>` · `agnetic.>` | **No imports** — isolated |
| telem | STARSHIP_TELEM | telemetry.> | (none) | Exports: telemetry to OPS |

> **Dual-subject table note:** Residual dual-publish during `aspen.` prefix migration remains active. H-013 (ASP-536) added per-role `aspen.*` ACLs in the `fleet-accounts.conf.tmpl`. The generated conf includes both namespaces. Migration not yet complete.

### 3.2 Fleet tool ACL (agents/fleet_policy.py)

| Check | Logic | Default |
|-------|-------|---------|
| Same-plant | `target_plant == None or == source_plant` | Allow |
| Red-team cross-plant during exercise | `is_red and exercise_active()` | Deny |
| Source plant isolation | `plant_isolated(source_plant)` | Deny outbound |
| Target plant isolation | `plant_isolated(target_plant)` | Deny inbound |
| ACL allow matrix | `acl.allow[source]` list | Same_plant_only |
| Global default | `acl.default` | `same_plant_only` (fail-closed) |

**Tool restrictions:**

| Team | Allowed tools | Denied tools |
|------|--------------|--------------|
| Ops | All | — |
| Red-team (exercise) | `read_file`, `list_dir`, `search_files`, `http_get`, `delegate_to_agent` | `opencode`, `opendesign`, `write_file`, `shell`, `http_post` |
| Blue-team (exercise) | Full diagnostics | `opencode` (blocked on range) |

### 3.3 Zero-trust scorecard

| Principle | Status | Evidence |
|-----------|--------|----------|
| **Verify explicitly** | Partial → **Improved** | NATS accounts authenticate; TLS by default on ops/edge (ASP-684); tool policy enforces per-call; no PKI for node identity |
| **Least privilege** | Partial | Agents hold role-scoped credentials; red-team subject-limited; OPS still has full mesh |
| **Assume breach** | Partial | Plant-range isolation; fail-closed ACL; no cross-plant trust; gatekeeper Phase 1+2 landed (ASP-540/564); residual is H-020 SPOF, design-only |
| **Never trust, always verify** | Partial | Tool policy checks every call; NATS accounts gate subjects; TLS default improves wire verification; no attestation/device identity |

### 3.4 IEC 62443 alignment

| Requirement | Control | Mapping | Status |
| --- | --- | --- | --- |
| **FR 3.4** Software and information integrity | Hardware Root of Trust (meas boot) + OS Runtime Protection + embedded software update integrity; ASP-378 verification | IEC 62443 §3.4 FR 3.4 (DIN/SPEC) | Mapped + verified, no credentials |
| **CR 1.1** — Identify & authenticate users (all human+programmatic) | NATS accounts, per-agent tokens, fleet-node identity | — | **Partial** — agents authenticated; no MFA, no PKI device identity |
| **CR 1.2** — Software process identity | Systemd `User=agnetic`, capability-based delegation (ADR-0009 Accepted, Phase 1+2) | — | **Partial** — OS user identity; no code signing |
| **CR 1.5** — Third-party/remote session integrity | Hermes gateway; Simplex bridge (dashboard Connect tab) | — | **Partial** |
| **CR 2.1** — Authorization enforcement | fleet_policy.py tool ACL, NATS subject permissions | — | **Satisfied** |
| **CR 2.3** — Dual approval for critical actions | `propose_act` -> `authorize` dual-human; estop dual-clear | — | **Satisfied** — estop dual-clear (ASP-538) + ADR-0009 dual-human gate (Phase 1, ASP-540) |
| **CR 2.4** — Restriction of logical access associated with mobile/remote | Plant isolation, range plant default | — | **Satisfied** |
| **CR 2.5** — Review of access rights | ACL audit in fleet.yaml; periodic threat model refresh | — | **Partial** — no automated drift detection |
| **CR 3.1** — Communication integrity | NATS JetStream; **TLS by default on ops/edge cells**, mutual TLS for WAN | — | **Satisfied (ASP-684)** — CR 3.1 gap closed |
| **CR 3.2** — Communication confidentiality | TLS by default; SecretsManager AES-256-GCM for stored secrets | — | **Satisfied (ASP-684)** — TLS default raises from Partial |
| **CR 3.3** — Zone/conduit boundary | Plant zones (ops/edge/range); NATS account boundaries | — | **Satisfied** |
| **CR 3.4** — Software update integrity | ADR-0008 package classification; `dpkg` signature via `gpgv` detached verify gate (ASP-378); CI gate blocks Dev-only in production (ASP-574) | — | **Satisfied (ASP-378/574)** |
| **CR 4.1** — System inventory | Fleet heartbeat + node register; Fleet Map dashboard | — | **Satisfied** |
| **CR 4.2** — Security event logging | `aspen.sentinel.audit.event` subject defined (ADR-0007); publisher + consumer wired (ASP-537): JSONL journal + JetStream durable trail + dashboard endpoints; anomaly detector live feed (ASP-687) | — | **Satisfied (ASP-537)** — offline-capable dual-path; no SIEM integration |
| **CR 4.3** — Continuous monitoring | Health checker, telemetry bus, Sentinel dashboard; anomaly detector live consumer wired (ASP-687) | — | **Partial** — improved with live anomaly feed; no alert on ACL drift |
| **CR 5.1** — Patch management | Debian packaging; systemd unit updates; full Python test suite CI gate (ASP-730) | — | **Partial** — no vulnerability scanning CI gate |
| **CR 5.2** — Malicious code protection | Tool sandbox, Droid Shield scanning, redaction | — | **Satisfied** |
| **CR 5.3** — Security functionality verification | Threat model refresh; stress tests; CI `security-nats-tls` job (ASP-684); `python-test-suite` required check (ASP-730); nightly Sections 1–23 | — | **Partial** — security-specific CI gates growing; no dedicated security scan |

---

## 4. Hardening Checklist

### 4.1 Immediate (v2.2 refresh — all resolved)

- [x] H-011: nkey-only NATS credential generator (ASP-536)
- [x] H-013: `aspen.*` subject ACLs in NATS template (ASP-536)
- [x] H-015: Audit publisher to `aspen.sentinel.audit.event` (ASP-537)
- [x] H-008: Gatekeeper shim Phase 1 + Phase 2 (ASP-540/564)
- [x] H-009: Dual-human collision logic (ASP-540)

### 4.2 Short-term (next 2 sprints)

- [x] **H-007:** Integration test for estop dual-human clear (ASP-573)
- [x] **H-012:** Replace hardcoded NATS URL (ASP-539)
- [x] **H-014:** AppArmor profile loading verification (ASP-374/575)
- [x] **F-011:** NATS rate limiting per-connection and per-account (ASP-375)
- [x] **F-012:** Cgroup per-agent resource limits (ASP-376)
- [x] **F-013:** Model digest pinning (ASP-377)
- [x] **F-014:** Signed package verify gate (ASP-378)
- [x] **F-020:** Draft software data-diode recipe
- [x] **F-022:** Edge→alpha ACL pivot removal (ASP-369)
- [x] **ASP-379:** Fail-open tool-anomaly detector (R1–R4)
- [x] **ASP-607:** Gatekeeper per-agent rate limiting
- [x] **ASP-659:** Nightly check flock serialization
- [x] **ASP-660:** Systemd unit count baseline fix
- [x] **ASP-684:** NATS TLS by default on ops/edge cells (H-024 P0-2)
- [x] **ASP-687:** Wire tool-anomaly detector to live audit consumer
- [x] **ASP-721:** NATS install guard in CI
- [x] **ASP-730:** Full Python test suite as required CI check
- [x] **ASP-696:** HybridIntel stub removal (attack surface reduction)
- [x] **ASP-732:** Branch protection enforced at 10 contexts
- [ ] **ASP-782:** Holographic catalog MemoryStore loader — not on origin/master (PR 79). No security credit until landed.
- [ ] **ASP-800:** Weekly architecture review 2026-10-19 — not on origin/master (PR 84).
- [ ] **ASP-796:** D1 plant-range cell profile, sim-only — not on origin/master (PR 85).
- [ ] **ASP-780:** Anomaly consumer hardening — not on origin/master (PR 83).
- [ ] **ASP-365:** Scrub literal NATS creds from legacy config — not on origin/master (PR 82).
- [ ] **ASP-820:** D1 cell security baseline — on ASP-819 branch, not on origin/master.
- [ ] **H-017:** NATS credential rotation cadence. Open for 6+ cycles. No ticket.
- [ ] **H-HOST-04:** Replace env-based master password with prompt, keyring, or TPM-backed secret. P2. No ticket this cycle.
- [ ] **F-017:** Node fingerprint for fleet heartbeat. Design doc on origin/master, no implementation. ASP-804 suggested.
- [ ] **H-024 P0-1 — ADR-0012 operator-of-record binding implementation:** Bind `human_id` to operator registry before non-sim actuator arm. ASP-777 suggested.

### 4.3 Medium-term (carried; v2.5 planning)

- [x] **ADR-0009 implementation (Phase 2):** Full token lifecycle (consumption/refresh), Hermes/Paperclip credential strip, immutable proxy enforcement. — Phase 1 (ASP-540) + Phase 2 (ASP-564) landed.
- [x] **TLS by default:** Implemented via ASP-684.
- [x] **Anomaly detector live consumer:** Wired via ASP-687.
- [ ] **NATS nkey migration (continued):** ASP-536 added nkey-only gen mode; residual: nkey-only CI, SYS account, `nk` availability.
- [ ] **Automated ACL drift detection:** Design-only. Tracked by ASP-805.
- [ ] **Security scan CI gate:** `bandit` high-severity report on `src/python`, report-only. Tracked by ASP-806.
- [ ] **Code signing:** Sign `sandbox_run`, `policyexec` binaries; verify at install time.
- [ ] **SIEM/Sentinel integration:** Connect audit events to external SIEM.
- [ ] **ADR-0012 operator binding implementation:** H-024 P0-1 gap; register operator identity before non-sim actuator arm.
- [ ] **Land branches with security impact from backlog:** ASP-365 (cred scrub), ASP-780 (anomaly hardening), ASP-774 (H-024 cell assessment), ASP-820 (D1 baseline) — all on branches, not origin/master.

---

## 5. Changes Since v2.4 (ASP-819 branch, 2026-10-26)

This refresh covers no functional change to origin/master since v2.4 was drafted. No additional security-relevant work has landed on origin/master since the ASP-819 biweekly security threat model refresh (commit 86caa33, 2026-10-26) was authored on a branch.

### Priority observation: Unmerged security backlog is accumulating

The following branches carry security-relevant changes that have not landed on origin/master:

| Branch | Topic | Impact | Age |
|--------|-------|--------|-----|
| ASP-365 (PR 82) | Scrub literal NATS creds from legacy nats/server.conf | Attack surface reduction + partial H-017 | ~1 cycle |
| ASP-780 (PR 83) | Anomaly consumer hardening (TLS-aware connect, bounded map) | Required before systemd enablement | ~1 cycle |
| ASP-782 (PR 79) | Holographic catalog MemoryStore loader | New capability (no security impact) | ~1 cycle |
| ASP-796 (PR 85) | D1 plant-range cell profile (sim-only) | F-023 opened; baseline defined in ASP-820 | ~1 cycle |
| ASP-800 (PR 84) | Weekly architecture review 2026-10-19 | Documentation | ~1 cycle |
| ASP-774 (PR 44) | H-024 cell assessment document | Certification baseline | ~2 cycles |
| ASP-819/ASP-820 | v2.4 threat model + F-023 D1 baseline | Documenting findings and baselines | ~1 cycle (this refresh supersedes) |

### Threats with no status change this cycle

All threat items remain in the same status as documented in v2.4. No new threats have been identified. No old threats have been closed.

---

## 6. Backlog Item Status

| Item | Priority | Status | Action |
|------|----------|--------|--------|
| H-007 (EStop single-human clear) | **Critical** | Covered (ASP-573) | Integration test added |
| H-008 (Propose_act self-auth) | **Critical** | Phase 1 + Phase 2 (ASP-540/564) | Dual-human + token lifecycle + credential strip |
| H-009 (Dual-human collision) | High | **Satisfied** | Identity uniqueness logic tested |
| H-010 (Stale capability tokens) | Medium | **Implemented (ASP-564)** | Short TTL + lifecycle; refuse if expired |
| H-011 (Plaintext NATS creds) | **High** | **Partial (ASP-536)** | nkey-only gen mode; residual: `nk` at gen time, SYS password |
| H-012 (Hardcoded NATS URL) | Medium | Closed (ASP-539) | Config/env refactor |
| H-013 (Missing aspen.* ACL) | **High** | **Closed (ASP-536)** | Template ACLs for all roles |
| H-014 (AppArmor deployment) | Medium | **Satisfied (ASP-374/575)** | Profiles staged; nightly Section 17 |
| H-015 (Audit trail) | **High** | **Closed (ASP-537)** | Publisher + consumer + dashboard; anomaly detector added |
| H-017 (Credential rotation) | Medium | **Open** — 6+ cycles | No rotation cadence, procedure, or expiry enforcement |
| H-019 (Dev-only CI gate) | Medium | **Closed (ASP-574)** | CI gate + nightly Section 16 |
| H-020 (Gatekeeper SPOF) | Medium | **Design only** | Redundancy plan separate |
| H-021 (aspen.sentinel permissions) | Medium | **Closed (ASP-369)** | ACL pivot removed |
| **H-022 (Physical cell HITL vault)** | **Critical** | **Implemented (ASP-432)** | Vault-gate; 19/19 tests; fail-closed |
| **H-023 (Independent estop watchdog)** | **High** | **Implemented (ASP-433)** | `EstopWatchdog` design/sim; live wire = Aspen START |
| **H-024 (IEC 62443-4-2 cell baseline)** | **High** | **P0-2 on tree (ASP-684); assessment not on tree** | TLS default on origin/master. Cell assessment PR 44. P0-1 open. |
| H-HOST-01 (NATS store access) | Low | Active | Existing systemd hardening |
| H-HOST-03 (Stale units) | Low | Check gap | Audit systemd flags |
| H-HOST-04 (Master password env) | Medium | **Open** | Keyring/prompt pattern |
| F-015 (Red lateral) | **High** | Active + live anomaly feed | Anomaly detector live consumer wired (ASP-687); blocking path still deferred |
| F-016 (ACL misconfig) | Medium | Active + F-022 closed | Fail-closed default; edge→alpha removed |
| F-017 (Spoofed heartbeat) | Medium | **Open** | Design doc on tree. No implementation. |
| F-013 (Unpinned model digests) | Low | Implemented (ASP-377) | Post-pull verification |
| F-018 (Exercise state race) | Low | Open | Atomic file write |
| F-019 (Delegated agent no plant) | Low | Informational | Document default |
| F-020 (Data-diode OSINT/ingest) | Medium | **Recipe complete** | Recipe reviewed; awaiting captain proof |
| F-011 (NATS rate limits) | Medium | **Implemented (ASP-375)** | Per-connection + per-account limits |
| F-012 (Cgroup limits) | Medium | **Implemented (ASP-376)** | 8 unit profiles; git-only |
| F-014 (Signed packages) | Medium | **Implemented (ASP-378)** | Verify path ships; ceremony deferred |
| F-022 (Edge→alpha pivot) | **High** | **Closed (ASP-369)** | ACL entry removed |
| **F-023 (D1 cell no baseline)** | Low | **Baseline defined but not landed** | ASP-820 on branch, not origin/master |
| ASP-379 (Tool-anomaly detector) | Low | **Implemented** | R1–R4 observation + live feed |
| ASP-607 (Gatekeeper rate limit) | Medium | **Implemented** | Per-agent sliding window |
| ASP-659 (Flock serialization) | Low | **Implemented** | `check-nightly.sh` flock guard |
| ASP-660 (Systemd count fix) | Low | **Closed** | Docs-only baseline correction |
| ASP-684 (TLS by default) | **High** | **Implemented** | H-024 P0-2 closed |
| ASP-687 (Anomaly consumer) | Medium | **Implemented** | Live feed path active; hardening on branch (ASP-780) |
| ASP-696 (HybridIntel removal) | Low | **Implemented** | Attack surface reduction |
| ASP-721 (NATS install guard) | Low | **Implemented** | CI reliability |
| ASP-730 (Python CI gate) | Medium | **Implemented** | Full test suite as required check |
| ASP-732 (Branch protection) | Low | **Resolved** | 10-context strict merge enforced |
| ASP-365 (NATS cred scrub) | Medium | **Not on origin/master** | PR 82. Partial H-017. |
| ASP-780 (Anomaly hardening) | Low | **Not on origin/master** | PR 83. Pre-service-enable hardening. |
| ASP-782 (Holographic catalog loader) | Low | **Not on origin/master** | PR 79. No security credit. |
| ASP-796 (D1 cell profile) | Low | **Not on origin/master** | PR 85. F-023 baseline defined (ASP-820, branch). |
| ASP-800 (Weekly arch review) | Low | **Not on origin/master** | PR 84. Last landed review is 2026-10-12. |
| ASP-819 (v2.4 threat model) | Low | **Not on origin/master** | Superseded by this v2.5 refresh. |
| ASP-820 (D1 baseline doc) | Low | **Not on origin/master** | On ASP-819 branch. Not merged. |

---

## 7. Attack Paths (STRIDE per zone)

### Z1 → Z2 (Bus → Ops Plant)

| Category | Path | Likelihood | Impact |
|----------|------|------------|--------|
| **S**poofing | Forge ops credentials on NATS bus | Low (accounts + password + TLS) | Critical — full mesh access |
| **T**ampering | Inject modified heartbeat/status | Medium (no integrity check) | High — false node state |
| **R**epudiation | Agent action without audit log | Low (audit publisher + consumer active; anomaly feed) | High — no forensic trail |
| **I**nfo disclosure | Leak via tool output to LLM context | Low (redaction active) | Medium — credential exposure |
| **D**oS | Flood fleet subjects | Low (max_connections, max_payload) | Medium — bus degradation |
| **E**levation | Cross-plant via delegated agent | Low (ACL fail-closed) | High — plant boundary |

### Z2 → Z3 (Ops → Edge)

| Category | Path | Likelihood | Impact |
|----------|------|------------|--------|
| **S**poofing | Impersonate edge node via heartbeat | Medium (no device identity) | Medium — inject into fleet status |
| **T**ampering | Modify edge telemetry | Low (NATS export is stream-only) | Low — telemetry variance |
| **E**levation | Ops agent sending unrestricted commands to edge | Medium (OPS has full mesh subjects) | High — edge host compromise |

### Z4 (Range — Red/Blue Exercise + D1 sim)

| Category | Path | Likelihood | Impact |
|----------|------|------------|--------|
| **S**poofing | Red agent impersonates blue | Low (separate NATS users per side) | Medium — bypass red tool restrictions |
| **E**levation | Red agent escapes range plant | Low (ACL isolation + NATS boundary) | Critical — production plant access |
| **T**ampering | Exercise state file race | Low (atomic write) | Medium — early/late exercise termination |
| **E**levation | D1 sim profile reused for physical cell | Low (profile not shipped by build-deb) | Critical — no security baseline applied (F-023) |

---

## 8. Recommendations for This Cycle

### P0 — Land unmerged security branches (accumulating backlog)

1. **[ ] Land anomaly consumer hardening (ASP-780, PR 83).** TLS-aware NATS connect, bounded actor map, dedupe seen-set, 16 new + 1 live-module tests. Required before systemd enablement of anomaly feed.

2. **[ ] Land NATS legacy credential scrub (ASP-365, PR 82).** Replaces literal creds in `nats/server.conf` with placeholders; hermetic test prevents recurrence. Partial H-017 progress.

3. **[ ] Implement NATS credential rotation cadence (H-017).** Open for 6+ cycles. Define a 90-day cadence with dry-run procedure. No live broker rotation.

4. **[ ] Node fingerprint for fleet heartbeat (F-017).** Implement from `docs/security/f-017-fleet-node-fingerprint.md` design. Add fingerprint field to register/heartbeat payload; ops-manager validates against allowlist.

### P1 — Next sprint

5. **[ ] ADR-0012 operator binding (H-024 P0-1, ASP-777).** Bind `human_id` to a persistent operator registry before non-sim actuator arm. ADR-0012 stays Proposed; do not implement from this refresh alone.

6. **[ ] NACL drift fixture (ASP-805).** Compare `config/fleet.yaml` to committed baseline; print audit-shaped report. No host cron.

7. **[ ] Bandit CI report job (ASP-806).** High-severity `bandit` on `src/python`, report-only. Not a required check.

### P2 — v2.6 planning

8. **[ ] NATS nkey migration (continued).** Residual of ASP-536: nkey-only CI, SYS account, `nk` availability.

9. **[ ] Replace env-based master password (H-HOST-04).** Keyring or prompt. Env fallback must warn.

10. **[ ] SIEM/Sentinel integration.** Audit events stay on local journal until a captain asks for an external sink.

11. **[ ] Code signing.** Sign `sandbox_run`, `policyexec`, `starshipd` after a captain key ceremony.

---

*End of threat model v2.5. Next refresh: 2026-11-16.*