# Weekly Architecture Review — 2026-11-09

**Issue:** ASP-872
**Reviewer:** aspen (Architect)
**Routine fire:** 2026-11-09T09:00Z (local 2026-11-09 02:00 MST)
**Period:** 2026-10-12 → 2026-11-09 (delta vs the last review **on `origin/master`**, ASP-773). ASP-800, ASP-818, and ASP-841 are incorporated here because none of those files are on master.
**Tree reviewed:** `origin/master` `edbc4408390c94727e6e8089199e7a61432cb409` after `git fetch origin master` this wake.
**SoR:** `docs/sor/MASTER_SPEC.md` (AspenGrove v4.0 — Three Organs)
**Fiscal posture:** unchanged. ASP $50 + BTH $50. Sim-only fleet. Wake-on-demand. Grok for architecture gates only. Grok Build stays terminated.

---

## 1. Executive verdict

| Area | Health | Delta vs 2026-10-12 (master) |
|------|--------|------------------------------|
| Product triad (OS / Sentinel / aspen-dev) | **Green (locked)** | Unchanged. No product commit on master |
| Platform ADRs 0001–0006 | **Green** | Hold |
| ADR-0007 / 0008 / 0009 | **Green (Accepted)** | Hold. No redesign |
| ADR-0010 C11 | **Amber** | Still the only nightly fail on the master record (p50 3.655 ms at `f179faf`). Do not retune |
| ADR-0011 sunset candidate | **Amber** | Still not filed. No consumer-share measurement |
| ADR-0012 operator-of-record | **Amber (Proposed)** | Still correct. Do not Accept. Do not start ASP-777 |
| ADR-0013 worktree isolation | **Green record / code present / ticket not closed** | Policy unchanged. Worker hash unchanged. ASP-736 still `in_review`. Do not re-decide |
| Agent mesh | **Amber** | CHG-0029 unchanged. OpenCode is running ASP-873. Do not invoke |
| Fleet / swarm / RRM | **Green (sim)** | Hold. PR 83 is still sim_only and not on master. It does not unblock ASP-418 |
| Act gate | **Green (sim)** | Unchanged. H-022 is not an authenticated principal |
| Sentinel anomaly (H-015) | **Green (fail-open)** | On master, still investigate, not a deny. PR 81 does not flip that. Service stays off |
| LangGraph (ADR-0005) | **Green/Amber** | Hold |
| Memory (ADR-0006) | **Green** | T1 only under freeze. PR 79 is a loader, not a new organ, not on master |
| Update integrity (F-014) | **Green (CI dep)** | PR 50 stayed closed, not merged |
| Branch protection | **Green, and it is why the register froze** | Live this wake. 10 required checks, `strict`, `enforce_admins`, 1 approving review. Sole collaborator is AbsolutionAI (admin) |
| NATS TLS templates (H-024 P0-2) | **Green (templates)** | Unchanged. Not a live rotate. Not ADR-0012 |
| Packaging / physical cell | **Deferred** | ASP-418 stays blocked. sim_only software only. ASP-796 owns that ticket |
| Nightly | **Green on master, record lagging** | `NIGHTLY_LATEST.md` is still ASP-764 PASS 158/159 at `f179faf` (2026-10-11). Later nightly PRs are not merged |
| Register hygiene | **Red on land, Amber on design** | Master froze at `edbc440` on 2026-10-12. Three weekly reviews are not the tree. This file supersedes them |

**Overall:** Decisions from 10-12 still hold. No architecture-changing commit landed after the 10-12 review itself. This week's fact is the **supersede rule**, not a new organ. Board addendum 2026-11-05: a newer weekly cancels the older Paperclip issue; a superseded weekly does not land; agents do not GitHub-close those PRs; agents do not request admin bypass. ASP-841 is still `in_review`. That is the duplicate this wake closes on the board, not on GitHub.

### Confirmations prior reviews asked for

| Check | Result this wake |
|-------|------------------|
| 10-12 review file on `origin/master` | Yes. `docs/ops/WEEKLY_ARCHITECTURE_REVIEW_2026-10-12.md` at `edbc440` |
| 10-19 / 10-26 / 11-02 review files on `origin/master` | **No.** `git ls-tree` empty for all three. PR 84, PR 87, and PR 90 are OPEN, `merged_at` null, `mergeable_state=blocked` |
| ADR-0012 still Proposed | Yes. Status line on master still Proposed |
| ASP-733 not closed on the 2026-10-04 PASS | Yes. Still `blocked`. ASP-769 is `blocked`. PR 61 is `behind` |
| PR 64 stayed closed | Yes. Closed, `merged_at` null. PRs 40, 50, and 66 the same |
| ASP-736 not closed since CHG-0034 | Yes. Still `in_review`, unassigned. Worker sha256 still `5ba33fc1fdc373e9116b8db527d0f620b77bfecebe98fa8b4384e3942f9b53ad` |
| ASP-774 / ASP-801 not done without `git ls-tree` | Yes. Both still `todo`. Assessment file absent. `nats/server.conf` on master still has 3 nonempty credential keys (1 `token`, 2 `user`). Values not printed |
| Board `done` is not the tree | `bandit` is absent from master `.github/workflows/ci.yml`. `docs/SECURITY_THREAT_MODEL_v2.2.md` is the threat-model file on master. No v2.3 or v2.4 file. `86caa33` is not an ancestor of `origin/master` |

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
| ADR-0010 C11 | Spike sandbox | Yes | p50 hw-debt. Do not retune the SLO |
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

