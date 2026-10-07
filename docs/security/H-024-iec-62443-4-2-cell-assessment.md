# H-024: NIST CSF / IEC 62443-4-2 formal assessment for cell deployment

**Status:** BASELINE ASSESSMENT (docs only)  
**Issue:** ASP-434 · Parent ASP-431 (Biweekly Security Threat-Model refresh)  
**Date:** 2026-09-22  
**Author:** Aspen (Paperclip)  
**Threat model SoR:** `docs/SECURITY_THREAT_MODEL_v2.2.md` §3.4  
**Scope of this document:** Gap analysis and identity role map only.  
**Explicit non-goals:** No Auditor wake. No live host apply. No firewall/SSH/AppArmor enforce. No physical cell commissioning.

---

## 1. Purpose

Before any **production manufacturing cell** is commissioned on Aspen OS, establish a formal baseline against:

1. **IEC 62443-4-2** component requirements in the band **CR 2.1 – CR 4.3** (use control → system integrity → data confidentiality → resource availability facets as implemented in AspenOS controls).
2. **NIST CSF 2.0** functions (Govern / Identify / Protect / Detect / Respond / Recover) as a plant-operator communication layer.
3. **Aspen OS identity model → IEC 62443 human/system roles** (operator, engineer, maintainer, viewer) so dual-human gates and NATS accounts map to industrial language.

This is the H-024 deliverable referenced from the ASP-431 threat-model cycle. It freezes a **readiness verdict** and a **gap backlog**. Implementation tickets are out of scope here unless Captain opens them.

---

## 2. Assessment boundary

| In scope | Out of scope |
|----------|--------------|
| Repo-committed controls (NATS ACLs, fleet_policy, gatekeeper, audit, packaging gates) | Live `aa-enforce`, SSH+UFW apply, NATS secret rotate on host |
| Cell profile assumptions: light-cell + full-plant (ADR-0009) | Physical robot arm / G9+ non-sim arm without ADR-0012 binding |
| Identity & authorization model as designed | Third-party SIEM product selection |
| CR 2.1–4.3 deep dive | Full CR 1.x / CR 5.x certification package (summarized only where they block 2.x–4.x) |
| NIST CSF mapping for cell ops brief | Formal accredited 62443 certification body engagement |

**Target SL-C (capability) intent for first production cell:** **SL-2** for authorization and zone boundary; **SL-1–2** for confidentiality/integrity of bus traffic until TLS-by-default lands. Not claiming certified SL-T or SL-A.

---

## 3. Aspen identity model → IEC 62443 roles

IEC 62443-4-2 / plant practice typically separates **human** roles (who may change configuration or command actuators) from **software process** identities. Aspen today has three identity planes that must be mapped explicitly.

### 3.1 Identity planes

```text
┌──────────────────────────────────────────────────────────────┐
│ Plane A — Human principals (manufacturing liability)         │
│  ADR-0012 operator registry → stable human_id                │
│  DualHumanGate / authorize_clear / propose_act authorizers   │
│  Presentation: Matrix, Sentinel HMI, voice (display only)    │
└────────────────────────────┬─────────────────────────────────┘
                             │ bound session → NATS SoR
┌────────────────────────────▼─────────────────────────────────┐
│ Plane B — Fleet / agent roles (runtime duty)                 │
│  config/fleet.yaml roles: proxy, romi, ergo, ops,            │
│  plant-controller, red-team, blue-team                       │
│  NATS accounts: OPS / EDGE / RANGE / TELEM (+ SYS)           │
│  Tool ACL via agents/fleet_policy.py                         │
└────────────────────────────┬─────────────────────────────────┘
                             │ capability tokens (ADR-0009)
┌────────────────────────────▼─────────────────────────────────┐
│ Plane C — OS / process identity                              │
│  systemd User=agnetic / nats; AppArmor profiles              │
│  package class Core / Plugin / Dev-only (ADR-0008)           │
└──────────────────────────────────────────────────────────────┘
```

### 3.2 Normative role map (cell deployment)

