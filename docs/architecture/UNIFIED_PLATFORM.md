# UNIFIED_PLATFORM.md — Modular Command & Control Platform (ABS-16)

**Linear:** BEL-DEFER — Unified Command & Control Platform  
**Paperclip:** ABS-16 (Unified Command & Control Platform)  
**Company:** Absolution Studios (ABS)  
**Status:** 🔄 In Progress  
**Date:** 2026-08-05  

---

## Vision

Build a **modular Command & Control platform** combining:
- **AspenOS** — Agent orchestration, memory layer, CE gates
- **WorldMonitor** — Global OSINT intelligence (geopolitics, maritime, aviation, cyber, climate, finance)
- **Flamingo/OpenFrame** — Distributed device orchestration (IoT, servers, drones, robots, satellites)
- **Sherlock** — Username enumeration across 300+ social networks
- **cybersecurity-osint** — Certificate Transparency, domain liveness, Twitter OSINT

Into a **single pane of glass** that manages **hundreds of nodes** — AI agents, IoT devices, satellites, servers, robotics, and drones — with conversational AI interface.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     UNIFIED COMMAND & CONTROL                   │
├─────────────────────────────────────────────────────────────────┤
│  CONVERSATIONAL INTERFACE (Jarvis-style)                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   Voice     │  │   Chat      │  │   Dashboard │             │
│  │   Input     │  │   Interface │  │   (React)   │             │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘             │
│         │                │                │                      │
│         └────────────────┼────────────────┘                      │
│                          ▼                                       │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              ORCHESTRATION LAYER (AspenOS)               │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │    │
│  │  │   Ergo CEO  │  │   Proxy     │  │   Romi      │       │    │
│  │  │  (Strategy) │  │  (Execution)│  │  (Creative) │       │    │
│  │  └─────────────┘  └─────────────┘  └─────────────┘       │    │
│  │  ┌─────────────┐  ┌─────────────┐                          │    │
│  │  │  OpenCode   │  │ OpenDesign  │                          │    │
│  │  │  (Coding)   │  │  (Design)   │                          │    │
│  │  └─────────────┘  └─────────────┘                          │    │
│  └─────────────────────────────────────────────────────────┘    │
│                          │                                       │
│         ┌────────────────┼────────────────┐                     │
│         ▼                ▼                ▼                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │  MEMORY     │  │  OSINT      │  │  DEVICE     │             │
│  │  LAYER      │  │  ENGINE     │  │  FLEET      │             │
│  │  (LanceDB + │  │  (WorldMon  │  │  (Flamingo/ │             │
│  │   SQLite)   │  │   + Sherlock│  │   OpenFrame)│             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Integration Matrix

| Component | Role | Integration Points |
|-----------|------|-------------------|
| **AspenOS (Ergo/Proxy/Romi)** | Orchestration brain | Memory layer, CE gates, agent mesh |
| **Memory Layer (ABS-10)** | Unified knowledge store | LanceDB vector + SQLite FTS5, all agents |
| **WorldMonitor** | Global intelligence | MCP tools: `search_abs_osint`, `store_osint_fact` |
| **Sherlock (ABS-17)** | Username enumeration | MCP tools: `enumerate_usernames`, `search_by_username` |
| **cybersecurity-osint (ABS-13)** | Infrastructure OSINT | MCP tools: `ct_abuse_enumerate`, `check_domains_live`, `twitter_osint` |
| **Flamingo/OpenFrame (ABS-15)** | Device fleet management | MCP tools: `flamingo_*`, cluster commands |
| **Local LLM (ABS-14)** | Conversational interface | Future: Jarvis voice/chat |

---

## MCP Tool Registry (Total: 20+ tools)

### Intelligence & OSINT
| Tool | Source | Description |
|------|--------|-------------|
| `search_abs_osint` | WorldMonitor | Search intelligence across domains + memory |
| `get_abs_memory_context` | Memory Layer | Agent context retrieval |
| `store_osint_fact` | Memory Layer | Promote intelligence to unified store |
| `enumerate_usernames` | Sherlock | Batch username enumeration (300+ sites) |
| `enumerate_username` | Sherlock | Single username enumeration |
| `get_username_profile` | Memory Layer | Username profile from history |
| `search_by_username` | Memory Layer | Search intelligence by username |
| `ct_abuse_enumerate` | cybersecurity-osint | CT log subdomain enumeration |
| `check_domains_live` | cybersecurity-osint | Domain liveness (HTTP 200) |
| `twitter_osint` | cybersecurity-osint | Twitter birthday/device/followers |

### Device & Fleet Management
| Tool | Source | Description |
|------|--------|-------------|
| `flamingo_list_devices` | Flamingo | List all registered devices |
| `flamingo_get_device` | Flamingo | Get device details |
| `flamingo_register_device` | Flamingo | Register IoT/server/drone/robot/satellite |
| `flamingo_list_clusters` | Flamingo | List device clusters |
| `flamingo_create_cluster` | Flamingo | Create device cluster |
| `flamingo_execute_command` | Flamingo | Execute command on device/cluster |
| `flamingo_execute_on_cluster` | Flamingo | Broadcast command to cluster |
| `flamingo_execute_on_all` | Flamingo | Broadcast to all devices |
| `flamingo_get_status` | Flamingo | System overview |

---

## Deployment Architecture

### Docker Compose Stack
```yaml
services:
  # Core Infrastructure
  postgres:          # PostgreSQL + pgvector (structured + vector)
  redis:             # Caching, pub/sub
  lancedb:           # Vector embeddings (LanceDB)
  
  # Intelligence
  worldmonitor:      # WorldMonitor API (port 3001)
  worldmonitor_mcp:  # WorldMonitor MCP (port 3002)
  sherlock_api:      # Sherlock wrapper API
  
  # OSINT
  ct_abuse_service:  # Certificate Transparency
  check_live_service: # Domain liveness
  twitter_osint_service: # Twitter analysis
  
  # Device Fleet
  flamingo_api:      # Flamingo/OpenFrame API (port 8081)
  flamingo_mcp:      # Flamingo MCP
  
  # Orchestration
  abs_mcp:           # ABS WorldMonitor MCP (stdio)
  memory_api:        # Memory HTTP API (port 8080)
  aspen_agents:      # Ergo, Proxy, Romi, OpenCode, OpenDesign
  
  # Monitoring
  prometheus:        # Metrics
  grafana:           # Dashboards
```

### Network Topology
```
Internet
    │
    ▼
┌──────────────────────────────────────┐
│         Load Balancer (nginx)        │
└──────────────┬───────────────────────┘
               │
    ┌──────────┼──────────┐
    ▼          ▼          ▼
┌────────┐ ┌────────┐ ┌────────┐
│ World- │ │  OSINT │ │ Fleet  │
│ Monitor│ │ Services│ │ Mgmt  │
└────┬───┘ └────┬───┘ └────┬───┘
     │          │          │
     └──────────┼──────────┘
                ▼
         ┌─────────────┐
         │  ABS MCP    │◄── Agents (Ergo, Proxy, Romi, etc.)
         │  (stdio)    │
         └──────┬──────┘
                │
         ┌──────┴──────┐
         ▼             ▼
    ┌─────────┐  ┌─────────┐
    │ Memory  │  │  Local  │
    │  API    │  │   LLM   │
    │ :8080   │  │ (Ollama)│
    └─────────┘  └─────────┘
```

---

## Implementation Phases

### Phase 1: Core Integration (Week 1) ✅
- [x] Memory Layer (ABS-10) — LanceDB + SQLite FTS5
- [x] abs-worldmonitor-mcp (ABS-12) — 10 base tools
- [x] Sherlock Integration (ABS-17) — 4 tools
- [x] cybersecurity-osint (ABS-13) — 3 tools
- [x] Flamingo Service (ABS-15) — 9 tools
- [x] MCP Server compilation — 20+ tools total

### Phase 2: Service Hardening (Week 2) 🔄
- [ ] Docker Compose full stack deployment
- [ ] PostgreSQL + pgvector schema migration
- [ ] LanceDB vector index optimization
- [ ] Health checks + monitoring (Prometheus/Grafana)
- [ ] API rate limiting & authentication
- [ ] Integration tests for all 20+ MCP tools

### Phase 3: Unified Platform (Week 3) 📋
- [ ] React Dashboard (single pane of glass)
- [ ] WebSocket real-time updates
- [ ] Conversational interface design
- [ ] Local LLM integration (Ollama + Nemotron/DeepSeek)
- [ ] Voice interface (Whisper + TTS)

### Phase 4: Production Hardening (Week 4) 📋
- [ ] Multi-node cluster deployment (10+ nodes)
- [ ] Satellite link simulation
- [ ] Drone/robot hardware integration
- [ ] Security audit (NIST CSF)
- [ ] Documentation & runbooks

---

## Conversational Interface Design (Jarvis)

### Intent Recognition
```
User: "Show me all live subdomains for github.com"
→ Intent: ct_abuse_enumerate
→ Parameters: {target_domain: "github.com", check_live: true}

User: "Deploy the new config to the drone cluster"
→ Intent: flamingo_execute_on_cluster
→ Parameters: {cluster_id: "drone_cluster", command: "deploy", params: {...}}

User: "What's the status of all IoT devices?"
→ Intent: flamingo_get_status
```

### Response Patterns
```
Jarvis: "Found 47 live subdomains for github.com. 
         Top 5: api.github.com, raw.githubusercontent.com, 
         gist.github.com, pages.github.com, codespaces.github.com.
         Stored in memory layer for future reference."
```

---

## Node Types Supported

| Node Type | Examples | Management |
|-----------|----------|------------|
| **AI Agents** | Ergo, Proxy, Romi, OpenCode, OpenDesign | AspenOS orchestration |
| **Servers** | Web, DB, API, GPU workers | Flamingo + SSH/Ansible |
| **IoT Sensors** | Temperature, motion, cameras | Flamingo MQTT/CoAP |
| **Drones** | DJI, custom, swarm | Flamingo + MAVLink |
| **Robots** | ROS2, Boston Dynamics Spot | Flamingo + ROS bridge |
| **Satellites** | CubeSats, ground stations | Flamingo + CCSDS |
| **Edge Devices** | Jetson, RPi, ESP32 | Flamingo lightweight agent |

---

## Security & Compliance

- **Zero Trust** — mTLS between all services
- **RBAC** — Role-based access (admin, operator, viewer)
- **Audit Logging** — All commands logged to memory layer
- **NIST CSF** — Aligned with BEL-114 security baseline
- **Secrets Management** — Vault integration (future)

---

## Success Metrics

| Metric | Target |
|--------|--------|
| MCP Tools Available | 20+ |
| Node Types Supported | 7+ |
| Concurrent Nodes Managed | 100+ |
| Latency (command → execution) | < 500ms |
| Memory Layer Query Latency | < 50ms |
| Uptime | 99.9% |
| Test Coverage | > 80% |

---

## Next Steps

1. **Complete Docker Compose** — Full stack deployment
2. **React Dashboard** — Single pane of glass UI
3. **Local LLM** — Ollama + Nemotron for Jarvis
4. **Hardware Integration** — Drone/robot test nodes
5. **Documentation** — API specs, runbooks, architecture diagrams

---

*Last Updated: 2026-08-05*  
*Status: Phase 1 Complete, Phase 2 In Progress*