`/home/tech/aspen-dev/scripts/paperclip-aider-worker.py` sha256 is `5ba33fc1fdc373e9116b8db527d0f620b77bfecebe98fa8b4384e3942f9b53ad`. `pin_owner_ok` is present. Script not edited. ASP-736 stays `in_review`. The ASP-773 errata that said the ticket was closed was the overclaim. The worker text is the record. Checkout still does not refresh a stale pin.

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

**Boundary violations this period:** none that changed the grove. Nothing new landed on `origin/master`.

**Placement, reconfirmed from the master tree plus open PRs that must not be treated as landed:**

- Tool-anomaly consumer stays fail-open and off the estop / authorize path. Service stays off.
- H-022 vault gate stays on physical cell acts only. Estop stays on the plain dual-human path.
- Gatekeeper packaging target remains plugin `aspen-gatekeeper`. Not a second core binary.
- Host-path derivation (ASP-733 / PR 61) is an install boundary, not a new organ. Not closed. PR 61 is `behind`.
- NATS TLS-by-default on master is a template default. It is not a live listener rotate and not ADR-0012.
- D1 sim profile (PR 83 / ASP-796) is software-only. It does not authorize physical D1.
- F-017 fingerprint (PR 88 / ASP-804) is a design + fixture. Not a live enroll. Not on master.
- Catalog MemoryStore loader (PR 79, and the later PR 91 / ASP-865) is not a new memory tier. Not on master.

**Sticky risk (unchanged):** `src/python/services` can shadow root `services/`. Do not "fix" that inside a safety ticket.

---

## 4. Agent-mesh and bus contracts

| Contract | Canonical | Status |
|----------|-----------|--------|
| Execution workspace | Paperclip `isolated_workspace` + `git_worktree` | **Live.** Unchanged this wake. Hermes session worktrees do not satisfy ADR-0013 |
| QA evidence | Pin `sourceIssueId` is the issue or its parent; named SHA is an ancestor of `HEAD` | **Live in the worker.** Ticket ASP-736 is not closed |
| QA handoff | One QA-gate child, parent `blocked` on that child. Auditor never sets the gate `done` | **Live (CHG-0029).** Do not merge a PR that puts the old text back |
| Control-plane URL | Bound listen address `http://100.78.55.13:3100` | Used this run. Do not reorder `allowedHostnames`. Do not set `server.bind=lan` |
| Land authority | Jo squash-merge after required checks are green. No admin bypass | **Standing rule (board addendum 2026-11-05, restated 2026-11-06).** A Paperclip accept is not a GitHub review. An agent must not `--admin` |
| Superseded weekly | Newer review cancels the older Paperclip issue. The older PR does not land | **This wake.** Do not GitHub-close those PRs from an agent heartbeat |
| Branch protection | 10 required checks, `strict`, `enforce_admins`, 1 approving review | **Live.** Contexts: lint, security-devonly-isolation, verify-package-signature, security-model-digests, python-test-suite, security-nats-tls, smoke, build-go, build-rust, build-c11 |
| Collaborators | AbsolutionAI is the only collaborator, role admin | Re-read this wake. A normal approving review of an AbsolutionAI-authored PR is impossible |
| Fleet register/HB/ops | `aspen.fleet.*` | Monorepo still dual-publishes legacy. Sunset not ready |
| Safety estop / clear | `aspen.safety.*` | Dual clear. Watchdog is a second latch |
| Authz | `aspen.authz.*` | Gatekeeper P1+P2. Vault row is additional for physical acts only |
| Sentinel | `aspen.sentinel.*` | Additive finding subject stays fail-open |
| NATS transport | TLS in cell firstboot templates | **Templates on master.** Live rotate stays frozen |
| NATS config secrets (H-017) | No literal creds in `nats/server.conf` | **Not true on master.** 3 nonempty credential keys. Values not recorded. ASP-801 owns the scrub via PR 82. Do not merge PR 18 |

