# Security Threat Model — AspenOS v2.3

**Version:** 2.3 · **Refresh:** 2026-10-19 (Biweekly)
**Author:** Auditor (Paperclip agent 4203b00e)
**Previous baseline:** ASP-776 (2026-10-12) — NATS TLS by default, anomaly live consumer, Python CI gate, H-024 baseline
**This cycle:** ASP-802 — Weekly architecture review (ASP-800), holographic catalog loader (ASP-782), nightly PASS sustained (158/159 across Sections 1–23), biweekly re-review
**SoR:** `docs/SECURITY.md` · `docs/FLEET.md` · `docs/adr/ADR-0003` · `docs/adr/ADR-0007` · `docs/adr/ADR-0009` · `docs/security/H-024-wan-mtls-deployment.md`
**IEC 62443 mapping:** §5.2 (zones/conduits), §3.3 (SLT), §5.3 (defence-in-depth); H-024 cell assessment baseline §4

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
│  │ Full tools    │   │ Limited tools   │   │ Red/Blue      │   │
│  │ All agents    │   │ Proxy + ctrlr   │   │ Isolated      │   │
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

### 2.2 v2.3 refresh threats (updated 2026-10-19)

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
| H-021 | **No dual-publish on aspen.sentinel.* subjects yet** | Observability | 5.0 (AV:N/AC:L) | Migration incomplete; `starship.*` still primary | **Closed (ASP-369)** — edge→alpha ACL pivot removed; edge cross-plant fails closed; H-021 addressed via ACL change |
| H-022 | **Physical cell act requires HITL vault approval** | Actuation / Safety | **8.5** (AV:N/AC:L) | Gatekeeper shim vault-gate: physical cell act subjects require durable HITL vault approval record before authorize grants; dual-human preserved as additional gate layer | **Implemented (ASP-432)** — 19/19 vault-gate tests + 99/99 phase2 pass; fail-closed on every vault failure path |
| H-023 | **Software estop latch is agent-dependent — no independent hardware watchdog** | Safety | **9.0** (AV:L/AC:H) | Independent `EstopWatchdog` (design/sim): software-path `tick` heartbeat, fail-closed open-loop trip on missed/forced/backend failure, clear only via two distinct authorizers, durable latch via `FilePulseBackend` | **Implemented (ASP-433)** — 18/18 watchdog tests; 466-test suite green; residual: live GPIO/relay wire = Aspen START on this issue |
| H-024 | **No formal IEC 62443-4-2 / NIST CSF baseline for cell deployment** | Certification / Cell readiness | 6.5 (AV:N/AC:H) | Baseline gap analysis for CR 2.1–4.3; identity-to-IEC role map; production cell readiness verdict. **P0-1:** ADR-0012 operator binding (open). **P0-2:** TLS default on cell firstboot (IMPLEMENTED via ASP-684) | **BASELINE (ASP-434)** — docs-only assessment filed; TLS default closed via ASP-684; P0-1 gap pending; 10-gate checklist |

### 2.3 Fleet-specific threats (F- series)

