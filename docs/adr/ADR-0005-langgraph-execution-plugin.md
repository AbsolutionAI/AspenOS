# ADR-0005: LangGraph as AspenOS execution plugin (Paperclip stays aspen-dev)

## Status
Accepted — 2026-08-06  
**SoR parent:** `docs/sor/ASPENGROVE_MASTER_SPEC_v4.0.md`  
**Linear:** BEL-193+ (LangGraph worker epic)

## Context
Master Spec v4.0 locks **Paperclip + Hermes** as the org orchestration layer owned by **aspen-dev** (companies, personas, budgets, CE). Legacy AspenOS agent loops need stronger in-process tool/RAG graphs without introducing a second org scheduler.

## Decision

### Split of responsibility
| Concern | System of record |
|---------|------------------|
| Companies, roles, budgets, issue mesh | **Paperclip** (aspen-dev) |
| Chat personas / Matrix gateway | **Hermes** |
| Fleet missions / membership / arm gates | **aspen-swarm-manager** |
| Edge lifecycle / estop / propose mediation | **aspen-edge-rrm** |
| In-process cognitive graphs (tools, RAG, multi-step reason) | **LangGraph worker plugin** |

### LangGraph worker rules
1. **Library, not company board.** No LangGraph “org chart” replacing Paperclip agents.
2. **Bus-native.** Inputs/outputs use aspen-contracts envelopes on NATS (or in-process bus in lab).
3. **Safety:** On safety-adjacent subjects, emit **only** `propose_act` (or equivalent proposal events). No direct actuator/driver calls.
4. **Dual human authorization** still required before any real `act` (Master Spec hard rule). Auto-RED quarantine may apply to known-bad proposals.
5. **Sim default:** `ASPEN_SIM=1` for CI; hardware paths gated.
6. **Optional dependency:** Core AspenOS runs without LangGraph installed; worker is an adapter package.

### Non-goals
- Replacing Paperclip for aspen-dev or Gumroad/X mesh  
- LangChain agents scheduling plant missions in parallel with swarm-manager  
- On-device large LLM as default RRM brain  

### Package
- **`aspen-langgraph-worker`** (Apache-2.0 runtime lane)  
- Consumed by AspenOS / edge lab compose profiles; **not** required on thin production edges until explicitly installed.

## Consequences
- aspen-dev remains Paperclip/Hermes SoR  
- AspenOS gains a modern graph runtime for cognitive steps  
- ADR-0002/0004 remain valid; this ADR adds an execution plugin class under “plugins”  
- Eval/tracing (e.g. LangSmith) is optional and off by default under fiscal freeze  

## Alternatives rejected
- Full migration of AspenOS orchestration to LangChain/CrewAI/AutoGen  
- Embedding LangGraph inside Paperclip process adapters as the only path  
- Dual mission schedulers (Paperclip + LangGraph both assigning fleet work)  
