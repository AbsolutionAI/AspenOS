# Security Threat Model — AspenOS v2.2

**Version:** 2.2 · **Refresh:** 2026-08-31 (Biweekly)  
**Author:** Auditor (Paperclip agent 4203b00e)  
**Previous baseline:** ASP-431 (2026-08-24) — F-015–F-019, H-022–H-026, H-007–H-015 backlog  
**SoR:** `docs/SECURITY.md` · `docs/FLEET.md` · `docs/adr/ADR-0003` · `docs/adr/ADR-0007` · `docs/adr/ADR-0009`  
**IEC 62443 mapping:** §5.2 (zones/conduits), §3.3 (SLT), §5.3 (defence-in-depth)

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
│     ║  JetStream store, subject routing, auth (accts/token)  ║   │
│     ╚═════╤══════════════════════╤══════════╤═══════════════╝   │
│           │                      │          │                    │
│  ┌────────┴──────┐   ┌──────────┴──────┐   ┌┴──────────────┐   │
│  │ ZONE 2        │   │ ZONE 3          │   │ ZONE 4        │   │
│  │ Ops Plant     │   │ Edge Plant      │   │ Range Plant   │   │
│  │ (plant-alpha) │   │ (plant-edge)    │   │ (plant-range) │   │
│  │ Full tools    │   │ Limited tools   │   │ Red/Blue      │   │
│  │ All agents    │   │ Proxy + ctrlr   │   │ Isolated      │   │
│  └───────────────┘   └─────────────────┘   └───────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

### Zone boundaries

| Boundary | Conduit | Auth | Notes |
|----------|---------|------|-------|
| Z0 → Z1 | NATS client/TLS or localhost | Token / accounts / none | Dev: no auth; prod must use accounts + optional TLS |
| Z2 ↔ Z1 | NATS `starship.*` / `aspen.*` | OPS account, full mesh | Exports to EDGE/TELEM |
| Z3 → Z1 | NATS heartbeat + proxy only | EDGE account, limited subjects | No mission/write subjects |
| Z4 ↔ Z1 | NATS range subjects only | RANGE account, isolated | No imports from OPS/EDGE |
| Agent ↔ Host | Systemd unit / AppArmor | User=agnetic, NoNewPrivileges | Optional sandbox_run + policyexec |

---

## 2. Threat Register

### 2.1 Core threats (carried from v2.1 baseline)

| ID | Threat | Asset | Risk (CVSS) | Mitigation | Status |
|----|--------|-------|-------------|------------|--------|
| H-001 | Agent RCE via tool execution | Shell/host | 8.5 (AV:N/AC:L) | Sandbox blocklists, C11 seccomp, path allowlists, 50KB output limit, 30s timeout | Active |
| H-002 | Lateral movement via red-team agent | Fleet nodes | 7.5 (AV:A/AC:L) | Fleet ACL, tool allowlists, `plant-range` isolation, RED_TEAM_ALLOWED only | Active |
| H-003 | NATS bus spoofed commands | Message bus | 8.0 (AV:N/AC:L) | Accounts/nkeys, token auth, per-subject permissions, optional TLS | Active |
| H-004 | Credential leak in logs/LLM context | Secrets | 6.5 (AV:N/AC:H) | Redaction patterns (password/token/secret/key), SecretsManager AES-256-GCM | Active |
| H-005 | Abliterated local model refusal bypass | Model safety | 7.0 (AV:L/AC:L) | Mandatory policy + sandbox + Droid Shield, never trust model alone | Active |
| H-006 | Cross-plant privilege escalation | Plant isolation | 7.0 (AV:N/AC:M) | `same_plant_only` default ACL, `check_cross_plant()` fail-closed | Active |

### 2.2 v2.2 refresh threats (updated 2026-08-31)

