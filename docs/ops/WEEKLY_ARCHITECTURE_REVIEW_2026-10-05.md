# Weekly Architecture Review — 2026-10-05

**Issue:** ASP-739
**Reviewer:** aspen (Architect)
**Routine fire:** 2026-10-05T09:00Z (local 2026-10-05 03:00 MDT)
**Period:** 2026-09-21 → 2026-10-05 (delta vs the last review **on `origin/master`**, ASP-627)
**Continuity note:** ASP-676 (2026-09-28) finished on the board. Its file never merged (PR 47). This review supersedes that PR. Do not merge it.
**Tree reviewed:** `origin/master` `44eb3c8`
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
| ADR-0011 sunset candidate | **Amber** | Still not filed. No consumer-share measurement |
| ADR-0012 operator-of-record | **Amber (Proposed)** | Still correct. Do not Accept |
| ADR-0013 worktree isolation | **Green record / Amber realization** | Policy live. Record on master (`4596b7c`, PR 45). QA pin can still point at another issue's tree |
| Agent mesh | **Amber** | Advertised API base is fixed. Aider QA cwd contract is not |
| Fleet / swarm / RRM | **Green (sim)** | Hold |
| Act gate | **Green (sim)** | H-022 and H-023 are on master. The cited index file was not. Landed with this review |
| LangGraph (ADR-0005) | **Green/Amber** | Hold |
| Memory (ADR-0006) | **Green** | T1 only under freeze |
| Update integrity (F-014) | **Green (CI dep)** | `verify-package-signature` installs `pyyaml` (`3a6f065`, PR 48). ASP-682 done |
| Packaging / physical cell | **Deferred** | ASP-418 / 435 / 383 / 650 stay blocked or held |
| Nightly | **Green on master, lagging the latest run** | `NIGHTLY_LATEST.md` is 2026-10-03 PASS 149/150 at `ad356a3`. Later nightlies live on their branches until merge |
| Register hygiene | **Amber** | Four architecture PRs are open and conflicting. One is mergeable and factually stale |

**Overall:** Decisions from 09-21 still hold. The 09-28 action (land ADR-0013, fix the signature-job import) is **done**. This week's architecture fact is a **realization gap**, not a redesign: Paperclip isolates per issue, and a QA run can still be pinned to a different issue's worktree and emit `AIDER_QA_PASS`.

---

## 2. ADR register

| ADR | Decision | Still valid? | Action |
|-----|----------|--------------|--------|
| ADR-0001 Packaging | Grove layers, MIT/Apache | Yes | Keep |
| ADR-0002 Swarm/RRM | propose_act only; no joint stream from C2 | Yes — hard | Keep sim-only |
| ADR-0003 Bus + G8 | Prefer `aspen.*`; dual-human authorize | Yes | Act-gate index now in git |
| ADR-0004 Light core | Kernel vs plugins | Yes | Gatekeeper stays monorepo shim until extract |
| ADR-0005 LangGraph | Cognitive plugin; Paperclip stays SoR | Yes | Hold |
| ADR-0006 Memory | T1 default; T2 optional | Yes | No PG under freeze |
| ADR-0007 Sentinel/C2 subjects | Additive `aspen.sentinel.*` / `aspen.authz.*` | Accepted | Keep |
| ADR-0008 Classification | core / plugin / dev-only | Accepted | H-019 gate stays. Do not merge PR 33 (wrong number, conflicting) |
| ADR-0009 Gatekeepers | No broad keys; P1+P2 accepted | Accepted | Packaging target remains plugin `aspen-gatekeeper` (ASP-628). Skeleton landed `a9831cc` |
| ADR-0010 C11 | Spike sandbox | Yes | p50 hw-debt. Do not retune the SLO |
| ADR-0011 (candidate) | Sunset dual-publish | **Not filed** | Still wait for consumer share or an external pilot |
| ADR-0012 OoR binding | NATS `human_id` is SoR; auth binding required before non-sim arm | **Proposed** | **Do not Accept.** H-022 is a durable approval row, not an authenticated principal |
| ADR-0013 Worktree isolation | Per-issue `git_worktree`; Hermes `.worktrees/hermes-*` does not count | **Accepted, on master** | Policy matches the ADR JSON. Do not re-accept. Errata in the ADR. Realization gap is ASP-736 |

### ADR-0013 evidence (this review)

Live `GET /api/projects/2f2b9b10-cfc4-423a-8d6f-ea8e54303b7f` `executionWorkspacePolicy`:

- `enabled: true`
- `defaultMode: isolated_workspace`
- `allowIssueOverride: false`
- `workspaceStrategy.type: git_worktree`
- `baseRef: master`
- `branchTemplate: {{issue.identifier}}-{{slug}}`
- `worktreeParentDir: .paperclip/worktrees`

Record commit `4596b7c` is an ancestor of `origin/master` (`44eb3c8`). PR 45 merged 2026-09-29. Flock `3d88b1a` is also an ancestor. Repo-local git identity is `packndeploy`, not the `Your Name` placeholder the ADR still narrates. Those sentences are historical. See the errata on the ADR. Do not treat them as open preconditions.