| IEC 62443 role (human / org) | Aspen binding | May authorize dual-human? | Typical NATS / tool surface | Notes |
|------------------------------|---------------|---------------------------|-----------------------------|-------|
| **Operator** | `human_id` in plant operator registry with role `operator`; UI “run cell / clear estop / accept propose_act” | **Yes** (primary) | Publish `aspen.edge.<node>.authorize`, `aspen.safety.authorize_clear`; subscribe fleet status + sentinel incidents | OoR may also be operator when proposing from HMI; self-approval still forbidden (ADR-0012) |
| **Engineer** | Registry role `engineer`; change cell recipe, ACL allow-lists, gatekeeper capability manifests, plant profile | **Yes** (second principal preferred for config-affecting acts) | Ops-scoped subjects; config write paths gated; no raw ROS2/OPC-UA without gatekeeper | Must not hold RANGE red-team creds on production plants |
| **Maintainer** | Registry role `maintainer`; package update, host restart windows, AppArmor/profile reload, secret rotation runbooks | **Conditional** — yes for safety clear only if dual-human policy allows; **no** sole approval for actuator `execute_act` | Host/ops tooling; update.sh verify path (CR 3.4); rotation scripts | Production cell: maintainer actions audit to `aspen.sentinel.audit.event` |
| **Viewer** | Registry role `viewer` / read-only Sentinel dashboard / telem subscribe | **No** | Subscribe status, telemetry, audit **read**; no authorize, no propose_act grant | Maps to TELEM-like least privilege; never OPS full mesh |
| **Service / agent (non-human)** | Paperclip agents, Hermes faces, micro-agents, LangGraph | **Never** as dual-human principals | `propose_act` only on safety-adjacent; capability tokens via gatekeeper | ADR-0012 §3 table — service IDs never count as humans |
| **Red-team (exercise only)** | `red-team` role, plant-range, isolation: true | **No** on production cell | Restricted toolset; no OPS import | Must not appear on plant-alpha production profile |

### 3.3 NATS account ↔ IEC zone/role (summary)

| NATS account | Fleet team | IEC-aligned use on cell | Production cell? |
|--------------|------------|-------------------------|------------------|
| STARSHIP_OPS | ops | Plant C2, engineer/operator console bus | Yes (ops-manager node) |
| STARSHIP_EDGE | edge | Cell controller / edge RRM | Yes (cell node) |
| STARSHIP_RANGE | red/blue | Training range only | **No** on production cell hosts |
| STARSHIP_TELEM | telem | Viewer / SIEM-style feed | Optional read path |
| SYS | system | NATS admin | Break-glass only |

### 3.4 Gaps in identity (blockers for certified cell language)

| ID | Gap | Severity for cell deploy | Mitigation path (not this ticket) |
|----|-----|--------------------------|-----------------------------------|
| ID-1 | ADR-0012 operator registry **not implemented** on non-sim; free-string `human_id` in sim | **High** for G9+ physical | Implement registry + bind before non-sim arm |
| ID-2 | No MFA / PKI device identity for humans or nodes (CR 1.1 partial; F-017 open) | Medium–High | Node fingerprint + operator session proof |
| ID-3 | OPS account still full mesh (least privilege partial) | Medium | Split ops-viewer vs ops-actuator subjects |
| ID-4 | No automated ACL drift detection (CR 2.5 / 4.3 partial) | Medium | Cron vs `fleet.yaml` → audit event |
| ID-5 | Gatekeeper packaging residual (ASP-628): monorepo source vs plugin default-ON for actuator plants | Medium | Finish plant-profile default ON |

---

## 4. IEC 62443-4-2 CR 2.1 – CR 4.3 gap analysis

Status vocabulary (this assessment):

| Status | Meaning |
|--------|---------|
| **Satisfied** | Control exists in repo, tested or nightly-gated, suitable for cell *design* baseline |
| **Partial** | Control exists but missing production defaults, automation, or binding |
| **Open** | Required for claimed SL on cell; not yet adequate |
| **N/A (deferred)** | Explicitly out of first cell SL claim |

Evidence anchors cite threat model §3.4 and closed ASP tickets. Refresh date of threat model: **2026-09-21**.

### 4.1 CR 2.x — Use control (authorization)