| ID | Threat | Asset | Risk (CVSS) | Mitigation | Status |
|----|--------|-------|-------------|------------|--------|
| H-007 | **EStop bypass — single-human clear** | Safety | **9.0** (AV:N/AC:L) | Dual-human `authorize_clear` before `clear` fires; `clear` alone never unlatches | **Gap: test coverage missing** |
| H-008 | **Propose_act self-authorization** | Actuation | **8.5** (AV:N/AC:L) | Gate must reject single-principal and self-approval; stable audited reasons | **ADR-0009 proposed, not implemented** |
| H-009 | **Dual-human collision — same principal counted twice** | Authorization | 7.5 (AV:N/AC:M) | Verify distinct `human_id` records in-window; duplicate-principal refuse with reason | Design spec req |
| H-010 | **Stale capability tokens post-expiry** | Gatekeeper | 6.0 (AV:N/AC:L) | Short TTL + NATS auth time window; refuse if expired | ADR-0009 |
| H-011 | **NATS plaintext credentials on disk** | Secrets | 7.5 (AV:L/AC:L) | `fleet-accounts.conf` contains passwords in plaintext; `mode 600`, never commit | **Active risk** |
| H-012 | **scheduler.py hardcoded NATS URL** | Bus | 5.5 (AV:L/AC:H) | `nats://[IP_ADDRESS]:4222` hardcoded — should use env or config | **Open** |
| H-013 | **No aspen.* subject ACL in NATS config** | Bus | 7.0 (AV:N/AC:L) | `fleet-accounts.conf` only restricts `starship.*` / `agnetic.*`; `aspen.*` subjects unrestricted | **Open: mid-migration** |
| H-014 | **Missing AppArmor profiles in deployment** | Host | 6.5 (AV:L/AC:M) | Profiles exist in `security/apparmor/` but install script may not run | Check gap |
| H-015 | **Audit trail not yet connected to aspen.sentinel.audit.event** | Forensics | 6.0 (AV:N/AC:L) | Subject defined (ADR-0007) but no publisher; no forensic query path | **Open** |
| H-016 | **LangGraph worker emit-side guard (H-018 completed)** | Mission subjects | 8.0 (AV:N/AC:L) | `aspen_lgw/guard.py`: blocks mission publish; `SwarmManager._busy_plants` prevents dual arm | **CLOSED** (ASP-533) |
| H-017 | **NATS credential rotation — no automatic rotation** | Credentials | 5.5 (AV:A/AC:H) | Manual `gen-nats-accounts.sh` only; no expiry enforcement | **Open** |
| H-018 | **Single-plant dual-arm prevention (H-018)** | Scheduler | 8.0 (AV:N/AC:M) | Dual guard layers: emit-side + scheduler-side | **CLOSED** (ASP-533) |
| H-019 | **Package classification bypass — Dev-only in production** | Supply chain | 6.0 (AV:N/AC:H) | ADR-0008 declares tiers; no CI enforcement yet | ADR-0008 proposed |
| H-020 | **Gatekeeper single point of failure** | Availability | 7.0 (AV:N/AC:H) | Mitigate with local fallback + redundant instances (ADR-0009) | Design only |
| H-021 | **No dual-publish on aspen.sentinel.* subjects yet** | Observability | 5.0 (AV:N/AC:L) | Migration incomplete; `starship.*` still primary | Mid-migration |

### 2.3 Fleet-specific threats (F- series)

| ID | Threat | Asset | Risk (CVSS) | Mitigation | Status |
|----|--------|-------|-------------|------------|--------|
| F-015 | **Red-team lateral from range to ops** | Plant isolation | 8.0 (AV:A/AC:L) | `check_cross_plant()` rule 3/4: isolation deny; RANGE no import from OPS | **Active** |
| F-016 | **Plant ACL misconfiguration opens cross-plant** | ACL | 6.5 (AV:N/AC:L) | Default `same_plant_only` fail-closed; explicit allow list | **Active** |
| F-017 | **Fleet heartbeat spoofing (register fake node)** | Identity | 7.5 (AV:N/AC:L) | NATS accounts + token; no PKI/fingerprint yet | **Open** |
| F-018 | **Exercise state race — start/stop collision** | Exercise | 5.0 (AV:N/AC:H) | Atomic file write; poll-based check in fleet_policy.py | **Open** |
| F-019 | **Delegated agent without plant tag** | Cross-plant | 6.0 (AV:N/AC:M) | `delegate_to_agent` accepts `plant`/`target_plant`; missing tag defaults no ACL | Informational |

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

