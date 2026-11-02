# Weekly Architecture Review — 2026-11-02

**Issue:** ASP-841
**Reviewer:** aspen (Architect)
**Routine fire:** 2026-11-02T09:00:20Z (local 2026-11-02 02:00 MST). Trigger `df14b391`, cron `0 9 * * 1` UTC. Next fire **2026-11-09T09:00:00Z**. Do not file a duplicate.
**Period:** 2026-10-12 → 2026-11-02 (delta vs the last review **on `origin/master`**, ASP-773). ASP-800 (2026-10-19) and ASP-818 (2026-10-26) are incorporated here because neither file is on master.
**Tree reviewed:** `origin/master` `edbc440` after `git fetch origin master` this wake.
**SoR:** `docs/sor/MASTER_SPEC.md` (AspenGrove v4.0 — Three Organs)
**Fiscal posture:** unchanged. ASP $50 + BTH $50. Sim-only fleet. Wake-on-demand. Grok for architecture gates only. Grok Build stays terminated.

---

## 1. Executive verdict

| Area | Health | Delta vs 2026-10-12 (master) |
|------|--------|------------------------------|
| Product triad (OS / Sentinel / aspen-dev) | **Green (locked)** | Unchanged. No product commit on master |
| Platform ADRs 0001–0006 | **Green** | Hold |
| ADR-0007 / 0008 / 0009 | **Green (Accepted)** | Hold. No redesign |
| ADR-0010 C11 | **Amber** | Still the only nightly fail on the master record (p50 3.655 ms). Do not retune. ASP-807 now exists and stays todo |
| ADR-0011 sunset candidate | **Amber** | Still not filed. No consumer-share measurement |
| ADR-0012 operator-of-record | **Amber (Proposed)** | Still correct. Do not Accept. Do not start ASP-777 |
| ADR-0013 worktree isolation | **Green record / code present / ticket not closed** | Policy unchanged. Worker hash unchanged. ASP-736 still `in_review` (CHG-0034). Do not re-decide |
| Agent mesh | **Amber** | CHG-0029 unchanged. OpenCode is running ASP-842. Do not invoke. Confirmation accept is not a GitHub review |
| Fleet / swarm / RRM | **Green (sim)** | Hold. PR 83 is still sim_only and not on master. It does not unblock ASP-418 |
| Act gate | **Green (sim)** | Unchanged. H-022 is not an authenticated principal |
| Sentinel anomaly (H-015) | **Green (fail-open)** | On master, still investigate, not a deny. PR 81 does not flip `fail_open`. Service stays off |
| LangGraph (ADR-0005) | **Green/Amber** | Hold |
| Memory (ADR-0006) | **Green** | T1 only under freeze. PR 79 is a loader, not a new organ, not on master |
| Update integrity (F-014) | **Green (CI dep)** | PR 50 stayed closed, not merged |
| Branch protection | **Green, and it is why the register froze** | Live this wake. 10 required checks, `strict`, `enforce_admins`, 1 approving review. Sole collaborator is AbsolutionAI (admin), who also authors the PRs |
| NATS TLS templates (H-024 P0-2) | **Green (templates)** | Unchanged. Not a live rotate. Not ADR-0012 |
| Packaging / physical cell | **Deferred** | ASP-418 stays blocked. Jo's answer (CHG-0037) was sim_only software only. ASP-796 owns that ticket |
| Nightly | **Green on master, record lagging** | `NIGHTLY_LATEST.md` is still ASP-764 PASS 158/159 at `f179faf` (2026-10-11). PRs 80, 86, 89 are later records, not merged. ASP-842 is in flight |
| Register hygiene | **Red on land, Amber on design** | Master froze at `edbc440` on 2026-10-12. Two weekly reviews, the v2.3/v2.4 threat model, and three board-done security claims are not the tree |

**Overall:** Decisions from 10-12 still hold. No architecture-changing commit landed after the 10-12 review itself. This week's fact is **the register cannot move by clicking Paperclip**. Confirmation `97f22dc5` was accepted on 2026-10-26. PR 87 is still open, zero reviews, `mergeable_state=blocked`. A Paperclip accept is not a GitHub approving review. This file supersedes PR 84 and PR 87. Do not merge either.

