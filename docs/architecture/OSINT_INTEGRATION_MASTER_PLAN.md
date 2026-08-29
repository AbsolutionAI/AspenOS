# OSINT Integration Master Plan
**Company:** Absolution Studios (ABS)  
**Paperclip Issues:** ABS-12 through ABS-16  
**Date:** 2026-08-04  
**Status:** 🚀 Phase 1 Complete — Repos forked/cloned, architecture designed

---

## Executive Summary

Building a **modular Command & Control platform** combining:
- **AspenOS**: Core agent mesh, memory layer, agent orchestration
- **WorldMonitor**: OSINT intelligence (maritime, aviation, cyber, geopolitics, climate, finance)
- **Flamingo-stack (fleetmdm)**: Distributed orchestration, MDM, osquery
- **cybersecurity-osint**: Curated OSINT tools & scripts
- **Local AI (Jarvis)**: Conversational interface for all systems

**Target:** Single pane of glass dashboard managing 100s of nodes (AI agents, IoT, satellites, servers, robotics, drones) with natural language Jarvis interface.

---

## Repository Inventory

| Repo | Location | Role | Status |
|------|----------|------|--------|
| **WorldMonitor** | `/home/tech/worldmonitor` | OSINT intelligence platform | ✅ Cloned (forked to AbsolutionAI) |
| **WorldMonitor MCP** | In WorldMonitor repo | MCP proxy server | ✅ Analyzed |
| **abs-worldmonitor-mcp** | `/home/tech/abs-worldmonitor-mcp` | ABS-specific MCP with memory layer | ✅ Scaffolded |
| **cybersecurity-osint** | `/home/tech/cybersecurity-osint` | OSINT tool curation + scripts | ✅ Cloned |
| **fleetmdm (flamingo-stack)** | `/home/tech/fleetmdm` | MDM/osquery + OpenFrame | ✅ Forked to AbsolutionAI |
| **abs-worldmonitor-mcp** | `/home/tech/abs-worldmonitor-mcp` | ABS MCP with memory integration | ✅ Scaffolded |

---

## Phase 1: Foundation ✅ COMPLETE

| Task | Status | Details |
|------|--------|---------|
| Fork WorldMonitor to AbsolutionAI | ✅ | `AbsolutionAI/worldmonitor` |
| Clone WorldMonitor locally | ✅ | `/home/tech/worldmonitor` |
| Fork fleetmdm to AbsolutionAI | ✅ | `AbsolutionAI/fleetmdm` |
| Clone fleetmdm locally | ✅ | `/home/tech/fleetmdm` |
| Clone cybersecurity-osint | ✅ | `/home/tech/cybersecurity-osint` |
| Scaffold abs-worldmonitor-mcp | ✅ | `/home/tech/abs-worldmonitor-mcp` |
| Architecture analysis doc | ✅ | `docs/architecture/WORLDMONITOR_INTEGRATION.md` |
| COMPANY_MAP.md updated | ✅ | OSINT mapped to ABS |
| ABS-11 Paperclip issue | ✅ | Done |
| Docker Compose stack | ✅ | `abs-worldmonitor-mcp/docker-compose.yml` |
| Database schema | ✅ | `abs-worldmonitor-mcp/init-db.sql` |
| ABS MCP server scaffold | ✅ | `abs-worldmonitor-mcp/src/` |
| Memory API server | ✅ | `abs-worldmonitor-mcp/src/memory-api.ts` |
| Memory client | ✅ | `abs-worldmonitor-mcp/src/memory-client.ts` |
| WorldMonitor client | ✅ | `abs-worldmonitor-mcp/src/worldmonitor-client.ts` |

---

## Phase 2: ABS MCP Server Implementation 🚧 IN PROGRESS

### ABS-12: abs-worldmonitor-mcp Implementation

