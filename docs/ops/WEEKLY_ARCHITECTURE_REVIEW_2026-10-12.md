# Weekly Architecture Review — 2026-10-12

**Issue:** ASP-773
**Reviewer:** aspen (Architect)
**Routine fire:** 2026-10-12T09:00Z (local 2026-10-12 03:00 MDT)
**Period:** 2026-10-05 → 2026-10-12 (delta vs the last review **on `origin/master`**, ASP-739)
**Tree reviewed:** `origin/master` `94e53f7`
**SoR:** `docs/sor/MASTER_SPEC.md` (AspenGrove v4.0 — Three Organs)
**Fiscal posture:** unchanged. ASP $50 + BTH $50. Sim-only fleet. Wake-on-demand. Grok for architecture gates only. Grok Build stays terminated.

---

## 1. Executive verdict

| Area | Health | Delta vs 2026-10-05 |
|------|--------|---------------------|
| Product triad (OS / Sentinel / aspen-dev) | **Green (locked)** | Unchanged |
| Platform ADRs 0001–0006 | **Green** | Hold |
| ADR-0007 / 0008 / 0009 | **Green (Accepted)** | Hold. No redesign |
| ADR-0010 C11 | **Amber** | Nightly still 158/159, C11 p50 only. Not a packaging fail |
| ADR-0011 sunset candidate | **Amber** | Still not filed. No consumer-share measurement |
| ADR-0012 operator-of-record | **Amber (Proposed)** | Still correct. TLS templates do not bind `human_id`. Do not Accept |
| ADR-0013 worktree isolation | **Green record / Green fail-closed** | Policy unchanged. Worker now aborts a cross-issue pin (ASP-736). Checkout still does not refresh a stale pin |
| Agent mesh | **Amber** | QA child encoding is the live contract. Repo CE doc lagged. PR 64 step 6 contradicts CHG-0029 |
| Fleet / swarm / RRM | **Green (sim)** | Hold |
| Act gate | **Green (sim)** | Unchanged. H-022 is not an authenticated principal |
| Sentinel anomaly (H-015) | **Green (fail-open)** | Consumer is on master (`f6ef0d7`). Still not a deny path. Subject was missing from the register |
| LangGraph (ADR-0005) | **Green/Amber** | Hold |
| Memory (ADR-0006) | **Green** | T1 only under freeze. Host-path derivation is still an install boundary (ASP-733), not a new organ |
| Update integrity (F-014) | **Green (CI dep)** | `pyyaml` is on master. PR 50 is conflicting and superseded |
| Branch protection | **Green** | Live this wake. HTTP 200. 10 required checks, `strict`, `enforce_admins` |
| NATS TLS templates (H-024 P0-2) | **Green (templates)** | ASP-684 merged (PR 58). Not a live rotate. Not ADR-0012 |
| Packaging / physical cell | **Deferred** | ASP-418 / 435 / 383 / 650 stay blocked or held |
| Nightly | **Green on master, lagging today's run** | `NIGHTLY_LATEST.md` is ASP-764 PASS 158/159 at `f179faf`. ASP-771 ran the same score in its own tree and is not on master |
| Register hygiene | **Amber** | Four open PRs would split the register if merged. One board-done assessment file is not on master |

**Overall:** Decisions from 10-05 still hold. The realization gap that review named is closed in the Aider worker, not by a new ADR. This week's architecture fact is a **contract mirror**: the mesh already runs CHG-0029 and an additive fail-open anomaly subject, and the repo register did not say so.

---

## 2. ADR register

| ADR | Decision | Still valid? | Action |
|-----|----------|--------------|--------|
| ADR-0001 Packaging | Grove layers, MIT/Apache | Yes | Keep |
| ADR-0002 Swarm/RRM | propose_act only; no joint stream from C2 | Yes — hard | Keep sim-only |
| ADR-0003 Bus + G8 | Prefer `aspen.*`; dual-human authorize | Yes | Keep |
| ADR-0004 Light core | Kernel vs plugins | Yes | Gatekeeper stays monorepo shim until extract |
| ADR-0005 LangGraph | Cognitive plugin; Paperclip stays SoR | Yes | Hold |
| ADR-0006 Memory | T1 default; T2 optional | Yes | No PG under freeze |
| ADR-0007 Sentinel/C2 subjects | Additive `aspen.sentinel.*` / `aspen.authz.*` | Accepted | Mirror `aspen.sentinel.tools.anomaly`. Not a new ADR |
| ADR-0008 Classification | core / plugin / dev-only | Accepted | H-019 gate stays. PR 59 is an extra rule-4 gate, stalled, not a status flip |
| ADR-0009 Gatekeepers | No broad keys; P1+P2 accepted | Accepted | Packaging target remains plugin `aspen-gatekeeper` |
| ADR-0010 C11 | Spike sandbox | Yes | p50 hw-debt. Do not retune the SLO |
| ADR-0011 (candidate) | Sunset dual-publish | **Not filed** | Still wait for consumer share or an external pilot |
| ADR-0012 OoR binding | NATS `human_id` is SoR; auth binding required before non-sim arm | **Proposed** | **Do not Accept.** TLS-by-default templates did not bind a principal |
| ADR-0013 Worktree isolation | Per-issue `git_worktree`; Hermes `.worktrees/hermes-*` does not count | **Accepted, on master** | Do not re-accept. Fail-closed pin check is in the worker. Errata updated |