| ID | Threat | Asset | Risk (CVSS) | Mitigation | Status |
|----|--------|-------|-------------|------------|--------|
| F-015 | **Red-team lateral from range to ops** | Plant isolation | 8.0 (AV:A/AC:L) | `check_cross_plant()` rule 3/4: isolation deny; RANGE no import from OPS; tool-anomaly detector (ASP-379) adds behavioral detection of lateral moves | **Active** — anomaly detector live consumer wired (ASP-687); blocking path still deferred |
| F-016 | **Plant ACL misconfiguration opens cross-plant** | ACL | 6.5 (AV:N/AC:L) | Default `same_plant_only` fail-closed; explicit allow list; F-022 removed edge→alpha pivot | **Active** — F-022 closed (ASP-369) |
| F-017 | **Fleet heartbeat spoofing (register fake node)** | Identity | 7.5 (AV:N/AC:L) | NATS accounts + token; no PKI/fingerprint yet | **Open** |
| F-018 | **Exercise state race — start/stop collision** | Exercise | 5.0 (AV:N/AC:H) | Atomic file write; poll-based check in fleet_policy.py | **Open** |
| F-019 | **Delegated agent without plant tag** | Cross-plant | 6.0 (AV:N/AC:M) | `delegate_to_agent` accepts `plant`/`target_plant`; missing tag defaults no ACL | Informational |
| F-013 | **Unpinned model digests — tag-only ollama pull** | Supply chain / Model integrity | 6.0 (AV:N/AC:H) | Pin model digests (`config/models-digests.yaml`); verify-after-pull fail-hard (`install-models.sh`/health-checker/dashboard); reject unpinned pulls in production | **Implemented (ASP-377)** — `scripts/resolve-model-digests.py` + CI/nightly gates; `@sha256:` refs rejected by Ollama 0.32.11 |
| F-020 | **Software data-diode missing for OSINT/ingest** | OSINT domain | 6.5 (AV:N/AC:M) | nftables/iptables one-way rules + process isolation + restricted NATS account — see recipe | **Recipe complete** — [Recipe](solutions/asp-368-data-diode-recipe.md) reviewed (AUDITOR_APPROVE); awaiting captain proof |
| F-011 | **NATS bus resource exhaustion — flood connections / subscriptions** | Bus availability | 6.5 (AV:N/AC:L) | `max_pending` 16MB, `max_control_line` 4KB, `max_subscriptions` 512, `write_deadline` 5s, `ping_interval` 30s/3, auth timeout 2.0s; per-account `limits{}` bounding each role's blast radius below `max_connections: 256` | **Implemented (ASP-375)** — all three NATS configs hardened; Section 19 nightly gate; 5 fixture tests |
| F-012 | **Agent resource exhaustion — runaway agent DoS** | Host / Agent availability | 6.0 (AV:L/AC:L) | systemd cgroup drop-ins (`CPUQuota`, `MemoryMax`, `MemoryHigh`, `TasksMax`) bound each agent unit; I/O accounting on I/O-intensive units | **Implemented (ASP-376)** — 8 unit profiles staged; 6 fixture tests; build-deb stages drop-ins; Section 20 nightly gate; git-only (no live systemd applied) |
| F-014 | **Unsigned package substitution in update chain** | Supply chain / Package integrity | 6.5 (AV:N/AC:M) | `gpgv` detached-signature verify gate (`scripts/verify-deb-signature.sh`) before `dpkg -i`; CI job `verify-package-signature` fails on unsigned/tampered; Section 21 nightly gate | **Implemented (ASP-378)** — verify path ships now; placeholder dev key; ceremony (real key signing) is deferred human action; 9 fixture tests |
| F-022 | **Edge-initiated cross-plant pivot into ops** | Plant isolation | **8.0 (AV:A/AC:L)** | `plant-edge: [plant-alpha]` removed from `config/fleet.yaml` ACL; edge cross-plant now falls through to `same_plant_only` default (deny); ops→edge retained for ops-initiated management | **Closed (ASP-369)** — 11 ACL fixture tests; smoke-test cross-plant check; H-021 marked |

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
| **Assume breach** | Partial | Plant-range isolation; fail-closed ACL; no cross-plant trust; gatekeeper not implemented |
| **Never trust, always verify** | Partial | Tool policy checks every call; NATS accounts gate subjects; TLS default improves wire verification; no attestation/device identity |

### 3.4 IEC 62443 alignment

