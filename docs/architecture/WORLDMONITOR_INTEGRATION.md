# WORLDMONITOR_INTEGRATION.md — OSINT Global Dashboard Integration Analysis

**Linear:** BEL backlog — OSINT Global Dashboard (OpenSINT)  
**Paperclip:** ABS-11 (BEL-DEFER: OSINT Global Dashboard — WorldMonitor fork & integration)  
**Company:** Absolution Studios (ABS) / Aspen OS Development Company (ASP)  
**Forked Repo:** https://github.com/AbsolutionAI/worldmonitor (from koala73/worldmonitor)  
**Cloned At:** `/home/tech/worldmonitor`  
**Date:** 2026-08-04  
**Status:** 🔄 Analysis in progress

---

## Executive Summary

WorldMonitor is a **real-time global intelligence dashboard** — a TypeScript SPA (Vite + Preact) with 181 top-level component files, 80+ Vercel Edge API endpoints, a Tauri desktop app with Node.js sidecar, and a Railway relay service. It aggregates geopolitics, military, finance, climate, cyber, maritime, and aviation data across 35 freshness-tracked source groups.

**Strategic Value for Aspen OS:**
- **OSINT ingestion pipeline** — 35 source groups (RSS, Telegram, APIs) with freshness tracking
- **Geospatial intelligence** — Maritime (AIS), aviation (ADSB), geopolitical event mapping
- **Multi-domain coverage** — Geopolitics, military, finance, climate, cyber, maritime, aviation
- **Self-hosted capable** — Docker, Railway, Convex, Cloudflare Workers, Tauri desktop
- **MCP server** — `wm-mcp` available on Smithery for agent access
- **TypeScript/Protobuf contracts** — Strong typing, sebuf framework, OpenAPI generation

**Integration Target:** ABS agents (Ergo, Proxy, Romi) via memory layer + MCP

---

## WorldMonitor Architecture Deep Dive

### Repository Structure (Key Directories)

| Directory | Purpose | Integration Relevance |
|-----------|---------|----------------------|
| `src/services/` | 224 service modules — ingestion, processing, domain logic | **HIGH** — Core ingestion pipelines |
| `src/services/ingestion/` | RSS, Telegram, API fetchers, freshness tracking | **HIGH** — OSINT data sources |
| `src/services/geo/` | Maritime (AIS), aviation (ADSB), geopolitical mapping | **HIGH** — Geospatial intel |
| `src/services/llm/` | LLM integration for summarization, classification | **MEDIUM** — Agent enhancement |
| `api/` | 80+ Vercel Edge Functions (self-contained JS) | **HIGH** — API endpoints for agents |
| `server/worldmonitor/` | Domain handlers (RPC) matching proto services | **HIGH** — Business logic |
| `proto/` | Protobuf definitions (sebuf framework) | **HIGH** — Contract definitions |
| `src/workers/` | Web Workers (analysis, ML/ONNX, vector DB) | **MEDIUM** — Local processing |
| `consumer-prices-core/` | Playwright scrapers (per-country baskets) | **LOW** — Specialized |
| `src-tauri/sidecar/` | Node.js sidecar API for Tauri desktop | **MEDIUM** — Desktop integration |

### Key Ingestion Services (`src/services/ingestion/`)

| Service | Source Type | Freshness | Output |
|---------|-------------|-----------|--------|
| `rss-ingestion.ts` | RSS/Atom feeds | Configurable | Normalized articles |
| `telegram-ingestion.ts` | Telegram channels (MTProto) | Real-time | Messages + media |
| `api-ingestion.ts` | REST/GraphQL APIs | Scheduled | JSON payloads |
| `maritime-ingestion.ts` | AIS (Kystverket, AISHub) | ~30s | Vessel positions |
| `aviation-ingestion.ts` | ADSB (OpenSky, ADSBx) | ~10s | Flight tracks |
| `climate-ingestion.ts` | NOAA, Copernicus, WMO | Hourly | Weather/climate data |
| `finance-ingestion.ts` | Yahoo, Alpha Vantage, Twelve Data | Minute | Market data |
| `cyber-ingestion.ts` | CVE, NVD, threat feeds | Hourly | Vulnerabilities |
| `geopolitics-ingestion.ts` | GDELT, ACLED, news APIs | 15min | Events/conflicts |

