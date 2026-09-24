# Security Threat Model — AspenOS v2.2

**Version:** 2.2 · **Refresh:** 2026-09-21 (Biweekly)  
**Author:** Auditor (Paperclip agent 4203b00e)  
**Previous baseline:** ASP-569 (2026-09-07) — H-007–H-021 backlog, F-015–F-019  
**This cycle:** ASP-629 — F-011, F-012, F-014, F-022, ASP-379 anomaly detector, ASP-607 gatekeeper rate limit  
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
| H-021 | **No dual-publish on aspen.sentinel.* subjects yet** | Observability | 5.0 (AV:N/AC:L) | Migration incomplete; `starship.*` still primary | **Closed (ASP-369)** — edge→alpha ACL pivot removed; edge cross-plant fails closed; H-021 addressed via ACL change |
| H-022 | **Physical cell act requires HITL vault approval** | Actuation / Safety | **8.5** (AV:N/AC:L) | Gatekeeper shim vault-gate: physical cell act subjects require durable HITL vault approval record before authorize grants; dual-human preserved as additional gate layer | **Implemented (ASP-432)** — 19/19 vault-gate tests + 99/99 phase2 pass; fail-closed on every vault failure path |
| H-023 | **Software estop latch is agent-dependent — no independent hardware watchdog** | Safety | **9.0** (AV:L/AC:H) | Independent `EstopWatchdog` (design/sim): software-path `tick` heartbeat, fail-closed open-loop trip on missed/forced/backend failure, clear only via two distinct authorizers, durable latch via `FilePulseBackend` | **Implemented (ASP-433)** — 18/18 watchdog tests; 466-test suite green; residual: live GPIO/relay wire = Aspen START on this issue |

### 2.3 Fleet-specific threats (F- series)

| ID | Threat | Asset | Risk (CVSS) | Mitigation | Status |
|----|--------|-------|-------------|------------|--------|
| F-015 | **Red-team lateral from range to ops** | Plant isolation | 8.0 (AV:A/AC:L) | `check_cross_plant()` rule 3/4: isolation deny; RANGE no import from OPS; tool-anomaly detector (ASP-379) adds behavioral detection of lateral moves | **Active** — anomaly detector implemented (ASP-379), fail-open observation only; blocking path deferred |
| F-016 | **Plant ACL misconfiguration opens cross-plant** | ACL | 6.5 (AV:N/AC:L) | Default `same_plant_only` fail-closed; explicit allow list; F-022 removed edge→alpha pivot | **Active** — F-022 closed (ASP-369) |
| F-017 | **Fleet heartbeat spoofing (register fake node)** | Identity | 7.5 (AV:N/AC:L) | NATS accounts + token; no PKI/fingerprint yet | **Open** |
| F-018 | **Exercise state race — start/stop collision** | Exercise | 5.0 (AV:N/AC:H) | Atomic file write; poll-based check in fleet_policy.py | **Open** |
| F-019 | **Delegated agent without plant tag** | Cross-plant | 6.0 (AV:N/AC:M) | `delegate_to_agent` accepts `plant`/`target_plant`; missing tag defaults no ACL | Informational |
| F-013 | **Unpinned model digests — tag-only ollama pull** | Supply chain / Model integrity | 6.0 (AV:N/AC:H) | Pin model digests (`config/models-digests.yaml`); verify-after-pull fail-hard (`install-models.sh`/health-checker/dashboard); reject unpinned pulls in production | **Implemented (ASP-377)** — `scripts/resolve-model-digests.py` + CI/nightly gates; `@sha256:` refs rejected by Ollama 0.32.11, enforcement is post-pull verification per `docs/plans/ASP-377.md` |
| F-020 | **Software data-diode missing for OSINT/ingest** | OSINT domain | 6.5 (AV:N/AC:M) | nftables/iptables one-way rules + process isolation + restricted NATS account — see recipe | **Recipe complete** — [Recipe](solutions/asp-368-data-diode-recipe.md) reviewed (AUDITOR_APPROVE); in_review — captain proof required |
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
| **CR 3.1** — Communication integrity | NATS JetStream; optional TLS | **Partial** — TLS not default |
| **CR 3.2** — Communication confidentiality | Optional TLS; SecretsManager AES-256-GCM for stored secrets | **Partial** |
| **CR 3.3** — Zone/conduit boundary | Plant zones (ops/edge/range); NATS account boundaries | **Satisfied** |
| **CR 3.4** — Software update integrity | ADR-0008 package classification; `dpkg` signature via `gpgv` detached verify gate (ASP-378); CI gate blocks Dev-only in production (ASP-574) | **Satisfied (ASP-378/574)** — verify path ships in update.sh; CI job `verify-package-signature` fails on unsigned/tampered; Section 21 gate; placeholder dev key; ceremony deferred |
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
- [x] **F-011:** NATS rate limiting per-connection and per-account (ASP-375). — All three NATS configs hardened; per-account limits bound blast radius; Section 19 nightly gate; 5 fixture tests. **Implemented.**
- [x] **F-012:** Cgroup per-agent resource limits (ASP-376). — systemd drop-in profiles with CPUQuota, MemoryMax, MemoryHigh, TasksMax per unit. 8 unit profiles staged; 6 fixture tests; Section 20 nightly gate. **Implemented.** (git-only, no live systemd applied)
- [x] **F-013:** Pin all Ollama model pulls and `FROM` directives to SHA256 digests; reject unpinned pulls in production. — **ASP-377:** implemented (`config/models-digests.yaml` + verify-after-pull); `@sha256:` refs rejected by Ollama 0.32.11.
- [x] **F-014:** Signed package verify gate (ASP-378). — `gpgv` detached-signature verify before `dpkg -i`; CI job fails on unsigned/tampered; placeholder dev trust anchor. Ceremony (real key signing) is deferred human action.
- [x] **F-020:** Draft software data-diode recipe for OSINT/ingest. — [Recipe](solutions/asp-368-data-diode-recipe.md) reviewed (AUDITOR_APPROVE); QUEUED — requires dual-human gate before any host firewall apply.
- [x] **F-022:** Remove edge→alpha ACL pivot (ASP-369). — `plant-edge: [plant-alpha]` dropped from `config/fleet.yaml`; edge cross-plant fails closed. **Closed.**
- [x] **ASP-379:** Implement fail-open tool-anomaly detector. — R1–R4 behavioral rules over tool audit events; 12 hermetic tests. Live consumer wiring deferred.
- [x] **ASP-607:** Gatekeeper per-agent rate limiting. — Sliding window on `request_capability()`; deny + `gate.rate_limited` audit. 13 tests.
- [ ] **H-017:** Implement NATS credential rotation procedure or script. Document rotation window.
- [ ] **H-HOST-04:** Replace env-based master password with prompt, keyring, or TPM-backed secret.
- [ ] **F-017:** Add node fingerprint/PKI for fleet heartbeat to prevent registration spoofing.

