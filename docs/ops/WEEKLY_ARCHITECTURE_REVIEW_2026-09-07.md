# Weekly Architecture Review — 2026-09-07

**Issue:** ASP-563  
**Reviewer:** aspen (Architect)  
**Period:** 2026-08-31 → 2026-09-07 (delta vs ASP-530 / `WEEKLY_ARCHITECTURE_REVIEW_2026-08-31.md`)  
**SoR:** `docs/sor/MASTER_SPEC.md` (AspenGrove v4.0 — Three Organs)  
**Fiscal posture:** $100/mo LLM freeze (ASP $50 + BTH $50); sim-only fleet; wake-on-demand; Grok only for architecture gates

---

## 1. Executive verdict

| Area | Health | Delta vs 2026-08-31 |
|------|--------|---------------------|
| Product triad (OS / Sentinel / aspen-dev) | **Green (locked)** | Unchanged |
| Platform ADRs 0001–0006 | **Green** | Hold |
| ADR-0007 Sentinel/C2 NATS subjects | **Green (Accepted)** | **Re-land Accepted on tip** (ASP-530 accept was orphaned); ACLs + audit publisher wired (ASP-536/537) |
| ADR-0008 Package classification | **Green (Accepted)** | **Re-land Accepted**; PACKAGES.md SoR; mesh enforce still open |
| ADR-0009 Capability gatekeepers | **Green (Accepted + Phase 1)** | Design accept restored; **Phase 1 dual-human + audit live** (ASP-540); Phase 2 residual |
| ADR-0012 Operator-of-record | **Amber (Proposed)** | **Restored filed ADR** (was missing from tip); G9 blocker, plan-only |
| Agent mesh (Paperclip + Hermes) | **Green** | Wake-on-demand; ASP/BTH sibling freeze map holds |
| Fleet / swarm / RRM contracts | **Green (sim)** | G6–G8 hold; H-018 **done** (ASP-533 dual guard) |
| Dual-human act gate (H-016) | **Green (sim)** | EdgeRRM + gatekeeper distinct-principal path |
| LangGraph plugin (ADR-0005) | **Green/Amber** | Emit-side + scheduler busy-plant guards closed H-018 risk; BEL-207–209 still open |
| Memory tiering (ADR-0006) | **Green** | Accepted; T1 default under freeze |
| C11 sandbox (ADR-0010) | **Amber** | Keep native mandatory; no change this period |
| Bus dual-publish sunset (ADR-0011 candidate) | **Amber** | Monorepo still `starship.*`/`agnetic.*` only; **not** ready to file |
| Doc/git hygiene | **Amber → fixing** | **Primary finding:** ASP-530 accept + 08-31 review + ADR-0012 never reached `origin/master` tip; agents re-saw Proposed |
| Packaging / physical cell | **Deferred** | Freeze + ASP-418 / H-022–H-025 backlog |
| Nightly packaging check | **Green** | ASP-553/562 cadence live |

**Overall:** Architecture **decisions hold**. Material eng progress since last review: **H-018 closed**, **gatekeeper Phase 1**, **aspen.* NATS ACL/nkey hardening**, nightly packaging. The main residual architecture risk is **register drift** — Accepted ADRs and the prior weekly review lived only on orphan hermes commits. This cycle **re-materializes Accepted status + ADR-0012 + continuity reviews on the active line**.

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
| **ADR-0007** Sentinel + authz NATS | Additive `aspen.sentinel.*` / `aspen.authz.*` | **Accepted 2026-08-31 · reconfirmed ASP-563** | Mirror aspen-contracts; Sentinel consumers |
| **ADR-0008** Core / Plugin / Dev-only | Three-tier + PACKAGES.md | **Accepted 2026-08-31 · reconfirmed ASP-563** | Enforce `classification` in mesh / CI (H-019) |
| **ADR-0009** Capability gatekeepers | No broad keys; propose_act + dual-human | **Accepted (design+P1) · ASP-563** | Phase 2: token lifecycle + credential strip |
| ADR-0010 C11 (file `0001-c11-…`) | Spike sandbox; Python CP | Yes | Keep |
| ADR-0011 (candidate) | Sunset dual-publish | Not filed | Wait >50% `aspen.*` or external pilot |
| **ADR-0012** Operator-of-record binding | NATS `human_id` SoR; UI display-only | **Proposed** (restored) | Implement only pre-G9; keep Proposed |

### Acceptance / reconfirm rationale (this review)

