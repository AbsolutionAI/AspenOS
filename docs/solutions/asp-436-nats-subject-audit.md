# ASP-436 — H-026: Per-role NATS Subject Permission Audit

**Date:** 2026-09-20
**Auditor:** Agent 4203b00e (Paperclip)
**Scope:** Per-role NATS publish/subscribe ACLs, cross-account imports/exports, and materialized config consistency — against least-privilege principle.
**References:**
- Threat model v2.2 §3.1 (ASP-431)
- `nats/fleet-accounts.conf.tmpl` — source of truth (multi-tenant accounts template)
- `nats/fleet-auth.yaml` — role ACL summary (mirror)
- `nats/subjects.yaml` — subject topology + aspen.* namespace
- `nats/fleet-bus.conf` — shared-token fleet bus (trusted LAN)
- `nats/agent-bus.conf` — dev-mode agent bus (no auth)
- `nats/server.conf` — legacy dev config (tracked in git)
- `src/python/gatekeeper/minimal_shim.py` — SAFETY_SUBJECTS + CAPABILITY_STORE
- `src/python/gatekeeper/safety_enforcer.py` — SafetySubjectEnforcer
- ADR-0007 (sentinel subjects), ADR-0003 (authz subjects), ADR-0009 (gatekeeper)

**Methodology:** Each role's permitted publish/subscribe subjects, exports, and imports were compared against the actual subjects used by that role's services. Over-permissions were flagged where the ACL grants access to subjects the role never needs.

---

## 1. Role ACL Matrix (as-configured in fleet-accounts.conf.tmpl)

| Role | Account | Publish Allow | Subscribe Allow | Exports | Imports |
|------|---------|---------------|-----------------|---------|---------|
| ops | STARSHIP_OPS | `starship.>`, `agnetic.>`, `aspen.sentinel.>`, `aspen.authz.>`, `aspen.fleet.>`, `aspen.safety.>` | (same) | fleet/agent/telemetry + aspen.sentinel/authz | EDGE fleet/edge/safety, TELEM telemetry (7 streams) |
| edge | STARSHIP_EDGE | fleet.{heartbeat,register,status}, agent.proxy.>, telemetry.>, aspen.fleet.>, aspen.edge.>, aspen.safety.{estop,authorize_clear} | fleet.>, fleet.ops.>, agent.proxy.>, aspen.fleet.>, aspen.edge.>, aspen.safety.{estop,clear}, aspen.sentinel.> | fleet.>, aspen.fleet.>, aspen.edge.>, aspen.safety.estop | aspen.sentinel.> (from OPS) |
| red | STARSHIP_RANGE | agent.proxy.>, fleet.heartbeat, aspen.fleet.node.{register,heartbeat}, aspen.edge.> | agent.proxy.>, fleet.exercise, aspen.fleet.>, aspen.safety.estop | (none) | (none — isolated) |
| blue | STARSHIP_RANGE | agent.>, fleet.{heartbeat,status}, aspen.fleet.>, aspen.edge.> | starship.>, agnetic.>, aspen.fleet.>, aspen.safety.estop, aspen.sentinel.fleet.overview | (none) | (none — isolated) |
| telem | STARSHIP_TELEM | telemetry.> | (none) | telemetry.> | (none) |

### 1.1 Dual-namespace inflation

Every role has both `starship.*` and `agnetic.*` allowances — a carry-over from the Alpha 2.0 dual-publish migration (H-021). This doubles ACL entropy for no security value. Once the migration completes, the `agnetic.*` entries should be removed.

---

## 2. Findings

### Finding F-001 (HIGH): OPS publish `aspen.safety.>` is over-permissive

**Config:** `fleet-accounts.conf.tmpl` lines 80-96 — OPS publish/subscribe both allow `"aspen.safety.>"` .

**Issue:** OPS as the sentinel/control host can publish to ALL safety subjects (`aspen.safety.estop`, `aspen.safety.clear`, `aspen.safety.authorize_clear`). Safety events are defined in ADR-0007 as edge-originated. The gatekeeper's `SafetySubjectEnforcer` provides application-layer protection, but the NATS ACL should also restrict OPS to **subscribe-only** for safety — OPS should observe safety state, not originate it.

**Risk:** An OPS credential compromise (or misbehaving OPS agent) can forge safety commands directly at the NATS level, bypassing the gatekeeper.

**Remediation:** Change OPS safety allowance to subscribe-only:
```
publish: { allow: ["starship.>", "agnetic.>", "aspen.sentinel.>", "aspen.authz.>", "aspen.fleet.>"] }
subscribe: { allow: [..., "aspen.safety.>"] }
```

