# F-017: Fleet node fingerprint for heartbeat / register

**Status:** Spec (fix pending)  
**Threat model:** F-017 (CVSS 7.5, AV:N/AC:L) — Fleet heartbeat spoofing  
**Related:** ADR-0003 (fleet subjects), ADR-0007 (authz), `docs/FLEET.md` (subject table)  
**Parent:** ASP-802 (2026-10-19 biweekly threat-model refresh)

---

## Problem

Fleet nodes register via `aspen.fleet.node.register` and advertise liveness via
`aspen.fleet.node.heartbeat` using NATS account + token authentication. A copied or
leaked credentials file lets an attacker register a fake node, inject false telemetry,
or exfiltrate fleet-state knowledge (plant topology, node roles, exercise status).

## Fingerprint field

Add an optional `node_fingerprint` field to both register and heartbeat payloads:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `node_id` | string | yes | Hostname or `STARSHIP_NODE_ID` |
| `hostname` | string | yes | `socket.gethostname()` |
| `plant` | string | yes | Plant identifier |
| `roles` | list[string] | yes | Agent roles |
| `team` | string | yes | Ops/red/blue |
| `profile` | string | yes | Server/edge/light-cell |
| `status` | string | yes | online/offline/degraded |
| `last_seen` | string | yes | ISO-8601 UTC |
| `capabilities` | dict | no | Hardware detection |
| **`node_fingerprint`** | **string** | **no (register)** / **yes (ops-validate)** | **SHA-256 of `/etc/machine-id` (or stable node identity file)** |

### Fingerprint derivation

```
node_fingerprint = sha256(machine_id_bytes)
```

Where `machine_id_bytes` is the trimmed content of `/etc/machine-id`
(stripped of leading/trailing whitespace, lowercased). This is the same
machine-identity source used by `systemd` and `dbus`, is present on every
Linux install, and does not change for the lifetime of the OS install.

**Rationale for SHA-256 of machine-id over ed25519:**
- No key-generation step; zero new secrets to manage
- `/etc/machine-id` is already root-owned and stable
- Ops-manager pre-populates its allowlist from the same source during
  firstboot — no out-of-band key distribution
- Ed25519 remains the upgrade path for PKI when CRL / key rotation is needed

### Payload examples

Register:
```json
{
  "node_id": "bt-asp-srv",
  "hostname": "bt-asp-srv",
  "plant": "plant-alpha",
  "roles": ["proxy", "ops"],
  "team": "ops",
  "profile": "server",
  "node_fingerprint": "abc123def456..."
}
```

Heartbeat:
```json
{
  "node_id": "bt-asp-srv",
  "status": "online",
  "last_seen": "2026-10-19T12:00:00+00:00",
  "node_fingerprint": "abc123def456..."
}
```

## Ops-manager validation

The ops-manager (fleet daemon) maintains an in-memory allowlist mapping
`node_id → node_fingerprint`. This allowlist is:

- Pre-populated from `config/fleet-fingerprints.yaml` at startup
- Read-only at runtime — new nodes must be enrolled by a captain by adding
  their fingerprint to the YAML file and reloading the daemon
- Compared on every register and heartbeat: if the payload carries a
  `node_fingerprint`, and the ops-manager has an allowlist entry for that
  `node_id`, the fingerprint **must match** or the payload is **rejected**
  (the state file is not updated and an audit event is published)

### Validation rules (in priority order)

1. If payload has no `node_fingerprint` and allowlist has no entry for
   `node_id` → **accept** (backward-compatible: pre-fingerprint nodes
   continue to work, and non-enrolled sim nodes are not blocked)
2. If payload has no `node_fingerprint` and allowlist **has** an entry →
   **reject** (enrolled node must advertise its fingerprint)
3. If payload has `node_fingerprint` and allowlist has no entry →
   **accept** but log (fleet-unknown-fingerprint warning; node is not yet
   enrolled but we don't drop its telemetry on the floor)
4. If payload has `node_fingerprint` and allowlist entry exists, and they
   **match** → **accept** (happy path)
5. If payload has `node_fingerprint` and allowlist entry exists, and they
   **differ** → **reject** (credential theft / spoofing attempt; publish
   `aspen.sentinel.audit.event` with result=deny)

### Allowlist format (`config/fleet-fingerprints.yaml`)

```yaml
# Known node fingerprints. Added by ops captain during node enrollment.
# The file is not created by default — an empty or missing file means
# "fingerprint validation is not active" (backward-compatible).
nodes:
  bt-asp-srv: "abc123def456..."
  cell-alpha-01: "789012..."
```

## Threat model update

Replace the current F-017 row:

| ID | Threat | Category | CVSS | Current mitigation | Status |
|----|--------|----------|------|--------------------|--------|
| F-017 | Fleet heartbeat spoofing (register fake node) | Identity | 7.5 | NATS accounts + token; no PKI/fingerprint yet | **Open** |

With:

| ID | Threat | Category | CVSS | Current mitigation | Status | Next step |
|----|--------|----------|------|--------------------|--------|-----------|
| F-017 | Fleet heartbeat spoofing (register fake node) | Identity | 5.3 (reduced) | NATS accounts + token + **optional fingerprint validation** (`node_fingerprint` field, ops-manager allowlist) | **Mitigated (spec, not enforced)** | Enroll first cell nodes in `config/fleet-fingerprints.yaml` and enable enforcement |

## Acceptance criteria

- [ ] Spec filed at `docs/security/f-017-fleet-node-fingerprint.md`
- [ ] Hermetic test: reject unknown/mismatched fingerprint
- [ ] Hermetic test: accept matching fingerprint
- [ ] Hermetic test: backward-compatible — no fingerprint accepted when allowlist is empty
- [ ] Threat-model F-017 can cite this spec
- [ ] PKI enrollment of real nodes is out of scope (ed25519 upgrade path documented)