1. **ADR-0007** — Subject table in `docs/FLEET.md`; ACL template covers `aspen.sentinel.*` / `aspen.authz.*` (ASP-536); audit publisher on `aspen.sentinel.audit.event` (ASP-537); gatekeeper fans decisions into audit. Linear BEL-196 design lock met in-repo; aspen-contracts mirror remains residual.
2. **ADR-0008** — `docs/PACKAGES.md` is classification SoR; cross-links ADR-0001/0004. Mesh metadata + CI “no Dev-only in prod images” still open (H-019).
3. **ADR-0009** — Design locked ASP-530; **Phase 1** (ASP-540) intercepts safety-adjacent propose_act, requires two distinct `human_id`s, refuses bare/single-human, audits every decision. Phase 2 (full token lifecycle, Hermes/Paperclip credential strip, immutable proxy) remains BEL-215 eng work — not a redesign.

### Register hygiene finding

ASP-530 flipped 0007/0008/0009 → Accepted and filed ADR-0012 + `WEEKLY_ARCHITECTURE_REVIEW_2026-08-31.md` on commit `af03ac5` / `13a7d7f`, but those commits **did not remain on `origin/master`**. Tip still showed **Proposed** and omitted ADR-0012 / 08-31 review. **Do not re-open design debate** — re-land status and continuity docs.

---

## 3. Module boundaries (check)

```
aspen-dev (Paperclip/Hermes)     ← org, budgets, CE, personas
        │ issues / heartbeats only
        ▼
AspenOS product surface
  ├── core: agent loop, policy, envelopes, health, bus interfaces, safety
  ├── plugins: swarm-manager, edge-rrm (+ DualHumanGate), langgraph-worker,
  │            memory, dashboard/Sentinel, gatekeeper (Phase 1 monorepo shim)
  └── drivers: MQTT / OPC-UA / ROS2 (last mile)
        │
        ▼
Hardware / sim (ASPEN_SIM=1 · plant-range status: sim_only)
```

**Boundary violations this period:** none observed.

**Placement notes:**

- Gatekeeper Phase 1 lives under monorepo `src/python/gatekeeper/` — still **dev/prototype path** per PACKAGES.md until production packaging chooses edge-adjacent plugin vs core-edge binary. Correct: **not** inside Paperclip.
- G8 DualHumanGate remains in **edge-rrm** (correct).
- H-018 dual guard: emit-side `aspen-langgraph-worker` + scheduler-side `aspen-swarm-manager._busy_plants` — correct split; Paperclip stays org SoR only.

**Sticky risks (updated):**

1. ~~Dual mission schedulers~~ — **mitigated** ASP-533 (H-018 closed). Keep regression tests green.
2. Monorepo `services/fleet.py` still dual-publishes **only** `starship.*`/`agnetic.*` while grove packages speak `aspen.*` — bridge gap remains; do **not** delete dual-publish yet (ADR-0011 not ready).
3. Threat-model checklist lag: H-011/H-013 still marked open in `SECURITY_THREAT_MODEL_v2.2.md` despite ASP-536 nkey/aspen ACL work — **docs reconcile** follow-up.
4. Physical G9 path still blocked on H-022 vault + ADR-0012 binding implementation + captain PO.

---

## 4. Agent-mesh & bus contracts

| Contract | Canonical | Status |
|----------|-----------|--------|
| Fleet register/HB/ops | `aspen.fleet.node.*`, `aspen.fleet.ops.status` | Grove packages; monorepo still starship/agnetic |
| Missions | `aspen.fleet.mission.*` | Swarm + H-018 busy-plant |
| Edge propose / authorize / command | `aspen.edge.<node>.*` | edge-rrm + G8 |
| Safety estop / clear | `aspen.safety.*` | Highest precedence; dual authorize_clear |
| Sentinel overview / audit / OSINT | `aspen.sentinel.*` | **Contracted + audit pub**; dashboard consumer residual |
| Authz gate request/decision/grant | `aspen.authz.*` | **Gatekeeper Phase 1** |
| LangGraph jobs | `aspen.worker.langgraph.*` | propose_act-out; mission emit guarded |
| Starship agents | `starship.*` / `agnetic.*` | Legacy dual-publish monorepo |

**Decision (this review):** Keep dual-publish. Do **not** file ADR-0011. Prefer monorepo publishers to **add** `aspen.fleet.*` alongside dual (inventory update) before any sunset.

**Safety hard rule:** Unchanged. Sim-only until G9 checklist + captain gate. No physical arm under freeze.

---

## 5. Pending design decisions

