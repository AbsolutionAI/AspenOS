# ASP-372 / H-008 / F-008: OT/ICS-aware firewall rule templates for manufacturing cells (compound)

**Status:** DRAFT — reference only. No host firewall is modified by this work.
**Source:** Security Threat Model v2.2 (ASP-298) — MEDIUM finding F-008 (cell
perimeter segmentation); reopened by board comment `672ab72e` (false-done:
prior draft existed only as an attachment).
**Plan:** `docs/plans/ASP-372.md`
**Master Spec ref:** `docs/sor/ASPENGROVE_MASTER_SPEC_v4.0.md` (manufacturing
cell / OT topology)
**Templates:** `docs/security/firewall-templates/`
**Parent issue:** ASP-298
**Updated:** 2026-09-20

---

## 1. Deliverable

Versioned, protocol-aware, **draft-only** cell perimeter firewall templates for
manufacturing cells that will run the MQTT / OPC-UA / ROS2 last-mile drivers.
They are committed to git so the intended cell perimeter policy is reproducible
and reviewable long before the physical cell gate exists. Application is gated
on physical cell commissioning — see §7.

Files in git (this is the fix for the reopen):

| File | Purpose |
|------|---------|
| `docs/security/firewall-templates/README.md` | Index, status notice, composition guide, compliance cross-ref |
| `docs/security/firewall-templates/nftables/cell-base.nft` | Default-deny base (table, chains, conntrack, logging) |
| `docs/security/firewall-templates/nftables/cell-mqtt.nft` | MQTT fragment (TLS-only cross-perimeter; 1883 cell-internal) |
| `docs/security/firewall-templates/nftables/cell-opcua.nft` | OPC-UA fragment (TCP 4840; discovery multicast blocked) |
| `docs/security/firewall-templates/nftables/cell-ros2.nft` | ROS2/DDS fragment (ephemeral UDP cell-internal; bridge/proxy only cross-perimeter) |
| `docs/security/firewall-templates/nftables/cell-compose.example.nft` | Single-file example (base + all protocols + `define` vars) |
| `docs/plans/ASP-372.md` | Plan (this ticket) |
| `tests/test_firewall_templates.py` | Hermetic checker — existence, text parse, DRAFT markers, no live `nft`/`ufw` |

## 2. Problem Statement

Manufacturing cell hosts today get firewall treatment ad hoc: per-host grants
decided at install time, not versioned, not protocol-aware, and with no
audit-coupled ruleset. When the industrial protocol drivers (MQTT, OPC-UA,
ROS2/DDS) land, there is no agreed default-deny cell-perimeter ruleset to ship
with the cell. F-008 of the ASP-298 refresh requires a draft, versioned,
protocol-aware cell firewall template set as the starting point for future cell
commissioning.

Attack surface (cell perimeter):

1. Cell PLC/RTU/robot nodes reachable from the plant VLAN with no default-deny.
2. Cleartext MQTT (1883) crossing the cell perimeter.
3. OPC-UA discovery multicast escaping the cell (endpoint enumeration).
4. ROS2/DDS ephemeral UDP range (49152-65535) leaking across the perimeter.

## 3. Design Decisions

| Decision | Rationale |
|----------|-----------|
| **nftables primary; UFW accepted as per-cell alternative** | nftables is the modern Linux firewall (Ubuntu 22.04+/Debian 11+). UFW application profiles remain an accepted alternative per cell but are not drafted yet (`README.md` notes this). |
| **Default-deny ingress, drop-forward, output accept** | Cells initiate outbound control/telemetry to the plant network; nothing unsolicited enters the cell. Aligns with IEC 62443-3-3 SR 5.1. |
| **TLS-only MQTT (8883) across perimeter; 1883 confined to cell** | Cleartext telemetry/control never leaves the cell boundary. |
| **OPC-UA discovery multicast blocked** | Prevents endpoint enumeration (`239.255.x.x` UDP 4840). Binary protocol TCP 4840 is the only OPC-UA path to the plant. |
| **ROS2 cross-perimeter only via explicit bridge/proxy** | DDS ephemeral UDP is cell-internal; cross-perimeter traffic must be a named, logged bridge flow. Default DDS multicast is confined to the cell subnet. |
| **Fragments + single-file composed example** | Reuse per cell; copy, substitute `define` vars, `nft -c -f` to check before any apply. |
| **Rate-limited drop logging + NEW-state acceptance logging** | ALCOA+ auditable reconstruction without log flooding. |
| **Systemd sandbox / DDS Security as additional layers** | Firewall is defence-in-depth; application-layer security (MQTT TLS, OPC-UA sign-and-encrypt, DDS Security) still required (IEC 62443-3-3 SR 5.3). |

## 4. Composition Strategy

Per cell, at commissioning time:

1. Start from `cell-compose.example.nft` (or `cell-base.nft` + fragments).
2. Substitute every `define $VAR` with the actual cell inventory IP/mask.
3. Remove protocol blocks the cell does not run (e.g. drop ROS2 for a
   non-robotic cell); document the removed blocks.
4. Confirm the non-standard ROS2 bridge port (1180 default) against the actual
   ROS2-over-TCP deployment; remove if unused.
5. Set `nf_conntrack_tcp_timeout_established` to 24h for long-lived OPC-UA
   sessions.
6. Syntax-check `nft -c -f <file>`; run the acceptance matrix (connectivity,
   negative, latency, audit-log inspection) before any Captain-approved apply.

## 5. QA / Verification

- `tests/test_firewall_templates.py`: each template file exists, is UTF-8 text,
  carries the DRAFT / do-not-apply marker, the composed example keeps balanced
  `{}` / `()` blocks, and the checker itself never shells out to `nft`/`ufw`.
- Full test suite still green (see `scripts/check-nightly.sh` pytest gate).

## 6. Gate / Human-in-the-loop

**DO NOT apply** any ruleset from these templates without the physical cell
gate. Application requires:

1. Physical cell gate commissioning (separate change order).
2. Protocol-driver deployment confirmation for the specific cell.
3. Regression testing against the cell's equipment inventory (§4 item 6).
4. Dual-human authorization (ADR-0009 / ASP-540 pattern) + Captain approval of
   a separate change order, with the ruleset diff, target host, rollback
   procedure, and maintenance window in the `propose_act` payload.
5. Outcome logged to `aspen.sentinel.audit.event` (ruleset hash, validation
   results, authorizing humans, rollback backup path).

## 7. Out of Scope

- ASP-370 (live SSH+UFW on `bt-asp-srv`) — separate ticket.
- Live `aa-enforce` — separate.
- Physical cell HITL / inspection — separate.
- Hardware-in-the-loop diode; classified domains (hardware diode deferred).

## 8. Related Documents

- `docs/SECURITY_THREAT_MODEL_v2.2.md` — F-008 / zone model (Z0-Z4)
- `docs/sor/ASPENGROVE_MASTER_SPEC_v4.0.md` — manufacturing cell topology
- `docs/solutions/asp-368-data-diode-recipe.md` — F-020 recipe (pattern source;
  also draft-only until dual-human gate)
- `docs/adr/ADR-0009-capability-based-gatekeepers.md` — dual-human authorization
- `docs/COMPOUND_ENGINEERING.md` — SDLC gates
- `docs/plans/ASP-372.md` — plan this ticket

---

*End of compound doc — DRAFT templates, not applied.*