**Gap:** `aspen.*` subjects are NOT yet in this permission matrix. The migration from `starship.*` to `aspen.*` is mid-flight (ADR-0007 proposed). Until the NATS config is regenerated with `aspen.*` subject entries, any agent with bus access can publish arbitrary `aspen.*` messages.

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
| **Verify explicitly** | Partial | NATS accounts authenticate; tool policy enforces per-call; no PKI for node identity |
| **Least privilege** | Partial | Agents hold role-scoped credentials; red-team subject-limited; OPS still has full mesh |
| **Assume breach** | Partial | Plant-range isolation; fail-closed ACL; no cross-plant trust; gatekeeper not implemented |
| **Never trust, always verify** | Partial | Tool policy checks every call; NATS accounts gate subjects; no attestation/device identity |

### 3.4 IEC 62443 alignment

| Requirement | Control | Status |
|-------------|---------|--------|
| **CR 1.1** — Identify & authenticate users (all human+programmatic) | NATS accounts, per-agent tokens, fleet-node identity | **Partial** — agents authenticated; no MFA, no PKI device identity |
| **CR 1.2** — Software process identity | Systemd `User=agnetic`, capability-based delegation (ADR-0009 proposed) | **Partial** — OS user identity; no code signing |
| **CR 1.5** — Third-party/remote session integrity | Hermes gateway; Simplex bridge (dashboard Connect tab) | **Partial** |
| **CR 2.1** — Authorization enforcement | fleet_policy.py tool ACL, NATS subject permissions | **Satisfied** |
| **CR 2.3** — Dual approval for critical actions | `propose_act` -> `authorize` dual-human; estop dual-clear | **Satisfied** (design) — ADR-0009 pending implementation |
| **CR 2.4** — Restriction of logical access associated with mobile/remote | Plant isolation, range plant default | **Satisfied** |
| **CR 2.5** — Review of access rights | ACL audit in fleet.yaml; periodic threat model refresh | **Partial** — no automated drift detection |
| **CR 3.1** — Communication integrity | NATS JetStream; optional TLS | **Partial** — TLS not default |
| **CR 3.2** — Communication confidentiality | Optional TLS; SecretsManager AES-256-GCM for stored secrets | **Partial** |
| **CR 3.3** — Zone/conduit boundary | Plant zones (ops/edge/range); NATS account boundaries | **Satisfied** |
| **CR 3.4** — Software update integrity | ADR-0008 package classification; `dpkg` signature | **Partial** — no CI gate enforcing Dev-only isolation |
| **CR 4.1** — System inventory | Fleet heartbeat + node register; Fleet Map dashboard | **Satisfied** |
| **CR 4.2** — Security event logging | `aspen.sentinel.audit.event` subject defined (ADR-0007) | **Gap** — no publisher, no storage, no query |
| **CR 4.3** — Continuous monitoring | Health checker, telemetry bus, Sentinel dashboard | **Partial** — no alert on ACL drift |
| **CR 5.1** — Patch management | Debian packaging; systemd unit updates | **Partial** — no vulnerability scanning CI gate |
| **CR 5.2** — Malicious code protection | Tool sandbox, Droid Shield scanning, redaction | **Satisfied** |
| **CR 5.3** — Security functionality verification | Threat model refresh; stress tests (67/69 pass) | **Partial** — no dedicated security scan CI |

---

## 4. Hardening Checklist

### 4.1 Immediate (v2.2 refresh gaps)

- [ ] **H-011:** Move NATS credentials from plaintext config to encrypted files or nkey-only auth. `fleet-accounts.conf` contains cleartext passwords.
- [ ] **H-013:** Regenerate NATS accounts config with `aspen.*` subject permissions. Current config only covers `starship.*` / `agnetic.*`.
- [ ] **H-015:** Wire audit publisher to `aspen.sentinel.audit.event`. No forensic trail currently records agent actions.
- [ ] **H-008:** Implement gatekeeper shim (ADR-0009). `propose_act` self-authorization is not cryptographically prevented.
- [ ] **H-009:** Verify dual-human authorization collision logic in `act_gate_contract.md` — distinct principal enforcement must reject duplicates.

### 4.2 Short-term (next 2 sprints)