### ADR-0013 evidence (this review)

Live `GET /api/projects/2f2b9b10-cfc4-423a-8d6f-ea8e54303b7f` `executionWorkspacePolicy` is unchanged from ASP-739:

- `enabled: true`
- `defaultMode: isolated_workspace`
- `allowIssueOverride: false`
- `workspaceStrategy.type: git_worktree`
- `baseRef: master`
- `branchTemplate: {{issue.identifier}}-{{slug}}`
- `worktreeParentDir: .paperclip/worktrees`

Not re-applied.

**Realization gap named on 10-05 is closed in the worker, not reversed:**

`/home/tech/aspen-dev/scripts/paperclip-aider-worker.py` `pin_owner_ok` (ASP-736, closed 2026-10-11):

- QA mode with no `executionWorkspaceId` raises `QA_ABORT` and does not fall back to ambient `AIDER_CWD`
- `sourceIssueId` must be the issue under review **or its parent** (QA children inherit the implementation workspace; ASP-759 → ASP-758 is allowed; ASP-733 pinned to ASP-728 is not)
- A named commit/head/sha on the latest `READY_FOR_AIDER_QA` comment must be an ancestor of `HEAD`
- It does not scan `.paperclip/worktrees`
- Close evidence: `python3 /home/tech/aspen-dev/scripts/test_aider_cwd_guard.py` exit 0, 10 tests OK

Checkout still does not refresh a stale pin. That is friction. It is no longer a false `AIDER_QA_PASS`. Do not file a second isolation ADR for the refresh gap.

---

## 3. Module boundaries

```
aspen-dev (Paperclip/Hermes)     org, budgets, CE, personas
        │ issues / heartbeats only
        ▼
AspenOS product surface
  ├── core: agent loop, policy, envelopes, health, bus interfaces
  ├── safety: src/python/safety/estop_watchdog.py   ← outside the agent loop
  ├── plugins: swarm-manager, edge-rrm, langgraph-worker, memory,
  │            dashboard/Sentinel, gatekeeper shim (+ vault_gate), tool-anomaly
  └── drivers: MQTT / OPC-UA / ROS2 (last mile)
        ▼
Hardware / sim (ASPEN_SIM=1 · plant-range sim_only until G9)
```

**Boundary violations this period:** none that change the grove.

**Placement, reconfirmed:**

- Tool-anomaly consumer (`src/python/sentinel/tool_anomaly_consumer.py`) subscribes `aspen.sentinel.audit.event` and publishes `aspen.sentinel.tools.anomaly`. `fail_open: True`. `action_required` is investigate. It does not sit on the estop or authorize path.
- H-022 vault gate stays on physical cell acts only. Estop stays on the plain dual-human path.
- H-023 watchdog stays outside the agent loop. `clear` still requires two distinct authorizers.
- Gatekeeper packaging target remains plugin `aspen-gatekeeper`. Not a second core binary.
- Host-path derivation (ASP-733 / PR 61) is an install boundary, not a new organ. Not closed.
- HybridIntel stub deletion (ASP-696) removed a dead module. It did not add an organ.
- NATS TLS-by-default (ASP-684) is a firstboot/template default plus a CI job. It is not a live listener rotate and not a new subject family.

**Sticky risk (unchanged):** `src/python/services` can shadow root `services/`. Do not "fix" that inside a safety ticket.

---

## 4. Agent-mesh and bus contracts

