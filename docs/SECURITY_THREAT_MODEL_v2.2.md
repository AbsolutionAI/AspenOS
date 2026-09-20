# Security Threat Model — AspenOS v2.2

**Version:** 2.2 · **Refresh:** 2026-09-14 (Biweekly)  
**Author:** Auditor (Paperclip agent 4203b00e)  
**Previous baseline:** ASP-569 (2026-09-07) — H-007–H-021 backlog, F-015–F-019  
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

### 2.2 v2.2 refresh threats (updated 2026-09-07)

| ID | Threat | Asset | Risk (CVSS) | Mitigation | Status |
|----|--------|-------|-------------|------------|--------|
| H-007 | **EStop bypass — single-human clear** | Safety | **9.0** (AV:N/AC:L) | Dual-human `authorize_clear` before `clear` fires; `clear` alone never unlatches | **Covered (ASP-573)** — dedicated negative-case integration test in `scripts/smoke-fleet-bus.py`; pinned `aspen-edge-rrm` gate |
| H-008 | **Propose_act self-authorization** | Actuation | **8.5** (AV:N/AC:L) | Gate must reject single-principal and self-approval; stable audited reasons | **Phase 1 implemented (ASP-540)** — safety-adjacent `propose_act` intercepted, dual-human enforced, bare/1-human forward refused + audited. **Phase 2 (ASP-564)** — token lifecycle (issue/consume/refresh/expire) + `SafetySubjectEnforcer` immutable proxy enforcement of safety subjects |
| H-009 | **Dual-human collision — same principal counted twice** | Authorization | 7.5 (AV:N/AC:M) | Verify distinct `human_id` records in-window; duplicate-principal refuse with reason | **Satisfied (ASP-540)** — `authorize_gate_request` dedupes by `human_id`; duplicate ignored + `gate.authorize.duplicate` audited |
| H-010 | **Stale capability tokens post-expiry** | Gatekeeper | 6.0 (AV:N/AC:L) | Short TTL + NATS auth time window; refuse if expired | **Implemented (ASP-564)** — short-TTL tokens (15 min) with active/consumed/expired lifecycle, refuse-if-expired on consume/refresh, stale cleanup; Phase 1 design in ADR-0009 |
| H-011 | **NATS plaintext credentials on disk** | Secrets | 7.5 (AV:L/AC:L) | nkey-only generator (ASP-536): `gen-nats-accounts.sh` emits `{nkey}` entries and drops plaintext when `nk` present; fallback password on missing `nk`; SYS account excluded | **Partial (ASP-536)** — nkey-only gen mode; residual: `nk` binary required at gen time, SYS account always password |
| H-012 | **scheduler.py hardcoded NATS URL** | Bus | 5.5 (AV:L/AC:H) | `nats://[IP_ADDRESS]:4222` hardcoded — should use env or config | **Closed** (ASP-539) |
| H-013 | **No aspen.* subject ACL in NATS config** | Bus | 7.0 (AV:N/AC:L) | Per-role `aspen.*` ACLs committed in template (ASP-536): ops=sentinel+authz+fleet+safety, edge=fleet+edge+estop+clear, range=scoped fleet/heartbeat; cross-account imports/exports wired | **CLOSED (ASP-536)** — template ACLs for all roles; residual: clients still dual-publish `starship.*` during migration |
| H-014 | **Missing AppArmor profiles in deployment** | Host | 6.5 (AV:L/AC:M) | Profiles exist in `security/apparmor/`; deb postinst loads them (ASP-374); nightly Section 17 verifies wiring; verified in ASP-575 | **Satisfied (ASP-374/575)** — profiles staged + loaded via `postinst` (`apparmor_parser -r`, no enforce); `install-daemon.sh` still unpaired but the deb path is the primary deployment |
| H-015 | **Audit trail not yet connected to aspen.sentinel.audit.event** | Forensics | 6.0 (AV:N/AC:L) | Subject defined (ADR-0007); publisher wired (ASP-537); Sentinel-dashboard consumer added (ASP-537 dashboard endpoints); offline-capable JSONL journal + JetStream durable trail; gatekeeper events covered; backfill replay | **CLOSED (ASP-537)** — publisher + consumer both wired; gateway-agnostic design ensures no event loss |
| H-016 | **LangGraph worker emit-side guard (H-018 completed)** | Mission subjects | 8.0 (AV:N/AC:L) | `aspen_lgw/guard.py`: blocks mission publish; `SwarmManager._busy_plants` prevents dual arm | **CLOSED** (ASP-533) |
| H-017 | **NATS credential rotation — no automatic rotation** | Credentials | 5.5 (AV:A/AC:H) | Manual `gen-nats-accounts.sh` only; no expiry enforcement | **Open** |
| H-018 | **Single-plant dual-arm prevention (H-018)** | Scheduler | 8.0 (AV:N/AC:M) | Dual guard layers: emit-side + scheduler-side | **CLOSED** (ASP-533) |
| H-019 | **Package classification bypass — Dev-only in production** | Supply chain | 6.0 (AV:N/AC:H) | ADR-0008 declares tiers; CI gate `check-no-devonly-in-prod.sh` wired in CI (`security-devonly-isolation`) + nightly Section 16 (ASP-574) | **CLOSED (ASP-574)** — gate script committed; CI + nightly wired; verified clean on current tree |
| H-020 | **Gatekeeper single point of failure** | Availability | 7.0 (AV:N/AC:H) | Mitigate with local fallback + redundant instances (ADR-0009) | **Design only** — Phase 2 (ASP-564) covers token lifecycle + credential strip; redundancy plan tracked separately |
| H-021 | **No dual-publish on aspen.sentinel.* subjects yet** | Observability | 5.0 (AV:N/AC:L) | Migration incomplete; `starship.*` still primary | Mid-migration |

