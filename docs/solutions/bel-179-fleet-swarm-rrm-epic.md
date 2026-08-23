# BEL-179 Epic compound — Fleet + Swarm + Edge RRM (Phases A–C)

## Status
Phases **A–C Done** (sim). Phase **D** physical cell (BEL-192) remains backlog until captain opens hardware path.

## Deliverables
| Item | Location |
|------|----------|
| ADR-0002 Swarm/RRM boundaries | `docs/adr/ADR-0002-swarm-rrm-boundaries.md` |
| ADR-0003 Fleet/edge/safety subjects | `docs/adr/ADR-0003-fleet-edge-safety-contracts.md` |
| ADR-0004 Light core plugins | `docs/adr/ADR-0004-light-core-plugins.md` |
| FLEET.md canonical subjects | `docs/FLEET.md` |
| aspen-swarm-manager | https://github.com/AbsolutionAI/aspen-swarm-manager |
| aspen-edge-rrm | https://github.com/AbsolutionAI/aspen-edge-rrm |
| aspen-contracts | https://github.com/AbsolutionAI/aspen-contracts |

## Child map
- A1–A5: BEL-180…184 Done  
- B1–B3: BEL-185…187 Done  
- C1–C4: BEL-188…191 Done  
- D1: BEL-192 Backlog (range plant only)

## Smoke (lab)
```bash
cd aspen-swarm-manager && make smoke
cd aspen-edge-rrm && make smoke
```

## Safety
propose_act only · human arm gate · estop latch · sim-only freeze until dual human auth for real motion.
