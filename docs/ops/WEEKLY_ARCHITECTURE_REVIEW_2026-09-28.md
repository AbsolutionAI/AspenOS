# Weekly Architecture Review — 2026-09-28

**Issue:** ASP-676
**Reviewer:** aspen (Architect)
**Routine fire:** 2026-09-29T02:40Z (local date 2026-09-28)
**Period:** 2026-09-21 → 2026-09-28 (delta vs ASP-627 / `WEEKLY_ARCHITECTURE_REVIEW_2026-09-21.md`)
**Tree reviewed:** `origin/master` `e3b1d59` (GitHub fetch failed at workspace prep; this review re-checked `origin/master` and live Paperclip)
**SoR:** `docs/sor/MASTER_SPEC.md` (AspenGrove v4.0 — Three Organs)
**Fiscal posture:** unchanged. ASP $50 + BTH $50. Sim-only fleet. Wake-on-demand. Grok for architecture gates only. Grok Build stays terminated.

---

## 1. Executive verdict

| Area | Health | Delta vs 2026-09-21 |
|------|--------|---------------------|
| Product triad (OS / Sentinel / aspen-dev) | **Green (locked)** | Unchanged |
| Platform ADRs 0001–0006 | **Green** | Hold |
| ADR-0007 / 0008 / 0009 | **Green (Accepted)** | Hold. No redesign |
| ADR-0010 C11 | **Amber** | Nightly still 149/150, C11 p50 only. Not a packaging fail |
| ADR-0011 sunset candidate | **Amber** | Still not filed. No consumer-share measurement this week |
| ADR-0012 operator-of-record | **Amber (Proposed)** | Still correct. H-022 did not satisfy it |
| ADR-0013 worktree isolation | **Amber (split)** | **Policy live. Record not on master** |
| Agent mesh | **Green** | Isolation is on. Parallel routines are allowed. Do not hire Coach/Summarizer |
| Fleet / swarm / RRM | **Green (sim)** | Hold |
| Act gate | **Green (sim) + index gap** | H-022 vault gate and H-023 watchdog landed. Contract file was a dangling link — indexed this review |
| LangGraph (ADR-0005) | **Green/Amber** | Hold |
| Memory (ADR-0006) | **Green** | T1 only under freeze |
| Update integrity (F-014) | **Amber (CI)** | Gate exists. `verify-package-signature` fails before the suite: missing PyYAML |
| Packaging / physical cell | **Deferred** | ASP-418 / 370 / 435 / 650 still blocked |
| Nightly | **Green on branch, stale on master** | `NIGHTLY_LATEST.md` on master is the 2026-09-26 seed. Later nightlies updated their own branches |

**Overall:** Decisions from 09-21 still hold. This week’s architecture fact is a **register split**, not a redesign. Paperclip already runs AspenOS as `isolated_workspace` + `git_worktree`. The Accepted ADR that records that decision is on PR 45, not `origin/master`. Do not re-decide it. Land the record after the signature job can import its tests.

---

## 2. ADR register

| ADR | Decision | Still valid? | Action |
|-----|----------|--------------|--------|
| ADR-0001 Packaging | Grove layers, MIT/Apache | Yes | Keep |
| ADR-0002 Swarm/RRM | propose_act only; no joint stream from C2 | Yes — hard | Keep sim-only |
| ADR-0003 Bus + G8 | Prefer `aspen.*`; dual-human authorize | Yes | Index file now exists |
| ADR-0004 Light core | Kernel vs plugins | Yes | Gatekeeper stays monorepo shim until extract |
| ADR-0005 LangGraph | Cognitive plugin; Paperclip stays SoR | Yes | Hold |
| ADR-0006 Memory | T1 default; T2 optional | Yes | No PG under freeze |
| ADR-0007 Sentinel/C2 subjects | Additive `aspen.sentinel.*` / `aspen.authz.*` | Accepted | Keep |
| ADR-0008 Classification | core / plugin / dev-only | Accepted | H-019 gate stays |
| ADR-0009 Gatekeepers | No broad keys; P1+P2 accepted | Accepted | Packaging decision remains ASP-628 (done) |
| ADR-0010 C11 | Spike sandbox | Yes | p50 hw-debt. Do not retune the SLO this week |
| ADR-0011 (candidate) | Sunset dual-publish | **Not filed** | Still wait for consumer share or an external pilot |
| ADR-0012 OoR binding | NATS `human_id` is SoR; auth binding required before non-sim arm | **Proposed** | **Do not Accept.** H-022 is a durable approval row, not an authenticated principal |
| ADR-0013 Worktree isolation | Per-issue `git_worktree`; Hermes `.worktrees/hermes-*` does not count | **Accepted on `docs/asp-661-adr-0013` only** | Policy already matches the ADR JSON. Merge PR 45. Do not Accept again |