### 2.3 Fleet-specific threats (F- series)

| ID | Threat | Asset | Risk (CVSS) | Mitigation | Status |
|----|--------|-------|-------------|------------|--------|
| F-015 | **Red-team lateral from range to ops** | Plant isolation | 8.0 (AV:A/AC:L) | `check_cross_plant()` rule 3/4: isolation deny; RANGE no import from OPS | **Active** |
| F-016 | **Plant ACL misconfiguration opens cross-plant** | ACL | 6.5 (AV:N/AC:L) | Default `same_plant_only` fail-closed; explicit allow list | **Active** |
| F-017 | **Fleet heartbeat spoofing (register fake node)** | Identity | 7.5 (AV:N/AC:L) | NATS accounts + token; no PKI/fingerprint yet | **Open** |
| F-018 | **Exercise state race — start/stop collision** | Exercise | 5.0 (AV:N/AC:H) | Atomic file write; poll-based check in fleet_policy.py | **Open** |
| F-019 | **Delegated agent without plant tag** | Cross-plant | 6.0 (AV:N/AC:M) | `delegate_to_agent` accepts `plant`/`target_plant`; missing tag defaults no ACL | Informational |
| F-013 | **Unpinned model digests — tag-only ollama pull** | Supply chain / Model integrity | 6.0 (AV:N/AC:H) | Pin all model `FROM` and `ollama pull` to SHA256 digests (`@sha256:...`); verify digest after pull; reject `:latest` tags in production | **Open (ASP-377)** — design spec at `docs/plans/ASP-377.md` |
| F-020 | **Software data-diode missing for OSINT/ingest** | OSINT domain | 6.5 (AV:N/AC:M) | nftables/iptables one-way rules + process isolation + restricted NATS account — see recipe | **Recipe complete** — [Recipe](solutions/asp-368-data-diode-recipe.md) reviewed (AUDITOR_APPROVE); in_review — captain proof required |

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