**Mesh roster (this wake):** Grok Build absent. Summarizer and Reflection Coach still `pending_approval` — do not approve. Runtime and Compliance paused. Aider idle. Auditor idle. OpenCode `running` on ASP-873 (nightly). This run is the aspen heartbeat for ASP-872. Do not invoke OpenCode, Aider, or Auditor.

Parallel routines are allowed. Same-issue double-invoke is still a checkout bug. Do not remove the ASP-659 flock.

### Land path (standing rule, not a new decision)

1. This file is the register. PR 84, PR 87, and PR 90 are superseded. Do not merge them.
2. Jo squash-merges **this** PR after required checks are green. No admin bypass. Agents do not merge.
3. Agents do not GitHub-close PR 84, PR 87, or PR 90. Jo already owns the unmerged close of 84 and 87. PR 90 joins that list because it is now superseded. That is the existing rule, not a new ask.
4. A Paperclip confirmation accept is not a merge. Do not mark this issue `done` until `git rev-parse origin/master` is a new SHA and `git ls-tree` shows this file.
5. PR 90 head `ddd1433`: smoke check-run `127701084938` completed **failure**; the other nine required checks completed **success**. This wake did not re-read the job log (blob auth rejected). The 2026-11-06 board note attributed that failure to `C11 p50 under 2ms`. Do not retune the gate here. A docs-only PR can fail that same check. Hold the land until smoke is actually green.

---

## 5. Pending design decisions

| # | Decision | Recommendation | Urgency |
|---|----------|----------------|---------|
| D1 | Accept ADR-0012? | **No.** Nothing this period bound `human_id` to an authenticated operator | High only before G9 |
| D2 | File ADR-0011? | **No.** No consumer-share data | Low |
| D3 | Re-accept ADR-0013 or close ASP-736? | **No.** Record and worker text match. The ticket close was reverted | Closed as a design question |
| D4 | Retune C11 p50? | **No.** Known hardware deviation on the master nightly record | Deferred |
| D5 | Live GPIO / physical arm / NATS rotate? | **No.** sim_only software only. Do not clear the ASP-418 done-blocker edge | Deferred |
| D6 | Merge PR 84, PR 87, or PR 90? | **No.** Superseded by this file. Merging any of them splits the latest-review pointer | High (register truth) |
| D7 | Treat the 2026-11-06 "land PR 90" note as still current? | **No.** That note was correct while ASP-841 was the current review. This file supersedes it. Comment the rule. Do not open a new board choice | Closed |
| D8 | Admin-merge from this wake? | **No.** Jo rejected admin bypass. Do not edit branch protection | Closed |
| D9 | Treat board `done` as the tree without `git ls-tree`? | **No.** Assessment file, v2.3/v2.4 threat model, and `bandit` in `ci.yml` are absent from `origin/master` | High (false-done vs tree) |
| D10 | New ADR for the land-authority gap? | **No.** Operating fact, not a product organ. Do not file ADR-0014 | Closed |
| D11 | Merge PR 91, 88, 83, 82, 79, 61, or 59 from this review? | **No.** Each already has an owner. Not a register decision | Hold |

---

## 6. Open issue map (architecture-relevant)

| Cluster | Issues | Disposition |
|---------|--------|-------------|
| This review | **ASP-872** | Docs this heartbeat. Not `done` until this file is on `origin/master` |
| Prior landed review | ASP-773 | Done. File is on master. Its ASP-736 close sentence is corrected in the ADR-0013 errata |
| Superseded unlanded reviews | **ASP-800** cancelled; **ASP-818** cancelled; **ASP-841** `in_review` (PR 90) | Cancel ASP-841 this wake. Do not merge PR 84, 87, or 90. Do not GitHub-close them from here |
| Land path | **ASP-844** `todo`, parent was ASP-841 | Retarget to this PR. Existing board ticket. Not a new decision |
| QA pin ticket | **ASP-736** `in_review`, unassigned | Code present, hash unchanged. Do not close from here |
| Host paths | **ASP-733** blocked; **ASP-769** blocked (GET `blockedBy` empty); PR 61 `behind` | Not a new ticket. Do not approve on the 2026-10-04 PASS. Do not repair the empty edge from this review |
| H-024 assessment | **ASP-774** `todo`; PR 44 open, `blocked` | Already the follow-up. File still absent. Do not duplicate |
| H-017 scrub | **ASP-801** `todo`; PR 82 open, `blocked`; PR 18 `dirty` | Already the follow-up. Do not merge 18. Do not print secret values. Do not rotate live NATS |
| ADR-0012 implementation | **ASP-777** `todo`, unassigned | Exists. Do not start |
| D1 sim profile | **ASP-796** `todo`; PR 83 open | Software-only. Does not unblock ASP-418 |
| Anomaly hardening | **ASP-780** `backlog`; PR 81 open | Before service enablement |
| Memory loader | **ASP-788** `in_review` (PR 79); **ASP-865** `blocked` (PR 91) | Not this review. Do not merge |
| Threat model | **ASP-802** `in_review` (PR 85) | v2.3 is not on master |
| Rule-4 gate | ASP-672 `in_review`; PR 59 | Stalled execution of an accepted ADR. Not a status flip |
| Empty-blocker resolver | ASP-725 `todo` | Server change. Do not start from this review |
| Nightly in flight | **ASP-873** `in_progress` (OpenCode) | Do not invoke. Do not merge a nightly from here. Master record is still 2026-10-11 |
| Physical / host | ASP-418 blocked by done ASP-650; ASP-435 blocked; ASP-383 blocked | Leave the stale edge. Clearing it unblocks the wrong work |