### ADR-0013 evidence (this review)

Live `GET /api/projects/2f2b9b10-cfc4-423a-8d6f-ea8e54303b7f` `executionWorkspacePolicy`:

- `enabled: true`
- `defaultMode: isolated_workspace`
- `allowIssueOverride: false`
- `workspaceStrategy.type: git_worktree`
- `baseRef: master`
- `branchTemplate: {{issue.identifier}}-{{slug}}`
- `worktreeParentDir: .paperclip/worktrees`

ASP-661 (decision) and ASP-664 (realization proof) are `done`. This issue’s own workspace is `git_worktree` at `.paperclip/worktrees/ASP-676-weekly-architecture-review`.

The record commit is `f801850` on `docs/asp-661-adr-0013`. PR: https://github.com/AbsolutionAI/AspenOS/pull/45. State: OPEN, MERGEABLE, checks UNSTABLE. Failure is not the ADR. Job `verify-package-signature` dies in `tests/conftest.py` with `ModuleNotFoundError: No module named 'yaml'`. The job installs `pytest` and not `pyyaml`. Sibling job `security-model-digests` already installs `pyyaml`.

Do not copy ADR-0013 into this branch. That duplicates PR 45 and will conflict. This review does not PATCH project policy again.

Stale sentence inside the ADR (fix on land, do not block land): it still says flock `3d88b1a` is not on `origin/master`. It is. `origin/master` is `e3b1d59`.

---

## 3. Module boundaries

```
aspen-dev (Paperclip/Hermes)     org, budgets, CE, personas
        │ issues / heartbeats only
        ▼
AspenOS product surface
  ├── core: agent loop, policy, envelopes, health, bus interfaces
  ├── safety: src/python/safety/estop_watchdog.py   ← H-023, not inside the agent loop
  ├── plugins: swarm-manager, edge-rrm, langgraph-worker, memory,
  │            dashboard/Sentinel, gatekeeper shim (+ vault_gate), tool-anomaly
  └── drivers: MQTT / OPC-UA / ROS2 (last mile)
        ▼
Hardware / sim (ASPEN_SIM=1 · plant-range sim_only until G9)
```

**Boundary violations this period:** none that change the grove.

**Placement, accepted this review:**

- H-022 vault gate stays in `src/python/gatekeeper/vault_gate.py`. Physical cell acts only. Estop stays on the plain dual-human path. `light-cell` skips the vault. That matches the code (`PHYSICAL_ACT_SUBJECTS` vs `SAFETY_SUBJECTS`).
- H-023 watchdog stays in `src/python/safety/`, outside the agent loop and outside edge-rrm. Independence is the point. Live GPIO remains an Aspen START, not this review.
- Gatekeeper packaging target remains plugin `aspen-gatekeeper` (ASP-628, done). Monorepo path is still the source.

**Sticky risk (no new ticket):** `src/python/services` shadows root `services/`, so `vault_gate.py` loads HITL by file path. Workaround is documented. Do not “fix” it inside a safety ticket.

---

## 4. Agent-mesh and bus contracts

| Contract | Canonical | Status |
|----------|-----------|--------|
| Execution workspace | Paperclip `isolated_workspace` + `git_worktree` | **Live.** Hermes session worktrees do not satisfy ADR-0013 |
| Fleet register/HB/ops | `aspen.fleet.*` | Monorepo still dual-publishes legacy. Sunset not ready |
| Missions | `aspen.fleet.mission.*` | Unchanged |
| Edge propose / authorize / command | `aspen.edge.<node>.*` | Unchanged |
| Safety estop / clear | `aspen.safety.*` | Dual clear. Watchdog is a second, independent latch — it does not replace bus estop |
| Authz | `aspen.authz.*` | Gatekeeper P1+P2. Vault row is additional for physical acts only |
| Sentinel | `aspen.sentinel.*` | Unchanged |
| LangGraph | `aspen.worker.langgraph.*` | propose_act out only |
| Cross-plant ACL | edge → alpha denied | Hold |