| Subtask | Status | Owner | Notes |
|---------|--------|-------|-------|
| Implement `search_abs_osint` tool | 🔄 | Proxy | Uses WorldMonitor API + memory layer |
| Implement `get_abs_memory_context` tool | 🔄 | Proxy | Queries memory API |
| Implement `store_osint_fact` tool | 🔄 | Proxy | Promotes to memory layer |
| Implement `get_worldmonitor_tools` / `call_worldmonitor_tool` | 🔄 | Proxy | Proxies to upstream MCP |
| Implement `health_check` | 🔄 | Proxy | Checks memory API + WorldMonitor |
| Dockerfile.mcp | ⏳ | Proxy | Multi-stage build |
| Unit tests for all 6 tools | ⏳ | Proxy | Vitest |
| CI/CD pipeline | ⏳ | Proxy | GitHub Actions |

### ABS-13: cybersecurity-osint Integration

| Subtask | Status | Owner | Notes |
|---------|--------|-------|-------|
| Fork to AbsolutionAI/cybersecurity-osint | ⏳ | Proxy | `gh repo fork` |
| Analyze OSINT-scripts/OSINT-master | ⏳ | Proxy | Extract usable scripts |
| Create `cybersecurity-osint-ingestion.ts` | ⏳ | Proxy | New WorldMonitor service |
| CVE/NVD synchronization | ⏳ | Proxy | NVD API + CVE database |
| Threat actor profiling | ⏳ | Proxy | MITRE ATT&CK mapping |
| Malware family tracking | ⏳ | Proxy | Malware Bazaar, VirusTotal |
| ATT&CK technique mapping | ⏳ | Proxy | STIX/TAXII integration |
| Cyber domain dashboard | ⏳ | Romi | New WorldMonitor tab |
| MCP tools: `search_cyber_threats`, `get_threat_actor`, `get_malware` | ⏳ | Proxy | Exposed via ABS MCP |
| Memory layer fact promotion | ⏳ | Proxy | `store_osint_fact` for cyber intel |

### ABS-14: Local AI / Jarvis Interface

| Subtask | Status | Owner | Notes |
|---------|--------|-------|-------|
| Deploy Ollama with Qwen2.5/DeepSeek | ⏳ | Proxy | Local LLM for conversations |
| Build conversational agent | ⏳ | Proxy | Natural language → MCP calls |
| Natural language → MCP translation | ⏳ | Proxy | Intent classification + tool calling |
| Conversation context via memory layer | ⏳ | Proxy | `get_abs_memory_context` |
| Multi-agent delegation (Ergo/Proxy/Romi) | ⏳ | Ergo | Route to specialist agents |
| Web UI (localhost:3006) | ⏳ | Romi | Preact/TypeScript |
| CLI: `abs-jarvis "query"` | ⏳ | Proxy | Simple CLI wrapper |
| Tauri desktop app | ⏳ | Proxy | Cross-platform |
| Voice interface (Whisper + TTS) | ⏳ | Proxy | Optional stretch |

### ABS-15: Flamingo-stack Integration

| Subtask | Status | Owner | Notes |
|---------|--------|-------|-------|
| Fork flamingo-stack/fleetmdm | ✅ | Proxy | Already forked to AbsolutionAI |
| Analyze OpenFrame architecture | 🔄 | Proxy | Multi-tenant MDM, per-tenant Redis |
| Integrate with AspenOS agent mesh | ⏳ | Proxy | Replace/augment NATS |
| Distributed agent registry | ⏳ | Proxy | Flamingo actor model |
| Consensus for agent leadership | ⏳ | Proxy | Raft/etcd |
| Distributed task scheduling | ⏳ | Proxy | BullMQ + Flamingo |
| Horizontal scaling (100s of nodes) | ⏳ | Proxy | K8s/Docker Swarm |
| IoT device management | ⏳ | Proxy | osquery + fleetmdm |
| Satellite ground station coordination | ⏳ | Proxy | Custom integration |
| Drone swarm orchestration | ⏳ | Proxy | MAVLink/ROS2 |
| Robotics fleet management | ⏳ | Proxy | ROS2 + fleetmdm |

### ABS-16: Unified Command & Control Platform

