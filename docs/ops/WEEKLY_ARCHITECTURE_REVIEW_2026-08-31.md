# Weekly Architecture Review — 2026-08-31

**Issue:** ASP-530  
**Reviewer:** aspen (Architect)  
**Period:** 2026-08-24 → 2026-08-31 (delta vs ASP-426 / `WEEKLY_ARCHITECTURE_REVIEW_2026-08-24.md`)  
**SoR:** `docs/sor/MASTER_SPEC.md` (AspenGrove v4.0 — Three Organs)  
**Fiscal posture:** $100/mo LLM freeze; sim-only fleet; wake-on-demand; Grok only for architecture gates

---

## 1. Executive verdict

| Area | Health | Delta vs 2026-08-24 |
|------|--------|---------------------|
| Product triad (OS / Sentinel / aspen-dev) | **Green (locked)** | Unchanged |
| Platform ADRs 0001–0006 | **Green** | On `origin/master`; ADR-0006 Accepted (ASP-514) |
| ADR-0007 Sentinel/C2 NATS subjects | **Amber → Accepted** | Filed + FLEET.md rows; **Accepted this review** |
| ADR-0008 Package classification | **Amber → Accepted** | Filed + PACKAGES.md; **Accepted this review** |
| ADR-0009 Capability gatekeepers | **Amber → Accepted (design)** | Shim prototype landed; **design Accepted**; runtime wiring continues |
| Agent mesh (Paperclip + Hermes) | **Green** | Layering clear; wake-on-demand under freeze |
| Fleet / swarm / RRM contracts | **Green (sim)** | G6–G8 hold; ASP-499 fleet-bus smoke blocked (path/import) |
| Dual-human act gate (H-016) | **Green (sim)** | Unchanged |
| LangGraph plugin (ADR-0005) | **Amber** | BEL-207/208/209 still open; H-018 scheduler guard still backlog |
| Memory tiering (ADR-0006) | **Green** | Accepted; T1 SQLite/Lance default under freeze |
| C11 sandbox (ADR-0010) | **Amber** | CI help/PATH hardened (ASP-522); keep native mandatory |
| Bus dual-publish sunset | **Amber** | Renumbered open candidate → **ADR-0011** (not filed) |
| Operator-of-record binding | **Amber** | Open candidate → **ADR-0012** (G9 blocker) |
| Doc/git hygiene | **Green** | Master Spec + ADR-0001..0009 present on master tip |
| Packaging / physical cell | **Deferred** | Freeze + ASP-418 backlog |

**Overall:** Architecture **decisions hold and expanded cleanly**. Last week closed the “missing SoR/ADR on master” risk. This week’s material advance is the **ADR-0007/8/9 triad** (Sentinel subjects, package tiers, gatekeeper design) plus gatekeeper shim + PACKAGES/FLEET doc alignment from ASP-525. Residual engineering risk is **runtime wiring** (gatekeeper on live NATS, H-018 dual-scheduler guard, fleet smoke import path) — not layering ambiguity.

---

## 2. ADR register

| ADR | Decision | Still valid? | Action |
|-----|----------|--------------|--------|
| ADR-0001 Packaging | Grove layers, MIT/Apache, AbsolutionAI org | Yes | Keep |
| ADR-0002 Swarm/RRM | propose_act only; human arm; no joint stream from C2 | Yes — **hard** | Keep sim-only |
| ADR-0003 Bus contracts | Prefer `aspen.*`; envelope + G8 authorize | Yes | Keep |
| ADR-0004 Light core | Kernel vs plugins | Yes | Align catalog with ADR-0008 |
| ADR-0005 LangGraph | Cognitive plugin; Paperclip stays SoR | Yes | Finish BEL-207–209 lean; H-018 |
| ADR-0006 Memory tiering | T1 LanceDB/SQLite; optional T2 PG+AGE | Yes (Accepted) | No PG under freeze |
| **ADR-0007** Sentinel + authz NATS subjects | Additive `aspen.sentinel.*` / `aspen.authz.*` | **Accepted 2026-08-31** | Mirror into aspen-contracts when free |
| **ADR-0008** Core / Plugin / Dev-only | Three-tier classification + PACKAGES.md | **Accepted 2026-08-31** | Enforce `classification` field in mesh |
| **ADR-0009** Capability gatekeepers | No broad keys; propose_act + dual-human | **Accepted (design) 2026-08-31** | Wire shim → NATS + Hermes adapters |
| ADR-0010 C11 (file `0001-c11-…`) | Spike sandbox; Python CP | Yes | Keep |
| ADR-0011 (candidate) | Sunset dual-publish | Not filed | Wait >50% `aspen.*` or external pilot |
| ADR-0012 (candidate) | Operator-of-record binding for DualHumanGate | Not filed | **Before any non-sim arm (G9+)** |

