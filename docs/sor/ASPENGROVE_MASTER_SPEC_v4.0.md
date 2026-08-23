# AspenGrove Master Architecture & Product Specification
**Version 4.0 — "Three Organs" Edition**  
**Classification:** Internal / Confidential — Absolution Studios  
**Date:** August 6, 2026  
**Status:** Authoritative Source of Truth  

**Locked Decisions (2026-08-06)**  
- Overarching Epic: **AspenGrove**  
- Three products: **AspenOS** · **Aspen Sentinel** · **aspen-dev**  
- Tagline: “Autonomous Systems Platform for Engineered Networks”  
- Dual licensing: MIT core + commercial manufacturing layer  
- aspen-dev = single source of truth for Paperclip companies + Hermes personas  
- Polyglot PostgreSQL (pgvector + Apache AGE + TimescaleDB) + Redis + MinIO  
- Hard rule: agents emit only `propose_act` on safety-adjacent subjects until dual human authorization  
- Auto-RED quarantine allowed for database-driven known threats  
- Software data-diode emulation for now (hardware diode later for gov contracts)  
- Task granularity: 1–4 hour agent-executable slices  

---

## 1. Executive Summary

AspenGrove is a single living organism expressed as three primary organs that can be installed together or separately:

| Product | Role | Analogy |
|---------|------|---------|
| **AspenOS** | Agentic-first operating system / control plane for manufacturing, robotics, drones, edge nodes, self-healing, and real-time hardware | Windows 11 IoT + real-time control layer |
| **Aspen Sentinel** | OSINT-aware + Human-in-the-Loop command & control workspace for the entire Grove (fleet overview, authorization gates, audit, incident response, task boards) | Microsoft 365 + Power BI + Sentinel for operators |
| **aspen-dev** | Development company backend that builds, packages, tests, self-heals, and evolves the other two products (and Gumroad sellables) | Internal engineering org + GitHub + Azure DevOps |

The organism metaphor remains: an aspen grove is one living system connected by underground roots. Individual trees (nodes, agents, packages) appear separate but share resources, intelligence, and resilience.

**Target domains:** Defense & Space Manufacturing, FDA-registered cGMP facilities (Chaé flagship), autonomous robotics, drone swarm C2, future space infrastructure, OSINT-aware R&D.

**Hardware reality (current):** Ubuntu 24.04 LTS server with temporary P2000; RTX 3090 pending; Jetson Orin NX desired but timeline open; soft-RT (PREEMPT_RT) + hard-RT bridge required.

---

## 2. Product Definitions & Boundaries

### 2.1 AspenOS (Agentic Operating System)
**Purpose:** Local-first, AI-native runtime that sits between human operators and physical/digital systems. Multi-agent orchestration, shared memory bus, self-healing code pipeline, vision & multi-sensor capacity, fleet command-and-control, RTOS bridge.

**Core capabilities locked from v3.0:**
- Multi-agent orchestration via Paperclip + Hermes roles
- NATS JetStream shared memory bus
- Self-healing pipeline (detect → propose → CI/CD gate → human approve → blue-green)
- Soft-RT (PREEMPT_RT + ROS 2) ↔ Hard-RT (QNX preferred) bridge
- Hybrid compute: local sensitive logic, private cloud for heavy (CRISPR, astrophysics, quantum)
- Zero-trust + cross-domain readiness

**Primary repo:** `AbsolutionAI/AspenOS`  
**Supporting packages (Core Runtime):**  
- `aspen-contracts` (L0 schemas, NATS subjects, ADRs)  
- `aspen-agent-runtime`  
- `aspen-edge-rrm` (Runtime Resource Manager + micro-agents)  
- `aspen-swarm-manager`  
- Parts of `aspen-dashboard` that become the AspenOS C2 surface  

### 2.2 Aspen Sentinel (OSINT + HITL Workspace)
**Purpose:** The operator-facing command dashboard for the entire AspenGrove. Builds on the OpenSINT / World Monitor lineage. Provides global awareness, incident response, fleet overview, authorization gates, audit ledger, task boards, email/chat/voice/vision collaboration surfaces.

**Key features:**
- Real-time fleet / plant / drone map
- Authorization modal with dual-key + biometric path for RED/BLACK actions
- OSINT ingest (software diode today)
- Shared memory browser + knowledge graph views
- Task boards, email/chat bridges, voice/vision interfaces
- ROE visualization (GREEN → YELLOW → RED → BLACK)

**Primary evolution path:** Evolve `aspen-dashboard` + OpenSINT project into a first-class product.  
**Optional plugins that feed it:** `aspen-sherlock-tool`, security baseline outputs, model-routing status.

### 2.3 aspen-dev (Development Company Backend)
**Purpose:** The organism that builds and maintains AspenOS, Aspen Sentinel, Gumroad products, and future projects. Single source of truth for:
- Paperclip company definitions and org charts
- Hermes personas / souls / skill catalogs
- Compound Engineering gates
- CI/CD pipelines (Gitea Actions preferred for offline readiness)
- Packaging mesh and redacted blueprints
- Self-pruning / self-growing logic (with 180-day horizon rules)

