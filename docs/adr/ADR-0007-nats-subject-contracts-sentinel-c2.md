# ADR-0007: NATS Subject Contracts for Aspen Sentinel + AspenOS C2

**Status:** Accepted — 2026-08-31  
**Accepted by:** ASP-530 Weekly Architecture Review  
**Reconfirmed:** ASP-563 Weekly Architecture Review (2026-09-07) — status re-landed after orphan commit  
**Linear:** BEL-196 (A3) · Parent BEL-193 (AspenGrove Three-Product Epic)  
**Schema home:** aspen-contracts (https://github.com/AbsolutionAI/aspen-contracts) — monorepo `docs/FLEET.md` is interim SoR until mirror  
**Related:** ADR-0003 (Fleet/Edge Safety), ADR-0009 (Gatekeepers), Master Spec v4.0 §3.1 (NATS/JetStream bus), BEL-179 (Fleet Epic)

## Context
Aspen Sentinel requires dedicated subjects for authorization gates, audit feeds, fleet overview, and OSINT ingest while preserving the existing `aspen.fleet.*` / `aspen.edge.*` / `aspen.safety.*` tree (ADR-0003). AspenOS C2 and micro-agents must interoperate without breaking changes. All safety-adjacent actions remain `propose_act` only until dual-human authorization.

## Decision
### Subject Prefix & Namespace
- Primary: `aspen.sentinel.*` and `aspen.authz.*`
- Preserve `aspen.` for all new work (sunset dual-publish `starship.*` / `agnetic.*` tracked as open candidate **ADR-0011**)
- Backward compatibility: existing fleet subjects unchanged

### New Subject Table (additions to FLEET.md / subject matrix)

| Subject                              | Payload (summary)                                      | QoS / Notes                          | Consumers                  |
|--------------------------------------|-------------------------------------------------------|--------------------------------------|----------------------------|
| `aspen.sentinel.fleet.overview`     | aggregate plants/nodes/status, degraded[]            | fan-in from fleet.heartbeat         | Sentinel dashboard        |
| `aspen.sentinel.audit.event`        | {event_id, actor, action, target, result, ts}        | durable JetStream                   | Sentinel audit, compliance|
| `aspen.sentinel.tools.anomaly`      | finding {finding_id, rule, severity, actor, message, window_s, events[], event_id, ts} | JetStream, `Nats-Msg-Id: finding_id` (best-effort, idempotent) | ops paging (R1 high), Sentinel dashboard |
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
- **Migration**: Existing Alpha clients continue on dual-prefix until >50% consumers on `aspen.*` (open candidate ADR-0011).

## Wired so far (ASP-537 / ASP-536)
- `aspen.sentinel.audit.event` — publisher live: `src/python/sentinel/audit.py`
  (`AuditEventPublisher`) + `scripts/sentinel-audit.py` CLI. Events use the
  `{event_id, actor, action, target, result, ts}` envelope, are appended to a
  JSONL journal (always) and mirrored into the `ASPEN_SENTINEL` JetStream stream
  on subject `aspen.sentinel.audit.event` (best-effort, idempotent replay). The
  gatekeeper shim (`ADR-0009`) fans capability decisions into this trail.
  Consumer (Sentinel dashboard) is follow-up.
- `aspen.sentinel.fleet.overview` — producer live:
  `src/python/sentinel/fleet_overview.py` (`FleetOverviewProducer`) +
  `scripts/sentinel-fleet-overview.py` CLI. Aggregates plants/nodes/status with
  `degraded[]`, fans in from `aspen.fleet.node.heartbeat` / `.register` /
  `aspen.fleet.ops.status`, journals every snapshot (JSONL, fsync) and mirrors
  to JetStream on `aspen.sentinel.fleet.overview`. The dashboard consumer
  (`GET /api/sentinel/overview`) prefers live → producer journal → local preview
  stub (`src/python/sentinel/consumer.py` `fleet_overview()`).
- `aspen.authz.gate.request/decision`, `aspen.authz.capability.grant` — subscribed
  / published by the gatekeeper shim (`src/python/gatekeeper/nats_client.py`).
  Since ASP-540 the gatekeeper intercepts safety-adjacent `propose_act`
  (`aspen.safety.*`, `aspen.edge.*.command`, `aspen.fleet.mission.start`),
  collects two distinct human approvals on `aspen.authz.gate.decision`
  (`{request_id, human_id}`), refuses bare/single-human forwards, and gates
  every decision into the ADR-0007 audit envelope.
- `aspen.sentinel.tools.anomaly` — consumer live:
  `src/python/sentinel/anomaly_consumer.py` (`AnomalyConsumer`) +
  `scripts/sentinel-tool-anomaly.py` CLI. Subscribes to
  `aspen.sentinel.audit.event`, feeds every event through
  `ToolAnomalyDetector` (ASP-379), and publishes findings to
  `aspen.sentinel.tools.anomaly`. Findings are journaled to
  `/var/lib/aspen/sentinel/anomaly.jsonl` (append + fsync, always) and mirrored
  to JetStream best-effort with `Nats-Msg-Id: finding_id`, where `finding_id` is
  a content hash of the incident so a replay collapses onto one message instead
  of paging twice. Rules: R1 `sensitive_read_then_egress` (high — page), R2
  `high_risk_burst`, R3 `denial_probe`, R4 `error_storm`. **Fail-open and
  log-only**: nothing here can block a tool call or alter a verdict.
  Delivery is at-most-once (`nc.subscribe`, not a durable pull consumer) — see
  the trade-off note in `docs/plans/ASP-687.md`.
- NATS ACLs for `aspen.sentinel.*` / `aspen.authz.*` / `aspen.fleet.*` /
  `aspen.safety.*` per role — `nats/fleet-accounts.conf.tmpl` (ASP-536).
  `aspen.sentinel.tools.anomaly` needs no ACL change: it falls under the existing
  `aspen.sentinel.>` grant (verified against the template).

**Next**: Sentinel dashboard consumer for `aspen.sentinel.fleet.overview` /
`aspen.sentinel.audit.event`; a durable JetStream pull consumer for
`aspen.sentinel.audit.event` (to replace ASP-687's at-most-once subscription);
ops paging consumer for `aspen.sentinel.tools.anomaly`; update Master Spec §3.1.

## Acceptance Criteria
- Contracts published in aspen-contracts repo
- FLEET.md / subject table updated with new rows + cross-links
- Example payloads for dual-human events documented
- No regression on BEL-179 fleet subjects
- Clear mapping documented for Sentinel dashboard

**Next**: Implement gatekeeper layer (BEL-215) as ADR-0009; update Master Spec §3.1.