---

## 7. Doc hygiene this heartbeat

1. This file.
2. `docs/plans/ASP-872.md`.
3. `docs/architecture/overview.md` last-review pointer, and the ADR-0013 bullet corrected for the reverted ticket close.
4. ADR index: 0012 stays Proposed; 0013 row notes the ticket is not closed; weekly pointer moves to this file.
5. ADR-0012 reconfirmation line. ADR-0013 errata addendum. No status flip.
6. Do not Accept ADR-0012. Do not file ADR-0011 or ADR-0014. Do not PATCH execution workspace policy. Do not edit branch protection. Do not edit the Aider worker. Do not edit the threat model.

### PRs left open on purpose

Do not merge any of these from this review. Do not GitHub-close them from this review.

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
| 84 | 10-19 review. Superseded |
| 85 | Threat model v2.3. Not on master |
| 86 | Nightly record 2026-10-22 |
| 87 | 10-26 review. Superseded |
| 88 | F-017 fingerprint. ASP-804 owns it. Not a live enroll |
| 89 | Nightly record. Not today's in-flight run |
| 90 | 11-02 review. Superseded by this file |
| 91 | Catalog loader land (ASP-865). Not a new organ |

Closed and still unmerged: 40, 50, 64, 66.

---

## 8. Follow-ups

1. **No new implementation ticket.** Open product gaps already have owners (ASP-774, ASP-801, ASP-796, ASP-804, ASP-736, ASP-733/769, ASP-780, ASP-672, ASP-725, ASP-777).
2. **Cancel ASP-841** this wake. Point the comment at ASP-872. Do not GitHub-close PR 90.
3. **Retarget ASP-844** to this PR. It is the existing land-path ticket. Do not open a second board decision. Standing rule: Jo squash-merges after smoke is green; no admin bypass; do not land 84, 87, or 90.
4. Do not start ASP-777, ASP-796, ASP-780, ASP-725, or ASP-672 from this review.
5. Do not open another re-QA of ASP-733.
6. Do not file next week's review.

---

## 9. Freeze-aware next week

**Do**

- Land this review only by Jo squash-merge after required checks are green. Cite the new `origin/master` SHA before calling it merged.
- Keep dual-human, vault-on-physical-only, H-018, fleet ACL, the nightly flock, and the QA pin fail-closed text.
- Treat a QA PASS as void when `sourceIssueId` is neither the issue nor its parent.
- Treat Auditor `done` on a QA gate as a contract break (CHG-0029).
- Treat board `done` as void when `git ls-tree origin/master` does not contain the file.
- Treat an unmerged weekly review as not the register.

**Don't**

- Physical arm, live `aa-enforce`, SSH/UFW apply, NATS rotate, or a new credential domain.
- Accept ADR-0012 or file ADR-0011.
- Delete dual-publish.
- Mark ASP-736 done. Use `board.key` to force a status.
- Admin-merge. Edit branch protection. Weaken `enforce_admins`.
- Approve Summarizer or Reflection Coach. Wake Grok Build. Unarchive ABSA or Content. Wake ABS.
- Merge any open PR in the table above from this review.
- GitHub-close PR 84, 87, or 90 from an agent heartbeat.
- Invoke OpenCode, Aider, or Auditor.

---

## 10. Sign-off

Architecture is coherent. The 10-12 decisions hold. Master has not moved for four weeks. The hole is still land authority, not a missing ADR. The new fact is procedural: three unlanded weeklies were stacking `in_review` decisions, and the standing rule is to cancel the Paperclip issue and not land the old PR. This file is the register. PR 90 is not.

**Next weekly:** ~2026-11-16. Confirm this file is on `origin/master` and cite the new SHA. Confirm PR 84, PR 87, and PR 90 were not merged. Confirm ADR-0012 is still Proposed. Confirm ASP-736 was not closed. Confirm ASP-841 is `cancelled`.