**Primary repo (to be elevated / created as canonical):** `aspen-dev`  
**Dev-only packages:**  
- `aspen-process-workers` (Aider, Agent Zero, etc.)  
- `aspen-paperclip-blueprints`  
- `aspen-hermes-profile-template`  
- `aspen-agent-personas`  
- `aspen-ce-gates`  
- `aspen-commerce-playbooks`  
- `aspen-private-lane`  
- `aspen-grove` (meta compose)  

### 2.4 Package Classification (Analysis)

| Category | Packages | Rationale |
|----------|----------|-----------|
| **Core Runtime** (ship with AspenOS) | aspen-contracts, aspen-agent-runtime, aspen-edge-rrm, aspen-swarm-manager, AspenOS monorepo | Required for any production deployment of the OS / fleet / edge |
| **Optional Plugins** | aspen-matrix-ops, aspen-sherlock-tool, aspen-security-baseline, aspen-model-routing | Useful but not mandatory for basic operation; can be composed in |
| **Dev-only** | aspen-process-workers, aspen-paperclip-blueprints, aspen-hermes-profile-template, aspen-agent-personas, aspen-ce-gates, aspen-commerce-playbooks, aspen-private-lane, aspen-grove | Belong to the development organism; not required on production edge nodes |
| **Sellable (outside core Grove)** | 9 Gumroad templates + gumroad-assets | Keep as pure revenue products unless a component is extracted for Sentinel UI |

**Gumroad fit recommendation:**  
- `react-admin-template` and selected pieces of `saas-starter-kit` / `api-boilerplate` → feed Aspen Sentinel dashboard.  
- All others remain pure sellable products under Absolution Digital Commerce.

---

## 3. Full Stack Architecture (Locked Five-Layer Topology)

```
GOVERNANCE LAYER          → Aspen Sentinel (HITL, audit, ROE, data-diode control)
ORCHESTRATION LAYER       → Paperclip + Hermes (owned by aspen-dev, exposed to AspenOS)
COGNITIVE LAYER           → Local Ollama/vLLM + private cloud heavy compute + shared memory
ADAPTATION LAYER          → Aider / OpenCode / Gitea / Compound Engineering (aspen-dev)
HARDWARE ABSTRACTION      → Soft-RT (PREEMPT_RT + ROS 2) + Hard-RT (QNX) + Zephyr + Jetson + NATS + Tailscale
```

### 3.1 Data & Memory (Confirmed)
- **Primary store:** PostgreSQL 16 polyglot  
  - pgvector (semantic / RAG)  
  - Apache AGE (property graph / causal reasoning) — preferred over Neo4j for operational efficiency at enterprise scale (single system to operate, SQL + Cypher)  
  - TimescaleDB (sensor telemetry)  
- **Hot session:** Redis  
- **Large artifacts / WORM:** MinIO  
- **Self-pruning policy (first 90 days):** Limited. Maintain `.md` skill catalog of all skills. Loaded skills pruned only after 180-day horizon review **or** when edge storage pressure triggers agent-role self-diagnostic feasibility determination.

### 3.2 Self-Healing & Rollback (Industry-Aligned)
**Preferred tiers (in order):**
1. Container blue-green (Tier 1 – fast)
2. ZFS snapshot (Tier 2)
3. QNX / hard-RT last-known-safe-state
4. Full image reflash (last resort)

**Standards alignment:**
- NASA-STD-8739.8 (Software Assurance & Software Safety)
- IEC 61508 SIL considerations for safety-related functions
- “Test as you fly” + independent verification where safety-adjacent
- Modified Condition/Decision Coverage (MC/DC) target for safety-critical paths when moving toward certification

**Hard rule:** On any safety-adjacent NATS subject, agents may only publish `propose_act`. Dual human authorization required before `act`. Auto-RED quarantine is permitted for threats already present in the known-threat database.

**Minimum CI/CD gates for hardware/fleet-touching code:**  
lint → unit → simulation (Gazebo / mock) → shadow / canary → human gate → deploy.  
Escalate rigor toward NASA/DoD practices as Chaé pilot and later gov contracts approach.

### 3.3 Hard-RTOS Recommendation
**Preferred:** QNX Neutrino (2026 leader in robotics functional safety per industry rankings, microkernel, IEC 61508 SIL 3 path, strong industrial & automotive pedigree).  
**Acceptable alternative:** VxWorks (still dominant in many KUKA/ABB controllers, excellent certification story).  
**Edge microcontrollers:** Zephyr or FreeRTOS.  
**Soft-RT compute nodes:** Ubuntu 24.04 + PREEMPT_RT + ROS 2 Humble/Iron.

### 3.4 Cross-Domain
- Software data-diode emulation now (iptables / one-way rules + process isolation).  
- Architecture ready for hardware diode (Securacore / Vigilant class) when classified domains appear for future gov contracts.  
- No classified domains today; design for future CUI / classified manufacturing + OSINT separation.

