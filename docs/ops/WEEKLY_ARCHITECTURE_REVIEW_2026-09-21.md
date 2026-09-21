# Weekly Architecture Review — 2026-09-21

**Issue:** ASP-627  
**Reviewer:** aspen (Architect)  
**Period:** 2026-09-07 → 2026-09-21 (delta vs ASP-563 / `WEEKLY_ARCHITECTURE_REVIEW_2026-09-07.md`)  
**Note:** ASP-595 (2026-09-14) completed on board without a continuity review file — this review covers the full two-week gap.  
**SoR:** `docs/sor/MASTER_SPEC.md` (AspenGrove v4.0 — Three Organs)  
**Fiscal posture:** $100/mo LLM freeze (ASP $50 + BTH $50); sim-only fleet; wake-on-demand; Grok only for architecture gates; **Grok Build terminated** (Captain 2026-09-18)

---

## 1. Executive verdict

| Area | Health | Delta vs 2026-09-07 |
|------|--------|---------------------|
| Product triad (OS / Sentinel / aspen-dev) | **Green (locked)** | Unchanged |
| Platform ADRs 0001–0006 | **Green** | Hold |
| ADR-0007 Sentinel/C2 NATS subjects | **Green (Accepted)** | **Overview producer + consumer path closed** (ASP-597 / ASP-566); aspen-contracts mirror **done** (ASP-565) |
| ADR-0008 Package classification | **Green (Accepted)** | **H-019 Dev-only CI gate done** (ASP-567/574); nightly §16 green |
| ADR-0009 Capability gatekeepers | **Green (Accepted P1+P2)** | **Phase 2 complete** (ASP-564); rate-limit residual closed (ASP-607) |
| ADR-0012 Operator-of-record | **Amber (Proposed)** | Still correct to keep Proposed until pre-G9 |
| Agent mesh (Paperclip + Hermes) | **Green** | One-wake ASP cadence; Aider QA + Auditor; Grok Build gone |
| Fleet / swarm / RRM contracts | **Green (sim)** | **H-021 ACL pivot removed** (ASP-369 tip); dual-human + H-018 hold |
| Dual-human act gate (H-016) | **Green (sim)** | Hold |
| LangGraph plugin (ADR-0005) | **Green/Amber** | H-018 guards hold; BEL-207–209 still lean backlog |
| Memory tiering (ADR-0006) | **Green** | T1 default under freeze |
| C11 sandbox (ADR-0010) | **Amber** | Nightly C11 p50 still ~3.2 ms (hw-dep known); not packaging fail |
| Bus dual-publish sunset (ADR-0011 candidate) | **Amber → improving** | **Monorepo now emits `aspen.fleet.*` alongside dual** (ASP-596); **do not file sunset yet** |
| Update integrity (F-013/F-014) | **Green** | Model digest pin (ASP-377) + signed-package gate (ASP-378) on tip; nightly §§21–22 PASS |
| Tool anomaly (H-015) | **Green (impl)** | Fail-open detector on tip (ASP-379); board disposition lag |
| Packaging / physical cell | **Deferred** | Freeze + ASP-418 / G9; ADR-0012 still gate |
| Nightly packaging check | **Green** | ASP-626 2026-09-21 **PASS** (148/149; C11 p50 known) |
| Doc/git hygiene | **Green** | ASP-563 re-land held on `origin/master`; no new orphan-accept risk this cycle |

**Overall:** Architecture **decisions hold and implementation caught up** to the 09-07 follow-up list. Nearly every ASP-563 child (Phase 2, H-019, Sentinel consumer/producer, contracts mirror, threat-model reconcile, monorepo `aspen.fleet.*` bridge) is **done on tip**. Residual architecture work is **narrow**: keep ADR-0012 Proposed, defer ADR-0011 sunset, local-proof-close stuck board issues whose code already landed, and decide **gatekeeper packaging placement** when production images matter.

---

## 2. ADR register

| ADR | Decision | Still valid? | Action |
|-----|----------|--------------|--------|
| ADR-0001 Packaging | Grove layers, MIT/Apache, AbsolutionAI org | Yes | Keep |
| ADR-0002 Swarm/RRM | propose_act only; human arm; no joint stream from C2 | Yes — **hard** | Keep sim-only |
| ADR-0003 Bus contracts | Prefer `aspen.*`; envelope + G8 authorize | Yes | Monorepo bridge improved (ASP-596) |
| ADR-0004 Light core | Kernel vs plugins | Yes | Gatekeeper still monorepo shim (see D3) |
| ADR-0005 LangGraph | Cognitive plugin; Paperclip stays SoR | Yes | Lean BEL-207–209 when free |
| ADR-0006 Memory tiering | T1 LanceDB/SQLite; optional T2 PG+AGE | Yes | No PG under freeze |
| **ADR-0007** Sentinel + authz NATS | Additive `aspen.sentinel.*` / `aspen.authz.*` | **Accepted** · reconfirm ASP-627 | Contracts mirror done; overview producer live |
| **ADR-0008** Core / Plugin / Dev-only | Three-tier + PACKAGES.md | **Accepted** · reconfirm ASP-627 | H-019 CI gate live |
| **ADR-0009** Capability gatekeepers | No broad keys; propose_act + dual-human | **Accepted (design + P1 + P2)** · ASP-627 | Design complete for monorepo path |
| ADR-0010 C11 (file `0001-c11-…`) | Spike sandbox; Python CP | Yes | Keep; p50 hw-debt |
| ADR-0011 (candidate) | Sunset dual-publish | **Not filed** | Wait consumer share / external pilot |
| **ADR-0012** Operator-of-record binding | NATS `human_id` SoR; UI display-only | **Proposed** | Implement only pre-G9; **do not Accept this cycle** |

