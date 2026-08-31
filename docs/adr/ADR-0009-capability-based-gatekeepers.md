# ADR-0009: Capability-Based Gatekeepers (No Broad API Keys)

**Status:** Accepted (design) — 2026-08-31  
**Accepted by:** ASP-530 Weekly Architecture Review  
**Implementation:** BEL-215 continues (NATS wire, adapter mediation, no broad keys in images)  
**Linear:** BEL-215 (Urgent) · Related BEL-196 (NATS contracts), ADR-0003 (Safety Contracts), Master Spec v4.0 hard rules  
**Prototype:** `src/python/gatekeeper/minimal_shim.py`  
**Target Products:** AspenOS (primary), Aspen Sentinel, aspen-dev

## Context
Current agents (Hermes, Paperclip, Opencode) receive broad credentials or direct NATS/ROS2 access. This violates the Master Spec hard rule: agents emit only `propose_act` on safety-adjacent subjects until dual human authorization. Cloudflare OS gatekeeper pattern provides the model: every access is mediated, logged, and capability-scoped.

## Decision
Introduce a **Gatekeeper layer** that sits between all agents/Paperclip and real systems (NATS, ROS2, OPC-UA, Git, Linear, file systems, etc.).

### Core Principles
1. **No broad keys ever**: Agents never hold raw credentials. They request capabilities via `aspen.authz.gate.request`.
2. **Propose + Dual Auth**: Safety-adjacent actions always start as `propose_act`. Dual-human approval required for RED/BLACK (estop, robot commands, fleet control, financial actions).
3. **Audit Everything**: Every observation, capability grant, and decision is logged to `aspen.sentinel.audit.event`.
4. **Modular Profiles**: Light Cell (minimal caps) vs Full Plant (full set) activated by plant profile.
5. **Software Data-Diode Emulation**: Gatekeeper enforces one-way flows where possible; hardware diode path preserved for future gov contracts.

### Gatekeeper Architecture (mermaid)
```mermaid
flowchart TD
    A[Agent / Paperclip] -->|propose_act + context| B[Gatekeeper]
    B -->|capability check + log| C{Decision Engine}
    C -->|grant| D[Capability Token (short-lived, scoped)]
    C -->|deny or propose| E[Human Gate / Dual Auth]
    E -->|authorize| D
    D --> F[Target System<br/>NATS / ROS2 / Git / Linear]
    B --> G[Audit Log<br/>aspen.sentinel.audit.event]
```

### Capability Manifest Example (for Light Cell)
```json
{
  "agent_id": "aspen-fleet-edge",
  "caps": [
    "aspen.fleet.node.heartbeat:read",
    "aspen.edge.<node>.propose_act:write",
    "aspen.sentinel.audit.event:write"
  ],
  "expires": "2026-08-30T00:00:00Z",
  "profile": "light-cell"
}
```

### Integration Points
- **NATS**: Gatekeeper issues nkey / JWT with subject-level permissions (supports BEL-196 subjects).
- **Hermes / Paperclip**: Adapter config routes all external calls through gatekeeper MCP or local proxy.
- **Sentinel**: Dashboard shows pending proposals + capability grants in real time.

## Consequences
- **Positive**: Zero-trust posture; full auditability; enables SME operator progressive assistance (BEL-240); supports manufacturing safety (real-time, offline capable).
- **Trade-offs**: Added latency on first request (mitigate with short-lived cached tokens); initial implementation effort.
- **Risks**: Gatekeeper itself becomes single point of failure (mitigate with local fallback + redundant instances).

## Acceptance Criteria
- Gatekeeper design documented + prototyped (local Python/Go shim)
- No agent holds broad credential in any AspenOS / Sentinel image
- All critical actions require explicit grant + human gate where required
- Full audit trail implemented and queryable from Sentinel
- Modular per Light Cell / Full Plant profiles

**Next**: Wire into BEL-196 NATS subjects; implement first gatekeeper shim; update Master Spec §4 (Security).

---

**Agent Surface Items (BEL-237/238/239/240)**: These are now unblocked by the gatekeeper layer. Next sprint: implement "Invoke Preferred Agent" affordance + Crash → Agent Briefing once ADR-0009 is accepted. Daily brief cron already surfaces progress.