- [ ] **H-007:** Add integration test for estop `clear` — verify single `authorize_clear` alone never unlatches.
- [ ] **H-012:** Replace hardcoded `nats://[IP_ADDRESS]:4222` in `agents/scheduler.py` with config/env.
- [ ] **H-014:** Verify AppArmor profiles load on all deployment targets; fail build if missing.
- [ ] **H-017:** Implement NATS credential rotation procedure or script. Document rotation window.
- [ ] **H-019:** Add CI gate to block Dev-only packages from production images.
- [ ] **H-HOST-04:** Replace env-based master password with prompt, keyring, or TPM-backed secret.
- [ ] **F-017:** Add node fingerprint/PKI for fleet heartbeat to prevent registration spoofing.

### 4.3 Medium-term (v2.3 planning)

- [ ] **ADR-0009 implementation:** Full gatekeeper shim with capability tokens, dual-human authorization, audit logging.
- [ ] **TLS by default:** Enable `STARSHIP_NATS_TLS=1` in firstboot templates. Document WAN deployment.
- [ ] **NATS nkey migration:** Replace password-based auth with nkeys across all accounts.
- [ ] **Automated ACL drift detection:** Cron job compares live ACL with `fleet.yaml` baseline.
- [ ] **Security scan CI gate:** Integrate `bandit` / `semgrep` into `make check` or CI pipeline.
- [ ] **Code signing:** Sign `sandbox_run`, `policyexec` binaries; verify at install time.
- [ ] **SIEM/Sentinel integration:** Connect audit events to external SIEM or Sentinel dashboard.

---

## 5. Changes Since Last Refresh (ASP-431, 2026-08-24)

| Change | Impact | New threats | Status |
|--------|--------|-------------|--------|
| ADR-0007 (NATS subject contracts) | Added `aspen.sentinel.*` + `aspen.authz.*` subjects | H-013, H-015, H-021 | Proposed; not wired |
| ADR-0008 (Package classification) | Core/Plugin/Dev-only tiers | H-019 | Proposed; no gate |
| ADR-0009 (Capability-based gatekeepers) | Eliminates broad credentials | H-008, H-010, H-020 | Proposed; not implemented |
| ADR-0006 (Memory store tiering) | T1 local-first + optional T2 PG | (none new) | Accepted |
| H-018 (ASP-533) completed | Dual-guard single-plant scheduler | H-016 → closed | **CLOSED** |
| `aspen.` prefix migration in progress | Dual-publish during transition | H-013, H-021 | Mid-flight |
| Dual-human gate design in ADR-0003 | Rejected duplicate principals | H-009 | Design spec |

### Threats closed this cycle

| Item | Reason | Closing evidence |
|------|--------|-----------------|
| H-016 (LangGraph emit-side guard) | Both guard layers implemented | ASP-533 DONE: `aspen_lgw/guard.py` + `SwarmManager._busy_plants` |
| H-018 (Single-plant dual-arm) | Dual guard prevents second arm on same plant | ASP-533: `PlantBusyError`, `arm_or_propose()` route to `propose_act` |

### New threats this cycle

| ID | Source | Rationale |
|----|--------|----------|
| H-021 | ADR-0007 migration | `aspen.sentinel.*` / `aspen.authz.*` subjects have no publish permissions in NATS accounts config |
| H-HOST-04 | Audit | `AGENTIC_MASTER_PASSWORD` env var places master secret in process env — leaks under /proc or crash dump |
| H-019 | ADR-0008 proposed | No CI gate prevents Dev-only packages from reaching production images |

---

## 6. Backlog Item Status

| Item | Priority | Status | Action |
|------|----------|--------|--------|
| H-007 (EStop single-human clear) | **Critical** | Gap | Add integration test |
| H-008 (Propose_act self-auth) | **Critical** | Gap | Gatekeeper implementation |
| H-009 (Dual-human collision) | High | Design spec | Verify identity uniqueness logic |
| H-010 (Stale capability tokens) | Medium | Design only | ADR-0009 phase |
| H-011 (Plaintext NATS creds) | **High** | **Open** | Encrypt or nkey-only |
| H-012 (Hardcoded NATS URL) | Medium | Open | Config/env refactor |
| H-013 (Missing aspen.* ACL) | **High** | **Open** | Regenerate NATS accounts |
| H-014 (AppArmor deployment) | Medium | Check gap | Verify install script |
| H-015 (Audit trail) | **High** | **Open** | Wire audit publisher |
| H-017 (Credential rotation) | Medium | Open | Rotation procedure |
| H-019 (Package classification CI) | Medium | Open | CI gate |
| H-020 (Gatekeeper SPOF) | Medium | Design only | Redundancy plan |
| H-021 (No aspen.sentinel permissions) | Medium | Open | Add to NATS config |
| H-HOST-01 (NATS store access) | Low | Active | Existing systemd hardening |
| H-HOST-03 (Stale units) | Low | Check gap | Audit systemd flags |
| H-HOST-04 (Master password env) | Medium | **Open** | Keyring/prompt pattern |
| F-015 (Red lateral) | **High** | Active | Existing isolation |
| F-016 (ACL misconfig) | Medium | Active | Fail-closed default |
| F-017 (Spoofed heartbeat) | Medium | Open | PKI fingerprint |
| F-018 (Exercise state race) | Low | Open | Atomic file write |
| F-019 (Delegated agent no plant) | Low | Informational | Document default |