### Confirmations the prior reviews asked for

| Check | Result |
|-------|--------|
| 10-12 review file on `origin/master` | Yes. `docs/ops/WEEKLY_ARCHITECTURE_REVIEW_2026-10-12.md` at `edbc440` |
| 10-19 review file on `origin/master` | **No.** PR 84 open, `blocked`, 0 reviews, head `2c7dbe1`. Confirmation `e788a977` still pending |
| 10-26 review file on `origin/master` | **No.** PR 87 open, `blocked`, 0 reviews, head `e9b198c`. Confirmation `97f22dc5` accepted and did not merge |
| ADR-0012 still Proposed | Yes |
| ASP-733 not closed on the 2026-10-04 PASS | Yes. Still `blocked` on ASP-769 (`in_review`). PR 61 is `behind` |
| PR 64 stayed closed | Yes. Closed, not merged. PRs 40, 50, and 66 stayed closed and unmerged |
| ASP-736 not closed with `board.key` since CHG-0034 | Yes. Still `in_review`, unassigned. Worker sha256 still `5ba33fc1fdc373e9116b8db527d0f620b77bfecebe98fa8b4384e3942f9b53ad` |
| ASP-774 / ASP-801 not done without `git ls-tree` | Yes. Both still `todo`. Assessment file absent. Legacy `nats/server.conf` still has credential keys (count only; values not printed) |
| ASP-803 / ASP-806 / ASP-819 done means the file is on master | **No.** All three are `done`. None of the claimed files are on `origin/master` |

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
| ADR-0007 Sentinel/C2 subjects | Additive `aspen.sentinel.*` / `aspen.authz.*` | Accepted | Anomaly subject stays fail-open. Not a new ADR |
| ADR-0008 Classification | core / plugin / dev-only | Accepted | H-019 gate stays. PR 59 is an extra rule-4 gate, stalled, not a status flip |
| ADR-0009 Gatekeepers | No broad keys; P1+P2 accepted | Accepted | Packaging target remains plugin `aspen-gatekeeper` |
| ADR-0010 C11 | Spike sandbox | Yes | p50 hw-debt. Do not retune the SLO. ASP-807 exists; do not start it from here |
| ADR-0011 (candidate) | Sunset dual-publish | **Not filed** | Still wait for consumer share or an external pilot |
| ADR-0012 OoR binding | NATS `human_id` is SoR; auth binding required before non-sim arm | **Proposed** | **Do not Accept.** Do not start ASP-777 |
| ADR-0013 Worktree isolation | Per-issue `git_worktree`; Hermes `.worktrees/hermes-*` does not count | **Accepted, on master** | Do not re-accept. Do not treat CHG-0034 as a design reopen |

### ADR-0013 evidence (this review)

Live `GET /api/projects/2f2b9b10-cfc4-423a-8d6f-ea8e54303b7f` `executionWorkspacePolicy` is unchanged:

- `enabled: true`
- `defaultMode: isolated_workspace`
- `allowIssueOverride: false`
- `workspaceStrategy.type: git_worktree`
- `baseRef: master`
- `branchTemplate: {{issue.identifier}}-{{slug}}`
- `worktreeParentDir: .paperclip/worktrees`

Not re-applied.

This heartbeat's Hermes session cwd was `.worktrees/hermes-6c9611ca` on `hermes/hermes-6c9611ca`. That does not satisfy ADR-0013. The review files are in the ASP-841 execution worktree.

Worker `/home/tech/aspen-dev/scripts/paperclip-aider-worker.py` still has `pin_owner_ok` and `QA_ABORT`. sha256 `5ba33fc1fdc373e9116b8db527d0f620b77bfecebe98fa8b4384e3942f9b53ad` (40380 bytes). Same hash the 10-19 review recorded. Script not edited.

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

**Boundary violations this period:** none on `origin/master`. Nothing new landed.

**Placement, reconfirmed:**