| # | Decision | Recommendation | Urgency |
|---|----------|----------------|---------|
| D1 | Re-land Accepted ADR-0007/8/9 + ADR-0012 + weekly reviews on master | **Do now** (this PR) | **High** |
| D2 | ADR-0009 Phase 2 scope | Token lifecycle + credential strip + proxy; no redesign | High (eng) |
| D3 | BEL-196 aspen-contracts mirror | Publish subject rows when free; monorepo FLEET.md interim SoR | Medium |
| D4 | Sentinel consumers | Dashboard/HMI subscribe audit + overview | Medium |
| D5 | ADR-0011 dual-publish sunset | **Defer** until consumer share or external pilot | Low now |
| D6 | ADR-0012 implement | **Defer** until pre-G9; keep Proposed | High before physical only |
| D7 | H-019 Dev-only CI gate | Mesh/CI block Dev-only in prod images | Medium |
| D8 | Physical ASP-418 / H-022–025 | Stay backlog until captain $0 PO + G9 | Deferred |
| D9 | Threat model checklist vs ASP-536 | Mark H-011/H-013 progress honestly | Low–med docs |

---

## 6. Open issue map (architecture-relevant, live board)

| Cluster | Issues | Disposition |
|---------|--------|-------------|
| This review | ASP-563 | **Done** this heartbeat |
| Prior review | ASP-530 | Done (accept orphaned — repaired here) |
| Gatekeeper P1 | ASP-540 | **Done** |
| H-018 scheduler | ASP-366 / ASP-533 | **Done** |
| NATS aspen ACL | ASP-536 | **Done** |
| Gatekeeper Phase 2 | **new child** | Next lean eng (Auditor/Runtime) |
| Contracts mirror | BEL-196 residual | Keep In Progress; design locked |
| Gatekeeper Linear | BEL-215 | In Progress — P1 done, P2 open |
| Physical / G9 | ASP-432 (H-022), 433–435, ASP-418 | Backlog — freeze |
| ACL pivot | ASP-369 | Backlog |
| Data-diode recipe | ASP-368 | Backlog |
| Hardening medium | ASP-371–376, 436 | Backlog; Flash when free |
| Packaging private | ASP-383 | Blocked (cash flow) |
| Nightly packaging | ASP-562 cadence | Ops — leave |

---

## 7. Doc hygiene actions (this heartbeat)

1. **Re-apply Accepted** on ADR-0007, ADR-0008; **Accepted (design + Phase 1)** on ADR-0009 with ASP-563 reconfirm.  
2. **Restore** ADR-0012 (Proposed) + index row.  
3. **Restore** `WEEKLY_ARCHITECTURE_REVIEW_2026-08-31.md` for continuity.  
4. **Write** this review `WEEKLY_ARCHITECTURE_REVIEW_2026-09-07.md`.  
5. **Refresh** ADR index README (Accepted rows + open candidate 0011 only).  
6. **Refresh** `docs/architecture/overview.md` last-review pointer + authz/sentinel subject families.  
7. **Note** threat-model checklist lag (no full rewrite this cycle).

---

## 8. Follow-up tasks (Paperclip children)

1. **Gatekeeper Phase 2 (ADR-0009 / BEL-215 residual)** — token lifecycle, Hermes/Paperclip credential strip, immutable proxy; assign Auditor or Runtime; Flash-only.  
2. **aspen-contracts mirror (BEL-196 residual)** — publish ADR-0007 subject rows; packndeploy when free.  
3. **Sentinel audit/overview consumer** — Dashboard; subscribe `aspen.sentinel.audit.event` (+ overview when published).  
4. **H-019 Dev-only package CI gate** — packndeploy; align ADR-0008.  
5. **Threat model checklist reconcile** — Auditor docs-only; H-011/H-013 vs ASP-536 evidence.  
6. No physical-cell / G9 implementation under freeze.  
7. Do **not** recreate cancelled ASP sweeps (514/525/529/544/541/524/511).

---

## 9. Freeze-aware next 2 weeks

**Do**

- Merge this docs PR so worktrees stop re-discovering Proposed ADRs  
- One Flash ticket at a time: prefer Gatekeeper Phase 2 or H-019 over greenfield  
- Keep dual-human + H-018 + fleet-bus smokes green  
- Keep nightly packaging cadence  

**Don’t**

- Physical arm / ASP-418 without captain gate  
- File ADR-0011 sunset or delete dual-publish  
- Implement ADR-0012 binding before G9 program starts  
- Widen plant-edge→alpha ACL (ASP-369) without threat review  
- Expand Grok beyond architecture gates  
- Unarchive ABSA/Content or wake ABS  

---

## 10. Sign-off

Architecture **coherent**. Safety control path advanced (H-018 closed, gatekeeper Phase 1, aspen ACL). Primary work this cycle is **register truth repair** (Accepted ADRs + ADR-0012 + weekly continuity on the active line) and **named Phase 2 follow-ups** — not redesigning the grove.

**Next weekly review:** ~2026-09-14 (or next ASP weekly ticket). Compare against this verdict table; confirm `origin/master` contains Accepted ADR-0007..0009, ADR-0012 Proposed, and this file.