**Realization gap (not a reversal):**

ASP-733 (`773f3928-61a9-4ce9-bbcf-8e2f857ee039`) is pinned to execution workspace `54dc4532-3cb1-4225-8a6d-7d14b66926ff`.

- Workspace name and branch: `ASP-728-nightly-packaging-deployment-check`
- `sourceIssueId`: `85524212-f0fb-47a6-a3a9-47f1f80065ef` (not ASP-733)
- Aider QA on 2026-10-04 ran there, printed `AIDER_QA_PASS`, and handed to Auditor
- Implementer commit `4099819` (PR 61, branch `ASP-734-daily-implementation-sweep`) is not in that tree

The worker at `/home/tech/aspen-dev/scripts/paperclip-aider-worker.py` does **not** scan for the newest worktree. `resolve_issue_cwd` uses `issue.executionWorkspaceId` and falls back to ambient `AIDER_CWD` only when that id is empty. It fail-closes if the pinned cwd is missing. It does **not** fail-close when the pin belongs to another issue. ASP-736's "newest worktree" hypothesis is wrong. The defect is a **cross-issue workspace pin** plus a QA pass that does not check `sourceIssueId` or the reviewed SHA.

---

## 3. Module boundaries

```
aspen-dev (Paperclip/Hermes)     org, budgets, CE, personas
        │ issues / heartbeats only
        ▼
AspenOS product surface
  ├── core: agent loop, policy, envelopes, health, bus interfaces
  ├── safety: src/python/safety/estop_watchdog.py   ← H-023, outside the agent loop
  ├── plugins: swarm-manager, edge-rrm, langgraph-worker, memory,
  │            dashboard/Sentinel, gatekeeper shim (+ vault_gate), tool-anomaly
  └── drivers: MQTT / OPC-UA / ROS2 (last mile)
        ▼
Hardware / sim (ASPEN_SIM=1 · plant-range sim_only until G9)
```

**Boundary violations this period:** none that change the grove.

**Placement, reconfirmed:**

- H-022 vault gate stays in `src/python/gatekeeper/vault_gate.py`. Physical cell acts only. Estop stays on the plain dual-human path. `light-cell` skips the vault. Matches `PHYSICAL_ACT_SUBJECTS` vs `SAFETY_SUBJECTS` in `minimal_shim.py` (read this review).
- H-023 watchdog stays in `src/python/safety/estop_watchdog.py`. `tick` does not clear a trip. `clear` requires two distinct authorizers. Live GPIO is not this contract.
- Gatekeeper packaging target remains plugin `aspen-gatekeeper` (ASP-628). Monorepo skeleton is `a9831cc`. Not a second core binary.
- Host-path derivation (ASP-733) is an install boundary, not a new organ. Do not close it on the voided QA.

**Sticky risk (unchanged):** `src/python/services` can shadow root `services/`. Do not "fix" that inside a safety ticket.

---

## 4. Agent-mesh and bus contracts

| Contract | Canonical | Status |
|----------|-----------|--------|
| Execution workspace | Paperclip `isolated_workspace` + `git_worktree` | **Live.** Hermes session worktrees do not satisfy ADR-0013. A pin whose `sourceIssueId` is another issue does not satisfy it either |
| Control-plane URL | Bound listen address, not `allowedHostnames[0]` | **Live this run.** `PAPERCLIP_API_URL` = `http://100.78.55.13:3100` = listen host. Installed `runtime-api.js` sha256 `2f70e09d…` (unpatched baseline was `5bfd564e…`). Do not reorder the allowlist. Do not set `server.bind=lan` |
| Fleet register/HB/ops | `aspen.fleet.*` | Monorepo still dual-publishes legacy. Sunset not ready |
| Missions | `aspen.fleet.mission.*` | Unchanged |
| Edge propose / authorize / command | `aspen.edge.<node>.*` | Unchanged |
| Safety estop / clear | `aspen.safety.*` | Dual clear. Watchdog is a second latch. It does not replace bus estop |
| Authz | `aspen.authz.*` | Gatekeeper P1+P2. Vault row is additional for physical acts only |
| Sentinel | `aspen.sentinel.*` | Unchanged |
| LangGraph | `aspen.worker.langgraph.*` | propose_act out only |
| Cross-plant ACL | edge → alpha denied | Hold |
| QA evidence | Aider runs in the issue workspace, then Auditor | **Broken for ASP-733.** A PASS from another issue's tree is not evidence |

**Mesh roster (this wake):** Grok Build absent. Reflection Coach and Summarizer still `pending_approval` — do not approve. OpenCode, Fast Coder, Aider, Auditor idle. This run is the only aspen heartbeat.

Parallel routines are allowed. Same-issue double-invoke is still a checkout bug. Do not remove the ASP-659 flock.

---

## 5. Pending design decisions