| CR | Title (short) | Aspen control | Status | Evidence | Cell residual |
|----|---------------|---------------|--------|----------|---------------|
| **CR 2.1** | Authorization enforcement | `fleet_policy.py` tool ACL; NATS subject permissions; gatekeeper capability check | **Satisfied** | TM §3.4; ASP-536 aspen.* ACLs; ASP-540/564/607 gatekeeper | Live NATS conf regenerate on cell host still manual residual |
| **CR 2.2** | Wireless / portable authorization | Not a first-class wireless product surface; remote sessions via Hermes/Simplex | **Partial** | CR 1.5 partial in TM | Treat remote HMI as CR 2.4 remote access; no separate wireless CR claim |
| **CR 2.3** | Dual approval / use control for critical functions | Dual-human `propose_act`→`authorize`; estop dual-clear | **Satisfied** (sim + code) | ASP-538, ASP-540, ADR-0009, ADR-0012 design | **Physical cell blocked** on unbound `human_id` (ID-1) |
| **CR 2.4** | Restriction of mobile / remote logical access | Plant isolation; range default isolated; F-022 edge→alpha deny | **Satisfied** | ASP-369; fleet.yaml `same_plant_only` | Production cell must not enable plant-range roles |
| **CR 2.5** | Configurable access rights review | fleet.yaml ACL + biweekly threat model | **Partial** | TM §3.4 | No automated drift (open item TM §4.3) |
| **CR 2.6–2.13** (session lock, least privilege config mgmt, etc.) | Various | Partial coverage via short-TTL tokens (ASP-564), rate limit (ASP-607), systemd non-root | **Partial / N/A band** | ASP-564 TTL 15m; ASP-607 | Session lock / concurrent session limits not productized for HMI |

**CR 2.x cell verdict:** Design baseline **pass for SL-2 authorization** *in software*. Production arm requires ADR-0012 binding (ID-1) before claiming use-control on physical actuators.

### 4.2 CR 3.x — System integrity

| CR | Title (short) | Aspen control | Status | Evidence | Cell residual |
|----|---------------|---------------|--------|----------|---------------|
| **CR 3.1** | Communication integrity | NATS JetStream; optional TLS | **Partial** | TM §3.4 | TLS not default; enable `STARSHIP_NATS_TLS=1` on cell firstboot |
| **CR 3.2** | Malicious code protection / input validation (product facet) | Tool sandbox, Droid Shield, redaction; (TM maps malicious code under CR 5.2) | **Satisfied** (host/tool) | SECURITY.md sandbox; CR 5.2 Satisfied in TM | Keep Dev-only out of cell images (ASP-574) |
| **CR 3.3** | Security functionality isolation / zone boundary | Plants ops/edge/range; NATS account boundaries; OT firewall **draft** templates | **Satisfied** (logical); **Partial** (host perimeter) | TM CR 3.3 Satisfied; ASP-372 draft nft only | Apply firewall templates only at Captain-approved commissioning |
| **CR 3.4** | Software integrity / update integrity | gpgv detached verify; CI unsigned fail; Dev-only isolation | **Satisfied** (git/CI) | ASP-378, ASP-574 | Real signing ceremony deferred; placeholder dev key not for customer cell |
| **CR 3.5–3.14** (audit non-repudiation facets spill into 4.x; code signing binaries) | sandbox_run/policyexec signing open | **Open** (code signing) | TM §4.3 medium-term | Sign native helpers before high-assurance cell |

**CR 3.x cell verdict:** Logical zone integrity **OK**. Bus TLS default and real package signing ceremony are **pre-production residuals**. Host nft apply is **commissioning-gated**, not missing design.

### 4.3 CR 4.x — Data confidentiality & resource availability (selected)

IEC 62443-4-2 CR 4.x covers confidentiality and availability-oriented component requirements. Aspen TM §3.4 tracks:

| CR | Title (short) | Aspen control | Status | Evidence | Cell residual |
|----|---------------|---------------|--------|----------|---------------|
| **CR 4.1** | Information confidentiality (TM: system inventory row uses 4.1 for inventory — see note) | SecretsManager AES-256-GCM; optional TLS; creds mode 600 | **Partial** | TM CR 3.2 / secrets; inventory as CR 4.1 in TM table | Align naming in next TM refresh; confidentiality still TLS-optional |
| **CR 4.1 (TM row)** | System inventory | Fleet heartbeat + register; Fleet Map | **Satisfied** | TM §3.4 | Add node fingerprint (F-017) for spoof resistance |
| **CR 4.2** | Security event logging / (TM) + SR-style secret wipe facets elsewhere | `aspen.sentinel.audit.event` JSONL + JetStream + dashboard | **Satisfied** | ASP-537 | No external SIEM; offline-capable is intentional for dark factory |
| **CR 4.3** | Continuous monitoring / DoS resource management facet | Health checker, telemetry, Sentinel; NATS rate limits (F-011); cgroups (F-012); gate rate limit | **Partial** | ASP-375, ASP-376, ASP-607; TM CR 4.3 Partial | No ACL-drift alert; anomaly detector fail-open only (ASP-379) |