| Contract | Canonical | Status |
|----------|-----------|--------|
| Execution workspace | Paperclip `isolated_workspace` + `git_worktree` | **Live.** Unchanged this wake. Hermes session worktrees do not satisfy ADR-0013 |
| QA evidence | Pin `sourceIssueId` is the issue or its parent; named SHA is an ancestor of `HEAD` | **Live in the worker (ASP-736).** A PASS from another issue's tree is not evidence |
| QA handoff | One QA-gate child, parent `blocked` on that child | **Live in agent instructions (CHG-0029).** Repo doc lagged. Auditor does not set the gate `done` |
| Control-plane URL | Bound listen address, not `allowedHostnames[0]` | **Live this run.** `PAPERCLIP_API_URL` = `http://100.78.55.13:3100`. Do not reorder the allowlist. Do not set `server.bind=lan` |
| Branch protection | 10 required checks, `strict`, `enforce_admins` | **Live.** Re-read HTTP 200 this wake. Contexts include `python-test-suite` and `security-nats-tls` |
| Fleet register/HB/ops | `aspen.fleet.*` | Monorepo still dual-publishes legacy. Sunset not ready |
| Missions | `aspen.fleet.mission.*` | Unchanged |
| Edge propose / authorize / command | `aspen.edge.<node>.*` | Unchanged |
| Safety estop / clear | `aspen.safety.*` | Dual clear. Watchdog is a second latch |
| Authz | `aspen.authz.*` | Gatekeeper P1+P2. Vault row is additional for physical acts only |
| Sentinel | `aspen.sentinel.*` | Additive finding subject `aspen.sentinel.tools.anomaly` (fail-open). Stream already binds `aspen.sentinel.>` |
| LangGraph | `aspen.worker.langgraph.*` | propose_act out only |
| Cross-plant ACL | edge → alpha denied | Hold |
| NATS transport | TLS in cell firstboot templates | **Templates on master.** Live rotate on bt-asp-srv stays frozen |

**Mesh roster (this wake):** Grok Build absent. Summarizer still `pending_approval` — do not approve. Reflection Coach is not on the roster. OpenCode `running` (do not invoke). Aider and Auditor idle after the ASP-771/772 nightly handoff. This run is the aspen heartbeat for ASP-773.

Parallel routines are allowed. Same-issue double-invoke is still a checkout bug. Do not remove the ASP-659 flock.

### QA handoff (CHG-0029, recorded this review)

Agent-authored `in_review` plus an agent assignee is `400 invalid_issue_disposition`. `blocked` with an empty `blockedBy` freezes the chain. ASP-725 (todo) is the server-side resolver fix. Until it ships, the grove encoding is:

1. One QA-gate child, assignee Aider, status `todo`. Parent `blocked` on that child. One Aider invoke.
2. Aider pass: gate `in_progress`, assignee Auditor. Not `in_review`. Not `done`.
3. Auditor pass: gate `in_progress`, assignee aspen. Auditor never sets `done`.
4. Aspen sets the gate `done` only after `auditor-evidence-check.py` passes and `LOCAL_PROOF` is posted.
5. Parent `done` only after local proof and the commit is on `origin/master`.

PR 64 step 6 (Auditor sets the gate `done`) is the pre-CHG-0029 text. Do not merge it.

---

## 5. Pending design decisions

| # | Decision | Recommendation | Urgency |
|---|----------|----------------|---------|
| D1 | Accept ADR-0012? | **No.** TLS templates did not bind `human_id` to an authenticated operator | High only before G9 |
| D2 | File ADR-0011? | **No.** No new consumer-share data | Low |
| D3 | Re-accept ADR-0013? | **No.** Record, policy, and fail-closed pin check already match | Closed as a design question |
| D4 | Retune C11 p50? | **No** | Deferred |
| D5 | Live GPIO / physical arm / NATS rotate? | **No.** ASP-418 and siblings stay blocked. Host rotate stays frozen | Deferred |
| D6 | Merge PR 64 as written? | **No.** Superseded by the CHG-0029 encoding in this review | High (register truth) |
| D7 | Treat the 2026-10-04 ASP-733 PASS as evidence? | **No.** Still void. ASP-733 is not done | Hold |
| D8 | Touch branch protection? | **No.** It is live. An agent must not edit repo rules unasked | Closed as a design question |
| D9 | Treat ASP-434 `done` as the H-024 assessment record? | **No.** `git ls-tree origin/master` has no `docs/security/H-024-iec-62443-4-2-cell-assessment.md`. PR 44 is the stranded file | High (false-done vs tree) |
| D10 | Close or merge PR 61 from this review? | **No.** `gh pr view 61` is OPEN, MERGEABLE, CLEAN. ASP-769's "PR closed" sentence is false | Hold |
| D11 | New ADR for the anomaly consumer? | **No.** Additive fail-open subject under Accepted ADR-0007 | Closed |

---

## 6. Open issue map (architecture-relevant)

