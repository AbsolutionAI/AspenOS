# Security Threat Model — Aspen OS / Starship OS (Manufacturing Cell + Fleet)

**Classification:** INTERNAL — Operations Security  
**Asset Owner:** Fleet Security (Auditor) · CEO review: aspen  
**Document ID:** `docs/SECURITY_THREAT_MODEL.md`  
**Version:** 2.2.0  
**Last Refreshed:** 2026-08-22 (ASP-298 biweekly)  
**Prior version:** 2.1.0 (2026-08-10, ASP-168)  
**Next Refresh Due:** 2026-09-05  
**Scope:** Standard manufacturing cell + fleet topology (plant-alpha, plant-edge, plant-range) + Grove control planes (Paperclip/aspen-dev, swarm/RRM, Sentinel HITL path)

**SoR cross-links**
- Master Spec v4.0: `docs/sor/MASTER_SPEC.md` / `ASPENGROVE_MASTER_SPEC_v4.0.md`
- Fleet: `docs/FLEET.md`, ADR-0002…0005, skill `aspen-fleet-edge`
- Host baseline: `docs/security/AUDITOR_BASELINE.md`
- Policy surface: `docs/SECURITY.md`, `config/fleet.yaml`, `agents/fleet_policy.py`

---

## 0. Refresh delta (2026-08-22)

| Change since 2.1.0 | Impact |
|--------------------|--------|
| Master Spec **propose_act + dual human auth** locked | New critical control requirement for OT path; still **not end-to-end wired** to Matrix `#aspen-authz` |
| Fleet packages (swarm-manager, edge-rrm, langgraph-worker) | Expand trust boundaries; micro-agents must remain propose-only |
| BEL-191 edge RRM **hash-chained audit** Done | Positive control on RRM path only — starship tool audit (H-004) still open |
| H-001…H-006 Paperclip children (ASP-169…174) still **backlog** | No material closure of prior CRITICAL/HIGH NATS/sandbox findings |
| `nats/agent-bus.conf` still **no-auth** default | F-001 remains CRITICAL |
| `nats/server.conf` ships **hardcoded token + passwords** | New F-016 (credential hygiene) |
| Paperclip :3100 board plane + workspace validation | New control-plane surface in model (F-019) |
| Host AUDITOR_BASELINE HIGH (SSH root/password, UFW allow-in) | Still open; tracked as host track H-HOST-* |

**Verdict:** Architecture intent improved (safety contracts, plant ACL, edge audit). **Deployed/default posture did not close prior critical gaps.** Zero-trust score remains weak; IEC 62443 still Level 1 / partial toward Level 2.

---

## 1. System topology

### 1.1 Manufacturing cell + fleet (ops plane)

```
  [External / WAN / OSINT] ---- software data-diode (SPEC; not enforced) ----
        |
  [Aspen Sentinel / HITL C2]   dual-human authz (SPEC; Matrix room docs-only)
        |
  [Paperclip + Hermes aspen-dev]   budgets, heartbeats, CE gates
        |
  [Ops Manager / Dashboard :8788]
        |  NATS JetStream  (accounts+TLS intended; agent-bus no-auth default)
   ┌────┴──────────────────────────────┐
   │                                   │
[plant-alpha]                     [plant-edge]
 production mesh                   thin / offline-tolerant
 ├── proxy / romi / ergo           ├── proxy
 ├── plant-controller              └── plant-controller
 └── ops
                                      [plant-range] isolation:true
                                       red-team (tool-capped) / blue-team
```

### 1.2 Actuation stack (ADR-0002 / 0003 / 0005)

```
Cognitive (LangGraph worker) ──propose_act only──┐
SwarmManager (mission DAG, plant ACL, arm gate) ─┼──► Edge RRM (budgets, estop latch, audit)
Micro-agents (sense→decide*) ──propose_act only──┘         │
                                                           ▼
                                                    Drivers (MQTT/OPC-UA/ROS2) — later
```

