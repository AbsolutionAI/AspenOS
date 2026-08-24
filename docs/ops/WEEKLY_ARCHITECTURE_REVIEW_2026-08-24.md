# Weekly Architecture Review — 2026-08-24

**Issue:** ASP-426  
**Reviewer:** aspen (Architect)  
**Period:** 2026-08-22 → 2026-08-24 (delta vs ASP-166 / `WEEKLY_ARCHITECTURE_REVIEW_2026-08-22.md`)  
**SoR:** `docs/sor/MASTER_SPEC.md` (AspenGrove v4.0 — Three Organs)  
**Fiscal posture:** $100/mo LLM freeze; sim-only fleet; wake-on-demand

---

## 1. Executive verdict

| Area | Health | Delta vs 2026-08-22 |
|------|--------|---------------------|
| Product triad (OS / Sentinel / aspen-dev) | **Green (locked)** | Unchanged |
| Platform ADRs 0001–0006 | **Amber → fixing** | Index + bodies still missing from many agent branches / not on `origin/master` — **restored this cycle** |
| Agent mesh (Paperclip + Hermes) | **Green** | Layering clear; no dual org board |
| Fleet / swarm / RRM contracts | **Green (sim)** | **G6–G8 landed:** cell profile, estop hash chain, dual-human wire |
| Dual-human act gate (H-016) | **Green (sim)** | ASP-364 **done** — `aspen_edge.gate` + EdgeRRM hold/authorize/act |
| LangGraph plugin (ADR-0005) | **Amber** | Still propose_act-only; H-018 scheduler guard backlog (ASP-366) |
| Memory tiering (ADR-0006) | **Amber** | Draft **Proposed**; ready for accept next review |
| C11 sandbox (ADR-0010) | **Amber** | Overhead gate ratified earlier; native mandatory (H-003) |
| Bus dual-publish | **Amber** | Inventory exists (`FLEET_SUBJECT_PUBLISHERS.md`); sunset still ADR-0007 candidate |
| Doc/git hygiene | **Red → fixing** | Master Spec + ADR-0001..0006 were **not** on this worktree tip / master — primary risk this week |
| Packaging / physical cell | **Deferred** | ASP-418 Phase D D1 backlog; freeze holds |

**Overall:** Architecture **decisions still hold** and the **safety control path is materially stronger** (G6–G8). The main residual risk is **git/docs lag**: SoR + ADR set keeps falling off branch tips and has not landed on `origin/master`, so agents and hermes worktrees re-discover “missing ADRs.” Fix is merge hygiene, not redesign.

---

## 2. ADR register

| ADR | Decision | Still valid? | Action |
|-----|----------|--------------|--------|
| ADR-0001 Packaging | Grove layers, MIT/Apache, AbsolutionAI org | Yes | Keep |
| ADR-0002 Swarm/RRM | propose_act only; human arm; no joint stream from C2 | Yes — **hard** | Keep sim-only |
| ADR-0003 Bus contracts | Prefer `aspen.*`; envelope schema | Yes | **Amended this cycle** with G8 `authorize` + dual `authorize_clear` |
| ADR-0004 Light core | Kernel vs plugins | Yes | Align module-catalog later |
| ADR-0005 LangGraph | Cognitive plugin; Paperclip stays SoR | Yes | Guard dual scheduler (ASP-366) |
| ADR-0006 Memory tiering | T1 LanceDB/SQLite default; optional T2 PG+AGE | **Proposed** | Accept when human/architect confirms (no PG install) |
| ADR-0010 C11 (file `0001-c11-…`) | Spike sandbox first; Python CP | Yes | Keep; H-003 mandatory native |
| ADR-0007 (candidate) | Sunset dual-publish | Not filed | Wait for consumer share or external pilot |
| ADR-0008 | Authenticated operator-of-record for gate | **Proposed** (ASP-429) | Filed; accept + implement before non-sim arm |

---

## 3. Module boundaries (check)

```
aspen-dev (Paperclip/Hermes)     ← org, budgets, CE, personas
        │ issues / heartbeats only
        ▼
AspenOS product surface
  ├── kernel-ish: agent loop, policy, envelopes, health, bus interfaces
  ├── plugins: swarm-manager, edge-rrm (+ DualHumanGate), langgraph-worker, memory, dashboard
  └── drivers: MQTT / OPC-UA / ROS2 (last mile)
        │
        ▼
Hardware / sim (ASPEN_SIM=1 · plant-range status: sim_only)
```

**Boundary violations this period:** none observed.  
**G8 placement is correct:** gate library lives in **edge-rrm** (not monorepo kernel, not Paperclip). Monorepo scripts are proof harnesses only.

**Sticky risks (unchanged):**

1. Dual mission schedulers (Paperclip + LangGraph/swarm both arming plant work) — **ASP-366**  
2. Monorepo `services/fleet.py` still dual-publishes legacy subjects while grove packages speak `aspen.*`  
3. Worktree layout breaks sibling `aspen-edge-rrm` imports — **mitigated** this cycle in `scripts/sim_dual_human_gate.py` path walk

---

## 4. Agent-mesh & bus contracts

