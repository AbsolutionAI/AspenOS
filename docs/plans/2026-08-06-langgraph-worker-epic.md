# Epic: LangGraph execution plugin (AspenOS)

**Status:** Done (v0.2 worker + grove lab compose)  
**Linear:** [BEL-200](https://linear.app/bellahtech/issue/BEL-200/epic-langgraph-execution-plugin-aspenos-paperclip-remains-aspen-dev)  
**ADR:** docs/adr/ADR-0005-langgraph-execution-plugin.md  
**SoR:** docs/sor/ASPENGROVE_MASTER_SPEC_v4.0.md  
**Package:** https://github.com/AbsolutionAI/aspen-langgraph-worker  
**Paperclip:** ASP-66

## Decision
Paperclip = aspen-dev. LangGraph = AspenOS cognitive plugin only. `propose_act` only.

## Children
| ID | Title | Status |
|----|-------|--------|
| BEL-201 | ADR-0005 accepted | Done |
| BEL-202 | Scaffold aspen-langgraph-worker | Done |
| BEL-203 | Contracts subjects | Done |
| BEL-204 | alarm-triage spike | Done |
| BEL-205 | Optional langgraph extra | Done |
| BEL-206 | Job bus + doc_assist | Done |
| BEL-207 | NATS lab consumer E2E | Done (`make nats-e2e`) |
| BEL-208 | pgvector doc_assist | Done (optional DSN + memory cascade) |
| BEL-209 | Hermes/Paperclip invoke hook | Done (`python -m aspen_lgw.invoke`) |
| BEL-210 | aspen-grove compose note | Done (`compose/langgraph-lab.yml`) |

## Verify
```bash
cd aspen-langgraph-worker && make smoke && make nats-e2e
cd aspen-grove && make smoke && make up-langgraph
```