**Non-negotiables (Master Spec + fleet skill)**
1. Micro-agents / LangGraph never write actuators directly  
2. Safety-adjacent subjects: **`propose_act` only** until **dual human authorization**  
3. `aspen.safety.estop` latches RRM; clear is human  
4. Non-sim arm requires human operator string ≠ `sim`  
5. plant-range never schedules into edge/alpha  
6. Physical cell (BEL-192) blocked until sim green + captain gate  

### 1.3 Data flows

| Flow | Protocol | Auth (intended) | Auth (default lab) | Encryption |
|------|----------|-----------------|--------------------|------------|
| Agent ↔ NATS | TCP 4222 | accounts + nkeys | **none** (agent-bus) or shared token | TLS optional |
| Swarm/RRM/worker bus | NATS or in-process | envelope + plant ACL | in-process skip for CI | N/A in-process |
| Paperclip API | HTTP 3100 | Bearer board/agent key | key on disk | Tailnet preferred |
| Agent ↔ Ollama | HTTP 11434 | none | localhost | loopback |
| Agent tools | local | policy + optional seccomp | Python blocklist only | N/A |
| OSINT → Grove | HTTPS + diode | SPEC software diode | **not enforced** | TLS to source |

---

## 2. Asset inventory & criticality

| Asset | Crit | Notes |
|-------|------|-------|
| NATS / JetStream bus | CRITICAL | Commands, missions, propose_act, estop, telemetry |
| Safety path (estop, arm, propose_act→act) | CRITICAL | Physical harm / production stop |
| Edge RRM + swarm-manager | CRITICAL | Lifecycle, mission arm, plant ACL |
| Fleet policy engine (`fleet_policy.py` + policyexec) | HIGH | Red/blue + cross-plant |
| Tool sandbox (CommandExecutor / sandbox_run) | HIGH | Agent RCE boundary |
| Paperclip board keys + API | HIGH | Org control plane / budget / hire |
| Secrets (NATS, LLM, GitHub, Hermes `.env`) | HIGH | Credential blast radius |
| Edge audit chain (BEL-191) | HIGH | Tamper-evident RRM actions |
| Osquery / StarAgent telemetry | MEDIUM | Detection feed |
| Dashboard :8788 | MEDIUM | Exercise controls, fleet map |
| LangGraph cognitive worker | MEDIUM | Must not become second scheduler |
| Abliterated / local models | MEDIUM | Weaker refusal → policy mandatory |
| Packaging / update path | MEDIUM | Supply chain |

---

## 3. STRIDE by component

### 3.1 NATS message bus

| Threat | S | Risk | Mitigation now | Gap |
|--------|---|------|----------------|-----|
| Spoofed commands / propose_act | S | CRITICAL | Docs: accounts+nkeys; ops firstboot | **agent-bus no auth**; shared token weak |
| Hardcoded server token/passwords in tree | I/S | CRITICAL | gitignore patterns elsewhere | `nats/server.conf` embeds secrets (F-016) |
| Tamper / bus snooping | T/I | HIGH | Optional TLS; account isolation | TLS not default; no message signing |
| Replay of mission/act | R | MEDIUM | JetStream exists | No signed nonce / authz ticket on act |
| Wildcard subject privilege | E | HIGH | Subject sketches | Not enforced without accounts |
| DoS connection flood | D | MEDIUM | max_connections=100 on agent-bus | No auth-rate limits; lab only |

**IEC 62443:** SR 3.1 / 3.3 / 4.1 — still partial; SR 1.4 fail (node enrollment open as H-002).

### 3.2 Command execution / tool sandbox

| Threat | S | Risk | Mitigation now | Gap |
|--------|---|------|----------------|-----|
| Agent RCE / wipe | S | CRITICAL | Blocklists, path allowlists, 50KB/30s | C11 sandbox **optional** (H-003) |
| sudo / priv-esc | E | HIGH | Blocked list | Python-only without policyexec |
| FS tamper | T | HIGH | AppArmor profiles in tree | Not default install (H-010) |
| Resource exhaustion | D | MEDIUM | Timeouts | No cgroups (H-012) |

### 3.3 Fleet ACL / zero trust / plants

