# Starship OS — Fleet, Plants, Ops Manager, Red/Blue

**Status:** Alpha 2.1 scaffold  
**Config:** `config/fleet.yaml`  
**Service:** `services/fleet.py`  
**CLI:** `starshipctl fleet …`

## Model

```
Fleet
 ├── Ops Manager (aggregates status on starship.fleet.ops.*)
 ├── Plant Alpha     (production mesh)
 ├── Plant Edge      (thin nodes)
 └── Plant Range     (red/blue exercise, isolated)
       ├── red-team roles
       └── blue-team roles
```

| Concept | Meaning |
|---------|---------|
| **Fleet** | Named multi-plant deployment |
| **Plant** | Site/zone with profile + allowed roles |
| **Ops manager** | Node that publishes fleet summary heartbeats |
| **Red team** | Offensive exercise role (restricted tools) |
| **Blue team** | Defensive exercise role |

Cluster mesh (`services/cluster.py`) remains the low-level node/task router.  
Fleet is the **topology + exercise** control plane on top.

## NATS subjects (canonical aspen.* + dual-publish)

**Canonical (ADR-0003):** `aspen.fleet.node.register|heartbeat`, `aspen.fleet.ops.status`, `aspen.fleet.mission.*`, `aspen.safety.estop|clear`  
**Packages:** [aspen-edge-rrm](https://github.com/AbsolutionAI/aspen-edge-rrm), [aspen-swarm-manager](https://github.com/AbsolutionAI/aspen-swarm-manager)

## NATS subjects (dual-publish legacy)

| Subject | Purpose |
|---------|---------|
| `starship.fleet.register` | Node registration |
| `starship.fleet.heartbeat` | Node heartbeat |
| `starship.fleet.status` | Node status snapshot |
| `starship.fleet.ops.status` | Ops manager aggregate |
| `starship.fleet.exercise` | Exercise start/stop events |

Legacy `agnetic.fleet.*` is dual-published for Alpha 2.0 clients.

## CLI

```bash
starshipctl fleet status
starshipctl fleet plants
starshipctl fleet register
starshipctl fleet nodes
starshipctl fleet exercise start
starshipctl fleet exercise stop
starshipctl fleet exercise status

# or directly
python3 services/fleet.py daemon
```

## Node override

`/etc/starship/fleet-node.yaml`:

```yaml
node:
  plant: plant-edge
  roles: [proxy, plant-controller]
  team: ops
  profile: edge
```

## Red/blue policy notes

- Exercises default to `plant-range` (`isolation: true`).
- Phase D D1 first physical cell (BEL-192): profile `config/cells/plant-range-d1.yaml`, runbooks under `docs/runbooks/plant-range-*`, sim proofs `scripts/sim_plant_range_cell_profile.py` + `scripts/sim_dual_human_gate.py`. **No free motion** until G6+G7 green and dual-auth usable.
- Red-team never gets unrestricted OpenCode (enforced in `agents/fleet_policy.py` + toolsets `red_team` / `security_audit`).
- Red-team allowed tools: `read_file`, `list_dir`, `search_files`, `http_get`, `delegate_to_agent`.
- Set identity via env: `STARSHIP_FLEET_TEAM=red` `STARSHIP_FLEET_ROLES=red-team` or `/etc/starship/fleet-node.yaml`.

## Cross-plant ACL

Config in `config/fleet.yaml` → `acl`:

```yaml
acl:
  default: same_plant_only   # same_plant_only | deny | allow
  allow:
    plant-alpha: [plant-edge]
    plant-edge: [plant-alpha]
    plant-range: []
```

Enforced by `fleet_policy.check_cross_plant` / `check_tool(..., target_plant=...)`:

1. Same plant → allow  
2. Red-team during exercise → deny all cross-plant  
3. Source or target `isolation: true` → deny  
4. Explicit `acl.allow[source]` list  
5. Default fail-closed (`same_plant_only` / `deny`)

`delegate_to_agent` accepts `plant` / `target_plant` for ACL checks.

## Multi-node NATS auth

| File | Purpose |
|------|---------|
| `nats/fleet-accounts.conf.tmpl` | Default bus — multi-tenant accounts (H-001) |
| `scripts/fleet-enroll.sh` | Node enrollment: signed tokens, CSR signing, revocation (H-002) |
| `nats/fleet-bus.conf` | Shared token placeholder (trusted LAN opt-in) |
| `scripts/gen-nats-accounts.sh` | Materialize accounts + nkeys + client envs |
| `nats/fleet-auth.yaml` | Role → account / subject map |
| `agents/nats_connect.py` | Client helper (user/pass / token / nkey) |
| `nats/server.conf` | Deprecated placeholder stub (H-017) — never live secrets |
| `/etc/starship/nats/active.conf` | Symlink to active server conf |
| `/etc/starship/nats.env` | Client credentials for fleet daemon |

### Modes

| Mode | When | Auth |
|------|------|------|
| **`accounts`** | **default (all profiles, H-001)** | per-role user/pass + optional nkeys |
| `token` / `fleet` | explicit `STARSHIP_NATS_MODE=fleet` | shared `STARSHIP_NATS_TOKEN` via fleet-bus |

Live credentials are generated under `/etc/starship/nats/` (or gitignored
`nats/creds/`). See `docs/SECURITY.md` H-017 for scrub + rotation.

```bash
# Generate multi-tenant accounts (ops)
bash scripts/gen-nats-accounts.sh --out /etc/starship/nats
nats-server -c /etc/starship/nats/fleet-accounts.conf
set -a; source /etc/starship/nats/creds/ops.env; set +a
python3 services/fleet.py daemon
```

Accounts: `STARSHIP_OPS` · `STARSHIP_EDGE` · `STARSHIP_RANGE` (red/blue) · `STARSHIP_TELEM` · `SYS`  
Nkeys: optional (`nk` from `go install github.com/nats-io/nkeys/nk@latest`) → `creds/*.nk`  
Heartbeats dual-publish `starship.fleet.heartbeat` + `agnetic.fleet.heartbeat`.

### TLS + mTLS (default in new deployments, H-006)

```bash
bash scripts/gen-nats-tls.sh --out /etc/starship/nats/tls --host ops.example
# per-node client identity (signed by the fleet CA):
bash scripts/gen-nats-tls.sh --out /etc/starship/nats/tls --node plant-edge-01
# opt out (dev only): STARSHIP_NATS_TLS=0 bash scripts/starship-firstboot.sh
```

Firstboot runs the generator automatically and appends `tls { ... verify: true }`
to the active conf — non-TLS connections are rejected and clients must present a
fleet-CA certificate (`STARSHIP_NATS_CA` + cert/key + `tls://` via `nats_connect.py`).

### Node enrollment (H-002)

Remote nodes get their fleet identity through a signed enrollment protocol
(`scripts/fleet-enroll.sh`) — the node's private key never leaves the node:

```bash
# 1. ops manager: mint an enrollment token (RSA-signed by the fleet CA key)
bash scripts/fleet-enroll.sh issue-token --node cell-7 --days 7

# 2. node: generate keypair + CSR locally (token checked up front)
bash scripts/fleet-enroll.sh request --node cell-7 --token <TOKEN> --dir /tmp/enroll-cell7

# 3. ship cell-7.csr + token to ops (out of band), then sign:
bash scripts/fleet-enroll.sh sign --request /path/to/request --out /etc/starship/nats/tls

# 4. ship back node-cell-7-cert.pem + node-cell-7.env; source before connecting
set -a; source /etc/starship/nats/tls/node-cell-7.env; set +a
```

A rogue node cannot join: signing refuses invalid, expired, mismatched, or
already-consumed tokens. Compromised nodes are revoked and every layer fails
closed — the signer refuses re-issue, the fleet daemon drops register/heartbeat
events from revoked peers, and `nats_connect.py` refuses to connect when the
local identity (`STARSHIP_NATS_CERT` CN) is revoked.

```bash
bash scripts/fleet-enroll.sh revoke --node cell-7 --reason stolen-laptop
bash scripts/fleet-enroll.sh revoke --list   # <tls-out>/revocations.list
```

## Firstboot

`scripts/starship-firstboot.sh`:

| Profile | NATS mode | Auth |
|---------|-----------|------|
| edge | accounts | multi-tenant (`gen-nats-accounts.sh`, edge role) |
| server | accounts | multi-tenant (`gen-nats-accounts.sh`, ops role) |
| **ops** | **accounts** | multi-tenant (`gen-nats-accounts.sh`) |

Overrides:
- `STARSHIP_NATS_MODE=fleet` + `STARSHIP_FLEET_BUS=1` — shared token fleet-bus (trusted LAN)  
- `STARSHIP_NATS_ROUTES=...` — cluster routes (token mode)

No-auth mode: removed in H-001 (ASP-169). The bus always authenticates.

```bash
STARSHIP_PROFILE=ops sudo bash scripts/starship-firstboot.sh
```

## Dashboard

- Plant map: `GET /api/fleet` · `GET /api/fleet/plants`
- Exercise: `POST /api/fleet/exercise` `{"action":"start"|"stop"}`
- Register: `POST /api/fleet/register`
- UI panel **Fleet Map** + Exercise Start/Stop buttons (port 8788)