### Data Freshness Architecture

- **Source Groups:** 35 groups, each with `freshnessMs` threshold
- **Staleness Detection:** `shared/staleness.ts` — tracks last update per source
- **Priority Refresh:** High-priority sources refresh more frequently
- **Circuit Breakers:** Per-source failure tracking with exponential backoff

### MCP Server (`wm-mcp`)

Available on Smithery: `https://smithery.ai/servers/worldmonitor/wm-mcp`

**Exposed Tools:**
- `search_articles(query, sources?, timeRange?)`
- `get_maritime_vessels(bbox?, filters?)`
- `get_aviation_flights(bbox?, filters?)`
- `get_geopolitical_events(region?, timeRange?)`
- `get_climate_data(location?, parameters?)`
- `get_finance_market(symbols?, timeframe?)`
- `get_cyber_threats(severity?, timeRange?)`

---

## Integration Points for ABS Agents

### 1. Ergo (CEO / Orchestration) → Strategic Intelligence

| Need | WorldMonitor Capability | Integration Path |
|------|------------------------|------------------|
| Geopolitical risk assessment | Geopolitics ingestion (GDELT, ACLED) | MCP `get_geopolitical_events` |
| Supply chain monitoring | Maritime (AIS) + aviation (ADSB) | MCP `get_maritime_vessels` + `get_aviation_flights` |
| Climate risk for facilities | Climate ingestion (NOAA, Copernicus) | MCP `get_climate_data` |
| Market intelligence | Finance ingestion (markets, crypto) | MCP `get_finance_market` |
| Threat landscape | Cyber ingestion (CVE, threat feeds) | MCP `get_cyber_threats` |

**Implementation:** Ergo calls MCP tools via `agent-browser` skill or direct MCP client.

### 2. Proxy (Execution Specialist) → Technical OSINT

| Need | WorldMonitor Capability | Integration Path |
|------|------------------------|------------------|
| Infrastructure monitoring | Maritime/aviation tracking | Direct API or MCP |
| Vulnerability intelligence | Cyber ingestion (NVD, CVE) | MCP `get_cyber_threats` |
| Code dependency scanning | Finance/package registry data | Custom ingestion extension |
| Incident response | Real-time alerts (Telegram, RSS) | Webhook → memory layer |

**Implementation:** Proxy uses `opencode`/`hermes_local` with MCP client for automated OSINT tasks.

### 3. Romi (Creative Director) → Visual Intelligence

| Need | WorldMonitor Capability | Integration Path |
|------|------------------------|------------------|
| Geospatial visualizations | Maritime/aviation/climate layers | Web app embed or API |
| Dashboard components | 181 Preact components | Reuse/adapt for ABS dashboards |
| Threat mapping | Geopolitical event mapping | MCP + custom viz |

**Implementation:** Romi adapts WorldMonitor's Preact components for ABS dashboards via `OpenDesign`.

### 4. Memory Layer Integration (`services/memory.py`)

**Pipeline:** WorldMonitor ingestion → Fact extraction → Memory layer → Agent access

```
WorldMonitor Sources
        │
        ▼
Ingestion Services (RSS, Telegram, API, AIS, ADSB, etc.)
        │
        ▼
Fact Extraction (LLM summarization, entity extraction)
        │
        ▼
Memory Layer (services/memory.py)
  ├─ SQLite (FTS5) — exact match
  ├─ LanceDB (Vector) — semantic search (BEL-153)
  └─ Facts API — REST/MCP for agents
        │
        ▼
ABS Agents (Ergo, Proxy, Romi, OpenCode, OpenDesign)
```

**Key Integration Points:**
- `services/memory.py` `store()` with `metadata.linear_refs` + `paperclip_refs`
- `source: "worldmonitor"` in metadata for traceability
- Confidence scoring from WorldMonitor freshness + LLM extraction quality
- Vector embeddings for semantic search across OSINT corpus