### 3.5 Networking & Identity
- NATS JetStream (subject naming: `aspen.{domain}.{service}.{action}.{priority}`)
- Tailscale mesh (private foundation) + Hermes Messaging Gateway (Matrix primary)
- SPIFFE/SPIRE for mTLS zero-trust identity (target)
- OPNsense for network segmentation

---

## 4. Long Horizon (5–15 Years)

| Horizon | Focus |
|---------|-------|
| Year 1–3 | Stable AspenOS v1 + Chaé pilot, ROS 2 fleet, vision inspection, edge nodes, grant commercialization |
| Year 4–7 | Federated learning across sites, quantum-resistant crypto, autonomous supply-chain agents, marketplace, space-habitat pilots |
| Year 8–15 | “Intelligent Matter”, planetary-scale coordination readiness, advanced neural interfaces (regulated), molecular-assembly research interfaces |

Design principles for longevity remain: modularity, open standards (ROS 2, DDS, OPC-UA, MQTT), security as default, human agency preserved for safety-critical actions, versioned APIs with long deprecation cycles.

---

## 5. Tool Decisions & Rejected Alternatives (Summary)

| Area | Chosen | Rejected / Deferred | Why |
|------|--------|---------------------|-----|
| Orchestration | Paperclip + Hermes | AutoGen, LangChain, CrewAI | Org-chart model + role routing + cost visibility |
| Messaging | NATS JetStream | Kafka, Redis Pub/Sub | Latency + persistence + operational simplicity |
| Knowledge | PostgreSQL + AGE + pgvector | Neo4j, Weaviate, Milvus as primary | Single operational surface |
| CI/CD | Gitea Actions | GitLab CE (heavier), GitHub Actions (internet dependency) | Offline-ready, lightweight |
| Hard-RTOS | QNX Neutrino (preferred) | VxWorks (acceptable), FreeRTOS (micro only) | Robotics safety leadership + certifications |
| Dashboard base | Evolve aspen-dashboard + OpenSINT | Pure third-party only | Local-first + full control |
| Remote access | Tailscale + Matrix (Hermes) | Public tunnels by default | Private mesh first |

All chosen tools are treated as starting points that will be developed further for Aspen efficiency.

---

## 6. Development Task Breakdown (Agent-Executable)

Tasks remain 1–4 hour slices. Full atomic breakdown will be pushed into Linear under the AspenGrove epic after this document is accepted. High-level phases:

**Phase A – Foundation Alignment (Week 1)**  
- Elevate / create canonical `aspen-dev` repo  
- Finalize package classification ADRs  
- Lock NATS subject contracts for Sentinel + AspenOS  
- Paperclip company definitions moved under aspen-dev ownership  

**Phase B – AspenOS Core Hardening**  
- Complete edge-rrm + swarm-manager integration  
- Soft-RT ↔ hard-RT bridge skeleton  
- Self-healing pipeline stages 1–7 with dual-auth gate  
- Polyglot PostgreSQL schema + AGE graph seed  

**Phase C – Aspen Sentinel MVP**  
- Evolve dashboard into Sentinel surface  
- Authorization modal + audit ledger  
- OSINT ingest path (software diode)  
- Fleet map + ROE visualization  

**Phase D – aspen-dev Completeness**  
- Hermes persona / skill catalog as code  
- Compound Engineering gates as enforceable CI  
- Packaging mesh publish pipeline  
- Self-pruning policy implementation (180-day horizon)  

**Phase E – Chaé Pilot Readiness**  
- Plant profile ACLs  
- First production line integration (OPC-UA / MQTT)  
- Operator training materials  
- 90-day stability instrumentation  

Detailed Linear issues will be generated from this document once approved.

---

## 7. Immediate Next Actions

1. Accept or amend this v4.0 specification.  
2. Create / elevate `aspen-dev` repository as canonical.  
3. Push atomic tasks into Linear under AspenGrove epic (I will do this on confirmation).  
4. Continue Matrix + Tailscale + Hermes gateway configuration on the server (prior draft still valid).  
5. Procure / schedule RTX 3090 and first Jetson Orin NX when budget allows.

---

## Appendix A – Package Ownership Matrix (Quick Reference)

**AspenOS owns runtime of:** contracts, agent-runtime, edge-rrm, swarm-manager  
**Aspen Sentinel owns:** dashboard evolution, OSINT surfaces, authorization UX  
**aspen-dev owns:** personas, blueprints, process workers, CE gates, commerce playbooks, private lane, meta compose  

---

## Appendix B – Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0–3.0 | Jul–Aug 2026 | Grok / Lumo | Prior architecture iterations |
| 4.0 | 2026-08-06 | Grok (CTO) | Three-product model, package classification, locked answers, Sentinel naming, aspen-dev ownership, full consolidation |

---

**END OF DOCUMENT**

This specification is the single source of truth for AspenGrove. All future ADRs, Linear issues, and package work must align with it or formally amend it.

---

**Project path (SoR):** `docs/sor/`  
**Ingested:** 2026-08-06T17:10:44-06:00  
**Rule:** Treat as authoritative; update via versioned revision, do not silently fork.
