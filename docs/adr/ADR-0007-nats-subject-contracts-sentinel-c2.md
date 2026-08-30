# ADR-0007: NATS Subject Contracts for Aspen Sentinel + AspenOS C2

**Status:** Proposed — 2026-08-29  
**Linear:** BEL-196 (A3) · Parent BEL-193 (AspenGrove Three-Product Epic)  
**Schema home:** aspen-contracts (https://github.com/AbsolutionAI/aspen-contracts)  
**Related:** ADR-0003 (Fleet/Edge Safety), Master Spec v4.0 §3.1 (NATS/JetStream bus), BEL-179 (Fleet Epic)

## Context
Aspen Sentinel requires dedicated subjects for authorization gates, audit feeds, fleet overview, and OSINT ingest while preserving the existing `aspen.fleet.*` / `aspen.edge.*` / `aspen.safety.*` tree (ADR-0003). AspenOS C2 and micro-agents must interoperate without breaking changes. All safety-adjacent actions remain `propose_act` only until dual-human authorization.

## Decision
### Subject Prefix & Namespace
- Primary: `aspen.sentinel.*` and `aspen.authz.*`
- Preserve `aspen.` for all new work (sunset dual-publish `starship.*` / `agnetic.*` per open ADR-0007 candidate)
- Backward compatibility: existing fleet subjects unchanged

### New Subject Table (additions to FLEET.md / subject matrix)

| Subject                              | Payload (summary)                                      | QoS / Notes                          | Consumers                  |
|--------------------------------------|-------------------------------------------------------|--------------------------------------|----------------------------|
| `aspen.sentinel.fleet.overview`     | aggregate plants/nodes/status, degraded[]            | fan-in from fleet.heartbeat         | Sentinel dashboard        |
| `aspen.sentinel.audit.event`        | {event_id, actor, action, target, result, ts}        | durable JetStream                   | Sentinel audit, compliance|
| `aspen.sentinel.osint.ingest`       | source, raw/ref, confidence, tags[]                  | optional replay                     | Sentinel OSINT pane       |
| `aspen.authz.gate.request`          | capability, resource, context, proposer_agent_id     | propose_act path                    | Gatekeeper (BEL-215)      |
| `aspen.authz.gate.decision`         | request_id, decision (grant/deny), humans[], note?   | dual-human required for RED/BLACK   | Agents, audit             |
| `aspen.authz.capability.grant`      | agent_id, caps[], expires?, scope                    | modular per Light Cell / Full Plant | Hermes/Paperclip agents   |
| `aspen.sentinel.incident.channel`   | incident_id, severity, summary, link                 | Buzz / Matrix bridge                | Sentinel operators        |

### Envelope & Safety Rules (unchanged from ADR-0003)
- All messages use `event-envelope.schema.json` (`id, source, type, time, data`).
- Safety-adjacent subjects (`aspen.authz.*`, `aspen.safety.*`, `aspen.edge.*.propose_act`) emit **only** `propose_act` until two distinct humans authorize via `aspen.edge.<node>.authorize` or `aspen.authz.gate.decision`.
- Gatekeeper layer (BEL-215) mediates all real-system access (NATS, ROS2, OPC-UA, Git, etc.). No agent ever holds broad credentials.

### Example Dual-Human Authorization Payload (aspen.authz.gate.decision)
```json
{
  "request_id": "uuid",
  "decision": "grant",
  "humans": ["josiah@bellahtech.com", "operator-2"],
  "capability": "aspen.fleet.mission.start",
  "resource": "plant:chaé-cell-01",
  "note": "Approved for shift 2026-08-29"
}
```

## Consequences
- **Positive**: Clean separation for Sentinel dashboard consumers; full audit trail; enables capability-based gatekeepers (BEL-215); supports Light Cell vs Full Plant profiles.
- **Risks / Mitigations**: Breaking change risk low (additive only). Dual-human path already enforced in safety contracts.
- **Migration**: Existing Alpha clients continue on dual-prefix until >50% consumers on `aspen.*` (open ADR-0007).

## Acceptance Criteria
- Contracts published in aspen-contracts repo
- FLEET.md / subject table updated with new rows + cross-links
- Example payloads for dual-human events documented
- No regression on BEL-179 fleet subjects
- Clear mapping documented for Sentinel dashboard

**Next**: Implement gatekeeper layer (BEL-215) as ADR-0009; update Master Spec §3.1.