| Subtask | Status | Owner | Notes |
|---------|--------|-------|-------|
| Unified repo: AbsolutionAI/aspen-command-control | ⏳ | Ergo | Monorepo |
| Dashboard integration (WorldMonitor + AspenOS + Flamingo) | ⏳ | Romi | Single pane of glass |
| Jarvis conversational interface | 🔄 | Proxy | ABS-14 delivery |
| 10+ node cluster demo | ⏳ | Proxy | Mixed node types |
| 3 AI agent nodes | ⏳ | Proxy | Ergo/Proxy/Romi |
| 2 IoT sensor nodes | ⏳ | Proxy | Fleetmdm + osquery |
| 1 simulated satellite ground station | ⏳ | Proxy | Mock + custom |
| 2 robotics nodes | ⏳ | Proxy | ROS2 + fleetmdm |
| 2 drone nodes | ⏳ | Proxy | MAVLink + swarm |
| Jarvis natural language commands | 🔄 | Proxy | "Show nodes with CPU>80%" |
| Distributed agent mesh self-healing | ⏳ | Proxy | Flamingo consensus |
| OSINT → memory → agent decisions | 🔄 | Proxy | End-to-end flow |
| Documentation: ARCHITECTURE.md, DEPLOYMENT.md, API.md | ⏳ | Ergo | Complete docs |

---

## Technical Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ASPEN COMMAND & CONTROL PLATFORM                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   JARVIS     │  │  WORLDMONITOR│  │  ASPENOS     │  │  FLAMINGO    │    │
│  │  (Local AI)  │  │  (OSINT)     │  │  (Agent Mesh)│  │  (Orchest.)  │    │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘    │
│         │                 │                 │                 │            │
│         ▼                 ▼                 ▼                 ▼            │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    ABS MEMORY LAYER (services/memory.py)             │   │
│  │  SQLite + LanceDB + FAISS  │  Fact Promotion  │  Context Injection  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│         │                 │                 │                 │            │
│         ▼                 ▼                 ▼                 ▼            │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │              ABS WORLDMONITOR MCP (abs-worldmonitor-mcp)             │   │
│  │  search_abs_osint  │  get_abs_memory_context  │  store_osint_fact   │   │
│  │  get_wm_tools      │  call_wm_tool           │  health_check       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│         │                 │                 │                 │            │
│         ▼                 ▼                 ▼                 ▼            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │   Ergo       │  │   Proxy      │  │   Romi       │  │  OpenCode/   │   │
│  │  (CEO)       │  │  (Builder)   │  │  (Creative)  │  │  OpenDesign  │   │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘   │
│         │                 │                 │                 │            │
│         ▼                 ▼                 ▼                 ▼            │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │              FLAMINGO ORCHESTRATION (fleetmdm / OpenFrame)           │   │
│  │  Distributed Actor Model  │  Consensus (Raft)  │  Message Bus       │   │
│  │  Agent Registry             │  Leadership Elect. │  Task Scheduler   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│         │                 │                 │                 │            │
│         ▼                 ▼                 ▼                 ▼            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │  AI Agents   │  │   IoT/Edge   │  │  Satellites  │  │  Robotics/   │   │
│  │  (Distributed)│  │  (osquery)   │  │  (Ground St.)│  │  Drones      │   │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow: OSINT → Memory → Agent Decisions

```
WorldMonitor Sources          Fact Extraction           Memory Layer              Agent Access
┌─────────────────┐          ┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│ RSS/Telegram    │  ──►     │ LLM Summarize   │  ──► │ SQLite + FTS5   │  ◄── │ Ergo (Strategic)│
│ AIS/ADSB        │          │ Entity Extract  │      │ LanceDB Vector  │      │ Proxy (Builder) │
│ APIs (CVE,NVD)  │          │ Confidence Score│      │ Facts API       │      │ Romi (Creative) │
│ Climate/Finance │          │ Tags + Refs     │      │ MCP + REST      │      │ OpenCode/Design │
└─────────────────┘          └─────────────────┘      └─────────────────┘      └─────────────────┘
```

---

## Deployment Stack (Docker Compose)