- Tool-anomaly consumer stays fail-open and off the estop / authorize path. PR 81 does not change that. Service stays off.
- H-022 vault gate stays on physical cell acts only.
- Gatekeeper packaging target remains plugin `aspen-gatekeeper`.
- Host-path derivation (ASP-733 / PR 61) is an install boundary, not a new organ. Not closed.
- NATS TLS-by-default remains templates. Not a live listener rotate. Not ADR-0012.
- F-017 fingerprint (ASP-804 / PR 88) is a design + fixture. Not a live enroll. Not on master.
- D1 sim profile (ASP-796 / PR 83) is software-only. It does not authorize physical D1.

**Sticky risk (unchanged):** `src/python/services` can shadow root `services/`. Do not "fix" that inside a safety ticket.

---

## 4. Agent-mesh and bus contracts

| Contract | Canonical | Status |
|----------|-----------|--------|
| Execution workspace | Paperclip `isolated_workspace` + `git_worktree` | **Live.** Unchanged. Hermes session worktrees do not satisfy ADR-0013 |
| QA evidence | Pin `sourceIssueId` is the issue or its parent; named SHA is an ancestor of `HEAD` | **Live in the worker.** Ticket ASP-736 is not closed |
| QA handoff | One QA-gate child, parent `blocked` on that child | **Live (CHG-0029).** Auditor does not set the gate `done` |
| Control-plane URL | Bound listen address `http://100.78.55.13:3100` | Used this run. Do not reorder `allowedHostnames`. Do not set `server.bind=lan` |
| Branch protection | 10 required checks, `strict`, `enforce_admins`, 1 approving review | **Live.** Contexts: lint, security-devonly-isolation, verify-package-signature, security-model-digests, python-test-suite, security-nats-tls, smoke, build-go, build-rust, build-c11 |
| Land authority | GitHub approving review, or an explicit admin-merge authorization | **Paperclip `request_confirmation` accept is not a review.** PR 78 landed because AbsolutionAI admin-merged it. PR 87 did not |
| Collaborators | AbsolutionAI is the only collaborator, role admin | A normal approving review of an AbsolutionAI-authored PR is impossible. Do not `--admin` from this wake |
| Fleet / missions / edge / safety / authz / sentinel | Unchanged subject families | Dual-publish stays. Sunset not ready |
| NATS transport | TLS in cell firstboot templates | Templates on master. Live rotate stays frozen |

**Mesh roster (this wake):** Grok Build absent. Summarizer still `pending_approval` — do not approve. Reflection Coach is not on the roster. Pending hire queue is empty — do not reopen a `claude_local` hire. OpenCode `running` on ASP-842 (do not invoke). Aider idle. Auditor idle. This run is the aspen heartbeat for ASP-841.

Parallel routines are allowed. Same-issue double-invoke is still a checkout bug. Do not remove the ASP-659 flock.

---

## 5. Pending design decisions

| # | Decision | Recommendation | Urgency |
|---|----------|----------------|---------|
| D1 | Accept ADR-0012? | **No.** Nothing this period bound `human_id` to an authenticated operator | High only before G9 |
| D2 | File ADR-0011? | **No.** No consumer-share data | Low |
| D3 | Re-accept ADR-0013 or close ASP-736? | **No.** Record and worker text match. The ticket close was reverted | Closed as a design question |
| D4 | Retune C11 p50? | **No.** ASP-807 is the reassessment ticket. Do not start it here | Deferred |
| D5 | Live GPIO / physical arm / NATS rotate? | **No.** Jo's ASP-418 answer was sim_only software only (CHG-0037). Do not clear the done-blocker edge; clearing it would make physical D1 look unblocked | Deferred |
| D6 | Merge PR 84 or PR 87? | **No.** Superseded by this file. Merging either splits the latest-review pointer | High (register truth) |
| D7 | Treat confirmation `97f22dc5` as a merge? | **No.** Accepted 2026-10-26. `origin/master` is still `edbc440` | Closed |
| D8 | Admin-merge this review from this wake? | **No.** Prior reviews required an explicit board authorization. None exists for this PR. Do not edit branch protection | High |
| D9 | Treat ASP-803 / ASP-806 / ASP-819 `done` as the tree? | **No.** Claimed files are absent from `origin/master`. No open PR for those three | High (false-done vs tree) |
| D10 | New ADR for the land-authority gap? | **No.** It is an operating fact, not a product organ. Do not file ADR-0014 | Closed |
| D11 | Enable the anomaly consumer, or merge PR 88/89 from here? | **No.** ASP-780, ASP-804, and the nightly owners already have those PRs | Hold |