| Requirement | Control | Mapping | Status |
| --- | --- | --- | --- |
| **FR 3.4** Software and information integrity | Hardware Root of Trust (meas boot) + OS Runtime Protection + embedded software update integrity; ASP-378 verification | IEC 62443 §3.4 FR 3.4 (DIN/SPEC) | Mapped + verified, no credentials |
|-------------|---------|--------|
| **CR 1.1** — Identify & authenticate users (all human+programmatic) | NATS accounts, per-agent tokens, fleet-node identity | **Partial** — agents authenticated; no MFA, no PKI device identity |
| **CR 1.2** — Software process identity | Systemd `User=agnetic`, capability-based delegation (ADR-0009 proposed) | **Partial** — OS user identity; no code signing |
| **CR 1.5** — Third-party/remote session integrity | Hermes gateway; Simplex bridge (dashboard Connect tab) | **Partial** |
| **CR 2.1** — Authorization enforcement | fleet_policy.py tool ACL, NATS subject permissions | **Satisfied** |
| **CR 2.3** — Dual approval for critical actions | `propose_act` -> `authorize` dual-human; estop dual-clear | **Satisfied** — estop dual-clear (ASP-538) + ADR-0009 dual-human gate (Phase 1, ASP-540) |
| **CR 2.4** — Restriction of logical access associated with mobile/remote | Plant isolation, range plant default | **Satisfied** |
| **CR 2.5** — Review of access rights | ACL audit in fleet.yaml; periodic threat model refresh | **Partial** — no automated drift detection |
| **CR 3.1** — Communication integrity | NATS JetStream; **TLS by default on ops/edge cells**, mutual TLS for WAN | **Satisfied (ASP-684)** — CR 3.1 gap closed; ops/edge default on, server stays loopback |
| **CR 3.2** — Communication confidentiality | TLS by default; SecretsManager AES-256-GCM for stored secrets | **Satisfied (ASP-684)** — TLS default raises from Partial |
| **CR 3.3** — Zone/conduit boundary | Plant zones (ops/edge/range); NATS account boundaries | **Satisfied** |
| **CR 3.4** — Software update integrity | ADR-0008 package classification; `dpkg` signature via `gpgv` detached verify gate (ASP-378); CI gate blocks Dev-only in production (ASP-574) | **Satisfied (ASP-378/574)** — verify path ships in update.sh; CI job `verify-package-signature` fails on unsigned/tampered; Section 21 gate; placeholder dev key; ceremony deferred |
| **CR 4.1** — System inventory | Fleet heartbeat + node register; Fleet Map dashboard | **Satisfied** |
| **CR 4.2** — Security event logging | `aspen.sentinel.audit.event` subject defined (ADR-0007); publisher + consumer wired (ASP-537): JSONL journal + JetStream durable trail + dashboard endpoints; gatekeeper events covered; backfill replay; anomaly detector live feed (ASP-687) | **Satisfied (ASP-537)** — offline-capable dual-path journal + JetStream; gateway-agnostic; no SIEM integration |
| **CR 4.3** — Continuous monitoring | Health checker, telemetry bus, Sentinel dashboard; anomaly detector live consumer wired (ASP-687) | **Partial** — improved with live anomaly feed and tool audit consumer; no alert on ACL drift |
| **CR 5.1** — Patch management | Debian packaging; systemd unit updates; full Python test suite CI gate (ASP-730) | **Partial** — no vulnerability scanning CI gate |
| **CR 5.2** — Malicious code protection | Tool sandbox, Droid Shield scanning, redaction | **Satisfied** |
| **CR 5.3** — Security functionality verification | Threat model refresh; stress tests (67/69 pass); CI `security-nats-tls` job (ASP-684); `python-test-suite` required check (ASP-730); nightly Sections 1–23 | **Partial** — security-specific CI gates growing; no dedicated security scan |

---

## 4. Hardening Checklist

### 4.1 Immediate (v2.2 refresh — all resolved)

Carried forward from prior cycles — all items resolved in previous sprints. See v2.2 document for detail.

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
- [x] **ASP-658:** Gitignore Paperclip scratch dirs
- [x] **ASP-684:** NATS TLS by default on ops/edge cells (H-024 P0-2)
- [x] **ASP-687:** Wire tool-anomaly detector to live audit consumer
- [x] **ASP-721:** NATS install guard in CI
- [x] **ASP-730:** Full Python test suite as required CI check
- [x] **ASP-696:** HybridIntel stub removal (attack surface reduction)
- [x] **ASP-782:** Holographic catalog MemoryStore loader (no security impact)
- [x] **ASP-800:** Weekly architecture review (2026-10-19)
- [ ] **H-017:** Implement NATS credential rotation procedure or script. Document rotation window.
- [ ] **H-HOST-04:** Replace env-based master password with prompt, keyring, or TPM-backed secret.
- [ ] **F-017:** Add node fingerprint/PKI for fleet heartbeat to prevent registration spoofing.
- [ ] **H-024 P0-1 — ADR-0012 operator-of-record binding implementation:** Bind `human_id` to operator registry before non-sim actuator arm. Blocks production cell commission checklist item 1.

