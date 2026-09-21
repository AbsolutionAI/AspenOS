# Cell Firewall Rule Templates — DRAFT

> **DRAFT — DO NOT APPLY.** These templates are reference material for ASP-372
> (H-008, F-008). Applying any of them to a host (including `bt-asp-srv`)
> requires physical cell commissioning, protocol-driver confirmation,
> regression testing, and Captain approval of a separate change order.
> Nothing here is enforced by CI against live hosts.

**Parent:** ASP-298 / ASP-372
**Status:** `DRAFT` (git only)
**Snippets:** nftables (primary). UFW application profiles are an accepted
alternative per cell but are not yet drafted here.

## Index

| File | Purpose |
|------|---------|
| `nftables/cell-base.nft` | Complete default-deny cell base (table, chains, conntrack, logging, catch-all) |
| `nftables/cell-mqtt.nft` | MQTT fragment (TLS-only across perimeter; 1883 confined to cell) |
| `nftables/cell-opcua.nft` | OPC-UA fragment (TCP 4840; discovery multicast blocked) |
| `nftables/cell-ros2.nft` | ROS2/DDS fragment (UDP 49152-65535 cell-internal; bridge/proxy only cross-perimeter) |
| `nftables/cell-compose.example.nft` | Single-file composed example (base + all protocols + `define` variables) |

## Network model

```
 PLANT/OT VLAN (ISA-95 L3)
      │
      ▼  cell_firewall (inet, default-deny ingress)
      │
  Cell control (PLC/RTU) ── MQTT/OPC-UA gateway ── ROS2 robot (DDS)
```

- Default-deny ingress, drop-forward, output acceptable for cells initiating
  outbound control/telemetry to the plant network.
- Every drop and every new cross-perimeter connection is logged (rate-limited)
  for ALCOA+ audit reconstruction.
- Placeholders (`<VAR>` in fragments, `define $VAR` in the composed example)
  are substituted per cell at commissioning time.

## Composition

Prefer the composed example during any future commissioning: copy
`nftables/cell-compose.example.nft`, substitute the `define` variables for the
cell inventory, `nft -c -f <file>` to syntax-check, then run the cell
acceptance matrix (connectivity, negative, latency, audit-log) before any
Captain-approved apply.

## Compliance cross-reference

| Requirement | Support |
|-------------|---------|
| IEC 62443-3-3 SR 5.1 | Zone/perimeter default-deny segmentation |
| IEC 62443-3-3 SR 5.3 | Defence-in-depth (firewall + TLS/DDS-security) |
| 21 CFR Part 11.10(e) | Audit log of permitted/blocked flows |
| ALCOA+ | Original kernel netfilter logs, ntp-synced |
| EU GMP Annex 11 | Logical access controls at network layer |

## Out of scope

ASP-370 (live SSH+UFW on `bt-asp-srv`), live `aa-enforce`, physical cell HITL.