> **Note on CR numbering in TM:** Threat model §3.4 labels **CR 4.1 = system inventory** and folds confidentiality primarily under **CR 3.2**. IEC 62443-4-2 official CR 4.x text emphasizes confidentiality/availability. This assessment preserves TM labels for cross-link stability and flags the naming drift for the next biweekly refresh (ASP-431 lineage). Cell owners should read **both** confidentiality (TLS/secrets) and inventory/monitoring rows before sign-off.

**CR 4.x cell verdict:** Logging baseline **pass**. Continuous monitoring **pass for liveness/telemetry**, **fail for automated policy drift and blocking anomaly response**.

### 4.4 Roll-up scorecard (CR 2.1–4.3)

| Band | Satisfied | Partial | Open | Cell deploy gate |
|------|-----------|---------|------|------------------|
| CR 2.1–2.5 core | 2.1, 2.3*, 2.4 | 2.2, 2.5 | — | *2.3 physical needs ID-1 |
| CR 3.1–3.4 core | 3.3 (logical), 3.4 (CI) | 3.1, 3.3 (host fw) | code signing | TLS default + ceremony before customer cell |
| CR 4.1–4.3 (TM) | 4.1 inventory, 4.2 log | 4.1 conf, 4.3 mon | F-017 | Drift alert recommended pre-prod |

```text
                 CR 2.x use control
            ┌─────────────────────────┐
            │ 2.1 OK  2.3 OK*  2.4 OK │
            │ 2.5 PARTIAL (no drift)  │
            └───────────┬─────────────┘
                        │
                 CR 3.x integrity
            ┌───────────▼─────────────┐
            │ 3.3 zones OK (logical)  │
            │ 3.4 pkg OK (CI/git)     │
            │ 3.1 TLS PARTIAL         │
            └───────────┬─────────────┘
                        │
                 CR 4.x conf / mon
            ┌───────────▼─────────────┐
            │ 4.2 audit OK            │
            │ 4.3 mon PARTIAL         │
            │ inventory OK / PKI open │
            └─────────────────────────┘
```

---

## 5. NIST CSF 2.0 mapping (cell operator brief)

| CSF function | Aspen OS artifacts | Cell readiness | Gaps to cite in ops brief |
|--------------|--------------------|----------------|---------------------------|
| **Govern (GV)** | Master Spec hard rules; CE gates; Paperclip/Linear SoR; fiscal freeze policy | Organizational controls exist | Formal risk acceptance owner for first cell still Captain |
| **Identify (ID)** | Fleet inventory, plants/roles in fleet.yaml, threat model v2.2, this H-024 | **Partial+** | Asset inventory lacks node PKI fingerprint (F-017) |
| **Protect (PR)** | NATS accounts, fleet ACL, gatekeeper, sandbox, AppArmor profiles (staged), signed-package verify path, OT fw drafts | **Partial+** | TLS default off; live aa-enforce / fw apply commissioning-gated; ADR-0012 unbound |
| **Detect (DE)** | Health checker, telemetry bus, sentinel audit, tool-anomaly (fail-open), rate limits | **Partial** | Anomaly not blocking; no ACL drift pager |
| **Respond (RS)** | Incident services, dual-human refuse paths, estop latch, plant isolation | **Partial+** | Runbooks strong in sim; physical HITL path needs bound operators |
| **Recover (RC)** | JetStream durability, offline JSONL audit, package reinstall paths | **Partial** | No formal cell DR table in this assessment; backup of `/etc/starship` creds is ops procedure |

**CSF one-liner for board:** Aspen can **Protect and Detect at design SL-2 intent** for a software-defined cell; **Govern/Identify** are documented; **Respond/Recover** on physical metal still depend on operator binding and host commissioning checklists (ASP-370/372/575 apply gates).

---

## 6. Cell deployment readiness verdict