| Threat | S | Risk | Mitigation now | Gap |
|--------|---|------|----------------|-----|
| Red-team lateral move | S | CRITICAL | RED_TEAM_ALLOWED; range isolation | Read-only still valuable recon |
| Edge→alpha pivot | S | HIGH | ACL allow list both ways | Explicit **bidirectional** edge↔alpha (F-prior) |
| Rogue node join | S | HIGH | local fleet-node.yaml | No enrollment/attestation (H-002) |
| Ops unrestricted tools | E | HIGH | Role catalog | ops allowlist missing (H-005) |
| Cross-plant during exercise | S | HIGH | red deny + isolation | Depends on exercise_active state file integrity |

### 3.4 Safety / OT manufacturing path (NEW depth in 2.2)

| Threat | S | Risk | Mitigation now | Gap |
|--------|---|------|----------------|-----|
| Direct act bypassing dual-human | S/E | CRITICAL | Spec + package design | **E2E dual-human gate not wired** (F-017 / H-016) |
| LangGraph/mission dual-scheduler | T | HIGH | ADR-0005: propose_act only | Process/org drift risk (F-018) |
| Estop clear by compromised agent | E | CRITICAL | clear = human intent | Bus auth weak ⇒ clear spoof risk if subject open |
| Sim→prod arm confusion | E | HIGH | ASPEN_SIM + operator≠sim | Need production dual-auth + policy env fail-closed |
| OT protocol bridge abuse | S | HIGH | No drivers in prod cell yet | Firewall/diode templates still open (H-008) |
| Audit gap on starship tools | R | HIGH | RRM hash chain Done | Agent tool audit missing (H-004) |

### 3.5 Secrets & supply chain

| Threat | S | Risk | Mitigation now | Gap |
|--------|---|------|----------------|-----|
| LLM context secret leak | I | HIGH | Redaction patterns | Pattern gaps |
| Secrets in repo | I | CRITICAL | gitignore | **server.conf passwords present** (F-016) |
| Model supply chain | T | MEDIUM | Policy for abliterated | No hash pin (H-013) |
| Unsigned packages | T | MEDIUM | deb layout checks | No signatures (H-014) |

### 3.6 Control plane — Paperclip / Hermes (NEW)

| Threat | S | Risk | Mitigation now | Gap |
|--------|---|------|----------------|-----|
| Board key theft ⇒ full org control | E | HIGH | File mode 600 habit | No rotation SLA; multi-company blast |
| Workspace cwd escape / wrong tree | T | MEDIUM | workspace_validation_failed gate | Must keep project cwd = git root |
| Agent runaway spend | D | MEDIUM | budgets + fiscal freeze | Budget $0 = unlimited anti-pattern |
| Unauthenticated bind of C2 ports | S | HIGH | Tailnet preferred | Host UFW default-allow (baseline HIGH-03) |

### 3.7 Host / cell perimeter (from AUDITOR_BASELINE)

| ID | Finding | Severity | Status |
|----|---------|----------|--------|
| HIGH-01 | PermitRootLogin yes | HIGH | Open |
| HIGH-02 | PasswordAuthentication yes | HIGH | Open |
| HIGH-03 | UFW default allow incoming | HIGH | Open (draft only PROTECT-1) |
| MED-* | fail2ban jails, sysctl | MEDIUM | Open |

---

## 4. Zero-trust posture

| Principle | 2.1 | 2.2 | Notes |
|-----------|-----|-----|-------|
| Verify explicitly | FAIL | FAIL | Still no node enrollment; agent-bus no-auth |
| Least privilege | PARTIAL | PARTIAL | Red capped; ops open; propose_act design helps OT |
| Assume breach | PARTIAL | PARTIAL+ | Edge audit chain helps RRM forensics |
| Continuous validation | PARTIAL | PARTIAL | Osquery + RRM audit; no tool audit H-004 |
| Never trust / always verify | FAIL | FAIL | No mTLS default; dual-human not enforced |

**Score: 2.6/5** (was 2.5) — +0.1 for RRM hash-chain + documented propose_act architecture only. **Not a production manufacturing posture.**

---

## 5. IEC 62443 gap analysis (manufacturing profile)