### Acceptance / reconfirm rationale (this review)

1. **ADR-0007** — ASP-565 mirrored subjects to aspen-contracts; ASP-597 publishes `aspen.sentinel.fleet.overview`; ASP-566 consumer path for audit (+ overview). BEL-196 design lock satisfied in-repo + contracts residual closed.
2. **ADR-0008** — `scripts/check-no-devonly-in-prod.sh` + nightly H-019 section PASS (ASP-567/574). Classification SoR remains `docs/PACKAGES.md`.
3. **ADR-0009** — Phase 2 (ASP-564) delivered token lifecycle, credential-strip proxy, safety subject enforcer; ASP-607 added per-agent rate limits. Status flips to **Accepted (design + Phase 1 + Phase 2)**. Remaining work is **packaging placement / production durability** (in-memory token registry → Redis/PG later), not redesign.
4. **ADR-0012** — Still the correct G9 gate. Free-string `human_id` is fine under `ASPEN_SIM=1`. **Keep Proposed.**

---

## 3. Module boundaries (check)

```
aspen-dev (Paperclip/Hermes)     ← org, budgets, CE, personas
        │ issues / heartbeats only
        ▼
AspenOS product surface
  ├── core: agent loop, policy, envelopes, health, bus interfaces, safety
  ├── plugins: swarm-manager, edge-rrm (+ DualHumanGate), langgraph-worker,
  │            memory, dashboard/Sentinel, gatekeeper (P1+P2 monorepo shim),
  │            tool-anomaly (fail-open over audit)
  └── drivers: MQTT / OPC-UA / ROS2 (last mile)
        │
        ▼
Hardware / sim (ASPEN_SIM=1 · plant-range status: sim_only)
```

**Boundary violations this period:** none observed.

**Placement notes:**

- Gatekeeper P1+P2 remains under monorepo `src/python/gatekeeper/` — correct as **dev/prototype** until packaging chooses edge-adjacent plugin vs core-edge binary (ADR-0004/0008). Not inside Paperclip.
- Tool anomaly detector lives under `src/python/sentinel/` + CLI — correct Sentinel organ; fail-open (investigation lead, not deny path).
- G8 DualHumanGate remains in **edge-rrm** (correct).
- Plugin local-path `update()` (ASP-620) stays package-mesh / monorepo plugin path — no org-scheduler bleed.

**Sticky risks (updated):**

1. Dual mission schedulers — **still mitigated** ASP-533; keep regression green.
2. Dual-publish — monorepo **adds** `aspen.fleet.*` (ASP-596) but still dual-publishes `starship.*`/`agnetic.*`. Sunset **not** ready (ADR-0011 not filed).
3. Threat-model checklist — largely reconciled (ASP-568 + later F/H closes). Keep biweekly refresh cadence.
4. Physical G9 — still blocked on vault/H-022, **ADR-0012 Accept + bind proof**, captain PO.
5. **Board lag:** ASP-369 and ASP-379 code on tip while issues stayed `in_progress` after Auditor `plan_only` exhaustion — architecture review local-proof closes them.

---

## 4. Agent-mesh & bus contracts

| Contract | Canonical | Status |
|----------|-----------|--------|
| Fleet register/HB/ops | `aspen.fleet.node.*`, `aspen.fleet.ops.status` | **Monorepo + grove**; legacy dual retained |
| Missions | `aspen.fleet.mission.*` | Swarm + H-018 busy-plant |
| Edge propose / authorize / command | `aspen.edge.<node>.*` | edge-rrm + G8 |
| Safety estop / clear | `aspen.safety.*` | Highest precedence; dual authorize_clear |
| Sentinel overview / audit / OSINT | `aspen.sentinel.*` | **Producer + consumer paths closed** |
| Authz gate request/decision/grant | `aspen.authz.*` | Gatekeeper P1+P2 |
| LangGraph jobs | `aspen.worker.langgraph.*` | propose_act-out; mission emit guarded |
| Starship agents | `starship.*` / `agnetic.*` | Legacy dual-publish monorepo |
| Cross-plant ACL | fleet policy | **edge→alpha denied** (H-021/ASP-369) |

**Decision (this review):** Keep dual-publish. Prefer measuring `aspen.*` consumer share before filing ADR-0011. Do **not** delete dual-publish.