| # | Decision | Recommendation | Urgency |
|---|----------|----------------|---------|
| D1 | Accept ADR-0012? | **No.** H-022 did not bind `human_id` to an authenticated operator | High only before G9 |
| D2 | File ADR-0011? | **No.** No new consumer-share data | Low |
| D3 | Re-accept ADR-0013? | **No.** Record and policy already match. Fix the pin check | **High (contract truth)** |
| D4 | Retune C11 p50? | **No** | Deferred |
| D5 | Live GPIO / physical arm? | **No.** ASP-418 and siblings stay blocked | Deferred |
| D6 | Merge PR 47? | **No.** Superseded. It still says ADR-0013 is not on master | High (register truth) |
| D7 | Treat `AIDER_QA_PASS` on ASP-733 as evidence? | **No.** Void it. Re-run only in a workspace whose `sourceIssueId` is ASP-733 and whose HEAD contains `4099819` | **High (false close)** |
| D8 | Branch protection on `master`? | Still required. ASP-732 is `in_review` (Auditor approved). Human apply. An agent must not set repo rules unasked | High, not this commit |
| D9 | Enable NATS TLS in firstboot (ASP-684)? | Implementation of H-024 P0-2, not a new ADR. Ticket is `todo`, blocker count 0. Do not start it from this review. Prod cell still needs ADR-0012 + TLS + package + Captain apply | Held |

---

## 6. Open issue map (architecture-relevant)

| Cluster | Issues | Disposition |
|---------|--------|-------------|
| This review | **ASP-739** | Docs this heartbeat. Not done until the file is on `origin/master` |
| Prior landed review | ASP-627 | Done. Verdict still holds |
| Stranded review | ASP-676 done, PR 47 open | Supersede. Do not merge |
| ADR-0013 record | ASP-661, ASP-664 done. PR 45 merged | Hold |
| QA cwd contract | **ASP-736** | Correct the root cause (pin, not a scan). Fail closed on `sourceIssueId` mismatch. Owner: aspen. Script is outside this repo |
| False QA | **ASP-733** | Blocked, assigned to Auditor, PASS is void. Do not approve |
| CI visibility | ASP-730 blocked, ASP-732 in_review | Full suite job exists on a branch. Protection is a human apply |
| H-024 TLS templates | ASP-684 todo | Unblocked. Not started here |
| Physical / host | ASP-370 done as dry-run script, ASP-418/435 blocked, ASP-633/650 held | Not this review |
| Host paths | ASP-733 / PR 61 | Real change. QA evidence is not |

---

## 7. Doc hygiene this heartbeat

1. This file.
2. `docs/architecture/overview.md` last-review pointer and the QA-pin note.
3. ADR index weekly pointer. ADR-0013 row notes the realization gap. ADR-0012 stays Proposed.
4. `docs/security/ACT_GATE_CONTRACT.md` — path ADR-0003 and the overview already cite. Drafted on the unmerged ASP-676 branch. Landed here after the subject lists and watchdog clear rule were re-read. Not a new decision.
5. ADR-0013 errata. Historical context left in place.
6. `docs/plans/ASP-678.md` status banner: the advertised-base class fix is live. The "staged, not activated" paragraph is history.
7. `docs/plans/ASP-739.md` — follow-ups.
8. Do not Accept ADR-0012. Do not file ADR-0011. Do not PATCH execution workspace policy.

---

## 8. Follow-ups

1. **ASP-736** (existing): fail closed in the Aider worker when `executionWorkspace.sourceIssueId` is not the issue under review, and when a named reviewed SHA is not an ancestor of `HEAD`. Do not scan worktrees. Do not edit AspenOS product code for this. Script: `/home/tech/aspen-dev/scripts/paperclip-aider-worker.py`.
2. **Re-QA ASP-733** (new child of this review): only after the workspace pin is that issue's tree and `4099819` is in `HEAD`. Until then Auditor must not approve.
3. Close superseded architecture PRs 33, 35, 39, 41, 47 so a later merge cannot split the register.
4. No other new architecture ticket.

---

## 9. Freeze-aware next week

**Do**

- Land this review on `origin/master` in the same cycle.
- Keep dual-human, vault-on-physical-only, H-018, fleet ACL, and the nightly flock.
- Treat a QA PASS as void when the workspace `sourceIssueId` disagrees with the issue.

**Don't**

- Physical arm, live `aa-enforce`, SSH/UFW apply, NATS rotate, or a new credential domain.
- Accept ADR-0012 or file ADR-0011.
- Delete dual-publish.
- Approve Reflection Coach or Summarizer.
- Wake Grok Build. Unarchive ABSA or Content. Wake ABS.
- Merge PR 47.
- Set GitHub branch protection from an agent heartbeat.

---

## 10. Sign-off

Architecture is coherent. The register caught up to the 09-28 policy fact (ADR-0013 on master, signature job imports). The control-plane URL contract is restored. The open hole is evidence: a QA adapter will certify the workspace it was pinned to, even when that workspace belongs to another issue.

**Next weekly:** ~2026-10-12. Confirm this file is on `origin/master`. Confirm ASP-733 was not closed on the 2026-10-04 PASS. Reconfirm ADR-0012 is still Proposed.