> **Dual-subject table note:** This table summarises `starship.*` / `agnetic.*` subject permissions, the pre-migration baseline. H-013 (ASP-536) added per-role `aspen.*` ACLs (sentinel, authz, fleet, safety) in the `fleet-accounts.conf.tmpl` — all roles have scoped `aspen.*` publish/subscribe and cross-account imports. The generated conf includes both namespaces. Residual: (a) clients still dual-publish `starship.*` during the `aspen.` prefix migration; (b) live NATS servers need a conf regenerate + reload to enforce. These rows will be folded into a single `Starship + Aspen` table at the next major refresh.

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
| **CR 2.3** — Dual approval for critical actions | `propose_act` -> `authorize` dual-human; estop dual-clear | **Satisfied** — estop dual-clear (ASP-538) + ADR-0009 dual-human gate (Phase 1, ASP-540) |
| **CR 2.4** — Restriction of logical access associated with mobile/remote | Plant isolation, range plant default | **Satisfied** |
| **CR 2.5** — Review of access rights | ACL audit in fleet.yaml; periodic threat model refresh | **Partial** — no automated drift detection |
| **CR 3.1** — Communication integrity | NATS JetStream; optional TLS | **Partial** — TLS not default |
| **CR 3.2** — Communication confidentiality | Optional TLS; SecretsManager AES-256-GCM for stored secrets | **Partial** |
| **CR 3.3** — Zone/conduit boundary | Plant zones (ops/edge/range); NATS account boundaries | **Satisfied** |
| **CR 3.4** — Software update integrity | ADR-0008 package classification; `dpkg` signature; CI gate blocks Dev-only in production (ASP-574) | **Satisfied (ASP-574)** — CI gate + nightly Section 16 enforce classification |
| **CR 4.1** — System inventory | Fleet heartbeat + node register; Fleet Map dashboard | **Satisfied** |
| **CR 4.2** — Security event logging | `aspen.sentinel.audit.event` subject defined (ADR-0007); publisher + consumer wired (ASP-537): JSONL journal + JetStream durable trail + dashboard endpoints; gatekeeper events covered; backfill replay | **Satisfied (ASP-537)** — offline-capable dual-path journal + JetStream; gateway-agnostic; no SIEM integration |
| **CR 4.3** — Continuous monitoring | Health checker, telemetry bus, Sentinel dashboard | **Partial** — no alert on ACL drift |
| **CR 5.1** — Patch management | Debian packaging; systemd unit updates | **Partial** — no vulnerability scanning CI gate |
| **CR 5.2** — Malicious code protection | Tool sandbox, Droid Shield scanning, redaction | **Satisfied** |
| **CR 5.3** — Security functionality verification | Threat model refresh; stress tests (67/69 pass) | **Partial** — no dedicated security scan CI |

---

## 4. Hardening Checklist

### 4.1 Immediate (v2.2 refresh gaps)

- [x] **H-011:** Move NATS credentials from plaintext config to encrypted files or nkey-only auth. `gen-nats-accounts.sh` now emits nkey-only entries when `nk` present (ASP-536); residual: `nk` must be available at generation time, SYS account always password.
- [x] **H-013:** Regenerate NATS accounts config with `aspen.*` subject permissions. Committed in template (ASP-536): all roles have scoped `aspen.*` publish/subscribe + cross-account imports.
- [x] **H-015:** Wire audit publisher to `aspen.sentinel.audit.event`. No forensic trail currently records agent actions.
- [x] **H-008:** Implement gatekeeper shim (ADR-0009). `propose_act` self-authorization is not cryptographically prevented. — **Phase 1 (ASP-540):** safety-adjacent proposal interception + dual-human authorization + refusal of bare/single-human forwards; every decision audited to `aspen.sentinel.audit.event`. **Phase 2 (ASP-564):** capability token lifecycle + credential-strip proxy + immutable safety-subject enforcement.
- [x] **H-009:** Verify dual-human authorization collision logic in `act_gate_contract.md` — distinct principal enforcement must reject duplicates. — **ASP-540:** `authorize_gate_request` ignores duplicate `human_id` (audited `gate.authorize.duplicate`); two distinct in-window approvals required.

### 4.2 Short-term (next 2 sprints)