| Contract | Canonical | Status |
|----------|-----------|--------|
| Fleet register/HB/ops | `aspen.fleet.node.*`, `aspen.fleet.ops.status` | Packages + inventory |
| Missions | `aspen.fleet.mission.*` | Swarm package |
| Edge propose | `aspen.edge.<node>.propose_act` | edge-rrm |
| Edge authorize (G8) | `aspen.edge.<node>.authorize` | **Wired** DualHumanGate |
| Edge command | `aspen.edge.<node>.command` | edge-rrm |
| Safety estop | `aspen.safety.estop` | Highest precedence |
| Safety clear | `authorize_clear` ×2 → `clear` | **Wired** dual-human |
| LangGraph | `aspen.worker.langgraph.job\|result` | Still propose_act out |
| Starship agents | `starship.*` / `agnetic.*` | Legacy dual-publish |

**Decision (this review):** Keep dual-publish; do **not** file ADR-0007 yet. Prefer implementing ASP-366 (single plant scheduler guard) before any subject deletion.

**Safety hard rule (strengthened):** G3 sim proofs + G8 control-path wire complete under `sim_only`. Physical/D1 remains **ASP-418** backlog.

---

## 5. Pending design decisions

| # | Decision | Recommendation | Urgency |
|---|----------|----------------|---------|
| D1 | Accept ADR-0006 memory tiering | **Accept** as Proposed→Accepted next human ack; no PG under freeze | Medium |
| D2 | operator-of-record identity source | **Filed** ADR-0008 Proposed (ASP-429); accept + bind before G9 | High before physical |
| D3 | Merge SoR+ADRs to `origin/master` | **Do now** — unblock every agent worktree | **High** |
| D4 | plant-edge→plant-alpha ACL (ASP-369) | Keep backlog; no ACL widen under freeze | Medium |
| D5 | Software data-diode recipe (ASP-368) | Spec-only Flash drip when free | Low–med |
| D6 | Physical bring-up ASP-418 | Stay backlog until captain $0 PO + G9 checklist | Deferred |
| D7 | Matrix authz bridge | Optional front-end; NATS payload is SoR | Low |

---

## 6. Open issue map (architecture-relevant, live board)

| Cluster | Issues | Disposition |
|---------|--------|-------------|
| This review | ASP-426 | **Done** this heartbeat |
| Dual-human / Phase D sim | ASP-364, 384, 416, 417 | **Done** |
| Phase D physical | ASP-418 | Backlog — freeze |
| Scheduler / LangGraph | ASP-366 (H-018) | **Promote next** lean eng |
| Safety residual | ASP-368, 369 | Backlog |
| Host baseline | ASP-370 | Human approval only |
| Hardening backlog | ASP-371–376 | Medium; Flash when free |
| Packaging blockers | ASP-119 blocked, ASP-388 blocked | Packaging track |
| Hourly sweep | ASP-425 | Ops cadence — leave |

---

## 7. Doc hygiene actions (this heartbeat)

1. **Restore** `docs/adr/ADR-0001`…`0006` + `README.md` onto active branch (were missing from worktree tip).  
2. **Restore** Master Spec alias + body (`docs/sor/MASTER_SPEC.md`, `ASPENGROVE_MASTER_SPEC_v4.0.md`).  
3. **Restore** prior review + `FLEET_SUBJECT_PUBLISHERS.md` for continuity.  
4. **Amend** ADR-0003 for G8 authorize / dual clear subjects.  
5. **Refresh** ADR index (ADR-0010 numbering; candidates 0007/0008).  
6. **Refresh** `docs/architecture/overview.md` safety + last-review pointer.  
7. **Harden** `scripts/sim_dual_human_gate.py` import path for hermes worktrees.  
8. **This review** under `docs/ops/WEEKLY_ARCHITECTURE_REVIEW_2026-08-24.md`.

---

## 8. Follow-up tasks (Paperclip children)

1. **Merge SoR + ADR set to master** — aspen / packndeploy (PR from this branch or cherry-pick docs-only)  
2. **H-018 single plant scheduler guard** — already ASP-366; assign robotics or Opencode when capacity  
3. **Accept ADR-0006** — aspen short confirmation issue (docs status flip only)  
4. **ADR-0008 draft: operator-of-record binding** — aspen plan-only before any G9  
5. No new physical-cell work under freeze

---

## 9. Freeze-aware next 2 weeks

**Do**

- Land SoR/ADR on `master` so worktrees stop losing them  
- Lean H-018 / ACL / data-diode specs on Flash  
- Keep dual-human sim proofs green (`sim_dual_human_gate.py`, edge-rrm tests)  
- Merge open security hermes branches when CI green  

**Don’t**

- Physical arm / ASP-418 without captain gate  
- Widen plant-edge→alpha ACL without threat review  
- Second mission scheduler  
- Expand Grok beyond architecture gates  

---

## 10. Sign-off

Architecture **coherent and safety path advanced (G6–G8)**. Primary work this cycle is **re-materializing SoR/ADRs on the active line** and **recording the G8 contract in ADR-0003**, not redesigning the grove.

**Next weekly review:** ~2026-08-31 (or next ASP weekly ticket). Compare against this file’s verdict table and confirm `origin/master` contains `docs/adr/ADR-0001`…`0006` + Master Spec.