### Finding F-002 (HIGH): EDGE publish `aspen.fleet.>` is over-permissive

**Config:** `fleet-accounts.conf.tmpl` line 141 — EDGE publish allows `"aspen.fleet.>"` .

**Issue:** `aspen.fleet.>` covers all fleet subjects including `aspen.fleet.mission.>` (mission lifecycle) and `aspen.fleet.ops.status` (ops-manager aggregate). An edge node should only publish:
- `aspen.fleet.node.register` — its own registration
- `aspen.fleet.node.heartbeat` — liveness
- `aspen.edge.>` — edge-specific subjects
- `aspen.safety.estop`, `aspen.safety.authorize_clear` — safety

**Risk:** Edge credential compromise allows publishing fake mission commands or ops status.

**Remediation:** Replace `"aspen.fleet.>"` with:
```
"aspen.fleet.node.register"
"aspen.fleet.node.heartbeat"
```

### Finding F-003 (MEDIUM): EDGE imports `aspen.sentinel.>` — scope too broad

**Config:** `fleet-accounts.conf.tmpl` line 172 — EDGE imports `{stream: {account: "STARSHIP_OPS", subject: "aspen.sentinel.>"}}`.

**Issue:** Edge imports ALL sentinel subjects: audit events, fleet overview, OSINT ingest, incident channel. Edge needs only `aspen.sentinel.fleet.overview` for real-time fleet status awareness.

**Risk:** Audit events and incident channel data are sent across the conduit to edge nodes, expanding the data-plane attack surface.

**Remediation:** Scope the import to `"aspen.sentinel.fleet.overview"` and add specific subjects as needed.

### Finding F-004 (HIGH): EDGE subscribe `aspen.sentinel.>` — same scope problem

**Config:** `fleet-accounts.conf.tmpl` line 158 — EDGE subscribe allows `"aspen.sentinel.>"`.

**Issue:** Even without changing the import, the EDGE subscribe permission permits subscribing to ALL sentinel subjects. Since the import from OPS gates what the account can actually receive, this is currently a no-op for subjects not imported, but it creates a dangerous default-widen pattern.

**Remediation:** Match the subscribe permission to the import scope: `"aspen.sentinel.fleet.overview"`.

### Finding F-005 (HIGH): RED publish `aspen.edge.>` is over-permissive

**Config:** `fleet-accounts.conf.tmpl` line 193 — RED publish allows `"aspen.edge.>"`.

**Issue:** RED in the isolated range plant can publish to ALL edge subjects, including:
- `aspen.edge.<node_id>.propose_act` — proposing actuation
- `aspen.edge.<node_id>.authorize` — authorizing actuation
- `aspen.edge.<node_id>.command` — sending commands

During exercise, the red team should simulate attacks but NOT have the ability to forge real edge actuation proposals at the NATS level.

**Risk:** Red publishing to `aspen.edge.*.authorize` or `aspen.edge.*.propose_act` could confuse downstream consumers or the gatekeeper if isolation boundaries are ever bridged.

**Remediation:** Restrict RED publish to only heartbeat/registration subjects within the range:
```
"starship.agent.proxy.>"
"starship.fleet.heartbeat"
"aspen.fleet.node.register"
"aspen.fleet.node.heartbeat"
```
Remove `"aspen.edge.>"` from RED publish.

### Finding F-006 (MEDIUM): RED subscribe `aspen.safety.estop` leaks production safety state

**Config:** `fleet-accounts.conf.tmpl` line 203 — RED subscribe allows `"aspen.safety.estop"`.

**Issue:** The range plant has no import from OPS or EDGE, so `aspen.safety.estop` messages from production plants should not reach RED. However, the ACL permission makes the subject visible in the account's namespace. If a future change adds an import to RANGE, the subscribe permission would immediately grant access to production safety state.

**Risk:** Anticipatory over-permission creates future-exposure latent risk.

**Remediation:** Remove `"aspen.safety.estop"` from RED subscribe. Add it later via a scoped import if the exercise scenario genuinely needs safety observability.

### Finding F-007 (MEDIUM): BLUE publish `starship.agent.>` is over-permissive

**Config:** `fleet-accounts.conf.tmpl` lines 212-214 — BLUE publish allows `"starship.agent.>"` and `"agnetic.agent.>"`.

**Issue:** BLUE can publish to ALL agent command subjects (`starship.agent.romi.command.*`, `starship.agent.ergo.command.*`, etc.) within the range. While the range is isolated (no exports), a compromised blue agent could send commands to any other agent within the range plant.