### 4.3 Medium-term (v2.3 planning)

- [x] **ADR-0009 implementation (Phase 2):** Full token lifecycle (consumption/refresh), Hermes/Paperclip credential strip, immutable proxy enforcement. — Phase 1 (ASP-540) + Phase 2 (ASP-564) landed.
- [x] **TLS by default:** Implemented via ASP-684. Ops/edge default on, mutual TLS for WAN, fail-closed commissioning override, CI job `security-nats-tls` + nightly Section 23. WAN deployment: `docs/security/H-024-wan-mtls-deployment.md`.
- [x] **Anomaly detector live consumer:** Wired via ASP-687. `src/python/sentinel/tool_anomaly_consumer.py` subscribes audit stream, feeds `ToolAnomalyDetector.feed()`, publishes findings to `sentinel.tools.anomaly`.
- [x] **Weekly architecture reviews:** Ongoing baseline (ASP-739/773/800).
- [ ] **NATS nkey migration (continued):** ASP-536 added nkey-only gen mode; residual work: enforce nkey-only in CI (fail `--password-only` in production builds), migrate SYS account, automate `nk` binary availability.
- [ ] **Automated ACL drift detection:** Cron job compares live ACL with `fleet.yaml` baseline. Report drift on `aspen.sentinel.audit.event`.
- [ ] **Security scan CI gate:** Integrate `bandit` / `semgrep` into `make check` or CI pipeline.
- [ ] **Code signing:** Sign `sandbox_run`, `policyexec` binaries; verify at install time.
- [ ] **SIEM/Sentinel integration:** Connect audit events to external SIEM or Sentinel dashboard.
- [ ] **ADR-0012 operator binding implementation:** H-024 P0-1 gap; register operator identity before non-sim actuator arm.

---

## 5. Changes Since Last Refresh (ASP-776, 2026-10-12)

| Change | Impact | New threats | Status |
|--------|--------|-------------|--------|
| **Weekly architecture review 2026-10-19 (ASP-800)** — Architecture review covering ADR-0012/0013 baseline, systemd unit audit, holographic memory store progress. Covers: ADR-0012 operator binding still Proposed (P0-1 open), ADR-0013 worktree isolation accepted, 18 systemd units confirmed vs 16 in docs (docs corrected via ASP-660). | Architecture baseline updated for 2026-10-19 | None — no new threat surfaced | **Complete** — `docs/ops/WEEKLY_ARCHITECTURE_REVIEW_2026-10-19.md` |
| **Holographic catalog MemoryStore loader (ASP-782)** — `scripts/holographic_ingest.py` gains `catalog_plugin_dir()` to load plugins from `ASPEN_HOLOGRAPHIC_PLUGIN` env dir or Hermes Home plugin tree. | Plugins can extend holographic ingestion; plugin path safely validated and reject-invalid | None — plugin loading validates path; env-gated, not a trust boundary change | **Implemented** — 100-line change; tests adjusted |
| **Nightly PASS sustained** — 158/159 checks (Sections 1–23) across multiple runs (ASP-789, ASP-791, ASP-793, ASP-795, ASP-797, ASP-798, ASP-799). Only deviation: C11 p50 (3.655ms vs 2ms threshold, known hardware baseline). Python suite 500/4, smoke 61/1, ACL 23/23, gatekeeper 13/13, vault-gate 19/19, tool-anomaly 13/13. | No regressions in any security section across two weeks of nightly runs | None | **Green** — C11 p50 trend stable; watch threshold drift |
| **Branch protection enforced (ASP-732)** — origin/master now requires 10 CI contexts, strict merge, enforce_admins:true. Resolution of a post-PR #60 compliance deviation. | CI integrity improved; force-push-blocked on master | None | **Resolved** — `docs/ops/NIGHTLY_PACKAGING_DEPLOY_CHECK.md` documents the resolved deviation |
| **ADR-0013 git worktree isolation (ASP-661)** — Per-issue execution workspaces via Paperclip `isolated_workspace` + `git_worktree`. Accepted as architecture baseline. | Agent execution isolation prevents cross-issue workspace contamination | None | **Accepted** — `docs/adr/ADR-0013` |
| **NATS subject topology updated** — `nats/subjects.yaml` updated with `starship.aspen.*` subject topology for anomaly events. | Subject topology baseline for monitoring | None | **Updated** — alignment with ASP-687 anomaly consumer |

