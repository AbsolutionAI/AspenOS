# ADR-0003: Fleet, edge, and safety bus contracts

## Status
Accepted — 2026-08-06  
**Linear:** BEL-181 · Epic BEL-179  
**Schema home:** [aspen-contracts](https://github.com/AbsolutionAI/aspen-contracts)

## Context
Fleet (`docs/FLEET.md`), multi-node (`MULTI_NODE.md`), and edge RRM need one subject tree so packages interoperate.

## Decision

### Subject prefix
Prefer **`aspen.`** for new work. Dual-publish `starship.*` / `agnetic.*` only when bridging Alpha clients.

### Core subjects

| Subject | Payload (summary) | QoS notes |
|---------|-------------------|-----------|
| `aspen.fleet.node.register` | node_id, plant, roles[], caps[], version | register on boot |
| `aspen.fleet.node.heartbeat` | node_id, ts, status, resource{}, agents[] | 5–30s |
| `aspen.fleet.ops.status` | aggregate plants/nodes, degraded[] | ops-manager |
| `aspen.fleet.mission.*` | mission graph events | swarm-manager |
| `aspen.edge.<node_id>.heartbeat` | RRM-local detail | optional fan-in to fleet heartbeat |
| `aspen.edge.<node_id>.propose_act` | act proposals from micro-agents | RRM in |
| `aspen.edge.<node_id>.command` | RRM → micro-agent commands | |
| `aspen.safety.estop` | reason, source, ts | **retain + fanout; all RRMs** |
| `aspen.safety.clear` | operator clear after estop | human only |

### Envelope
All messages use aspen-contracts `event-envelope.schema.json`:
`id, source, type, time, data`.

### Safety
- `aspen.safety.estop` must be processable offline (local last-value if bus down after receipt).
- Actuation path checks estop latch before driver call.

## Consequences
- Implement ops-manager + fake edge against these names
- Update FLEET.md subject table to match
- JetStream streams: `FLEET`, `EDGE`, `SAFETY` (lab)

## Alternatives rejected
- Per-vendor topic schemes without envelope  
- Heartbeats only inside Paperclip (loses offline plant)  