---

## 6. Open issue map (architecture-relevant)

| Cluster | Issues | Disposition |
|---------|--------|-------------|
| This review | **ASP-841** | Docs this heartbeat. Not done until this file is on `origin/master` |
| Prior landed review | ASP-773 | Done. File is on master. Its ASP-736 close sentence is corrected in the ADR-0013 errata |
| Prior unlanded reviews | **ASP-800** `in_review` (PR 84, confirmation `e788a977` pending); **ASP-818** `in_review` (PR 87, confirmation accepted, question `b31166d7` pending) | Superseded. Do not merge. Do not accept `e788a977`. Do not pick `admin_bypass` on `b31166d7` |
| QA pin ticket | **ASP-736** `in_review`, unassigned | Code present, hash unchanged. Do not close from here |
| Host paths | **ASP-733** blocked; **ASP-769** `in_review`; PR 61 `behind` | Not a new ticket. Do not approve on the 2026-10-04 PASS |
| H-024 assessment | **ASP-774** `todo`; PR 44 open, `blocked` | Already the follow-up. File still absent. Do not duplicate |
| H-017 scrub | **ASP-801** `todo`; PR 82 open, `blocked`; PR 18 `dirty` | Already the follow-up. Do not merge 18. Do not print secret values. Do not rotate live NATS |
| False-done since 10-26 | **ASP-803** done (rotation runbook claimed, file absent); **ASP-806** done (`bandit` not in master `ci.yml`); **ASP-819** done (v2.4 commit `86caa33` not on master, no open PR) | Recorded here. Do not reopen from this review. Do not treat `done` as the tree |
| C11 reassessment | **ASP-807** `todo` | Now on the board. Do not start. Do not retune |
| F-017 fingerprint | **ASP-804** `in_review`; QA **ASP-827** done; PR 88 open, `blocked`, 0 reviews | Not landed. Not a live enroll |
| ADR-0012 implementation | **ASP-777** `todo`, unassigned | Exists. Do not start |
| D1 sim profile | **ASP-796** `todo`; PR 83 open | Software-only. Does not unblock ASP-418 |
| Anomaly hardening | **ASP-780** `backlog`; PR 81 open | Before service enablement |
| Memory loader | **ASP-788** `in_review`; PR 79 | Not this review |
| Threat model | **ASP-802** `in_review` (PR 85) | v2.3 is not on master. ASP-819's v2.4 is also not on master |
| Rule-4 gate | ASP-672 `in_review`; PR 59 | Stalled execution of an accepted ADR. Not a status flip |
| Empty-blocker resolver | ASP-725 `todo` | Server change. Do not start from this review |
| Nightly record | PR 80, PR 86, PR 89 open; **ASP-842** `in_progress` (OpenCode) | Master record is still 2026-10-11. Do not merge a nightly from here. Do not invoke OpenCode |
| Physical / host | ASP-418 blocked by done ASP-650; ASP-435 blocked; ASP-383 deferred | Leave the stale edge. Clearing it unblocks the wrong work |
| Agent merge containment | ASP-778 `backlog` | Do not auto-assign. Do not start |

---

## 7. Doc hygiene this heartbeat

1. This file.
2. `docs/plans/ASP-841.md`.
3. `docs/architecture/overview.md` last-review pointer, and the ADR-0013 bullet corrected for CHG-0034.
4. ADR index: 0012 stays Proposed; 0013 row notes the reverted close; weekly pointer moves to this file.
5. ADR-0012 reconfirmation line. ADR-0013 errata addendum. No status flip.
6. Do not Accept ADR-0012. Do not file ADR-0011 or ADR-0014. Do not PATCH execution workspace policy. Do not edit branch protection. Do not edit the Aider worker. Do not edit the threat model.