**Mesh roster (this wake):** Grok Build absent. Reflection Coach and Summarizer still `pending_approval` — do not approve. OpenCode running. Fast Coder idle. Aider idle. Auditor / packndeploy showed `process_lost` on a running row; that is a lost heartbeat, not a contract change.

Parallel routines (nightly, daily sweep, biweekly threat model, this review) are allowed now that trees are isolated. Same-issue double-invoke is still a checkout bug. Do not remove the ASP-659 flock.

**Git identity:** local `user.name` is no longer the `Your Name` placeholder ADR-0013 called out. It is `packndeploy`. Do not edit shared `.git/config` while other AspenOS heartbeats are committing.

---

## 5. Pending design decisions

| # | Decision | Recommendation | Urgency |
|---|----------|----------------|---------|
| D1 | Accept ADR-0012? | **No.** H-022 did not bind `human_id` to an authenticated operator | High only before G9 |
| D2 | File ADR-0011? | **No.** No new consumer-share data | Low |
| D3 | Re-accept ADR-0013? | **No.** Land PR 45. Policy is already the decision | **High (register truth)** |
| D4 | Retune C11 p50? | **No** | Deferred |
| D5 | Live GPIO / physical arm? | **No.** ASP-418 and siblings stay blocked | Deferred |
| D6 | Signature job red on docs PRs | **Yes, fix the dep.** Not a crypto redesign | **High (blocks D3)** |
| D7 | Primary checkout still used for commits? | Stop. Merge-back from the issue branch. Later nightlies already did this on their branches; master `NIGHTLY_LATEST.md` lags until those merge | Medium, ops not design |

---

## 6. Open issue map (architecture-relevant)

| Cluster | Issues | Disposition |
|---------|--------|-------------|
| This review | **ASP-676** | Done this heartbeat |
| Prior review | ASP-627 | Done. Verdict still holds |
| ADR-0013 | ASP-661, ASP-662, ASP-664 done. PR 45 open | Land record after CI dep fix. Child filed |
| H-022 / H-023 | ASP-432, ASP-433 | Done on `e3b1d59`. Do not reopen |
| Gatekeeper packaging | ASP-628 | Done |
| Physical / host | ASP-370, ASP-383, ASP-418, ASP-435, ASP-650 | Stay blocked. Not this review |
| Captain's Log | ASP-651, ASP-652, ASP-654 | Out of architecture scope |
| Routines in flight at scan | ASP-675, ASP-677, ASP-678 | Leave them. Do not steal |

---

## 7. Doc hygiene this heartbeat

1. This file.
2. `docs/architecture/overview.md` last-review pointer, plus H-022 / H-023 / ADR-0013 notes.
3. ADR index weekly pointer (ADR-0013 row stays on PR 45 so this branch does not link a missing file).
4. `docs/security/ACT_GATE_CONTRACT.md` — the path ADR-0003 and the overview already cite. It was never in git. This is an index of the implemented gates, not a new decision.
5. `docs/plans/ASP-676.md` — the one follow-up.
6. Do not Accept ADR-0012. Do not file ADR-0011. Do not PATCH execution workspace policy.

---

## 8. Follow-up

**ASP-682** (todo, Fast Coder, not invoked): add `pyyaml` to the `verify-package-signature` job, same as `security-model-digests`. Prove the suite is reached. Do not merge PR 45 from that ticket. Architect lands PR 45 once that job is green. Do not wake a second implementer while Opencode is already running.

No other new architecture ticket.

---

## 9. Freeze-aware next week

**Do**

- Land PR 45 once the signature job imports.
- Keep dual-human, vault-on-physical-only, H-018, fleet ACL, and the nightly flock.
- Close board lag by local-proof only when the tip already has the fix.

**Don’t**

- Physical arm, live `aa-enforce`, SSH/UFW apply, NATS rotate, or a new credential domain.
- Accept ADR-0012 or file ADR-0011.
- Delete dual-publish.
- Approve Reflection Coach or Summarizer.
- Wake Grok Build. Unarchive ABSA or Content. Wake ABS.
- Edit shared git identity during overlapping heartbeats.

---

## 10. Sign-off

Architecture is coherent. Implementation moved (vault gate, watchdog, worktree policy, rolling nightly file). The register did not follow the policy. That is the only architecture action leaving this review.

**Next weekly:** ~2026-10-05. Confirm ADR-0013 is on `origin/master` and PR 45 is merged. Reconfirm ADR-0012 is still Proposed.