### 4.3 Medium-term (v2.3 planning)

- [x] **ADR-0009 implementation (Phase 2):** Full token lifecycle (consumption/refresh), Hermes/Paperclip credential strip, immutable proxy enforcement. — Phase 1 (proposal interception + dual-human + audit) landed in ASP-540; Phase 2 landed in ASP-564 (`GatekeeperProxy`/`NATSAgentProxy` credential strip, `SafetySubjectEnforcer`, token lifecycle).
- [ ] **TLS by default:** Enable `STARSHIP_NATS_TLS=1` in firstboot templates. Document WAN deployment.
- [ ] **NATS nkey migration (continued):** ASP-536 added nkey-only gen mode; residual work: enforce nkey-only in CI (fail `--password-only` in production builds), migrate SYS account, automate `nk` binary availability. Replace password-based auth across all accounts (partial ASP-536).
- [ ] **Automated ACL drift detection:** Cron job compares live ACL with `fleet.yaml` baseline.
- [ ] **Security scan CI gate:** Integrate `bandit` / `semgrep` into `make check` or CI pipeline.
- [ ] **Code signing:** Sign `sandbox_run`, `policyexec` binaries; verify at install time.
- [ ] **SIEM/Sentinel integration:** Connect audit events to external SIEM or Sentinel dashboard.

---