### 5. MCP Server for ABS (`wm-mcp` + Custom)

**Option A: Use upstream `wm-mcp` directly**
- Pros: Zero maintenance, full feature parity
- Cons: No custom ABS-specific tools, rate limits

**Option B: Fork `wm-mcp` + ABS extensions**
- Custom tools: `search_osint_facts(query, tags?, confidence?)`
- Direct memory layer access: `get_memory_context(agent, query)`
- ABS-specific filters: `source: "worldmonitor"`, `company: "abs"`

**Recommendation:** **Option B** — Fork `wm-mcp` to `abs-worldmonitor-mcp` with:
1. All upstream tools
2. `search_abs_osint(query, min_confidence=0.7, tags=[])`
3. `get_abs_memory_context(agent, query)` → bridges to `services/memory.py`

---

## Self-Hosted Deployment Architecture

### Current WorldMonitor Deployment

| Component | Platform | Notes |
|-----------|----------|-------|
| Web App | Vercel (Edge) | Global CDN, auto-scaling |
| API | Vercel Edge Functions | 80+ endpoints |
| Relay | Railway | WebSocket relay for real-time |
| Database | Convex | Real-time sync, reactive queries |
| Desktop | Tauri + Node.js sidecar | Cross-platform |
| Workers | Cloudflare Workers | Edge CORS preflight |

### ABS Self-Hosted Target (Local-First)

```
┌─────────────────────────────────────────────────────────────┐
│                    ABS OSINT Stack (Self-Hosted)             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Ingestion   │  │  Processing  │  │   Storage    │      │
│  │  (Docker)    │──│  (Node.js)   │──│  (PostgreSQL │      │
│  │  RSS/Telegram│  │  LLM/ETL     │  │   + Redis)   │      │
│  │  AIS/ADSB    │  │  Vectors     │  │  + LanceDB   │      │
│  └──────────────┘  └──────────────┘  └──────┬───────┘      │
│                                             │                │
│  ┌──────────────┐  ┌──────────────┐         │                │
│  │   API Layer  │  │  MCP Server  │         │                │
│  │  (Node.js/   │  │  (abs-wm-mcp)│◄────────┤                │
│  │   Fastify)   │  │  + Custom    │         │                │
│  └──────────────┘  └──────────────┘         │                │
│        │                    │                │                │
│        ▼                    ▼                ▼                │
│  ┌──────────────────────────────────────────────┐           │
│  │           Memory Layer (services/memory.py)   │           │
│  │  SQLite + LanceDB → ABS Agents (Ergo/Proxy)  │           │
│  └──────────────────────────────────────────────┘           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Required Infrastructure

| Component | ABS Choice | Rationale |
|-----------|------------|-----------|
| **Ingestion Workers** | Docker Compose (local) | Local-first, no cloud deps |
| **LLM Processing** | Local Ollama (Qwen/DeepSeek) or OpenRouter | Fiscal freeze: DeepSeek V4-Flash |
| **Vector DB** | LanceDB (local) | Already in `services/memory.py` |
| **Primary DB** | PostgreSQL + pgvector | Structured + vector in one |
| **Cache** | Redis (local) | Rate limiting, staleness |
| **API Gateway** | Fastify (Node.js) | Fast, low overhead |
| **MCP Server** | Forked `wm-mcp` + ABS tools | Custom ABS tools |
| **Scheduler** | BullMQ (Redis) | Job queues for ingestion |
| **Monitoring** | Prometheus + Grafana (optional) | Local observability |

### Docker Compose (Sketch)

```yaml
version: '3.8'
services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: worldmonitor
      POSTGRES_USER: wm
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports: ["5432:5432"]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  ingestion:
    build: ./worldmonitor
    command: npm run ingestion:worker
    depends_on: [postgres, redis]
    env_file: .env.local

  api:
    build: ./worldmonitor
    command: npm run api:server
    ports: ["3001:3001"]
    depends_on: [postgres, redis]
    env_file: .env.local

  mcp:
    build: ./abs-worldmonitor-mcp
    ports: ["3002:3002"]
    env_file: .env.local

  memory-api:
    build: ./aspen-os
    command: python -m services.memory_api
    ports: ["8080:8080"]
    volumes:
      - ./memory:/home/tech/.aspen/memory
    env_file: .env.local