**Risk:** Within-range lateral movement — blue-agent compromise can commandeer other range agents.

**Remediation:** Scope BLUE to proxy subjects only:
```
"starship.agent.proxy.>"
"starship.fleet.heartbeat"
"starship.fleet.status"
```

### Finding F-008 (MEDIUM): BLUE subscribe `starship.>` is over-permissive

**Config:** `fleet-accounts.conf.tmpl` line 223 — BLUE subscribe allows `["starship.>", "agnetic.>", ...]`.

**Issue:** BLUE can subscribe to all subjects within the range account. Since RED and BLUE share the same account (STARSHIP_RANGE), BLUE can see RED's proxy traffic and RED can see BLUE's agent traffic.

**Risk:** No within-account isolation between red and blue teams. This is by design (single account for range), but should be documented as a known limitation.

**Remediation:** Accept as design constraint for v2.2. Consider splitting RANGE into separate sub-accounts (RANGE_RED, RANGE_BLUE) in a future architecture review. Document in §Known Limitations.

### Finding F-009 (MEDIUM): BLUE publish `aspen.fleet.>` is over-permissive

**Config:** `fleet-accounts.conf.tmpl` line 218 — BLUE publish allows `"aspen.fleet.>"`.

**Issue:** Same pattern as F-002. Blue does not need to publish mission or ops-status subjects.

**Remediation:** Restrict to node register/heartbeat same as red (F-005).

---

## 3. Cross-Account Import/Export Audit

| Exporting Account | Exported Subjects | Importing Account | Status |
|-------------------|-------------------|-------------------|--------|
| STARSHIP_OPS | `starship.fleet.>`, `starship.agent.>`, `starship.telemetry.>`, `agnetic.fleet.>`, `agnetic.agent.>`, `agnetic.telemetry.>`, `aspen.sentinel.>`, `aspen.authz.>` | (none import starship.agent.> or agnetic.agent.>) | **Dead exports:** `starship.agent.>`, `agnetic.agent.>` — no consumer imports these. Cleanup opportunity. |
| STARSHIP_OPS | `aspen.sentinel.>` | STARSHIP_EDGE | **Active — but too broad (F-003).** |
| STARSHIP_OPS | `aspen.authz.>` | (none import) | **Dead export.** No role imports authz subjects. Gatekeeper publishes internally. |
| STARSHIP_EDGE | `starship.fleet.>`, `agnetic.fleet.>`, `aspen.fleet.>`, `aspen.edge.>`, `aspen.safety.estop` | STARSHIP_OPS | **Active.** Used for fleet status, edge telemetry, safety events. |
| STARSHIP_TELEM | `starship.telemetry.>`, `agnetic.telemetry.>` | STARSHIP_OPS | **Active.** Dual legacy waste. |

### 3.1 Dead export impact

Three exports have no import consumer:
1. `starship.agent.>` — OPS exports full agent mesh subject namespace
2. `agnetic.agent.>` — Legacy mirror of above
3. `aspen.authz.>` — Authz subject namespace

These are benign (no consumer = no blast radius) but inflate the ACL surface area. Every unused export is one misconfiguration away from being consumed by a future import.

### 3.2 Edge import surface

EDGE imports 7 streams from TELEM and OPS. 4 are legacy (`starship.*` + `agnetic.*` duplicates). The `aspen.safety.estop` import from EDGE to OPS is necessary for the sentinel host to observe estop state. The `aspen.edge.>` import enables OPS to monitor per-node edge proposals and authorizations.

---

## 4. Materialized Config Drift

The checked-in template (`fleet-accounts.conf.tmpl`) and the generated config (`nats/fleet-accounts.conf`, gitignored) differ in:
- **Rate limiting headers:** Template has ASP-375 rate-limit comments and per-account connection/subscription caps (`max_connections`, `max_subscriptions`); materialized config has NO account-level limits.
- **nkey-auth:** Materialized config uses nkey entries (confirmed H-011); the template uses password placeholders.

**Impact:** Materialized config must be regenerated to apply ASP-375 rate limits and ASp-436 ACL fixes.

---

## 5. Legacy Dev Config with Hardcoded Credentials (CRITICAL)

### Finding F-010 (CRITICAL): `nats/server.conf` contains plaintext credentials in tracked file

**File:** `nats/server.conf` — tracked in git at commit `c8672c12` (initial Alpha 2.1 reconcile).

**Content:**
```yaml
authorization: ***
  token: "agnetic_s3cr3t_t0k3n"
  ...
  users: [
    {user: "admin", password: "agnetic_admin_2026"}
    {user: "agnetic", password: "agnetic_user_2026"}
  ]
```