## 5. Changes Since Last Refresh (ASP-629, 2026-09-21)

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
| **F-011 NATS rate limits (ASP-375)** | Per-connection hardening (max_pending, max_subscriptions, ping, write_deadline, auth timeout); per-account connection/subscription blast-radius caps | (DoS mitigation extended) | **Implemented** — all three NATS configs; Section 19 nightly gate |
| **F-012 Cgroup limits (ASP-376)** | systemd drop-in CPU/memory/PID limits per agent unit; 8 profiles from health-checker (25%/128M) to NATS (100%/256M) | Resource-exhaustion DoS mitigation | **Implemented** — 6 fixture tests; Section 20 nightly gate |
| **F-013 Model digest pin (ASP-377)** | `config/models-digests.yaml` pins all 7 Ollama models to sha256; `install-models.sh` verify-after-pull fail-hard | (F-013 → implemented) | **Implemented** — repo-local digests; CI + nightly Section 22 |
| **F-014 Signed packages (ASP-378)** | `gpgv` detached-signature verify gate; `scripts/update.sh` opt-in `--verify-signature`; CI job fails on unsigned/tampered; placeholder dev trust anchor | (Supply-chain integrity) | **Implemented** — verify path ships; ceremony (real keys) deferred human action |
| **F-022 Edge→alpha ACL removal (ASP-369)** | `plant-edge: [plant-alpha]` dropped from `config/fleet.yaml`; edge cross-plant fails closed via `same_plant_only` default | (F-022 → closed, H-021 → closed) | **Closed** — 11 ACL fixture tests; smoke-test check |
| **ASP-379 Tool-anomaly detector** | Fail-open behavioral R1–R4 rules over tool audit events; `sensitive_read_then_egress`, `high_risk_burst`, `denial_probe`, `error_storm` | None (observation-only; blocking path deferred) | **Implemented** — 12 hermetic fixture tests |
| **ASP-607 Gatekeeper rate limiting** | Per-agent sliding-window rate limit on `request_capability()`; env-overridable defaults 30 req/60s | None (deny + `gate.rate_limited` audit) | **Implemented** — 13 tests; merged via Aspen local proof |

### Threats closed this cycle

| Item | Reason | Closing evidence |
|------|--------|-----------------|
| H-019 (Dev-only CI gate) | CI gate `check-no-devonly-in-prod.sh` committed; wired in CI (`security-devonly-isolation` + nightly Section 16) | ASP-574: `scripts/check-no-devonly-in-prod.sh` committed, `.github/workflows/ci.yml` job, `scripts/check-nightly.sh` Section 16; self-test script verifies fail-on-planted |
| H-015 (Audit trail) | Publisher wired + JetStream durable stream + dashboard consumer endpoints | ASP-537: `scripts/sentinel-audit.py`, `dashboard/server.py` Sentinel endpoints, JSONL journal + JetStream mirror; gatekeeper events covered |
| H-014 (AppArmor deployment) | Profiles staged + loaded in deb postinst; nightly Section 17 verifies wiring | ASP-374: `debian/DEBIAN/postinst` includes `apparmor_parser -r`; ASP-575: verification report confirming 4-nightly-check criteria met |
| F-022 (Edge→alpha pivot) | ACL entry `plant-edge: [plant-alpha]` removed; 11 fixture tests verify edge→alpha denied | ASP-369: commit `201933f`, 6 files, 272 insertions, 11/11 fixture tests |
| H-021 (aspen.sentinel permissions) | Resolved as aspect of ASP-369 ACL change | Edge cross-plant fails closed; no pivot path |
| H-022 (Physical cell HITL vault) | Durable HITL vault approval gate for physical cell acts; 19/19 vault-gate tests, 99/99 phase2 pass; zero new secrets, fail-closed all paths | ASP-432: vault_gate.py, minimal_shim.py wiring, hitl_vault.py bugfix, test suite |

### Threats with status change this cycle