| Service | Image | Port | Resources |
|---------|-------|------|-----------|
| PostgreSQL + pgvector | `pgvector/pgvector:pg16` | 5432 | 2CPU/4GB |
| Redis | `redis:7-alpine` | 6379 | 1CPU/1GB |
| WorldMonitor Ingestion | Custom (Dockerfile.ingestion) | - | 2CPU/2GB |
| WorldMonitor API | Custom (Dockerfile.api) | 3001 | 1CPU/1GB |
| WorldMonitor MCP Proxy | Custom (Dockerfile.mcp-proxy) | 3002 | 0.5CPU/512MB |
| ABS WM MCP | Custom (Dockerfile.mcp) | 3002 | 1CPU/1GB |
| ABS Memory API | Custom (Dockerfile.memory-api) | 8080 | 1CPU/1GB |
| BullMQ Dashboard | `ghcr.io/bull-board/bull-board` | 3004 | 0.5CPU/512MB |
| Prometheus | `prom/prometheus` | 9090 | 1CPU/2GB |
| Grafana | `grafana/grafana` | 3005 | 0.5CPU/1GB |

---

## Next Immediate Actions (Priority Order)

### 1. Complete ABS-12 (abs-worldmonitor-mcp) — **This Week**
- [ ] Implement all 6 MCP tools
- [ ] Add Dockerfile.mcp
- [ ] Write unit tests
- [ ] Test memory layer integration
- [ ] Test WorldMonitor MCP proxy

### 2. Complete ABS-13 (cybersecurity-osint) — **Next Week**
- [ ] Fork to AbsolutionAI
- [ ] Build ingestion service
- [ ] Add cyber domain to WorldMonitor
- [ ] Expose MCP tools

### 3. Complete ABS-14 (Jarvis) — **Week 3**
- [ ] Deploy Ollama + Qwen2.5
- [ ] Build conversational agent
- [ ] Build Web UI + CLI

### 4. Complete ABS-15 (Flamingo) — **Week 4**
- [ ] Analyze OpenFrame architecture
- [ ] Integrate with AspenOS mesh
- [ ] Deploy 10-node test cluster

### 5. Complete ABS-16 (Unified Platform) — **Week 5-6**
- [ ] Create unified monorepo
- [ ] Integrate all dashboards
- [ ] 10+ node demo
- [ ] Documentation

---

## Resource Requirements

| Resource | Current | Target |
|----------|---------|--------|
| **CPU** | 8 cores | 32+ cores (for 10+ node cluster) |
| **RAM** | 32 GB | 64+ GB |
| **Storage** | 500 GB | 2+ TB (PostgreSQL + vector + raw data) |
| **GPU** | Quadro P2000 (5GB) | RTX 4090 / A100 (for local LLM) |

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| WorldMonitor upstream breaking changes | Medium | Medium | Pin fork, selective cherry-pick |
| LLM costs (Jarvis) | High | Medium | DeepSeek V4-Flash only; batch processing |
| AIS/ADSB data volume | High | High | Bbox filtering, sampling, retention |
| Flamingo OpenFrame complexity | High | High | Incremental integration, start with fleetmdm |
| Convex dependency in WorldMonitor | Medium | High | Replace with PostgreSQL + pgvector |
| MCP protocol changes | Low | Medium | Version pinning, adapter pattern |

---

## Success Criteria (ABS-16 Definition of Done)

- [ ] **Unified repo**: `AbsolutionAI/aspen-command-control` with all submodules
- [ ] **Dashboard**: Single pane of glass (WorldMonitor + AspenOS + Flamingo)
- [ ] **Jarvis**: Conversational interface answering OSINT + orchestration queries
- [ ] **10+ node cluster**: 3 AI agents, 2 IoT, 1 sat ground station, 2 robotics, 2 drones
- [ ] **Natural language commands work**:
  - "Show me all nodes with CPU > 80%"
  - "Task drone swarm to survey sector 7"
  - "Analyze Russian naval activity in Baltic"
  - "Deploy security patch to all edge nodes"
- [ ] **Self-healing**: Agent mesh recovers from node failure
- [ ] **OSINT → Agent decisions**: Intelligence flows to agent actions
- [ ] **Documentation**: ARCHITECTURE.md, DEPLOYMENT.md, API.md, JARVIS.md

---

*Last updated: 2026-08-04*  
*Owner: Ergo (CEO) / Proxy (Execution)*  
*Next review: 2026-08-11*