- [x] **H-007:** Add integration test for estop `clear` — verify single `authorize_clear` alone never unlatches. — **ASP-573:** dedicated negative-case integration test in `scripts/smoke-fleet-bus.py` (H-007 block) + `aspen-edge-rrm` pin bumped to gated master; bare clear and single `authorize_clear` audited `clear_refused_insufficient_auths` and never unlatch.
- [x] **H-012:** Replace hardcoded `nats://[IP_ADDRESS]:4222` in `agents/scheduler.py` with config/env.
- [x] **H-014:** Verify AppArmor profiles load on all deployment targets; fail build if missing.
- [ ] **H-017:** Implement NATS credential rotation procedure or script. Document rotation window.
- [x] **H-019:** Add CI gate to block Dev-only packages from production images.
- [ ] **H-HOST-04:** Replace env-based master password with prompt, keyring, or TPM-backed secret.
- [ ] **F-017:** Add node fingerprint/PKI for fleet heartbeat to prevent registration spoofing.
- [ ] **F-013:** Pin all Ollama model pulls and `FROM` directives to SHA256 digests; reject `:latest` in production. — **ASP-377:** design spec at `docs/plans/ASP-377.md`
- [x] **F-020:** Draft software data-diode recipe for OSINT/ingest. — [Recipe](solutions/asp-368-data-diode-recipe.md) reviewed (AUDITOR_APPROVE); QUEUED — requires dual-human gate before any host firewall apply.

### 4.3 Medium-term (v2.3 planning)

- [x] **ADR-0009 implementation (Phase 2):** Full token lifecycle (consumption/refresh), Hermes/Paperclip credential strip, immutable proxy enforcement. — Phase 1 (proposal interception + dual-human + audit) landed in ASP-540; Phase 2 landed in ASP-564 (`GatekeeperProxy`/`NATSAgentProxy` credential strip, `SafetySubjectEnforcer`, token lifecycle).
- [ ] **TLS by default:** Enable `STARSHIP_NATS_TLS=1` in firstboot templates. Document WAN deployment.
- [ ] **NATS nkey migration (continued):** ASP-536 added nkey-only gen mode; residual work: enforce nkey-only in CI (fail `--password-only` in production builds), migrate SYS account, automate `nk` binary availability. Replace password-based auth across all accounts (partial ASP-536).
- [ ] **Automated ACL drift detection:** Cron job compares live ACL with `fleet.yaml` baseline.
- [ ] **Security scan CI gate:** Integrate `bandit` / `semgrep` into `make check` or CI pipeline.
- [ ] **Code signing:** Sign `sandbox_run`, `policyexec` binaries; verify at install time.
- [ ] **SIEM/Sentinel integration:** Connect audit events to external SIEM or Sentinel dashboard.

---

## 5. Changes Since Last Refresh (ASP-569, 2026-09-07)

| Change | Impact | New threats | Status |
|--------|--------|-------------|--------|
| **H-019 CI gate (ASP-574)** — Dev-only package isolation | CI gate prevents Dev-only tooling in production images; `security-devonly-isolation` CI job + nightly Section 16 | (H-019 → closed) | **CLOSED** — gate script, CI wire, nightly wire, self-test all committed |
| **H-014 AppArmor in deb postinst (ASP-374/575)** | Profiles staged + loaded via `debian/DEBIAN/postinst` (`apparmor_parser -r`); nightly Section 17 verifies 4 checks | (H-014 → satisfied) | **Satisfied** — profile presence, build-deb staging, postinst wiring, no-enforce all verified |
| **H-007 estop integration test (ASP-573)** | Dedicated negative-case test in `smoke-fleet-bus.py`; bare clear + single auth clear refused; dual distinct clear works | None (H-007 → covered) | **Covered** |
| **H-015 audit consumer (ASP-537)** | Dashboard endpoints for Sentinel audit events; offline JSONL journal + JetStream durable trail; gatekeeper events covered | (H-015 → closed) | **CLOSED** — publisher + consumer both wired; gateway-agnostic design |
| **H-008 Phase 2 token lifecycle (ASP-564)** | Credential-strip proxy (`GatekeeperProxy`/`NATSAgentProxy`), `SafetySubjectEnforcer`, token issue/consume/refresh/expire lifecycle | None (H-008 mitigation extended) | **Implemented** — Phase 1 + Phase 2 both landed |
| **ADR-0012 filed** | Operator-of-record binding ADR (Proposed, not implemented) | None (design-only) | Filed as Proposed |
| **Agent Zero removal** | Removed from host; reduces attack surface (legacy service gone) | None | Clean |
| **Nightly check — 2 new sections** | Section 16 Dev-only isolation, Section 17 AppArmor wiring | None | Live since 2026-09-09 |
| **ISO_BUILDER.md** | Documents skip-by-design policy for control-plane host | None | Documentation |

