# Weekly Architecture Review — 2026-08-22

**Issue:** ASP-166  
**Reviewer:** aspen (Architect)  
**Period:** ~2026-08-06 → 2026-08-22  
**SoR:** `docs/sor/MASTER_SPEC.md` (AspenGrove v4.0 — Three Organs)  
**Fiscal posture:** $100/mo LLM freeze; sim-only fleet; wake-on-demand

---

## 1. Executive verdict

| Area | Health | Notes |
|------|--------|-------|
| Product triad (OS / Sentinel / aspen-dev) | **Green (locked)** | Master Spec v4.0 authoritative |
| Platform ADRs 0001–0005 | **Amber** | Content solid; **were untracked on disk** — committing this cycle |
| Agent mesh (Paperclip + Hermes) | **Green** | Layering clear; no dual org board |
| Fleet / swarm / RRM contracts | **Green (sim)** | BEL-179 packages + ADR-0002/3; physical cell backlog |
| LangGraph plugin (ADR-0005) | **Amber** | Scaffold + worker done; BEL-207–210 open |
| Memory layer (BEL-154) | **Green → tail** | Ingest/hooks landed; AppFlowy blocked; `memory.py` drift open |
| C11 sandbox (ADR-0010) | **Red/amber** | Seccomp + p50 regressions on smoke (ASP-357 cluster) |
| Doc coherence | **Red → fixing** | Legacy Starship `ARCHITECTURE.md` vs Master Spec; subject dual-publish |
| Packaging / install paths | **Amber** | `/opt/agnetic` → `/opt/starship` residue; deb/ISO follow-ups |

**Overall:** Architecture **decisions hold**. Main risk is **documentation and repo hygiene lagging decisions**, plus **runtime smoke regressions** (C11/NATS tooling) that block packaging confidence — not a layering failure.

---

## 2. ADR register

| ADR | Decision | Still valid? | Action |
|-----|----------|--------------|--------|
| ADR-0001 Packaging | Grove layers, MIT/Apache, AbsolutionAI org | Yes | Keep; mesh epic ASP-46 |
| ADR-0002 Swarm/RRM | propose_act only; human arm; no joint stream from C2 | Yes — **hard** | Keep sim-only |
| ADR-0003 Bus contracts | Prefer `aspen.*`; envelope schema | Yes | Dual-publish window still needed (see §4) |
| ADR-0004 Light core | Kernel vs plugins | Yes | Align module-catalog later |
| ADR-0005 LangGraph | Cognitive plugin; Paperclip stays SoR | Yes | Finish BEL-207–210 when unblocked |
| ADR-0010 C11 (legacy “ADR 0001”) | Spike sandbox first; Python CP through Alpha | Yes | Treat regressions as eng debt, not ADR reopen |

**Numbering collision resolved** in `docs/adr/README.md` (C11 → logical ADR-0010).

---

## 3. Module boundaries (check)

```
aspen-dev (Paperclip/Hermes)     ← org, budgets, CE, personas
        │ issues / heartbeats only
        ▼
AspenOS product surface
  ├── kernel-ish: agent loop, policy, envelopes, health, bus interfaces
  ├── plugins: swarm-manager, edge-rrm, langgraph-worker, memory, dashboard
  └── drivers: MQTT / OPC-UA / ROS2 (last mile)
        │
        ▼
Hardware / sim (ASPEN_SIM=1 default under freeze)
```

**Boundary violations watched this week:** none new. Sticky risk remains **dual mission schedulers** (Paperclip assigning plant work *and* LangGraph/swarm both arming) — ADR-0005 explicitly forbids; keep on review checklist.

**Starship monorepo vs grove packages:** monorepo still carries Alpha 2.1 services (`services/fleet.py`, C11, StarAgent). Grove packages are the **forward boundary**. Do not collapse swarm/RRM back into monorepo kernel.

---

## 4. Agent-mesh & bus contracts

| Contract | Canonical | Legacy bridge | Gap |
|----------|-----------|---------------|-----|
| Fleet register/HB/ops | `aspen.fleet.node.*`, `aspen.fleet.ops.status` | `starship.fleet.*`, `agnetic.fleet.*` | Monorepo fleet daemon primarily legacy names |
| Missions | `aspen.fleet.mission.*` | — | Swarm package |
| Edge propose/command | `aspen.edge.<node>.*` | — | edge-rrm |
| Safety | `aspen.safety.estop\|clear` | — | Must remain highest precedence |
| LangGraph | `aspen.worker.langgraph.job\|result` | — | BEL-207 NATS E2E open |
| Starship agents (Romi/Proxy) | `starship.agent.*` / `agnetic.*` | dual-publish | Legacy product surface |