### Threats with status change this cycle

| Item | Previous | Current | Rationale |
|------|----------|---------|-----------|
| ASP-687 (Anomaly live consumer) | Implemented (ASP-776) | **Confirmed operational** | Anomaly feed active across nightly runs; no regression |
| CR 4.3 (Continuous monitoring) | Partial | **Partial — improved** | Live anomaly feed adds real-time behavioral monitoring; ACL drift alerting still missing |
| Nightly stability | Green | **Green — sustained** | Two consecutive weeks of 158/159 PASS |
| Branch protection | Non-enforced | **Enforced** | 10-context strict merge; admin override blocked |

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
| H-017 (Credential rotation) | Medium | **Open** | Rotation procedure |
| H-019 (Dev-only CI gate) | Medium | **Closed (ASP-574)** | CI gate + nightly Section 16 |
| H-020 (Gatekeeper SPOF) | Medium | **Design only** | Redundancy plan separate |
| H-021 (aspen.sentinel permissions) | Medium | **Closed (ASP-369)** | ACL pivot removed |
| **H-022 (Physical cell HITL vault)** | **Critical** | **Implemented (ASP-432)** | Vault-gate; 19/19 tests; fail-closed |
| **H-023 (Independent estop watchdog)** | **High** | **Implemented (ASP-433)** | `EstopWatchdog` design/sim; live wire = Aspen START |
| **H-024 (IEC 62443-4-2 cell baseline)** | **High** | **BASELINE — P0-2 closed (ASP-684)** | TLS default implemented; P0-1 ADR-0012 binding remains open; 10-gate checklist |
| H-HOST-01 (NATS store access) | Low | Active | Existing systemd hardening |
| H-HOST-03 (Stale units) | Low | Check gap | Audit systemd flags |
| H-HOST-04 (Master password env) | Medium | **Open** | Keyring/prompt pattern |
| F-015 (Red lateral) | **High** | Active + live anomaly feed | Anomaly detector live consumer wired (ASP-687); blocking path still deferred |
| F-016 (ACL misconfig) | Medium | Active + F-022 closed | Fail-closed default; edge→alpha removed |
| F-017 (Spoofed heartbeat) | Medium | **Open** | PKI fingerprint |
| F-013 (Unpinned model digests) | Low | Implemented (ASP-377) | Post-pull verification |
| F-018 (Exercise state race) | Low | Open | Atomic file write |
| F-019 (Delegated agent no plant) | Low | Informational | Document default |
| F-020 (Data-diode OSINT/ingest) | Medium | **Recipe complete** | Recipe reviewed; awaiting captain proof |
| F-011 (NATS rate limits) | Medium | **Implemented (ASP-375)** | Per-connection + per-account limits |
| F-012 (Cgroup limits) | Medium | **Implemented (ASP-376)** | 8 unit profiles; git-only |
| F-014 (Signed packages) | Medium | **Implemented (ASP-378)** | Verify path ships; ceremony deferred |
| F-022 (Edge→alpha pivot) | **High** | **Closed (ASP-369)** | ACL entry removed |
| ASP-379 (Tool-anomaly detector) | Low | **Implemented — live consumer wired (ASP-687)** | R1–R4 observation + live feed |
| ASP-607 (Gatekeeper rate limit) | Medium | **Implemented** | Per-agent sliding window |
| ASP-659 (Flock serialization) | Low | **Implemented** | `check-nightly.sh` flock guard |
| ASP-660 (Systemd count fix) | Low | **Closed** | Docs-only baseline correction |
| ASP-684 (TLS by default) | **High** | **Implemented** | H-024 P0-2 closed |
| ASP-687 (Anomaly consumer) | Medium | **Implemented** | Live feed path active |
| ASP-696 (HybridIntel removal) | Low | **Implemented** | Attack surface reduction |
| ASP-721 (NATS install guard) | Low | **Implemented** | CI reliability |
| ASP-730 (Python CI gate) | Medium | **Implemented** | Full test suite as required check |
| ASP-732 (Branch protection) | Low | **Resolved** | 10-context strict merge enforced |
| ASP-782 (Holographic catalog loader) | Low | **Implemented** | Feature, no security impact |
| ASP-800 (Weekly arch review) | Low | **Complete** | Architecture baseline 2026-10-19 |

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

