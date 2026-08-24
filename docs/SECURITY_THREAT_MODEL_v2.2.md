# Security Threat Model v2.2 — Aspen OS

**Refresh cycle:** ASP-431 (2026-08-24) ← ASP-168 (2026-08-10) ← ASP-298 (baseline)
**Scope:** Standard manufacturing cell + fleet topology
**Reviewer:** Auditor (paperclip agent 4203b00e)
**Status:** Current

---

## Asset inventory

| ID | Asset | Type | Classification |
|----|-------|------|----------------|
| A01 | NATS/JetStream bus | Message bus | Critical — C2/traffic backbone |
| A02 | Agent runtime (proxy/romi/ergo) | AI process | High — tool execution authority |
| A03 | Single-plant scheduler (LangGraph) | Workflow engine | Critical — can propose acts |
| A04 | Manufacturing cell (range) | Physical/edge node | Critical — safety-adjacent motion |
| A05 | Dashboard (port 8788) | Web UI | Medium — monitoring + chat |
| A06 | osquery telemetry (StarAgent) | Metrics agent | Low — read-only telemetry |
| A07 | Paperclip C2 (port 3100) | Control plane | Critical — org mesh takeover |
| A08 | Fleet node identity / enrollment | Identity system | Critical — spoofing prevention |
| A09 | Ollama model files (abliterated GGUF) | Model artifacts | High — weaker refusal surface |
| A10 | Systemd service units | OS services | High — persistence + privilege |
| A11 | C11 sandbox (`sandbox_run` / `policyexec`) | Isolation binary | Critical — tool fail-closed gate |

---

## Threat matrix

### F-001: Unauthenticated NATS bus (CLOSED)

| Property | Value |
|----------|-------|
| **Status** | **Closed** — H-001 delivered ASP-169 |
| **Asset** | A01 |
| **Risk** | Agent RCE via spoofed commands on bus |
| **Remediation** | Accounts + nkeys by default (H-001); no-auth `agent-bus` mode removed; legacy `nats/server.conf` is placeholder-only |
| **Verification** | `grep -r 'authorization' nats/fleet-accounts.conf` |

### F-002: No node identity / enrollment (CLOSED)

| Property | Value |
|----------|-------|
| **Status** | **Closed** — H-002 delivered ASP-170 |
| **Asset** | A08 |
| **Risk** | Rogue node joins fleet, spoofs telemetry or commands |
| **Remediation** | Signed enrollment tokens (fleet-CA CSR); revocation list at sign/connect/peer layers; `fleet-enroll.sh` |
| **Verification** | `scripts/fleet-enroll.sh --verify` |

### F-003: Software sandbox only (CLOSED)

| Property | Value |
|----------|-------|
| **Status** | **Closed** — H-003 delivered ASP-171 |
| **Asset** | A11 |
| **Risk** | Python `CommandExecutor` blocklist bypass; no OS-level confinement |
| **Remediation** | C11 `sandbox_run` (seccomp-bpf + NEWNS/NEWPID) and `policyexec` are mandatory (fail closed at startup); `python3 -m native_check` runs as `ExecStartPre` |
| **Verification** | `python3 -m native_check && echo OK` |

### F-004: No audit trail for tool execution (CLOSED)

| Property | Value |
|----------|-------|
| **Status** | **Closed** — H-004 delivered ASP-172 |
| **Asset** | A02 |
| **Risk** | Forensics impossible after compromise; no tamper-evidence |
| **Remediation** | Per-agent JSONL audit log at `/var/log/starship/audit/<agent>.jsonl`; hash-chained via `EdgeRRM.verify_audit()` on safety path |
| **Verification** | `head -5 /var/log/starship/audit/proxy.jsonl` |

### F-005: Unrestricted ops role tools (CLOSED)

| Property | Value |
|----------|-------|
| **Status** | **Closed** — H-005 delivered ASP-173 |
| **Asset** | A02 |
| **Risk** | Ops agent can use `vault_approve`/`vault_deny`; expansion tools (`opencode`) available unnecessarily |
| **Remediation** | Ops role minimum-necessary tool allowlist in `config/policy.default.json`; `vault_approve`/`vault_deny` and `opencode`/`opendesign` explicitly denied; new tools added deliberately |
| **Verification** | `jq '.roles.ops.tools.deny' config/policy.default.json` |

### F-006: Plaintext NATS transport (CLOSED)