### PRs left open on purpose

| PR | Why it must not merge from this review |
|----|----------------------------------------|
| 18 | `dirty`. Not the H-017 scrub. PR 82 is |
| 29 | `dirty` packaging forward-port |
| 36 | `dirty` fleet-bus smoke. Not reviewed line-by-line |
| 44 | H-024 assessment. ASP-774 owns it |
| 51 | Learning doc, `behind`. Not a register split |
| 59 | Stalled ADR-0008 rule-4 gate. ASP-672 owns it |
| 61 | ASP-733 host paths. `behind`. ASP-769 owns the re-QA |
| 79 | Memory loader. ASP-788 owns it |
| 80 | Nightly record 2026-10-16 |
| 81 | Anomaly hardening. Service stays off |
| 82 | H-017 scrub. ASP-801 owns it. Do not print values |
| 83 | sim_only D1 profile. ASP-796 owns it |
| 84 | 10-19 review. Superseded. Do not merge |
| 85 | Threat model v2.3. Not on master |
| 86 | Nightly record 2026-10-22 |
| 87 | 10-26 review. Superseded. Do not merge |
| 88 | F-017 fingerprint. ASP-804 owns it. Not a live enroll |
| 89 | Nightly ASP-833. Not today's in-flight run |

Closed and still unmerged: 40, 50, 64, 66.

---

## 8. Follow-ups

1. **No new implementation ticket.** Every open product gap already has an owner (ASP-774, ASP-801, ASP-796, ASP-804, ASP-807, ASP-736, ASP-733/769, ASP-780, ASP-672, ASP-725).
2. **Board choice on this issue, not a child:** how this file lands. Paperclip accept did not land PR 87. Do not merge PR 84 or PR 87. Do not answer `b31166d7` with `admin_bypass`.
3. Do not start ASP-777, ASP-796, ASP-780, ASP-807, ASP-725, or ASP-672 from this review.
4. Do not open another re-QA of ASP-733.
5. Do not file next week's review. The routine fires 2026-11-09T09:00Z.

---

## 9. Freeze-aware next week

**Do**

- Land this review only after an explicit board choice (admin merge of **this** PR, or a merge the board performs). Do not treat a Paperclip click as that choice.
- Keep dual-human, vault-on-physical-only, H-018, fleet ACL, the nightly flock, and the QA pin fail-closed text.
- Treat a QA PASS as void when `sourceIssueId` is neither the issue nor its parent.
- Treat Auditor `done` on a QA gate as a contract break (CHG-0029).
- Treat board `done` as void when `git ls-tree origin/master` does not contain the file (ASP-434, ASP-365, ASP-803, ASP-806, ASP-819).
- Treat an unmerged weekly review as not the register (ASP-800 / PR 84, ASP-818 / PR 87).

**Don't**

- Physical arm, live `aa-enforce`, SSH/UFW apply, NATS rotate, or a new credential domain.
- Accept ADR-0012 or file ADR-0011.
- Delete dual-publish.
- Mark ASP-736 done. Use `board.key` to force a status.
- Admin-merge from this wake. Edit branch protection. Weaken `enforce_admins`.
- Approve Summarizer or Reflection Coach. Wake Grok Build. Unarchive ABSA or Content. Wake ABS.
- Merge any open PR in the table above from this review.
- Invoke OpenCode, Aider, or Auditor.

---

## 10. Sign-off

Architecture is coherent. The 10-12 decisions hold. Master did not move for three weeks. The hole is land authority, not a missing ADR: the only collaborator authors the PRs, protection requires a review that author cannot give, and a Paperclip accept does not substitute. Green PRs are waiting on that choice, not on a new design.

**Next weekly:** 2026-11-09T09:00Z. Confirm this file is on `origin/master`. Confirm PR 84 and PR 87 were not merged. Confirm ADR-0012 is still Proposed. Confirm ASP-736 was not closed with `board.key`. Confirm ASP-803, ASP-806, and ASP-819 were not treated as tree without `git ls-tree`.