| Question | Answer |
|----------|--------|
| May we claim a **design-time** IEC 62443-4-2 CR 2.1–4.3 baseline for Aspen OS cell software? | **Yes — with Partials documented** (this file). |
| May we commission a **sim / plant-range** cell? | **Yes**, under existing sim dual-human free-string rules. |
| May we commission a **production actuator cell (non-sim)**? | **No** until: (1) ADR-0012 operator registry binding, (2) TLS-on bus for that plant, (3) real package trust anchor or documented risk acceptance, (4) Captain-approved host fw/AppArmor apply. |
| Auditor required to close H-024 docs? | **No** — board ASP-635 closeout: docs only, no Auditor wake. |
| Live host apply in this ticket? | **No.** |

### 6.1 Production cell entry checklist (future; not executed here)

1. [ ] Operator registry populated (operator / engineer / maintainer / viewer) with bound `human_id`.
2. [ ] Two distinct humans dry-run authorize + estop clear on target plant profile.
3. [ ] NATS accounts mode + TLS; no RANGE credentials on cell hosts.
4. [ ] `fleet.yaml` ACL review signed by engineer role; drift job scheduled or accepted risk.
5. [ ] Gatekeeper profile `light-cell` or `full-plant` default ON for actuators (ASP-628).
6. [ ] Package verify against non-placeholder key **or** written risk acceptance.
7. [ ] nft cell templates composed + `nft -c` checked; apply only with Captain approval.
8. [ ] AppArmor profiles loaded per ASP-575 posture decision (enforce vs complain is separate approval).
9. [ ] Sentinel audit consumer reachable offline-first; anomaly detector at least observing.
10. [ ] This H-024 assessment attached to cell commissioning record.

---

## 7. Gap backlog (tracking only)

Prioritized for **next** hardening slices — do not implement under ASP-434.

| Priority | Gap | Suggested follow-up | Blocks production cell? |
|----------|-----|---------------------|-------------------------|
| P0 | ADR-0012 operator-of-record binding implementation | New ASP under safety/edge | **Yes** (actuators) |
| P0 | TLS default on cell firstboot templates | TM §4.3 item | **Yes** (customer claim) |
| P1 | Automated ACL drift → `aspen.sentinel.audit.event` | TM open item | Strongly recommended |
| P1 | F-017 node fingerprint on heartbeat | TM §4.2 | Spoof resistance |
| P1 | Package signing ceremony (leave placeholder) | ASP-378 residual | Customer cell |
| P2 | Wire tool-anomaly to live consumer (blocking optional) | ASP-379 residual | No (detect quality) |
| P2 | Split OPS least privilege (viewer vs actuator bus) | Identity ID-3 | Hardening |
| P2 | TM §3.4 CR 4.x label reconcile vs IEC text | Next ASP-431 refresh | Docs clarity |
| P3 | Native binary code signing | TM §4.3 | High-assurance only |
| P3 | External SIEM connector | TM §4.3 | Optional |

---

## 8. References

| Doc | Role |
|-----|------|
| `docs/SECURITY_THREAT_MODEL_v2.2.md` | SoR findings + §3.4 CR table |
| `docs/SECURITY.md` | Runtime security architecture |
| `docs/adr/ADR-0009-capability-based-gatekeepers.md` | Capability / dual-auth model |
| `docs/adr/ADR-0012-operator-of-record-binding.md` | Human principal binding (required pre-physical) |
| `docs/adr/ADR-0007-nats-subject-contracts-sentinel-c2.md` | Authz/audit subjects |
| `docs/adr/ADR-0003-fleet-edge-safety-contracts.md` | Safety bus contracts |
| `config/fleet.yaml` | Plants, roles, ACL |
| `docs/security/firewall-templates/` | Draft cell perimeter (ASP-372) |
| `docs/solutions/asp-378-signed-packages.md` | CR 3.4 evidence |
| `docs/solutions/asp-537-sentinel-audit-publisher.md` | CR 4.2 evidence |
| `docs/solutions/asp-540-gatekeeper-dual-human.md` | CR 2.3 evidence |
| `docs/sor/ASPENGROVE_MASTER_SPEC_v4.0.md` | Product hard rules |

---

## 9. Change log

| Date | Change |
|------|--------|
| 2026-09-22 | Initial H-024 baseline assessment (ASP-434). Docs only. |

---

*End of H-024 assessment.*