| Property | Value |
|----------|-------|
| **Status** | **Closed** — H-006 delivered ASP-174 |
| **Asset** | A01 |
| **Risk** | Passive eavesdropping on bus; credential replay |
| **Remediation** | TLS + mTLS default on new deployments; firstboot auto-runs `gen-nats-tls.sh`; fleet-CA per-node identities |
| **Verification** | `ss -lntp | grep 4222 && nats-server --signal probe` |

### F-007: Hardcoded NATS credentials in git (CLOSED)

| Property | Value |
|----------|-------|
| **Status** | **Closed** — H-017 delivered ASP-365 |
| **Asset** | A01 |
| **Risk** | Lab tokens in `nats/server.conf` leaked to git history; usable on production LAN |
| **Remediation** | All hardcoded secrets scrubbed from repo; `nats/server.conf` is placeholder-only; installer never points `active.conf` at it; lab hosts rotate credentials |
| **Verification** | `git log --all -p --diff-filter=M -- nats/server.conf \| grep -c 'password'` (expect 0) |

### F-008: No dual-human authorize for safety-adjacent acts (OPEN — H-016 G8 wired, sim-only)

| Property | Value |
|----------|-------|
| **Status** | **Mitigated (sim-only)** — H-016 delivered ASP-364 (G8) |
| **Asset** | A04 |
| **Risk** | Single agent/human can command physical cell motion; no dual-auth prior to act |
| **Remediation** | `DualHumanGate` in `EdgeRRM`: `propose_act` held until 2 distinct humans authorize; `ASPEN_GATE_WINDOW_S` default 600s; `self_approval` refused; all events hash-chained audit log |
| **Dependency** | Requires Aspen Architect to wire `operator_of_record` from authenticated identity source |
| **Verification** | `python3 scripts/sim_act_gate_wire.py && echo OK` |
| **Production gate** | Cell remains `status: sim_only` — `ASPEN_SIM=0` drivers blocked until G9 |

### F-009: Estop latch single-point clear (MITIGATED)

| Property | Value |
|----------|-------|
| **Status** | **Mitigated** — G7 delivered ASP-417 |
| **Asset** | A04 |
| **Risk** | One human can unlatch estop; same human who triggered it could clear without review |
| **Remediation** | Two distinct humans required to authorize estop clear; stop-causer refused (`self_approval`); matches dual-human propose_act pattern |
| **Verification** | `python3 scripts/sim_act_gate_wire.py --test-estop` |

### F-010: Tool output secret leakage (MITIGATED)

| Property | Value |
|----------|-------|
| **Status** | **Mitigated** (ongoing) |
| **Asset** | A02 |
| **Risk** | Secrets in stdout/logs reach LLM context; prompt injection exfil |
| **Remediation** | Redaction patterns in `CommandExecutor`; AES-256-GCM `SecretsManager`; gitignored cred paths; `DroidShield` scan_text/scan_file/scan_git_diff |
| **Gap** | Redaction rules are Python regex — need coverage review for manufacturing OT protocols |

### F-011: Abliterated model weaker refusal (MITIGATED — policy + sandbox)

| Property | Value |
|----------|-------|
| **Status** | **Accepted** with compensating controls |
| **Asset** | A09 |
| **Risk** | Locally fine-tuned abliterated models may comply with harmful instructions |
| **Remediation** | Mandatory `sandbox_run` + `policyexec` + `CommandBlocklist`; tool allowlist; never rely on model refusal alone |

### F-012: No Paperclip C2 hardening (CLOSED)

| Property | Value |
|----------|-------|
| **Status** | **Closed** — H-019 delivered ASP-367 |
| **Asset** | A07 |
| **Risk** | Paperclip `:3100` exposed; board keys world-readable; budgets at $0=unlimited |
| **Remediation** | C2 hardening runbook at `docs/security/PAPERCLIP_C2_HARDENING.md`; biweekly checklist includes F-019 items |
| **Verification** | `stat -c '%a' ~/.paperclip/keys/board.key` (expect 600) |

### F-013: Cross-plant ACL bidirectional (OPEN — H-021 backlog)

| Property | Value |
|----------|-------|
| **Status** | **Open** — H-021 in backlog |
| **Asset** | A02/A08 |
| **Risk** | `plant-alpha → plant-edge` ACL allows outbound from ops to edge; pivot from compromised edge back to alpha is implicitly allowed by symmetric allow entry; red-team during exercise restricted but greenfield workstations lack isolation |
| **Remediation** | Revisit ACL symmetric/allow vs directional; add edge→alpha deny as default; require explicit one-way edges |
| **Priority** | Medium — risk exists only when both plants have active agents |