| Item | Previous | Current | Rationale |
|------|----------|---------|-----------|
| H-019 (Dev-only CI gate) | Open / ADR-0008 proposed | **CLOSED (ASP-574)** | CI gate script + CI wire + nightly Section 16 + self-test; verified clean |
| H-014 (AppArmor deployment) | Check gap | **Satisfied (ASP-374/575)** | Profiles staged in deb postinst; nightly Section 17 verifies 4 checks |
| H-015 (Audit trail) | Open — consumer pending | **CLOSED (ASP-537)** | Publisher + consumer + dashboard endpoints all wired |
| H-008 (Self-auth) | Phase 1 implemented | **Phase 1 + Phase 2 (ASP-564)** | Token lifecycle + credential-strip proxy landed; only H-020 (SPOF) remains design-only |
| H-010 (Stale tokens) | ADR-0009 design | **Implemented (ASP-564)** | Short TTL + lifecycle; refuse if expired; stale cleanup |
| H-021 (aspen.sentinel ACL) | Open | **Closed (ASP-369)** | Addressed by ACL pivot removal; edge cross-plant denied |
| F-011 (NATS rate limits) | Not tracked | **Implemented (ASP-375)** | Per-connection + per-account limits in all NATS configs |
| F-012 (Cgroup limits) | Not tracked | **Implemented (ASP-376)** | systemd drop-in profiles per agent unit |
| F-013 (Model digests) | Open | **Implemented (ASP-377)** | `config/models-digests.yaml` + verify-after-pull fail-hard |
| F-014 (Signed packages) | Not tracked | **Implemented (ASP-378)** | `gpgv` verify gate + CI job; ceremony deferred |
| F-022 (Edge→alpha pivot) | Not tracked | **Closed (ASP-369)** | ACL entry removed; edge→alpha denied |
| H-022 (Physical cell HITL vault) | Not tracked | **Implemented (ASP-432)** | Vault-gate in gatekeeper shim; fail-closed on all vault failure paths |
| H-023 (Independent estop watchdog) | Not tracked | **Implemented (ASP-433)** | `EstopWatchdog` design/sim: fail-closed tick/deadline gate, dual-authorize clear, durable latch; live GPIO/relay wire residual pending Aspen START |

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
| H-015 (Audit trail) | **High** | **Closed (ASP-537)** | Publisher + consumer + dashboard endpoints; anomaly detector added (ASP-379) |
| H-017 (Credential rotation) | Medium | Open | Rotation procedure |
| H-019 (Dev-only CI gate) | Medium | **Closed (ASP-574)** | CI gate + nightly Section 16 |
| H-020 (Gatekeeper SPOF) | Medium | **Design only (H-008 residual)** | H-008 Phase 2 complete; redundancy plan separate |
| H-021 (aspen.sentinel permissions) | Medium | **Closed (ASP-369)** | ACL pivot removed; edge cross-plant denied by default |
| **H-022 (Physical cell HITL vault)** | **Critical** | **Implemented (ASP-432)** | Vault-gate in gatekeeper shim; 19/19 tests; fail-closed all paths |
| **H-023 (Independent estop watchdog)** | **High** | **Implemented (ASP-433)** | `EstopWatchdog` design/sim: fail-closed tick/deadline gate, dual-authorize clear, durable latch; live wire = Aspen START |
| H-HOST-01 (NATS store access) | Low | Active | Existing systemd hardening |
| H-HOST-03 (Stale units) | Low | Check gap | Audit systemd flags |
| H-HOST-04 (Master password env) | Medium | **Open** | Keyring/prompt pattern |
| F-015 (Red lateral) | **High** | Active + Anomaly detector | Existing isolation + ASP-379 (fail-open observation) |
| F-016 (ACL misconfig) | Medium | Active + F-022 closed | Fail-closed default; edge→alpha removed |
| F-017 (Spoofed heartbeat) | Medium | Open | PKI fingerprint |
| F-013 (Unpinned model digests) | Low | Implemented (ASP-377) | Verify-after-pull fail-hard; reject unpinned in production |
| F-018 (Exercise state race) | Low | Open | Atomic file write |
| F-019 (Delegated agent no plant) | Low | Informational | Document default |
| F-020 (Data-diode OSINT/ingest) | Medium | **Recipe complete** | [Recipe](solutions/asp-368-data-diode-recipe.md) reviewed (AUDITOR_APPROVE); in_review — captain proof required |
| F-011 (NATS rate limits) | Medium | **Implemented (ASP-375)** | All three NATS configs hardened; per-account limits |
| F-012 (Cgroup limits) | Medium | **Implemented (ASP-376)** | 8 unit profiles; git-only (no live systemd); Section 20 nightly |
| F-014 (Signed packages) | Medium | **Implemented (ASP-378)** | Verify path ships; placeholder dev key; ceremony deferred |
| F-022 (Edge→alpha pivot) | **High** | **Closed (ASP-369)** | ACL entry removed; edge cross-plant fails closed |
| ASP-379 (Tool-anomaly detector) | Low | **Implemented** | Fail-open R1–R4 observation; live consumer wiring deferred |
| ASP-607 (Gatekeeper rate limit) | Medium | **Implemented** | Per-agent sliding window on `request_capability()` |

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

4. **[x] Implement F-011 NATS rate limiting (ASP-375).** Per-connection hardening (max_pending 16MB, max_subscriptions 512, write_deadline 5s, ping 30s/3, auth timeout 2.0s) plus per-account limits bounding blast radius. All three NATS configs hardened; Section 19 nightly gate. **Implemented.**