### Threats closed this cycle (since 2026-09-07)

| Item | Reason | Closing evidence |
|------|--------|-----------------|
| H-019 (Dev-only CI gate) | CI gate `check-no-devonly-in-prod.sh` committed; wired in CI (`security-devonly-isolation` + nightly Section 16) | ASP-574: `scripts/check-no-devonly-in-prod.sh` committed, `.github/workflows/ci.yml` job, `scripts/check-nightly.sh` Section 16; self-test script verifies fail-on-planted |
| H-015 (Audit trail) | Publisher wired + JetStream durable stream + dashboard consumer endpoints | ASP-537: `scripts/sentinel-audit.py`, `dashboard/server.py` Sentinel endpoints, JSONL journal + JetStream mirror; gatekeeper events covered |
| H-014 (AppArmor deployment) | Profiles staged + loaded in deb postinst; nightly Section 17 verifies wiring | ASP-374: `debian/DEBIAN/postinst` includes `apparmor_parser -r`; ASP-575: verification report confirming 4-nightly-check criteria met |

### Threats with status change this cycle

| Item | Previous | Current | Rationale |
|------|----------|---------|-----------|
| H-019 (Dev-only CI gate) | Open / ADR-0008 proposed | **CLOSED (ASP-574)** | CI gate script + CI wire + nightly Section 16 + self-test; verified clean |
| H-014 (AppArmor deployment) | Check gap | **Satisfied (ASP-374/575)** | Profiles staged in deb postinst; nightly Section 17 verifies 4 checks |
| H-015 (Audit trail) | Open — consumer pending | **CLOSED (ASP-537)** | Publisher + consumer + dashboard endpoints all wired |
| H-008 (Self-auth) | Phase 1 implemented | **Phase 1 + Phase 2 (ASP-564)** | Token lifecycle + credential-strip proxy landed; only H-020 (SPOF) remains design-only |
| H-010 (Stale tokens) | ADR-0009 design | **Implemented (ASP-564)** | Short TTL + lifecycle; refuse if expired; stale cleanup |

---

## 6. Backlog Item Status

| Item | Priority | Status | Action |
|------|----------|--------|--------|
| H-007 (EStop single-human clear) | **Critical** | Covered | Integration test added (ASP-573) |
| H-008 (Propose_act self-auth) | **Critical** | Gap | Gatekeeper implementation — Phase 1 (ASP-540) dual-human; Phase 2 (ASP-564) token lifecycle + credential strip |
| H-009 (Dual-human collision) | High | Design spec | Verify identity uniqueness logic |
| H-010 (Stale capability tokens) | Medium | **Implemented (ASP-564)** | Short TTL + lifecycle; refuse if expired |
| H-011 (Plaintext NATS creds) | **High** | **Partial (ASP-536)** | nkey-only gen mode; residual: `nk` at gen time, SYS password |
| H-012 (Hardcoded NATS URL) | Medium | Closed (ASP-539) | Config/env refactor |
| H-013 (Missing aspen.* ACL) | **High** | **Closed (ASP-536)** | Template ACLs committed for all roles |
| H-014 (AppArmor deployment) | Medium | **Satisfied (ASP-374/575)** | Profiles staged in deb postinst; nightly Section 17 |
| H-015 (Audit trail) | **High** | **Closed (ASP-537)** | Publisher + consumer + dashboard endpoints |
| H-017 (Credential rotation) | Medium | Open | Rotation procedure |
| H-019 (Dev-only CI gate) | Medium | **Closed (ASP-574)** | CI gate + nightly Section 16 |
| H-020 (Gatekeeper SPOF) | Medium | **Design only (H-008 residual)** | H-008 Phase 2 complete; redundancy plan separate |
| H-021 (No aspen.sentinel permissions) | Medium | Open | Add to NATS config |
| H-HOST-01 (NATS store access) | Low | Active | Existing systemd hardening |
| H-HOST-03 (Stale units) | Low | Check gap | Audit systemd flags |
| H-HOST-04 (Master password env) | Medium | **Open** | Keyring/prompt pattern |
| F-015 (Red lateral) | **High** | Active | Existing isolation |
| F-016 (ACL misconfig) | Medium | Active | Fail-closed default |
| F-017 (Spoofed heartbeat) | Medium | Open | PKI fingerprint |
| F-013 (Unpinned model digests) | Low | **Open (ASP-377)** | Pin to SHA256 digests; reject `:latest` in production |
| F-018 (Exercise state race) | Low | Open | Atomic file write |
| F-019 (Delegated agent no plant) | Low | Informational | Document default |
| F-020 (Data-diode OSINT/ingest) | Medium | **Recipe complete** | [Recipe](solutions/asp-368-data-diode-recipe.md) reviewed (AUDITOR_APPROVE); in_review — captain proof required |

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