### F-014: No software data-diode for OT commands (OPEN — H-020 backlog)

| Property | Value |
|----------|-------|
| **Status** | **Open** — H-020 in backlog |
| **Asset** | A04 |
| **Risk** | `aspen.edge.<node>.authorize` subject is bidirectional on NATS; a compromised plant-controller could replay captured authorize messages |
| **Remediation** | Software data-diode pattern: one-way publish bridge from plant to edge; no NATS subscription on plant-side consumer; see Master Spec |
| **Priority** | High — needed before G9 physical bring-up |

### F-015: IEC 62443-4-2 CR 2.1 gap (OPEN)

| Property | Value |
|----------|-------|
| **Status** | **Open** — new finding v2.2 |
| **Asset** | A02, A03, A04 |
| **Risk** | No formal identification and authentication control for all human and software access to the manufacturing cell (62443-4-2 CR 2.1) |
| **Remediation** | Map Aspen OS identity model (ServiceAccountManager, NATS nkeys, Paperclip board keys) to IEC 62443 roles: operator, engineer, maintainer, viewer |
| **Priority** | Medium |

### F-016: Session management for single-plant scheduler (OPEN — H-018 backlog)

| Property | Value |
|----------|-------|
| **Status** | **Open** — H-018 in backlog |
| **Asset** | A03 |
| **Risk** | Single-plant LangGraph scheduler can propose acts without session replay audit; no idempotency on `propose_act` |
| **Remediation** | Guard `propose_act` with session-bound nonce; reject replayed proposals |
| **Priority** | Medium — applies before G9 |

### F-017: Physical cell network segmentation (OPEN)

| Property | Value |
|----------|-------|
| **Status** | **Open** — new finding v2.2 |
| **Asset** | A04 |
| **Risk** | Cell network shares the same NATS bus as plant agents; compromised ROMI/Ergo can reach cell subjects |
| **Remediation** | OT-level network segmentation: cell NATS on separate transport (dedicated loop or VLAN); drop-and-forward bridge for authorized subjects only |
| **Priority** | High — physical prerequisite before any real motion |

### F-018: Container/sandbox escape from tool execution (OPEN)

| Property | Value |
|----------|-------|
| **Status** | **Open** — new finding v2.2 |
| **Asset** | A11 |
| **Risk** | `sandbox_run` uses seccomp + namespaces but NOT user namespaces — kernel bug in same-uid namespace can escape |
| **Remediation** | Add user namespace isolation to `sandbox_run`; escalate to cgroups-per-agent (H-012) for containment |
| **Priority** | Medium |

### F-019: Supply chain integrity for GGUF models (OPEN — H-013 backlog)

| Property | Value |
|----------|-------|
| **Status** | **Open** — H-013 in backlog |
| **Asset** | A09 |
| **Risk** | Tampered GGUF model distributed via Ollama Hub; adversarial weights produce harmful output despite sandbox |
| **Remediation** | SHA-256 pinning in `Modelfile`; signature verification on pull; CI checksum diff on update |
| **Priority** | Medium |

---

## IEC 62443 mapping (manufacturing cell)

| Requirement | Aspen OS coverage | Gap |
|-------------|-------------------|-----|
| **CR 2.1** — Identification and authentication | NATS nkeys + Paperclip board keys + ServiceAccountManager | No mapping to cell-operator/engineer roles |
| **CR 2.2** — Authentication enforcement | nkeys mandatory (H-001); TLS client certs (H-006) | Software data-diode needed for OT path (H-020) |
| **CR 2.3** — User identification | `operator_of_record` tracked per proposal (H-016) | Not wired to authenticated identity source in production |
| **CR 2.4** — Identifier management | Node enrollment tokens + revocation list (H-002) | Rotation SLA not automated (H-007) |
| **CR 2.5** — Session integrity | Audit hash chain (ASP-172/H-004 + ASP-417) | Not extended to single-plant scheduler (H-018) |
| **CR 2.6** — Session termination | systemd `TimeoutStopSec`; NATS client disconnect | No idle session timeout for agent NATS connections |
| **CR 2.7** — Least privilege | Ops tool allowlist (H-005); red-team restricted (fleet ACL) | Per-role NATS subject permissions not audited (H-021) |
| **CR 3.1** — Physical security | N/A (environment-specific) | Document expected physical controls for cell deployment |
| **CR 3.2** — Software process integrity | C11 sandbox mandatory (H-003); tamper-evident audit (H-004) | No signed packages (H-014) |
| **CR 3.3** — Network segmentation | Plant isolation via fleet ACL + `plant-range` isolation | Separate OT transport needed (F-017) |
| **CR 3.4** — Boundary protection | Cross-plant ACL | No industrial firewall rules (H-008) |
| **CR 4.1** — Information confidentiality | TLS+mTLS (H-006); encrypted secrets (AES-256-GCM) | Secret rotation not automated (H-007) |
| **CR 4.2** — Information integrity | Audit hash chain; signed enrollment (H-002) | Model hash pinning missing (H-013) |
| **CR 4.3** — Denial of service protection | NATS max_payload, max_pending limits | No rate limiting on subjects (H-011); no cgroups (H-012) |