| Requirement | Status | Evidence / gap |
|-------------|--------|----------------|
| SR 1.1 Human user ID | PARTIAL | HITL dual-human specified; not enforced in software path |
| SR 1.4 Identifier management | FAIL | No node enrollment (H-002) |
| SR 2.1 Authorization enforcement | PARTIAL | fleet_policy + sandbox optional |
| SR 2.5 Input validation | PARTIAL | Tool allowlists; weak command sanitize |
| SR 3.1 / 3.3 AuthN | PARTIAL→FAIL default | accounts mode not default lab |
| SR 4.1 Confidentiality | PARTIAL | TLS optional |
| SR 4.2 Persistence / rotation | FAIL | No automated secret rotation (H-007) |
| SR 4.3 Cryptography | PASS (available) | AES-GCM secrets helper; TLS available |
| SR 5.1 / 5.2 Network segmentation | PARTIAL | Plant ACL logical; host UFW weak |
| SR 6.1 Audit | PARTIAL | RRM chain yes; tool path no |
| SR 7.1 Segmentation | PARTIAL | NATS accounts + plant isolation |
| SR 7.3 Least privilege | PARTIAL | Red yes; ops no |
| SR 7.5 Resource limits | FAIL | No cgroups (H-012) |
| SR 8.1 Malicious code | PARTIAL | Blocklist only |

**Maturity:** **SL-T / SL 1 (Initial)** with architecture aiming at **SL 2** once H-001…H-006 + dual-human gate land.  
**Target for dark-factory cell:** SL 2 network + application for C2/OT bridge before physical (BEL-192).

---

## 6. Risk register

### Still open from 2.1 (unchanged severity)

| ID | Finding | Sev | Track |
|----|---------|-----|-------|
| F-001 | agent-bus zero auth default | CRITICAL | H-001 / ASP-169 |
| F-002 | No node enrollment | CRITICAL | H-002 / ASP-170 |
| F-003 | Optional C11 sandbox/policyexec | HIGH | H-003 / ASP-171 |
| F-004 | ops unrestricted tools | HIGH | H-005 / ASP-173 |
| F-005 | TLS optional / no mTLS | HIGH | H-006 / ASP-174 |
| F-006 | No starship tool audit trail | HIGH | H-004 / ASP-172 |
| F-007 | No secret rotation | MEDIUM | H-007 (create if missing) |
| F-008 | No OT/ICS firewall template | MEDIUM | H-008 |
| F-009 | Cred file mode not enforced | MEDIUM | H-009 |
| F-010 | AppArmor not default | MEDIUM | H-010 |
| F-011 | Weak NATS rate limits | MEDIUM | H-011 |
| F-012 | No per-agent cgroups | MEDIUM | H-012 |
| F-013 | No model hash pin | LOW | H-013 |
| F-014 | Unsigned packages | LOW | H-014 |
| F-015 | No behavioral anomaly | LOW | H-015 |

### New in 2.2

| ID | Finding | Sev | Track |
|----|---------|-----|-------|
| F-016 | Hardcoded NATS token/passwords in `nats/server.conf` | CRITICAL | **H-017** |
| F-017 | Dual-human authorize path for propose_act→act not implemented end-to-end | CRITICAL | **H-016** |
| F-018 | Risk of dual mission schedulers (Paperclip vs LangGraph/swarm) | HIGH | **H-018** |
| F-019 | Paperclip C2 surface (keys, bind, multi-company) under-modeled | HIGH | **H-019** |
| F-020 | Software data-diode (Master Spec) not enforceable control | MEDIUM | **H-020** |
| F-021 | Host SSH/UFW baseline HIGH items still open | HIGH | **H-HOST-01** (human apply) |
| F-022 | Bidirectional plant-alpha↔edge ACL enables pivot after edge compromise | HIGH | **H-021** (revisit ACL to default deny edge→alpha or brokered ops only) |

---

## 7. Hardening checklist

### Status legend
`[ ]` open · `[~]` partial · `[x]` done · `[H]` human/sudo gate

### Immediate (P0 — next sprint; freeze-friendly docs/code first)