**Safety hard rule:** Unchanged. Sim-only until G9 checklist + captain gate. No physical arm under freeze. Grok Build **terminated** — no sim-prod lane via that agent.

---

## 5. Pending design decisions

| # | Decision | Recommendation | Urgency |
|---|----------|----------------|---------|
| D1 | ADR-0009 status after Phase 2 | **Accept P1+P2** (this PR) | **High** (register truth) |
| D2 | ADR-0012 Accept? | **No** — keep Proposed until pre-G9 bind program | High before physical only |
| D3 | Gatekeeper packaging placement | **Decided ASP-628:** plugin `aspen-gatekeeper`, profile default ON for actuators | Done (docs) |
| D4 | ADR-0011 dual-publish sunset | **Defer**; optional inventory of consumer share | Low now |
| D5 | Live JetStream subject for tool-anomaly findings | Optional ops page; fail-open detector already useful offline | Low |
| D6 | Physical ASP-418 / H-022–025 | Stay backlog until captain $0 PO + G9 | Deferred |
| D7 | BEL-215 Linear status | Design + monorepo eng complete — mark Done/In Review on Linear when human free | Low docs |
| D8 | C11 p50 threshold | Accept hw-dep deviation or revisit ADR-0010 SLOs off freeze | Deferred |

---

## 6. Open issue map (architecture-relevant, live board at review)

| Cluster | Issues | Disposition |
|---------|--------|-------------|
| This review | **ASP-627** | **Done** this heartbeat |
| Prior reviews | ASP-563, ASP-595 | Done (595 missing file — gap closed here) |
| ASP-563 children | 564 P2, 565 contracts, 566 consumer, 567/574 H-019, 568 threat docs, 596 aspen.fleet bridge, 597 overview | **All done** |
| H-021 ACL | ASP-369 | Code on tip (`201933f`) — **local-proof → done** |
| H-015 anomaly | ASP-379 | Code on tip (`0848280`) — **local-proof → done** |
| Private packaging | ASP-383 | **Blocked** (cash flow) — leave |
| Physical / G9 | ASP-418, H-022–025 lineage | Backlog — freeze |
| Grok Build park | ASP-516 etc. | Obsolete; agent terminated |
| Nightly packaging | ASP-626 | Done PASS |

---

## 7. Doc hygiene actions (this heartbeat)

1. Write `WEEKLY_ARCHITECTURE_REVIEW_2026-09-21.md` (this file).  
2. Flip **ADR-0009** → Accepted (design + Phase 1 + Phase 2) with ASP-627 reconfirm.  
3. Refresh ADR index README (0009 row + latest weekly pointer).  
4. Refresh `docs/architecture/overview.md` last-review pointer + gatekeeper/anomaly notes.  
5. Local-proof close ASP-369 and ASP-379 on Paperclip with tip evidence.  
6. Do **not** Accept ADR-0012; do **not** file ADR-0011.

---

## 8. Follow-up tasks

1. **Gatekeeper production packaging placement (ADR-0004/0008/0009 residual)** — **Decided ASP-628:** production target = plugin `aspen-gatekeeper` (profile default ON for actuator plants); not a second core-edge binary; monorepo path remains source until extract; durable token backend later. Plan: `docs/plans/ASP-628-gatekeeper-packaging.md`.  
2. **ADR-0011 readiness inventory (optional)** — measure share of consumers on `aspen.*` vs legacy dual; file ADR only if >50% or external pilot.  
3. **ADR-0012** — no eng until pre-G9; keep Proposed.  
4. **Linear BEL-215 / BEL-196** — human status align to Done when convenient (design locked + monorepo residual closed).  
5. No physical-cell / G9 implementation under freeze.  
6. Do **not** recreate cancelled ASP sweeps; do **not** wake Grok Build.

---

## 9. Freeze-aware next 2 weeks

**Do**

- Merge this docs PR so ADR-0009 register matches tip eng  
- Prefer Flash hardening leftovers / packaging hygiene one ticket at a time  
- Keep dual-human + H-018 + fleet ACL + nightly packaging green  
- Close board lag immediately when tip already has the fix (local-proof pattern)

**Don’t**

- Physical arm / ASP-418 without captain gate  
- File ADR-0011 sunset or delete dual-publish  
- Accept/implement ADR-0012 binding before G9 program  
- Re-open edge→alpha ACL  
- Expand Grok beyond architecture gates  
- Hire/wake Reflection Coach / Summarizer or Grok Build  
- Unarchive ABSA/Content or wake ABS  

---

## 10. Sign-off

Architecture **coherent and implementation-aligned**. The 09-07 follow-up backlog is largely **closed on tip**. This cycle’s architecture work is **register truth** (ADR-0009 P2 accept), **continuity review** (two-week gap including missing ASP-595 file), and **board hygiene** (369/379 local-proof). No redesign of the grove.

**Next weekly review:** ~2026-09-28 (or next ASP weekly ticket). Compare against this verdict table; confirm ADR-0009 shows P1+P2 Accepted on `origin/master`.