---

## Backlog hardening items (carried forward from v2.1)

| ID | Finding | Priority | Owner |
|----|---------|----------|-------|
| H-007 | Automated secret rotation (IEC 62443 SR 4.2) | Medium | Security |
| H-008 | OT/ICS-aware firewall rule templates for manufacturing cell | Medium | Security |
| H-009 | Enforce mode 600 on all credential/config files in packaging | High | Ops |
| H-010 | Install AppArmor profiles in deb postinst | Medium | Ops |
| H-011 | NATS rate limiting + tighter connection limits | Medium | Engineering |
| H-012 | cgroups per-agent resource limits | Low | Engineering |
| H-013 | Model hash pinning / signature verification | Medium | Security |
| H-014 | Signed packages and update integrity checks | Medium | Ops |
| H-015 | Behavioral anomaly detection on tool execution patterns | Low | Security |
| H-018 | Session-bound guard for single-plant scheduler propose_act | Medium | Engineering |
| H-020 | Software data-diode for OT command path | **High** | Engineering |
| H-021 | Revisit plant-edge→plant-alpha ACL (asymmetric/directional) | Medium | Security |
| H-HOST-01 | Apply AUDITOR_BASELINE SSH+UFW (human approval req.) | High | Ops |

---

## New hardening items (v2.2 findings)

| ID | Finding | Priority | Rationale |
|----|---------|----------|-----------|
| H-022 | HITL vault approval gate for physical cell act | **Critical** | G9 gate condition — no physical motion without human-in-the-loop vault approval |
| H-023 | Hardware estop watchdog (independent of agent software) | **High** | Software estop can fail if agent process is compromised; physical watchdog needed |
| H-024 | NIST CSF / IEC 62443-4-2 formal assessment for cell deployment | **High** | Baseline gap analysis before production deployment |
| H-025 | OT network segmentation (dedicated cell transport) | **High** | F-017 — cell must not share NATS transport with plant agents |
| H-026 | Per-role NATS subject permission audit (verify no over-permission) | Medium | H-021 sibling — audit current subject exports against least-privilege |

---

## Biweekly checklist update (current)

| Check | Status | Notes |
|-------|--------|-------|
| NATS: no live secrets in git; accounts + TLS defaults | **Verified** | H-001/H-006/H-017; `nats/server.conf` placeholder-only |
| Paperclip C2: F-019 items | **Verified** | Runbook at `docs/security/PAPERCLIP_C2_HARDENING.md` |
| Dual-human propose_act→act path wired (H-016) | **Verified** | `DualHumanGate` in EdgeRRM; sim-only until G9 |
| Host baseline SSH/UFW (H-HOST-01) | **Not yet** | Backlog; human approval required |
| Sandbox/policyexec mandatory (H-003); ops allowlist (H-005) | **Verified** | `native_check` ExecStartPre; denylist in `policy.default.json` |
| Budgets non-zero where zero=unlimited; freeze caps | **Verified** | Per C2 runbook |
| No secrets in issue/Linear bodies; key files mode 600 | **Verified** | No new leaks observed |
| IEC 62443 mapping current | **Verified** | Table v2.2 in this document |

---

## Revision history

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| v2.2 | 2026-08-24 | Auditor (ASP-431) | F-015–F-019 findings; H-022–H-026 items; IEC 62443 mapping table; closed F-007, F-012; mitigated F-008, F-009 |
| v2.1 | 2026-08-10 | Auditor (ASP-168) | F-001–F-014 findings; H-001–H-006, H-007–H-021, H-HOST-01; baseline IEC 62443 mapping |