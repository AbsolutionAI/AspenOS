# Starship OS Architecture

> **Superseded as product SoR (2026-08-22).**  
> Authoritative architecture: [`docs/sor/MASTER_SPEC.md`](sor/MASTER_SPEC.md) (AspenGrove v4.0).  
> Living overview: [`docs/architecture/overview.md`](architecture/overview.md).  
> ADRs: [`docs/adr/README.md`](adr/README.md).  
> Weekly review: [`docs/ops/WEEKLY_ARCHITECTURE_REVIEW_2026-08-22.md`](ops/WEEKLY_ARCHITECTURE_REVIEW_2026-08-22.md).  
> This file is retained as **historical Alpha agent-mesh notes** (Romi/Proxy/Ergo + legacy `agnetic.*` subjects). Prefer Master Spec + ADR-0002/0003 for fleet/safety.

A native AI operating system for complex system control. AI agents are first-class system services communicating via a NATS/JetStream message bus.

## Philosophy

- **Agent-Native**: AI agents are first-class citizens of the OS
- **Specialization**: Each subsystem has a dedicated agent with focused capabilities
- **Learning**: Agents improve through experience, creating and refining skills autonomously
- **Local-First**: All intelligence runs locally via Ollama; cloud providers optional
- **Bus-Oriented**: Agents communicate asynchronously via NATS/JetStream subjects

## Architecture

```
User/Opencode
    │
    ▼
┌─────────────────────────────────────┐
│         Hermes Orchestrator         │
│   (central coordinator, routing)    │
└──────────┬──────────┬───────────────┘
           │          │
    ┌──────▼──┐  ┌────▼──────┐
    │  Proxy  │  │   Romi    │
    │ (tech)  │  │ (client)  │
    └──────┬──┘  └────┬──────┘
           │          │
    ┌──────▼──────────▼──────┐
    │    NATS/JetStream Bus   │
    │  agnetic.agent.*.*     │
    │  agnetic.telemetry.*   │
    └──────┬──────────┬──────┘
           │          │
    ┌──────▼──┐  ┌────▼──────┐
    │ StarAgent│  │   Ergo    │
    │ (Rust)   │  │ (auto)    │
    └─────────┘  └───────────┘
```

## Agents

### Proxy (Tech Agent)
- System diagnostics, troubleshooting, log analysis
- Resource monitoring and alerting
- File system and process queries
- Model: qwen2.5:7b

### Romi (Client Agent)
- User-facing natural language interface
- Task explanation and status reporting
- Preference management and user modeling
- Model: qwen2.5:7b

### Ergo (Automation Agent)
- Scheduled tasks and cron workflows
- Event-triggered automations
- Backup and maintenance routines
- Model: Eve-V2 (3.4B)

### StarAgent (Rust)
- Cross-platform system metric collection
- Reports to NATS: cpu, mem, disk, net telemetry
- Low-level system monitoring daemon

## Communication

### NATS Subjects
- `agnetic.agent.proxy.command.<cmd>` — Proxy directives
- `agnetic.agent.proxy.event.<event>` — Proxy events
- `agnetic.agent.proxy.status` — Proxy health status
- `agnetic.agent.romi.command.<cmd>` — Romi directives
- `agnetic.agent.romi.event.<event>` — Romi events
- `agnetic.agent.romi.status` — Romi health status
- `agnetic.agent.ergo.command.<cmd>` — Ergo directives
- `agnetic.agent.ergo.event.<event>` — Ergo events
- `agnetic.agent.ergo.status` — Ergo health status
- `agnetic.telemetry.cpu` — CPU metrics
- `agnetic.telemetry.mem` — Memory metrics
- `agnetic.telemetry.disk` — Disk metrics
- `agnetic.telemetry.net` — Network metrics

## Tech Stack

- **Hermes Agent v0.18.2** — Agent framework with self-improvement loop
- **Ollama v0.31.1** — Local LLM inference (CUDA, RTX 4050 5.6 GB VRAM)
- **Qwen2.5:7b** — Primary local model (4.7 GB)
- **Eve-V2 (3.4B)** — Secondary local model for automation (3.4 GB)
- **NATS v2.10.7** — Agent communication bus
- **Go 1.22** — Agnetic CLI
- **Rust 1.96** — StarAgent system monitor
- **Opencode** — Development interface

## Directory Structure

```
agnetic-os/
├── cli/                    # Agnetic CLI (Go/Cobra)
├── agent/                  # StarAgent (Rust)
├── agents/                 # Hermes Agent YAML configs
├── skills/                 # Hermes Agent skills
├── nats/                   # NATS/JetStream configuration
├── docs/                   # Documentation
├── CLAUDE.md               # AI tool configuration
└── README.md
```

## Development Roadmap

1. [x] Foundation: Hermes Agent + Ollama installed
2. [x] Skills: System Health, Knowledge Store
3. [x] Models: qwen2.5:7b + Eve-V2 pulled
4. [x] Hermes configured for local Ollama
5. [x] Dev toolchain: NATS, Go, Rust installed
6. [ ] NATS agent bus: wired and tested
7. [ ] Proxy/Romi/Ergo agents: configured and connected
8. [ ] Agnetic CLI: Go/Cobra bootstrap commands
9. [ ] StarAgent: Rust system monitor
10. [ ] Distribution: Build as custom Linux ISO