**Status:** The ASP-365/H-017 scrub commit (`191020e`) replaced these with placeholders and added a `DEPRECATED` header, but that commit was **never merged to master** — it lives only on branch `hermes/asp-459-packaging-forward-port`.

**Risk:** Plaintext credentials committed to the repo. Even if these are stale lab credentials, they represent a revocable credential disclosure. Anyone with repo access can read them.

**Remediation:** Forward-port commit `191020e` changes to `nats/server.conf` to master. This replaces the credentials with placeholders and adds the `DEPRECATED` header.

---

## 6. Legacy Dual-Publish Subject Waste (H-021 sibling)

Every role ACL includes both `starship.*` and `agnetic.*` allowances — a 2x factor of ACL surface area during the migration window. The migration from `agnetic.*` to `starship.*` to `aspen.*` leaves three parallel namespaces.

**Impact by role:**
| Role | Starship entries | Agnetic entries | Aspen entries | Total entries | Waste factor |
|------|-----------------|-----------------|---------------|---------------|-------------|
| ops | 1 (wildcard) | 1 (wildcard) | 4 | 6 | 33% waste |
| edge | 5 | 4 | 7 | 16 | 25% waste |
| red | 2 | 2 | 3 | 7 | 28% waste |
| blue | 3 | 3 | 2 | 8 | 37% waste |
| telem | 1 | 1 | 0 | 2 | 50% waste |

Additionally, subagent subjects (in `agent_daemon.py` lines 94-99) use the legacy `agnetic.agent.<name>.*` pattern — these will break if `agnetic.*` is ever removed from the ops ACL.

---

## 7. Summary and Recommendations

### HIGH priority (fix this sprint)

| Finding | Role | Issue | Remediation |
|---------|------|-------|-------------|
| **F-010** | all | `nats/server.conf` has plaintext creds in tracked file | Forward-port ASP-365 scrub to master |
| **F-001** | ops | OPS publishes to `aspen.safety.>` | Restrict to subscribe-only for safety |
| **F-002** | edge | EDGE publishes `aspen.fleet.>` | Scope to node.register/node.heartbeat only |
| **F-004** | edge | EDGE subscribes `aspen.sentinel.>` | Scope import to fleet.overview |
| **F-005** | red | RED publishes `aspen.edge.>` | Remove; restrict to heartbeat/register only |

### MEDIUM priority (next sprint)

| Finding | Role | Issue | Remediation |
|---------|------|-------|-------------|
| **F-003** | edge | Sentinel import too broad | Match to fleet.overview scope |
| **F-006** | red | Subscribe `aspen.safety.estop` | Remove; add back with scoped import if needed |
| **F-007** | blue | Publish `starship.agent.>` | Scope to proxy subjects |
| **F-008** | blue | Subscribe `starship.>` | Document as known constraint |
| **F-009** | blue | Publish `aspen.fleet.>` | Scope to node register/heartbeat |

### LOW priority (v2.3 planning)

| Item | Detail |
|------|--------|
| Dead export cleanup | `starship.agent.>`, `agnetic.agent.>`, `aspen.authz.>` — remove exports with no import consumer |
| Legacy dual-publish consolidation | Once `agnetic.*` traffic ceases, remove all `agnetic.*` ACL entries |
| Subagent subject migration | `agent_daemon.py` subagent subjects use `agnetic.agent.*` — migrate to `starship.agent.*` before legacy removal |
| RANGE sub-account split | Split STARSHIP_RANGE into STARSHIP_RANGE_RED / STARSHIP_RANGE_BLUE for within-exercise isolation |

---

## 8. Next Steps

1. **Commit this audit document** to `docs/solutions/asp-436-nats-subject-audit.md`.
2. **Fix F-010** (server.conf credentials): cherry-pick or forward-port `191020e` changes.
3. **Apply F-001 through F-009** by editing `nats/fleet-accounts.conf.tmpl` and verifying with `scripts/gen-nats-accounts.sh --no-nkeys --out /tmp/nats-test`.
4. **Regenerate** the materialized config on target systems (`bash scripts/gen-nats-accounts.sh --out /etc/starship/nats`).
5. **Reload** NATS config: `kill -HUP $(pidof nats-server)`.
6. **Update threat model** (v2.3 refresh) with H-026 disposition and F-001 through F-010 tracking.
7. **Re-run** `make test` to verify no gatekeeper or NATS client tests regress.

---

*End of audit. Auditor: 4203b00e. Date: 2026-09-20.*