### Acceptance rationale (this review)

1. **ADR-0007** — Additive subject table in monorepo `docs/FLEET.md` + ADR body; no break to BEL-179 fleet subjects; dual-human path unchanged. Linear BEL-196 design lock satisfied in-repo; optional publish to AbsolutionAI/aspen-contracts remains implementation follow-up.
2. **ADR-0008** — PACKAGES.md is SoR for Core/Plugin/Dev-only; cross-links ADR-0001/0004; BEL-195 acceptance met for ADR + matrix. Remaining: mesh tooling enforces `classification` metadata.
3. **ADR-0009** — Design + local shim (`src/python/gatekeeper/minimal_shim.py`) meet “documented + prototyped.” Full “no broad keys in any image” is **implementation** under BEL-215 — design is locked so agents stop inventing alternate authz patterns.

---

## 3. Module boundaries (check)

```
aspen-dev (Paperclip/Hermes)     ← org, budgets, CE, personas
        │ issues / heartbeats only
        ▼
AspenOS product surface
  ├── core: agent loop, policy, envelopes, health, bus interfaces, safety
  ├── plugins: swarm-manager, edge-rrm (+ DualHumanGate), langgraph-worker,
  │            memory, dashboard/Sentinel surfaces, gatekeeper (target plugin/core-edge)
  └── drivers: MQTT / OPC-UA / ROS2 (last mile)
        │
        ▼
Hardware / sim (ASPEN_SIM=1 · plant-range status: sim_only)
```

**Boundary violations this period:** none observed.

**Placement notes:**

- Gatekeeper shim correctly lives as **dev prototype** under monorepo `src/python/gatekeeper/` (PACKAGES.md Dev-only until production path chosen: prefer edge-adjacent plugin, not Paperclip).
- G8 DualHumanGate remains in **edge-rrm** (correct).
- Paperclip must **not** become plant mission scheduler (ADR-0005 + H-018 still required).

**Sticky risks:**

1. Dual mission schedulers (Paperclip + LangGraph/swarm arming plant work) — promote H-018 when capacity  
2. Monorepo `services/fleet.py` dual-publish legacy while grove packages speak `aspen.*`  
3. ASP-499: fleet bus smoke cannot import `aspen_edge` in standalone checkout — packaging/CI boundary debt  

---

## 4. Agent-mesh & bus contracts

| Contract | Canonical | Status |
|----------|-----------|--------|
| Fleet register/HB/ops | `aspen.fleet.node.*`, `aspen.fleet.ops.status` | Packages + inventory |
| Missions | `aspen.fleet.mission.*` | Swarm package |
| Edge propose / authorize / command | `aspen.edge.<node>.*` | edge-rrm + G8 |
| Safety estop / clear | `aspen.safety.*` | Highest precedence |
| **Sentinel overview / audit / OSINT** | `aspen.sentinel.*` | **Contracted (ADR-0007)** |
| **Authz gate request/decision/grant** | `aspen.authz.*` | **Contracted (ADR-0007/0009)** |
| LangGraph | `aspen.worker.langgraph.job\|result` | propose_act out only |
| Starship agents | `starship.*` / `agnetic.*` | Legacy dual-publish → ADR-0011 |

**Decision (this review):**

- **Accept** ADR-0007/0008/0009 design.  
- **Keep** dual-publish; do **not** file ADR-0011 yet.  
- Prefer H-018 single plant scheduler guard + gatekeeper NATS wiring before any subject deletion.  
- Gatekeeper production path: short-lived scoped tokens; agents never hold raw NATS/ROS/Git plant credentials.

**Safety hard rule (unchanged):** G3 sim proofs + G8 control-path under `sim_only`. Physical/D1 remains ASP-418 / captain gate. ADR-0012 before G9.

---

## 5. Pending design decisions