1. **[x] Add integration test for estop dual-human clear (H-007).** Dedicated negative-case integration test added in `scripts/smoke-fleet-bus.py` (H-007 block, ASP-573): bare `clear` refused, single `authorize_clear` + `clear` refused, dual distinct `authorize_clear` + `clear` unlatches; audit verified. `aspen-edge-rrm` pin bumped in `third_party/pins.json` to the gated master (`f4f2c8d`+) so CI/nightly clone the gated RRM.

2. **[x] Implement H-019 CI gate — block Dev-only packages from production images.** PACKAGES.md defines three tiers (Core/Plugin/Dev-only). `scripts/check-no-devonly-in-prod.sh` parses PACKAGES.md, scans production paths, fails if any Dev-only path is found. Wired as CI job `security-devonly-isolation` + nightly Section 16. Self-test mode verifies planted markers are detected. **CLOSED (ASP-574).**

3. **[x] Verify AppArmor profiles load on all deployment targets (H-014).** Profiles exist at `security/apparmor/`; `debian/DEBIAN/postinst` stages + loads them via `apparmor_parser -r` (no enforce, ASP-374). Nightly Section 17 verifies: (1) profiles exist in source, (2) `build-deb.sh` stages them, (3) `postinst` runs `apparmor_parser`, (4) `postinst` avoids `aa-enforce`. **Satisfied (ASP-374/575).**

### P1 — Next sprint

4. **[ ] NATS credential rotation procedure (H-017).** Document a rotation workflow: regenerate creds with `gen-nats-accounts.sh`, distribute new `.env` files, restart NATS clients. The script has no expiry enforcement or rotation window — document a 90-day rotation cadence and add a reminder cron.

5. **[ ] Replace env-based master password with keyring or prompt (H-HOST-04).** `AGENTIC_MASTER_PASSWORD` lives in process env and leaks via `/proc` or crash dumps. Migrate to `keyring` backend or prompt-on-startup with TPM-backed sealed secret. Fall back to env only as a last resort with a documented warning.

6. **[ ] Node fingerprint for fleet heartbeat (F-017).** Fleet nodes register with NATS account + token but no PKI identity. A compromised bus credentials file lets an attacker register a fake node. Add a fingerprint field (`ed25519` public key or machine-id hash) to the `aspen.fleet.node.register` / `aspen.fleet.node.heartbeat` payload; ops-manager validates against a known-node allowlist.

### P2 — v2.3 planning

7. **ADR-0009 Phase 2:** Full token lifecycle (consumption/refresh), Hermes/Paperclip credential strip, immutable proxy enforcement, redundancy plan for SPOF (H-020). — Implemented in ASP-564 (except the H-020 redundancy plan, tracked separately).

8. **TLS by default:** Enable `STARSHIP_NATS_TLS=1` in firstboot templates. Document WAN deployment with mutual TLS.

9. **Automated ACL drift detection:** Cron job compares `fleet.yaml` ACL baseline against live fleet state from heartbeats. Report drift events on `aspen.sentinel.audit.event`.

10. **Security scan CI gate:** Integrate `bandit` (Python) and `semgrep` (multi-lang) into `make check` or CI pipeline. Start with critical/high rules only to avoid noise.

11. **Code signing:** Sign `sandbox_run`, `policyexec`, `starshipd` binaries; verify signature at install/start time.

---

*End of threat model v2.2. Next refresh: 2026-09-28.*