**Decision (this review):** Keep dual-publish through Alpha; open **ADR-0007 candidate** when >50% consumers speak `aspen.*` or before first external plant pilot. Do **not** delete legacy subjects under freeze.

**Safety hard rule (unchanged):** safety-adjacent path = **`propose_act` only** until **dual human authorization**. Auto-RED quarantine OK. Software data-diode for now.

---

## 5. Pending design decisions

| # | Decision | Recommendation | Urgency |
|---|----------|----------------|---------|
| D1 | Memory SoR: LanceDB path (BEL-154) vs Master Spec PG+AGE+pgvector | **Tiered:** edge/local LanceDB + optional promote to PG later; file ADR-0006 when implementing PG | Medium |
| D2 | C11 p50/seccomp smoke red | Engineering fix (ASP-357); do not reverse ADR-0010 | High (packaging) |
| D3 | `/opt/agnetic` residue | Continue path alignment tickets; no architecture flip | Medium |
| D4 | AppFlowy sync (MEMORY Component 5) | **Remain blocked** under freeze (BEL-135 style) | Low |
| D5 | Physical cell BEL-192 | **Stay backlog** until sim solid + budget | Deferred |
| D6 | Sentinel MVP vs dashboard | Freeze-deferred; product boundary locked in Master Spec | Deferred |
| D7 | Sticky in_progress epics ASP-50/66/46 | Disposition hygiene — mark done or create concrete residual children | Medium |

---

## 6. Open issue map (architecture-relevant)

| Cluster | Issues | Disposition advice |
|---------|--------|-------------------|
| Weekly review dups | ASP-166 (this), ASP-296 blocked | Close 296 as duplicate after 166 done |
| Fleet epic | ASP-50 | If packages+ADRs accepted, close or reduce to residual list |
| LangGraph | ASP-66 | Residual: BEL-207–210 only |
| Package mesh | ASP-46 | Reference/review — close if map accepted |
| Memory drift | ASP-98 | Assign implementation |
| AppFlowy | ASP-79 | Keep blocked |
| C11/smoke | ASP-357, 148/149, 188/189, 354 | Single owner packndeploy/runtime |
| ISO/paths | ASP-119–121, 151, 190–192, 352–353 | Packaging track |
| Rust toolchain dups | ASP-147, ASP-154 | Dedup |

---

## 7. Doc hygiene actions (this heartbeat)

1. **Commit** previously untracked `docs/adr/ADR-0001`…`0005`, `docs/sor/**`, LangGraph epic plan.
2. **Add** `docs/adr/README.md` (numbering + open candidates).
3. **Banner** legacy `docs/ARCHITECTURE.md` → point to Master Spec + overview.
4. **Refresh** `docs/architecture/overview.md` for Three Organs + `aspen.*` subjects.
5. **This review** under `docs/ops/`.

---

## 8. Follow-up tasks created

See Paperclip children of ASP-166 (and Linear mirrors when MCP available):

1. **Commit SoR + ADRs** (this PR) — aspen  
2. **ADR-0006 draft: memory store tiering** — aspen (plan-only under freeze)  
3. **Subject dual-publish inventory** — runtime (list publishers of `starship.fleet.*` vs `aspen.fleet.*`)  
4. **Epic disposition pass** ASP-50 / ASP-66 / ASP-46 — aspen  
5. **C11 smoke cluster** remains on existing ASP-357 (no new epic)

---

## 9. Freeze-aware next 2 weeks

**Do**

- Land SoR/ADR git hygiene  
- Fix smoke blockers that protect install confidence  
- Memory drift ASP-98 if cheap  
- Keep fleet **sim + Flash** only  

**Don’t**

- Physical arm / real cell  
- Sentinel/OSINT volume  
- Dual mission schedulers  
- Expand Grok beyond architecture gates  

---

## 10. Sign-off

Architecture **coherent**. Primary work this cycle is **making the paper real in git** and **closing doc/subject drift**, not redesigning the grove.

**Next weekly review:** ~2026-08-29 (or next ASP weekly ticket). Compare against this file’s verdict table.