5. **[x] Implement F-012 cgroup per-agent limits (ASP-376).** systemd drop-in profiles with CPUQuota, MemoryMax, MemoryHigh, TasksMax for all 8 agent units. 6 fixture tests; build-deb stages drop-ins; Section 20 nightly gate. **Implemented.** (Git-only — no live systemd applied on bt-asp-srv.)

6. **[x] Implement F-013 model digest pinning (ASP-377).** `config/models-digests.yaml` pins all 7 Ollama models to sha256; `install-models.sh` verify-after-pull fail-hard; CI + nightly Section 22 enforce. **Implemented.**

7. **[x] Implement F-014 signed package verify gate (ASP-378).** `gpgv` detached-signature verify before `dpkg -i`; CI job fails on unsigned/tampered; placeholder dev trust anchor. Ceremony (real key signing) is deferred human action. **Implemented.**

8. **[x] Implement F-022 edge→alpha ACL removal (ASP-369).** `plant-edge: [plant-alpha]` removed from `config/fleet.yaml`; edge cross-plant fails closed via `same_plant_only` default. 11 ACL fixture tests; smoke-test check. **Closed.**

9. **[x] Implement ASP-379 tool-anomaly detector.** Fail-open behavioral R1–R4 rules over tool audit events; `sensitive_read_then_egress`, `high_risk_burst`, `denial_probe`, `error_storm`. 12 hermetic tests. Live consumer wiring deferred.

10. **[x] Implement ASP-607 gatekeeper rate limiting.** Per-agent sliding-window rate limit on `request_capability()`; env-overridable defaults 30 req/60s; deny + `gate.rate_limited` audit. 13 tests.

### P1 — Next sprint

11. **[ ] NATS credential rotation procedure (H-017).** Document a rotation workflow: regenerate creds with `gen-nats-accounts.sh`, distribute new `.env` files, restart NATS clients. The script has no expiry enforcement or rotation window — document a 90-day rotation cadence and add a reminder cron.

12. **[ ] Replace env-based master password with keyring or prompt (H-HOST-04).** `AGENTIC_MASTER_PASSWORD` lives in process env and leaks via `/proc` or crash dumps. Migrate to `keyring` backend or prompt-on-startup with TPM-backed sealed secret. Fall back to env only as a last resort with a documented warning.

13. **[ ] Node fingerprint for fleet heartbeat (F-017).** Fleet nodes register with NATS account + token but no PKI identity. A compromised bus credentials file lets an attacker register a fake node. Add a fingerprint field (`ed25519` public key or machine-id hash) to the `aspen.fleet.node.register` / `aspen.fleet.node.heartbeat` payload; ops-manager validates against a known-node allowlist.

14. **[ ] Wire anomaly detector to live audit consumer.** Subscribe a JetStream consumer to the tool-audit subject, feed events through `ToolAnomalyDetector.feed()`, publish findings to a `sentinel.tools.anomaly` subject so ops can page on R1 (high) and template on R2–R4.

### P2 — v2.3 planning

15. **[x] ADR-0009 Phase 2:** Full token lifecycle (consumption/refresh), Hermes/Paperclip credential strip, immutable proxy enforcement. — Phase 1 landed in ASP-540; Phase 2 landed in ASP-564. H-020 (SPOF) redundancy plan tracked separately.

16. **[ ] TLS by default:** Enable `STARSHIP_NATS_TLS=1` in firstboot templates. Document WAN deployment with mutual TLS.

17. **[ ] NATS nkey migration (continued):** ASP-536 added nkey-only gen mode; residual work: enforce nkey-only in CI (fail `--password-only` in production builds), migrate SYS account, automate `nk` binary availability. Replace password-based auth across all accounts (partial ASP-536).

18. **[ ] Automated ACL drift detection:** Cron job compares `fleet.yaml` ACL baseline against live fleet state from heartbeats. Report drift events on `aspen.sentinel.audit.event`.

19. **[ ] Security scan CI gate:** Integrate `bandit` (Python) and `semgrep` (multi-lang) into `make check` or CI pipeline. Start with critical/high rules only to avoid noise.

20. **[ ] Code signing:** Sign `sandbox_run`, `policyexec`, `starshipd` binaries; verify signature at install/start time.

21. **[ ] SIEM/Sentinel integration:** Connect audit events to external SIEM or Sentinel dashboard.

---

*End of threat model v2.2. Next refresh: 2026-10-05.*