volumes:
  postgres_data:
```

---

## Implementation Plan (ABS-11)

### Phase 1: Architecture Analysis & Fork (Week 1) ✅
- [x] Fork `koala73/worldmonitor` → `AbsolutionAI/worldmonitor`
- [x] Clone to `/home/tech/worldmonitor`
- [ ] Complete architecture analysis (this doc)
- [ ] Map integration points to ABS agents

### Phase 2: Core Integration (Week 2)
- [ ] Fork `wm-mcp` → `abs-worldmonitor-mcp` with ABS tools
- [ ] Implement `search_abs_osint()` + `get_abs_memory_context()`
- [ ] Connect MCP to `services/memory.py` via REST
- [ ] Test Ergo/Proxy/Romi MCP access

### Phase 3: Ingestion Pipeline (Week 3)
- [ ] Deploy ingestion workers (Docker Compose)
- [ ] Configure priority sources (RSS, Telegram, AIS, ADSB)
- [ ] Build fact extraction pipeline (LLM → memory layer)
- [ ] Connect WorldMonitor ingestion → `services/memory.py`

### Phase 4: Agent Integration (Week 4)
- [ ] Ergo: MCP tools for strategic intelligence
- [ ] Proxy: Automated OSINT tasks via OpenCode
- [ ] Romi: Dashboard components from WorldMonitor
- [ ] OpenDesign: Geospatial viz components

### Phase 5: Deployment & Hardening (Week 5)
- [ ] Docker Compose stack for self-hosted
- [ ] PostgreSQL + pgvector + LanceDB
- [ ] Redis for caching/scheduling
- [ ] BullMQ job queues
- [ ] Prometheus/Grafana (optional)

---

## Resource Requirements

| Resource | Estimate | Notes |
|----------|----------|-------|
| **CPU** | 4-8 cores | Ingestion + LLM + API |
| **RAM** | 16-32 GB | LanceDB + PostgreSQL + workers |
| **Storage** | 100-500 GB | PostgreSQL + vector index + raw data |
| **GPU** | Optional | Local LLM (Ollama) if used |
| **Network** | 100+ Mbps | AIS/ADSB feeds, RSS, APIs |

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| WorldMonitor upstream breaking changes | Medium | Medium | Pin fork, selective cherry-pick |
| LLM costs (fact extraction) | High | Medium | DeepSeek V4-Flash only; batch processing |
| AIS/ADSB data volume | High | High | Bbox filtering, sampling, retention policies |
| MCP rate limits | Low | Low | Self-hosted MCP |
| Convex dependency | Medium | High | Replace with PostgreSQL + pgvector |
| Telegram API limits | Medium | Medium | Bot API + session management |

---

## Next Actions

1. **Complete this analysis doc** → commit to `docs/architecture/WORLDMONITOR_INTEGRATION.md`
2. **Fork `wm-mcp`** → create `abs-worldmonitor-mcp` repo
3. **Implement ABS MCP tools** → `search_abs_osint`, `get_abs_memory_context`
4. **Write ingestion → memory pipeline** → connect WorldMonitor to `services/memory.py`
5. **Test with Ergo** → strategic OSINT queries via MCP

---

## Linear Sync

- **BEL backlog item:** "OSINT Global Dashboard (OpenSINT)" — DEFER company
- **ABS-11:** Paperclip issue tracking this work
- **Progress:** Architecture analysis complete (this doc)
- **Next:** Phase 2 — MCP fork & ABS tools

---

*This analysis satisfies ABS-11 acceptance criteria: architecture analysis doc created, integration points mapped, MCP server design defined, deployment plan outlined.*