| ID | Item | Status | Owner | Paperclip |
|----|------|--------|-------|-----------|
| H-001 | NATS accounts+nkeys default; remove no-auth agent-bus default | [ ] | Runtime | ASP-169 |
| H-002 | Fleet node enrollment + signed identity | [ ] | Auditor + Runtime | ASP-170 |
| H-003 | Mandatory C11 sandbox + policyexec fail-closed | [ ] | Runtime | ASP-171 |
| H-004 | Per-agent tool audit JSONL | [ ] | Auditor | ASP-172 |
| H-005 | Ops role minimum tool allowlist | [ ] | Auditor | ASP-173 |
| H-016 | Wire dual-human gate for propose_act→act (Matrix `#aspen-authz` + Sentinel) | [ ] | aspen + Dashboard | **new** |
| H-017 | Scrub hardcoded NATS creds from `nats/server.conf`; generate-only path | [ ] | Runtime | **new** |

### Short-term (P1)

| ID | Item | Status | Owner |
|----|------|--------|-------|
| H-006 | NATS TLS default + mTLS | [ ] | Runtime / ASP-174 |
| H-007 | Automated secret rotation (SR 4.2) | [ ] | Runtime |
| H-008 | OT/ICS firewall rule templates | [ ] | Compliance + Auditor |
| H-009 | Packaging enforces mode 600 on creds | [ ] | packndeploy |
| H-010 | AppArmor install in postinst | [ ] | packndeploy |
| H-018 | CI/architecture guard: single plant scheduler; LangGraph propose_act-only tests | [ ] | robotics + aspen |
| H-019 | Paperclip C2 hardening runbook (tailnet bind, key rotation, workspace git-root) | [ ] | aspen / Runtime |
| H-020 | Software data-diode policy (iptables/nft + process isolation recipe) | [ ] | Auditor |
| H-021 | ACL review: remove or gate edge→alpha direct allow | [ ] | Auditor + aspen |
| H-HOST-01 | Apply AUDITOR_BASELINE SSH+UFW (human approve) | [H] | Human / Auditor |

### Medium-term (P2)

| ID | Item | Status |
|----|------|--------|
| H-011 | NATS rate/connection limits beyond defaults | [ ] |
| H-012 | cgroups per-agent | [ ] |
| H-013 | Model hash pinning | [ ] |
| H-014 | Signed debs / update integrity | [ ] |
| H-015 | Behavioral anomaly on tools | [ ] |

---

## 8. ACL review snapshot (`config/fleet.yaml`)

```yaml
acl:
  default: same_plant_only   # fail-closed default — GOOD
  allow:
    plant-alpha: [plant-edge]
    plant-edge: [plant-alpha]   # RISK: edge compromise → alpha (F-022)
    plant-range: []             # GOOD + isolation:true
```

**Recommendation (H-021):** Prefer `plant-edge → plant-alpha` only via **ops broker subjects** (read status / propose), not general cross-plant tool delegation. Keep range empty.

**Red-team tools:** `read_file`, `list_dir`, `search_files`, `http_get`, `delegate_to_agent` — still correct; never OpenCode/shell/write.

---

## 9. Acceptance for biweekly refresh (this cycle)

- [x] Topology includes Grove control plane + actuation stack  
- [x] ACLs re-reviewed against live `config/fleet.yaml`  
- [x] Zero-trust scored with delta  
- [x] IEC 62443 table updated for propose_act / dual-human  
- [x] Risk register carries forward open F-001…015 + new F-016…022  
- [x] Follow-up hardening tasks created for **new** P0/P1 items  
- [x] Next refresh dated **2026-09-05**

---

## 10. Version history

| Date | Ver | Author | Changes |
|------|-----|--------|---------|
| 2026-08-10 | 2.1.0 | Auditor | Initial full STRIDE + IEC + ZT + H-001…015 |
| 2026-08-22 | 2.2.0 | aspen (ASP-298) | Biweekly: Master Spec/fleet packages, propose_act dual-human gap, RRM audit credit, hardcoded NATS creds, Paperclip C2, ACL pivot finding, checklist status, next due 2026-09-05 |