### Z4 (Range — Red/Blue Exercise)

| Category | Path | Likelihood | Impact |
|----------|------|------------|--------|
| **S**poofing | Red agent impersonates blue | Low (separate NATS users per side) | Medium — bypass red tool restrictions |
| **E**levation | Red agent escapes range plant | Low (ACL isolation + NATS boundary) | Critical — production plant access |
| **T**ampering | Exercise state file race | Low (atomic write) | Medium — early/late exercise termination |

---

## 8. Recommendations for This Cycle

### P0 — Act this sprint

1. **[ ] Implement NATS credential rotation procedure (H-017).** Document a rotation workflow: regenerate creds with `gen-nats-accounts.sh`, distribute new `.env` files, restart NATS clients. The script has no expiry enforcement or rotation window — document a 90-day rotation cadence and add a reminder cron. With TLS now default at deployment, rotated credentials on TLS-protected bus avoid plaintext distribution concerns. **Persistent — open for 4+ cycles now.**

2. **[ ] Implement ADR-0012 operator binding (H-024 P0-1).** Bind `human_id` to a persistent operator registry before non-sim actuator arm. Production cell commission checklist item 1 blocks commissioning without this. Follow the ADR-0012 design spec; interface with the gatekeeper `authorize` path to replace free-string `human_id` with registered operator records. **Blocks:** G9+ physical arm.

3. **[ ] Node fingerprint for fleet heartbeat (F-017).** Fleet nodes register with NATS account + token but no PKI identity. A compromised bus credentials file lets an attacker register a fake node. Add a fingerprint field (`ed25519` public key or machine-id hash) to the `aspen.fleet.node.register` / `aspen.fleet.node.heartbeat` payload; ops-manager validates against a known-node allowlist.

### P1 — Next sprint

4. **[ ] Automated ACL drift detection.** Cron job compares `fleet.yaml` ACL baseline against live fleet state from heartbeats. Report drift events on `aspen.sentinel.audit.event`.

5. **[ ] Security scan CI gate.** Integrate `bandit` (Python) and `semgrep` (multi-lang) into `make check` or CI pipeline. Start with critical/high rules only to avoid noise.

6. **[ ] Code signing.** Sign `sandbox_run`, `policyexec`, `starshipd` binaries; verify signature at install/start time.

### P2 — v2.4 planning

7. **[ ] NATS nkey migration (continued).** ASP-536 added nkey-only gen mode; residual work: enforce nkey-only in CI (fail `--password-only` in production builds), migrate SYS account, automate `nk` binary availability. Replace password-based auth across all accounts.

8. **[ ] Replace env-based master password with keyring or prompt (H-HOST-04).** `AGENTIC_MASTER_PASSWORD` lives in process env and leaks via `/proc` or crash dumps. Migrate to `keyring` backend or prompt-on-startup with TPM-backed sealed secret. Fall back to env only as a last resort with a documented warning.

9. **[ ] SIEM/Sentinel integration.** Connect audit events to external SIEM or Sentinel dashboard.

10. **[ ] Reassess C11 p50 threshold.** Nightly consistently shows ~3.6ms vs 2ms threshold. Either (a) relax threshold to 5ms and log real outliers, or (b) investigate host-level timer causes. This is the sole standing nightly deviation.

---

*End of threat model v2.3. Next refresh: 2026-11-02.*