| Cluster | Issues | Disposition |
|---------|--------|-------------|
| This review | **ASP-773** | Docs this heartbeat. Not done until the file is on `origin/master` |
| Prior landed review | ASP-739 | Done. Verdict still holds. File is on master |
| QA pin | ASP-736 done | Worker fail-closed. Do not reopen |
| Host paths | **ASP-733** blocked on **ASP-769** | Pin `be96305f` is ASP-733's tree. Aider aborted on zero target files (2026-10-11). Assignee is still Auditor. Not a new architecture ticket. Do not approve on the 2026-10-04 PASS |
| CE encoding | ASP-744 done; PR 64 open | Board close is not the repo record. This review writes the CHG-0029 text. Close PR 64. Do not merge it |
| Empty-blocker resolver | ASP-725 todo | Server change. Do not start from this review |
| Rule-4 classification gate | ASP-672 `in_review`, unassigned; PR 59 | Stalled execution of an accepted ADR. Not a status flip. Do not merge until rebased and QA'd |
| Branch protection | ASP-732 done | Reconfirmed live this wake |
| TLS templates | ASP-684 done, PR 58 on master | Templates only |
| H-024 assessment | ASP-434 done; PR 44 open, BEHIND, MERGEABLE | File missing on master. Follow-up, not a merge from this review |
| Nightly in flight | ASP-771 blocked on ASP-772 | Today's 158/159 is not the master record. Do not merge it from here |
| Physical / host | ASP-418/435 blocked, ASP-650 todo (captain), ASP-383 deferred | Not this review |

---

## 7. Doc hygiene this heartbeat

1. This file.
2. `docs/plans/ASP-773.md`.
3. `docs/architecture/overview.md` last-review pointer, anomaly bullet, ADR-0013 bullet.
4. ADR index: 0012 stays Proposed; 0013 row notes the worker close; weekly pointer moves.
5. ADR-0012 reconfirmation line. ADR-0013 errata addendum. No status flip.
6. `docs/COMPOUND_ENGINEERING.md` — CHG-0029 encoding. PR 64 is not the source.
7. `nats/subjects.yaml` and `docs/FLEET.md` — mirror `aspen.sentinel.tools.anomaly`. String copied from `SUBJECT_TOOL_ANOMALY`. Not a new subject decision.
8. Do not Accept ADR-0012. Do not file ADR-0011. Do not PATCH execution workspace policy. Do not edit branch protection.

### PRs closed as superseded (register hygiene)

| PR | Why it must not merge |
|----|------------------------|
| 64 | Auditor-sets-gate-done. Contradicts CHG-0029 |
| 50 | CONFLICTING. `pyyaml` already on master in `verify-package-signature` |
| 66 | CONFLICTING. Read-back fix already on master (`f179faf`, PR 57) |
| 40 | Dated nightly file. Contradicts rolling `NIGHTLY_LATEST.md` |

Left open on purpose: PR 61 (ASP-733, mergeable), PR 59 (stalled rule-4 gate), PR 44 (assessment not on master — follow-up, do not blind-merge), PR 51 (learning doc, not a register split), PR 18/29/36 (wide or stale; not reviewed line-by-line; do not merge from this wake).

---

## 8. Follow-ups

1. **Land the H-024 assessment file** (new child of this review): re-read PR 44 against `docs/security/H-024-wan-mtls-deployment.md`, then land `docs/security/H-024-iec-62443-4-2-cell-assessment.md` on `origin/master`. Do not Accept ADR-0012. Do not rotate live NATS.
2. No other new architecture ticket.
3. Do not open a third re-QA of ASP-733. ASP-769 already owns the rebase QA. Its stall is an empty file list, not a pin.

---

## 9. Freeze-aware next week

**Do**

- Land this review on `origin/master` in the same cycle.
- Keep dual-human, vault-on-physical-only, H-018, fleet ACL, the nightly flock, and the QA pin fail-closed.
- Treat a QA PASS as void when `sourceIssueId` is neither the issue nor its parent.
- Treat Auditor `done` on a QA gate as a contract break (CHG-0029).

**Don't**

- Physical arm, live `aa-enforce`, SSH/UFW apply, NATS rotate, or a new credential domain.
- Accept ADR-0012 or file ADR-0011.
- Delete dual-publish.
- Approve Summarizer. Revive Reflection Coach. Wake Grok Build. Unarchive ABSA or Content. Wake ABS.
- Merge PR 64, 50, 66, or 40.
- Set GitHub branch protection from an agent heartbeat.
- Invoke OpenCode, Aider, or Auditor from this review.

---

## 10. Sign-off

Architecture is coherent. The 10-05 decisions hold. The pin hole is closed in the worker. TLS templates and branch protection landed without becoming a physical-cell approval. The open hole is the register: the repo CE doc did not match the mesh, one board-done assessment file is not on master, and a handful of open PRs would put the old text back.

**Next weekly:** ~2026-10-19. Confirm this file is on `origin/master`. Confirm ADR-0012 is still Proposed. Confirm ASP-733 was not closed on the 2026-10-04 PASS. Confirm PR 64 stayed closed.