---

## 7. Attack Paths (STRIDE per zone)

### Z1 → Z2 (Bus → Ops Plant)

| Category | Path | Likelihood | Impact |
|----------|------|------------|--------|
| **S**poofing | Forge ops credentials on NATS bus | Low (accounts + password) | Critical — full mesh access |
| **T**ampering | Inject modified heartbeat/status | Medium (no integrity check) | High — false node state |
| **R**epudiation | Agent action without audit log | High (no audit publisher) | High — no forensic trail |
| **I**nfo disclosure | Leak via tool output to LLM context | Low (redaction active) | Medium — credential exposure |
| **D**oS | Flood fleet subjects | Low (max_connections, max_payload) | Medium — bus degradation |
| **E**levation | Cross-plant via delegated agent | Low (ACL fail-closed) | High — plant boundary |

### Z2 → Z3 (Ops → Edge)

| Category | Path | Likelihood | Impact |
|----------|------|------------|--------|
| **S**poofing | Impersonate edge node via heartbeat | Medium (no device identity) | Medium — inject into fleet status |
| **T**ampering | Modify edge telemetry | Low (NATS export is stream-only) | Low — telemetry variance |
| **E**levation | Ops agent sending unrestricted commands to edge | Medium (OPS has full mesh subjects) | High — edge host compromise |

### Z4 (Range — Red/Blue Exercise)

| Category | Path | Likelihood | Impact |
|----------|------|------------|--------|
| **S**poofing | Red agent impersonates blue | Low (separate NATS users per side) | Medium — bypass red tool restrictions |
| **E**levation | Red agent escapes range plant | Low (ACL isolation + NATS boundary) | Critical — production plant access |
| **T**ampering | Exercise state file race | Low (atomic write) | Medium — early/late exercise termination |

---

## 8. Recommendations for This Cycle

### P0 — Act this sprint

1. **Regenerate NATS accounts config with `aspen.*` subjects.** The current `fleet-accounts.conf` only restricts `starship.*` / `agnetic.*`. The `aspen.*` prefix (ADR-0007) has no subject-level ACL. An agent with bus credentials can publish arbitrary `aspen.fleet.mission.*` or `aspen.safety.*` messages without restriction.

2. **Encrypt NATS credentials in fleet-accounts.conf.** Currently 6 cleartext passwords are stored in the config file. Use nkey-only auth or encrypted creds files.

3. **Begin gatekeeper shim implementation** (ADR-0009). At minimum, a local proxy that intercepts `propose_act` on safety-adjacent subjects and enforces dual-human authorization before forwarding.

### P1 — Next sprint

4. **Wire `aspen.sentinel.audit.event` publisher.** Without audit, all agent actions are forensically opaque. Start with a simple JSONL file backed by JetStream.

5. **Replace hardcoded NATS URL in scheduler.py** with `nats_connect.py` helper or env config.

6. **Add integration test for estop clear** — verify dual-human gate prevents single-principal unlatch.

### P2 — v2.3 planning

7. **PKI for node identity** — fleet heartbeat should include a node fingerprint (e.g., TPM or pre-shared public key) to prevent registration spoofing (F-017).

8. **TLS by default** in firstboot templates for WAN deployments.

9. **Automated ACL drift detection** — cron job compares `fleet.yaml` ACL against live fleet state.

---

*End of threat model v2.2. Next refresh: 2026-09-14.*