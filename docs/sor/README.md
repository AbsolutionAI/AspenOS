# AspenGrove — Sources of Truth

**Authority:** Documents in this directory override older plans/ADRs on conflict unless a newer dated SoR is filed.

| Doc | Role | Path |
|-----|------|------|
| **Master Spec v4.0** | Product + architecture SoR (“Three Organs”) | `ASPENGROVE_MASTER_SPEC_v4.0.md` · alias `MASTER_SPEC.md` |
| **Matrix + Tailscale + Hermes install** | Operator remote-access / gateway install SoR | `ASPENGROVE_MATRIX_TAILSCALE_HERMES_INSTALL.md` · alias `MATRIX_TAILSCALE_HERMES_INSTALL.md` · also `docs/ops/MATRIX_TAILSCALE_HERMES_INSTALL.md` |

## Locked product triad (v4.0)
1. **AspenOS** — agentic OS / control plane  
2. **Aspen Sentinel** — HITL C2 / OSINT-aware ops workspace  
3. **aspen-dev** — engineering backend (Paperclip cos + Hermes personas SoR)

## Related living maps (subordinate)
- `docs/PACKAGE_MAP.md` — GitHub package mesh  
- `docs/adr/` — decision records (must align upward to Master Spec)  
- `docs/FLEET.md` — fleet bus (implement under Master Spec safety rules)

## Captains note
Ingested 2026-08-06 from captain-supplied v4.0 + Matrix/TS/Hermes install guides.

## Execution plugin decision
- **ADR-0005:** LangGraph worker for AspenOS cognitive graphs; Paperclip remains aspen-dev SoR.

## Product sources (agent universal memory)
| Product | Path |
|---------|------|
| **epos-human** (Epichuman Chrome) | `products/epos-human/` |
| **pcake stack** (credential/intent gateway; not Aspen Sentinel) | `products/pcake-stack/` |
| Combined analysis | `products/ANALYSIS_epos_pcake.md` |
