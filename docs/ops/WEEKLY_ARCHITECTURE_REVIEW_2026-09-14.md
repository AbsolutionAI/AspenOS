# Weekly Architecture Review — 2026-09-14

**Issue:** ASP-595  
**Reviewer:** aspen (Architect)  
**Period:** 2026-09-07 → 2026-09-14 (delta vs ASP-563 / `WEEKLY_ARCHITECTURE_REVIEW_2026-09-07.md`)  
**SoR:** `docs/sor/MASTER_SPEC.md` (AspenGrove v4.0 — Three Organs)  
**Fiscal posture:** $100/mo LLM freeze (ASP $50 + BTH $50); sim-only fleet; wake-on-demand; Grok only for architecture gates

---

## 1. Executive verdict

| Area | Health | Delta vs 2026-09-07 |
|------|--------|---------------------|
| Product triad (OS / Sentinel / aspen-dev) | **Green (locked)** | Unchanged |
| Platform ADRs 0001–0006 | **Green** | Hold |
| ADR-0007 Sentinel/C2 NATS subjects | **Green (Accepted)** | Audit **consumer** + dashboard routes landed (ASP-580/566 lineage); overview producer still open |
| ADR-0008 Package classification | **Green (Accepted)** | **H-019 CI gate live** (`check-no-devonly-in-prod.sh` + CI + nightly §16; ASP-574/567) |
| ADR-0009 Capability gatekeepers | **Green (Accepted + P1 + P2)** | **Phase 2 done** (ASP-564): token lifecycle, credential-strip proxy, SafetySubjectEnforcer |
| ADR-0012 Operator-of-record | **Amber (Proposed)** | Hold — pre-G9 only; no implement under freeze |
| Agent mesh (Paperclip + Hermes) | **Green** | Lean board (3 open ASP); wake-on-demand holds |
| Fleet / swarm / RRM contracts | **Green (sim)** | H-018 hold; dual-human hold; sim-only |
| Dual-human act gate (H-016) | **Green (sim)** | EdgeRRM + monorepo gatekeeper P1+P2 |
| LangGraph plugin (ADR-0005) | **Green/Amber** | Emit + busy-plant guards hold; BEL-207–209 lean when free |
| Memory tiering (ADR-0006) | **Green** | T1 default; ingest hooks compound notes present |
| C11 sandbox (ADR-0010) | **Amber** | Nightly known fail: p50 > 2ms HW-dependent only |
| Bus dual-publish sunset (ADR-0011 candidate) | **Amber** | Monorepo `services/fleet.py` still `starship.*`/`agnetic.*` only; **not** ready to file |
| Doc/git hygiene | **Green** | ASP-563 accept + ADR-0012 **on `origin/master`** (`dfd0933` / #38) — prior orphan risk closed |
| Packaging / physical cell | **Deferred** | Freeze + ASP-418 / H-022–H-025 backlog |
| Nightly packaging check | **Green (ops)** | ASP-594 2026-09-14 **PASS** (107/1 known C11); sticky ASP-579 `blocked` is process debt, not architecture fail |

**Overall:** Architecture **decisions hold and implementation caught up**. Material eng progress this week: **Gatekeeper Phase 2**, **H-019 Dev-only isolation gate**, **Sentinel audit consumer**, register truth repair **merged**. Residual architecture risk shifts from “ADR status drift” to **bus prefix bridge** (monorepo still not emitting `aspen.fleet.*`) and **pre-G9 binding** (ADR-0012 still Proposed). No redesign required.

---

## 2. ADR register

| ADR | Decision | Still valid? | Action |
|-----|----------|--------------|--------|
| ADR-0001 Packaging | Grove layers, MIT/Apache, AbsolutionAI org | Yes | Keep |
| ADR-0002 Swarm/RRM | propose_act only; human arm; no joint stream from C2 | Yes — **hard** | Keep sim-only |
| ADR-0003 Bus contracts | Prefer `aspen.*`; envelope + G8 authorize | Yes | Keep |
| ADR-0004 Light core | Kernel vs plugins | Yes | Align catalog with ADR-0008 |
| ADR-0005 LangGraph | Cognitive plugin; Paperclip stays SoR | Yes | Lean BEL-207–209 when free |
| ADR-0006 Memory tiering | T1 LanceDB/SQLite; optional T2 PG+AGE | Yes (Accepted) | No PG under freeze |
| **ADR-0007** Sentinel + authz NATS | Additive `aspen.sentinel.*` / `aspen.authz.*` | **Accepted** | aspen-contracts mirror residual; overview producer residual |
| **ADR-0008** Core / Plugin / Dev-only | Three-tier + PACKAGES.md | **Accepted** | **H-019 enforced** in CI/nightly |
| **ADR-0009** Capability gatekeepers | No broad keys; propose_act + dual-human | **Accepted (design + P1 + P2)** · ASP-595 | Phase 3: durable token store (Redis/PG) — backlog under freeze |
| ADR-0010 C11 (file `0001-c11-…`) | Spike sandbox; Python CP | Yes | Keep; accept HW p50 variance on this host |
| ADR-0011 (candidate) | Sunset dual-publish | Not filed | Wait monorepo **adds** `aspen.fleet.*` + >50% consumers or external pilot |
| **ADR-0012** Operator-of-record binding | NATS `human_id` SoR; UI display-only | **Proposed** | Implement only pre-G9; keep Proposed |

### Acceptance / reconfirm rationale (this review)

1. **ADR-0009 Phase 2** — ASP-564 delivered token issue/consume/refresh/expire/cleanup, `GatekeeperProxy`/`NATSAgentProxy` credential strip, and `SafetySubjectEnforcer` (77 Phase 2 + 43 Phase 1 tests). Design unchanged. Mark **Accepted (design + Phase 1 + Phase 2)**. Residual is **ops durability** (in-memory `TOKEN_REGISTRY`), not a redesign — track as Phase 3 backlog.
2. **ADR-0008 / H-019** — `scripts/check-no-devonly-in-prod.sh` parses PACKAGES.md Dev-only list, scans production surfaces, wired in CI `security-devonly-isolation` and nightly §16 (ASP-574; earlier false-done ASP-567 corrected). Threat-model checklist reconciled this cycle.
3. **ADR-0007 consumers** — monorepo Sentinel audit consumer + `/api/sentinel/audit*` routes closed the consumer residual from ASP-563. `aspen.sentinel.fleet.overview` producer still not live (dashboard notes). aspen-contracts package mirror still residual (BEL-196).

### Register hygiene finding (closed)

ASP-563 re-land of Accepted 0007–0009 + ADR-0012 + weekly continuity **is on `origin/master`**. Tip no longer reverts to Proposed. **No further register repair required this cycle.**

---

## 3. Module boundaries (check)

```
aspen-dev (Paperclip/Hermes)     ← org, budgets, CE, personas
        │ issues / heartbeats only
        ▼
AspenOS product surface
  ├── core: agent loop, policy, envelopes, health, bus interfaces, safety
  ├── plugins: swarm-manager, edge-rrm (+ DualHumanGate), langgraph-worker,
  │            memory, dashboard/Sentinel consumer, gatekeeper (monorepo shim P1+P2)
  └── drivers: MQTT / OPC-UA / ROS2 (last mile)
        │
        ▼
Hardware / sim (ASPEN_SIM=1 · plant-range status: sim_only)
```

**Boundary violations this period:** none observed.

**Placement notes:**

- Gatekeeper P1+P2 remains under monorepo `src/python/gatekeeper/` — still **dev/prototype path** per PACKAGES.md Dev-only examples (`minimal_shim`); correct: **not** inside Paperclip; H-019 deliberately does **not** ban source presence, only production packaging surfaces.
- G8 DualHumanGate remains in **edge-rrm** (correct).
- Sentinel audit consumer in monorepo `src/python/sentinel/` + dashboard routes — correct Sentinel organ surface.
- H-018 dual guard split unchanged and correct.

**Sticky risks (updated):**

1. ~~Register drift (Accepted ADRs orphaned)~~ — **closed** on master.
2. ~~Gatekeeper Phase 2 residual~~ — **closed** (ASP-564); Phase 3 durable store only.
3. ~~H-019 no CI~~ — **closed** (ASP-574).
4. Monorepo `services/fleet.py` still dual-publishes **only** `starship.*`/`agnetic.*` while grove packages + gatekeeper speak `aspen.*` — bridge gap remains; do **not** delete dual-publish (ADR-0011 not ready). Prefer **add** `aspen.fleet.*` alongside dual before any sunset.
5. Physical G9 path still blocked on H-022 vault + ADR-0012 binding + captain PO.
6. Gatekeeper in-memory token registry — acceptable under freeze/sim; not production multi-node ready.

---

## 4. Agent-mesh & bus contracts

| Contract | Canonical | Status |
|----------|-----------|--------|
| Fleet register/HB/ops | `aspen.fleet.node.*`, `aspen.fleet.ops.status` | Grove packages; monorepo still starship/agnetic |
| Missions | `aspen.fleet.mission.*` | Swarm + H-018 busy-plant |
| Edge propose / authorize / command | `aspen.edge.<node>.*` | edge-rrm + G8 |
| Safety estop / clear | `aspen.safety.*` | Highest precedence; dual authorize_clear |
| Sentinel overview / audit / OSINT | `aspen.sentinel.*` | **Audit pub + consumer**; overview producer residual |
| Authz gate request/decision/grant | `aspen.authz.*` | **Gatekeeper P1 + P2** |
| LangGraph jobs | `aspen.worker.langgraph.*` | propose_act-out; mission emit guarded |
| Starship agents | `starship.*` / `agnetic.*` | Legacy dual-publish monorepo |

**Decision (this review):** Keep dual-publish. Do **not** file ADR-0011. Next eng step when free: monorepo publishers **add** `aspen.fleet.*` (and matching shape) alongside dual — inventory in `docs/ops/FLEET_SUBJECT_PUBLISHERS.md`.

**Safety hard rule:** Unchanged. Sim-only until G9 checklist + captain gate. No physical arm under freeze.

**Agent mesh:** ASP open set is lean (`ASP-595` this review, `ASP-383` packaging private blocked on cash flow, sticky `ASP-579` nightly parent blocked while child cadence ASP-594+ runs green). Do not thrash ASP-579 this cycle; ops PASS is the architecture signal.

---

## 5. Pending design decisions

| # | Decision | Recommendation | Urgency |
|---|----------|----------------|---------|
| D1 | ADR-0009 Phase 2 status flip | **Accept P2 this review** (docs) | **High — done here** |
| D2 | H-019 threat-model checklist | **Mark closed** vs ASP-574 evidence | **High — done here** |
| D3 | Monorepo add `aspen.fleet.*` alongside dual | Lean eng when free; prep ADR-0011 | Medium |
| D4 | Sentinel `fleet.overview` producer | Dashboard/ops when free | Medium |
| D5 | BEL-196 aspen-contracts mirror | Publish subject rows when free | Medium |
| D6 | ADR-0011 dual-publish sunset | **Defer** until consumer share or external pilot | Low now |
| D7 | ADR-0012 implement | **Defer** until pre-G9 | High before physical only |
| D8 | Gatekeeper Phase 3 durable tokens | Backlog under freeze | Low |
| D9 | Physical ASP-418 / H-022–025 | Stay backlog until captain $0 PO + G9 | Deferred |
| D10 | H-014 AppArmor deploy path | VERIFY-only remains; no `aa-enforce` without captain | Low–med docs/ops |

---

## 6. Open issue map (architecture-relevant, live board)

| Cluster | Issues | Disposition |
|---------|--------|-------------|
| This review | ASP-595 | **Done** this heartbeat |
| Prior review | ASP-563 | Done — master merge confirmed |
| Gatekeeper P1 | ASP-540 | Done |
| Gatekeeper P2 | ASP-564 | **Done** |
| H-019 Dev-only CI | ASP-574 / ASP-567 | **Done** |
| Sentinel consumer | ASP-580 lineage / monorepo | **Done** (audit path) |
| H-018 scheduler | ASP-533 | Done |
| NATS aspen ACL | ASP-536 | Done |
| Contracts mirror | BEL-196 residual | Keep — design locked |
| Gatekeeper Linear | BEL-215 | P1+P2 done; Phase 3 residual only |
| Physical / G9 | ASP-432 (H-022), 433–435, ASP-418 | Backlog — freeze |
| Packaging private | ASP-383 | Blocked (cash flow) |
| Nightly packaging | ASP-594 cadence / ASP-579 sticky | Ops green; process cleanup optional |
| Follow-ups | **new children below** | Lean Flash when free |

---

## 7. Doc hygiene actions (this heartbeat)

1. **Write** this review `WEEKLY_ARCHITECTURE_REVIEW_2026-09-14.md`.  
2. **Flip ADR-0009** → Accepted (design + Phase 1 + Phase 2); residual = Phase 3 durable store.  
3. **Refresh** ADR index README + architecture overview last-review pointer.  
4. **Reconcile** threat-model H-019 (+ related rows) to CLOSED vs ASP-574.  
5. **Note** FLEET_SUBJECT_PUBLISHERS reviewed date (no subject deletions).  
6. Create **lean** Paperclip follow-ups only (no physical / no ADR-0011 file / no cancelled-sweep recreate).

---

## 8. Follow-up tasks (Paperclip children)

1. **Monorepo fleet triple-publish (prep ADR-0011)** — `services/fleet.py` add `aspen.fleet.*` (ADR-0003 shapes) **alongside** existing dual; update `FLEET_SUBJECT_PUBLISHERS.md`; no deletions. Assign OpenCode when free; Flash-only.  
2. **Sentinel fleet.overview producer** — publish aggregate overview on `aspen.sentinel.fleet.overview`; Dashboard consumer already expects it.  
3. **aspen-contracts mirror (BEL-196 residual)** — packndeploy when free; monorepo FLEET.md remains interim SoR.  
4. **Gatekeeper Phase 3 (optional)** — durable token registry; **backlog under freeze** — do not start unless multi-node sim needs it.  
5. No physical-cell / G9 / ADR-0012 implement under freeze.  
6. Do **not** recreate cancelled ASP sweeps (514/525/529/544/541/524/511).  
7. Do **not** `aa-enforce` live AppArmor without captain approval.

---

## 9. Freeze-aware next 2 weeks

**Do**

- Merge this docs PR so tip points at 2026-09-14 review + ADR-0009 P2 accept  
- One Flash ticket at a time: prefer monorepo `aspen.fleet.*` add **or** overview producer over greenfield  
- Keep dual-human + H-018 + gatekeeper P1/P2 + H-019 + nightly packaging green  
- Keep board lean; cycle unblocked work only  

**Don’t**

- Physical arm / ASP-418 without captain gate  
- File ADR-0011 sunset or delete dual-publish  
- Implement ADR-0012 binding before G9 program starts  
- Widen plant-edge→alpha ACL without threat review  
- Expand Grok beyond architecture gates  
- Unarchive ABSA/Content or wake ABS  
- Live host policy enforce (`aa-enforce`) without captain  

---

## 10. Sign-off

Architecture **coherent and advanced**. Safety control path complete through gatekeeper Phase 2; supply-chain Dev-only gate enforced; Sentinel audit path is two-sided (pub + consumer); ADR register truth holds on master. Primary work this cycle is **status truth** (P2 accept + H-019 checklist) and **named lean bridge follow-ups** — not redesigning the grove.

**Next weekly review:** ~2026-09-21 (or next ASP weekly ticket). Compare against this verdict table; confirm tip contains ADR-0009 P2 accept and this file.