| # | Decision | Recommendation | Urgency |
|---|----------|----------------|---------|
| D1 | ADR-0007/8/9 status | **Accepted this review** (done) | — |
| D2 | Publish Sentinel subjects to aspen-contracts GitHub | Flash/docs PR when free; monorepo is interim SoR | Medium |
| D3 | Gatekeeper runtime path (NATS nkey/JWT vs local proxy) | Prefer NATS JWT subject ACLs + dual-human for RED/BLACK; keep shim offline-capable | High (eng) |
| D4 | operator-of-record identity (ADR-0012) | File before G9; Matrix/`#aspen-authz` binds `human_id` only | High before physical |
| D5 | H-018 single plant scheduler guard | Spec + guard when Opencode/robotics capacity | High (eng) |
| D6 | dual-publish sunset (ADR-0011) | Wait consumer share / external pilot | Low under freeze |
| D7 | Physical bring-up ASP-418 | Stay backlog until captain + G9 + ADR-0012 | Deferred |
| D8 | BEL-237–242 agent surface (crash briefing, invoke preferred, cost panel, progressive AI, Buzz UI) | Unblocked by ADR-0009 design; implement **after** gatekeeper wire, Flash-only | Medium product |

---

## 6. Open issue map (architecture-relevant)

| Cluster | Issues | Disposition |
|---------|--------|-------------|
| This review | **ASP-530** | **Done** this heartbeat |
| ADR triad implement | BEL-195, BEL-196, BEL-215 | Design locked; eng tails open |
| Fleet smoke | ASP-499 | Blocked — path/import; Opencode |
| Daily/nightly ops | ASP-524, ASP-525 | Blocked disposition hygiene — not architecture redesign |
| LangGraph tails | BEL-207, BEL-208, BEL-209 | Lean Flash when free |
| Agent surface | BEL-237–242 | After gatekeeper wire |
| Package mesh epic | BEL-164 | In Progress — freeze lean |
| Physical cell | ASP-418 (if present) / prior Phase D | Deferred |

Paperclip open set is **thin** under freeze (mostly blocked hygiene + this review). Linear holds the deeper architecture backlog — correct SoR split.

---

## 7. Doc hygiene actions (this heartbeat)

1. Write this review: `docs/ops/WEEKLY_ARCHITECTURE_REVIEW_2026-08-31.md`  
2. Flip ADR-0007/0008/0009 → **Accepted** with ASP-530 citation  
3. Refresh `docs/adr/README.md` index statuses  
4. Point `docs/architecture/overview.md` last-review → this file; add Sentinel/authz subject families  
5. Fix stale “open ADR-0007 candidate” wording inside ADR-0007 body → ADR-0011  
6. Create Paperclip follow-up children for eng tails  
7. Comment Linear BEL-195 / BEL-196 / BEL-215 with accept + remaining work  

---

## 8. Follow-up tasks

1. **Gatekeeper NATS wire** — Runtime/Opencode: publish/consume `aspen.authz.*` + audit events from shim; no broad keys in adapter env for plant actions  
2. **aspen-contracts mirror** — packndeploy/docs: publish ADR-0007 subject table to AbsolutionAI/aspen-contracts  
3. **H-018 scheduler guard** — robotics/Opencode: single plant mission arm path (prior ASP-366 intent)  
4. **ASP-499 fleet smoke import** — Opencode: standalone checkout finds `aspen_edge`  
5. **ADR-0012 draft** — aspen plan-only before any G9  
6. No physical-cell / ACL widen under freeze  

---

## 9. Freeze-aware next 2 weeks

**Do**

- Wire gatekeeper design into one offline-capable path + unit proof  
- Close ASP-499 smoke so nightly packaging stays honest  
- Lean BEL-207 NATS lab consumer if broker available  
- Keep dual-human sim proofs green  
- Marketing/revenue work remains higher priority than greenfield OS when budgets tight  

**Don’t**

- Physical arm / G9 without captain + ADR-0012  
- Second mission scheduler  
- Delete `starship.*` / `agnetic.*` subjects yet  
- Expand Grok beyond architecture / CE fail / brand  
- Treat gatekeeper shim as production authz without audit JetStream  

---

## 10. Sign-off

Architecture **coherent**. Prior week’s SoR/ADR land risk is closed. This week **accepts ADR-0007, ADR-0008, and ADR-0009 (design)** and records the grove boundary: **aspen-dev orchestrates humans/agents; AspenOS/Sentinel own plant contracts and capability mediation.**

**Next weekly review:** ~2026-09-07 (or next ASP weekly ticket). Compare against this verdict table; expect gatekeeper wire progress and BEL-195/196/215 status movement.
