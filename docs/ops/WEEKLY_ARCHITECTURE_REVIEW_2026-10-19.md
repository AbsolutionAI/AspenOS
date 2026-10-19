# Weekly Architecture Review — 2026-10-19

**Issue:** ASP-800
**Reviewer:** aspen (Architect)
**Routine fire:** 2026-10-19T09:00Z (local 2026-10-19 03:00 MDT)
**Period:** 2026-10-12 → 2026-10-19 (delta vs the last review **on `origin/master`**, ASP-773)
**Tree reviewed:** `origin/master` `edbc440` (merge of PR 78)
**SoR:** `docs/sor/MASTER_SPEC.md` (AspenGrove v4.0 — Three Organs)
**Fiscal posture:** unchanged. ASP $50 + BTH $50. Sim-only fleet. Wake-on-demand. Grok for architecture gates only. Grok Build stays terminated.

---

## 1. Executive verdict

| Area | Health | Delta vs 2026-10-12 |
|------|--------|---------------------|
| Product triad (OS / Sentinel / aspen-dev) | **Green (locked)** | Unchanged. Nothing new landed on master |
| Platform ADRs 0001–0006 | **Green** | Hold |
| ADR-0007 / 0008 / 0009 | **Green (Accepted)** | Hold. No redesign |
| ADR-0010 C11 | **Amber** | Still the only nightly fail. 10-16 record (not on master) measured p50 3.565 ms. Do not retune |
| ADR-0011 sunset candidate | **Amber** | Still not filed. No consumer-share measurement |
| ADR-0012 operator-of-record | **Amber (Proposed)** | Still correct. TLS templates and the unmerged sim profile do not bind `human_id`. Do not Accept. Do not start ASP-777 |
| ADR-0013 worktree isolation | **Green record / code present / ticket not closed** | Policy unchanged. Worker hash matches the 2026-10-11 comment. Jo reverted the ticket close (CHG-0034). Do not re-decide |
| Agent mesh | **Amber** | CHG-0029 encoding unchanged. Master now requires 1 approving review. Do not bypass with `board.key` |
| Fleet / swarm / RRM | **Green (sim)** | Hold. PR 83 is a sim_only profile, not on master, and does not unblock ASP-418 |
| Act gate | **Green (sim)** | Unchanged. H-022 is not an authenticated principal |
| Sentinel anomaly (H-015) | **Green (fail-open)** | On master, still investigate, not a deny. PR 81 does not touch `fail_open`. Service stays off |
| LangGraph (ADR-0005) | **Green/Amber** | Hold |
| Memory (ADR-0006) | **Green** | T1 only under freeze. PR 79 is a loader, not a new organ, not on master |
| Update integrity (F-014) | **Green (CI dep)** | PR 50 stayed closed |
| Branch protection | **Green, tighter** | Live this wake. 10 required checks, `strict`, `enforce_admins`, **1 approving review** |
| NATS TLS templates (H-024 P0-2) | **Green (templates)** | Unchanged. Not a live rotate. Not ADR-0012 |
| Packaging / physical cell | **Deferred** | ASP-418 / 435 / 383 stay blocked or held |
| Nightly | **Green on master, record lagging** | `NIGHTLY_LATEST.md` is still ASP-764 PASS 158/159 at `f179faf` (2026-10-11). PR 80 is the 2026-10-16 record. Not merged |
| Register hygiene | **Amber** | Two board-done claims are not the tree. H-024 is ASP-774. H-017 is ASP-801. ASP-736 is the reverse: code present, ticket reopened |

**Overall:** Decisions from 10-12 still hold. No architecture-changing commit landed on `origin/master` this period — the only commits after `94e53f7` are the review itself (`7e2a81e`, merge `edbc440`). This week's fact is **close authority**. The 10-12 review treated ASP-736 as done. Jo reverted that close the same day. The worker text is still there. A board `done` is still not a file on master.

### Confirmations the 10-12 review asked for

| Check | Result |
|-------|--------|
| Review file on `origin/master` | Yes. `docs/ops/WEEKLY_ARCHITECTURE_REVIEW_2026-10-12.md` at `edbc440` |
| ADR-0012 still Proposed | Yes |
| ASP-733 not closed on the 2026-10-04 PASS | Yes. Still `blocked`. ASP-769 still `in_review` |
| PR 64 stayed closed | Yes. Closed 2026-10-12T09:08Z. PRs 40, 50, and 66 stayed closed too |

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
| ADR-0012 OoR binding | NATS `human_id` is SoR; auth binding required before non-sim arm | **Proposed** | **Do not Accept.** Do not start ASP-777 from this review |
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

**Close authority, corrected:**

ASP-773 wrote "ASP-736 closed that gap." That overclaimed. On 2026-10-12T17:42Z Jo reverted ASP-736 to `in_review` (CHG-0034). The 2026-10-11 close used `board.key`. That is not a decision by Jo.

This wake re-read `/home/tech/aspen-dev/scripts/paperclip-aider-worker.py`. `sha256` is `5ba33fc1fdc373e9116b8db527d0f620b77bfecebe98fa8b4384e3942f9b53ad`. That matches the 2026-10-11 comment. `pin_owner_ok` is still in the file. The test script hash matches too. The code has not drifted. The ticket is not closed.

Do not mark ASP-736 `done` from this review. Do not edit the worker (it is outside this repo). Do not use `board.key` to force the status. Independent verification is a process gate, not a new ADR. Checkout still does not refresh a stale pin. That remains friction, not a reason to file a second isolation ADR.

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

**Boundary violations on `origin/master` this period:** none. No product commit landed.

**Placement, reconfirmed on master:**

- Tool-anomaly consumer subscribes `aspen.sentinel.audit.event` and publishes `aspen.sentinel.tools.anomaly`. `fail_open: True`. `action_required` is investigate. It does not sit on the estop or authorize path.
- H-022 vault gate stays on physical cell acts only. Estop stays on the plain dual-human path.
- H-023 watchdog stays outside the agent loop. `clear` still requires two distinct authorizers.
- Gatekeeper packaging target remains plugin `aspen-gatekeeper`. Not a second core binary.
- Host-path derivation (ASP-733 / PR 61) is an install boundary, not a new organ. Not closed. PR 61 is BEHIND.
- NATS TLS-by-default (ASP-684) is a firstboot/template default plus a CI job. It is not a live listener rotate and not a new subject family.

**Unmerged slices, not new organs:**

- PR 83 (`config/cells/plant-range-d1.sim.yaml`) is `sim_only: true`, `aspen_sim: true`, `motion_allowed: false`, no hardware blocks, not copied by `build-deb.sh` / `install-daemon.sh`. It does not bind `human_id`. It does not unblock ASP-418. ASP-796 owns it and is unassigned; assignment needs Jo. Do not merge from this review.
- PR 81 hardens the anomaly consumer (TLS/creds connect, stream existence check, fsync, actor cap, deterministic finding id). The diff does not change `fail_open` or `action_required`. Service enablement stays off. ASP-780 owns it (`backlog`).
- PR 79 adds a catalog MemoryStore loader. Head is `023c412`, one commit after `c360049`. ASP-788 owns the land and still names `c360049` as the required ancestor. Not a new memory tier. Do not merge from here.

**Sticky risk (unchanged):** `src/python/services` can shadow root `services/`. Do not "fix" that inside a safety ticket.

---

## 4. Agent-mesh and bus contracts

| Contract | Canonical | Status |
|----------|-----------|--------|
| Execution workspace | Paperclip `isolated_workspace` + `git_worktree` | **Live.** Unchanged this wake. Hermes session worktrees do not satisfy ADR-0013 |
| QA evidence | Pin `sourceIssueId` is the issue or its parent; named SHA is an ancestor of `HEAD` | **Text present in the worker.** Ticket ASP-736 is `in_review`, not `done` (CHG-0034) |
| QA handoff | One QA-gate child, parent `blocked` on that child | **Unchanged (CHG-0029).** Auditor does not set the gate `done` |
| Control-plane URL | Bound listen address, not `allowedHostnames[0]` | **Live this run.** `PAPERCLIP_API_URL` = `http://100.78.55.13:3100`. Health HTTP 200. Do not reorder the allowlist. Do not set `server.bind=lan` |
| Branch protection | 10 required checks, `strict`, `enforce_admins`, 1 approving review | **Live.** Re-read this wake. Not edited. This is why green PRs sit `BLOCKED` |
| Close authority | Jo, or the CE chain. Not `board.key` | **CHG-0034.** Do not force `done` or a merge from an agent heartbeat |
| Fleet register/HB/ops | `aspen.fleet.*` | Monorepo still dual-publishes legacy. Sunset not ready |
| Missions | `aspen.fleet.mission.*` | Unchanged |
| Edge propose / authorize / command | `aspen.edge.<node>.*` | Unchanged |
| Safety estop / clear | `aspen.safety.*` | Dual clear. Watchdog is a second latch |
| Authz | `aspen.authz.*` | Gatekeeper P1+P2. Vault row is additional for physical acts only |
| Sentinel | `aspen.sentinel.*` | Additive finding subject stays fail-open. Stream already binds `aspen.sentinel.>` |
| LangGraph | `aspen.worker.langgraph.*` | propose_act out only |
| Cross-plant ACL | edge → alpha denied | Hold |
| NATS transport | TLS in cell firstboot templates | **Templates on master.** Live rotate on bt-asp-srv stays frozen |
| NATS config secrets (H-017) | No literal creds in `nats/server.conf` | **Not true on master.** ASP-365 `done` is not the tree. PR 82 is the scrub. PR 18 is not |

**Mesh roster (this wake):** Grok Build absent. Summarizer still `pending_approval` — do not approve. Reflection Coach is not on the roster. OpenCode idle (last heartbeat 2026-10-19T08:22Z) — do not invoke. Aider idle since 2026-10-14. Auditor idle since 2026-10-14. Runtime paused. Compliance paused. This run is the aspen heartbeat for ASP-800.

Parallel routines are allowed. Same-issue double-invoke is still a checkout bug. Do not remove the ASP-659 flock.

### GitHub review gate (new this period)

PR 78 merged 2026-10-12T09:11Z with zero reviews, by `AbsolutionAI`. Today's protection requires `required_approving_review_count: 1` and `enforce_admins: true`. Open PRs 44, 59, 79, 80, 81, 82, and 83 are MERGEABLE with the ten required checks green, and `mergeStateStatus` BLOCKED.

That is a process gate, not a new ADR. Do not edit the rule from an agent heartbeat. Do not use `board.key` to skip it. CHG-0031 (agents cannot merge) stays backlog. Do not start it from here.

---

## 5. Pending design decisions

| # | Decision | Recommendation | Urgency |
|---|----------|----------------|---------|
| D1 | Accept ADR-0012? | **No.** ASP-777 is the implementation ticket for before a non-sim arm. Do not start it | High only before G9 |
| D2 | File ADR-0011? | **No.** No new consumer-share data | Low |
| D3 | Re-accept ADR-0013, or reopen the design because ASP-736 is `in_review`? | **No.** Record and policy match. Worker text is present. The reopen is close authority (CHG-0034), not a new design | Closed as a design question |
| D4 | Retune C11 p50? | **No.** 3.565 ms on the unmerged 10-16 record is the same known miss | Deferred |
| D5 | Live GPIO / physical arm / NATS rotate? | **No.** ASP-418 and siblings stay blocked. Host rotate stays frozen | Deferred |
| D6 | Merge the superseded CE / nightly / signature PRs? | **No.** 40, 50, 64, 66 stayed closed. Leave them closed | Closed |
| D7 | Treat the 2026-10-04 ASP-733 PASS as evidence? | **No.** Still void. ASP-733 is `blocked`. PR 61 is BEHIND | Hold |
| D8 | Touch branch protection? | **No.** It is live, including the new 1-review rule | Closed as a design question |
| D9 | Treat ASP-434 `done` as the H-024 assessment record? | **No.** File still absent from `git ls-tree origin/master`. ASP-774 owns the land. PR 44 is BLOCKED, checks green | High (false-done vs tree) |
| D10 | Treat ASP-365 `done` as the H-017 scrub record? | **No.** Literal `password` / `token` keys remain on master. ASP-801 owns the land via PR 82. Do not merge PR 18 | High (false-done vs tree) |
| D11 | New ADR for the anomaly consumer, or enable it as a service? | **No.** Fail-open under Accepted ADR-0007. PR 81 does not flip that. ASP-780 owns the hardening | Closed |
| D12 | Merge PR 83 and call D1 unblocked? | **No.** The profile is sim-only and allowed as a later software slice. It does not authorize physical D1. Assignment needs Jo | Hold |
| D13 | Merge PR 79 / 80 / 59 from this review? | **No.** ASP-788, ASP-791, and ASP-672 already own those lands | Hold |

---

## 6. Open issue map (architecture-relevant)

| Cluster | Issues | Disposition |
|---------|--------|-------------|
| This review | **ASP-800** | Docs this heartbeat. Not done until the file is on `origin/master` |
| Prior landed review | ASP-773 | Done. File is on master. Its ASP-736 close sentence is corrected above |
| Next weekly | routine `3da2ac30`, cron `0 9 * * 1` UTC | Next fire **2026-10-26T09:00Z**. Do not file a duplicate |
| QA pin ticket | **ASP-736** `in_review`, unassigned | Code present, hash unchanged. Do not close from here. Do not re-decide ADR-0013 |
| Host paths | **ASP-733** blocked; **ASP-769** `in_review`; PR 61 BEHIND | Not a new architecture ticket. Do not approve on the 2026-10-04 PASS |
| H-024 assessment | **ASP-774** `todo`, unassigned; PR 44 open | Already the follow-up. Do not duplicate. Do not blind-merge |
| H-017 scrub | **ASP-801** `todo`, unassigned; PR 82 open; PR 18 CONFLICTING | New this review. Land 82 after a human review. Do not merge 18 |
| ADR-0012 implementation | **ASP-777** `todo`, unassigned | Exists. Do not start. Not an acceptance |
| D1 sim profile | **ASP-796** `todo`, unassigned; PR 83 open | Software-only. Does not unblock ASP-418. Assignment needs Jo |
| Anomaly hardening | **ASP-780** `backlog`; PR 81 open | Before service enablement. Not a contract flip |
| Memory loader land | **ASP-788** `in_review`; PR 79 head `023c412` | Not this review. Honor the ancestor rule already on ASP-788 |
| Rule-4 classification gate | ASP-672 `in_review`, unassigned; PR 59 | Stalled execution of an accepted ADR. Not a status flip |
| Empty-blocker resolver | ASP-725 `todo` | Server change. Do not start from this review |
| Nightly record | ASP-791 `in_review` (PR 80); ASP-771 blocked; ASP-797 / ASP-799 blocked | Master record is still 2026-10-11. Do not merge a nightly from here |
| Physical / host | ASP-418 / 435 blocked, ASP-383 deferred | Not this review |
| Agent merge containment | ASP-778 `backlog` (CHG-0031) | Do not auto-assign. Do not start |

---

## 7. Doc hygiene this heartbeat

1. This file.
2. `docs/plans/ASP-800.md`.
3. `docs/architecture/overview.md` last-review pointer, and the ADR-0013 bullet corrected for CHG-0034.
4. ADR index: 0012 stays Proposed; 0013 row notes the reverted close; weekly pointer moves.
5. ADR-0012 reconfirmation line. ADR-0013 errata addendum. No status flip.
6. Do not Accept ADR-0012. Do not file ADR-0011. Do not PATCH execution workspace policy. Do not edit branch protection. Do not edit the Aider worker.

### PRs left open on purpose

| PR | Why it must not merge from this review |
|----|----------------------------------------|
| 18 | CONFLICTING wide tree. Not the H-017 scrub. PR 82 is |
| 29 | CONFLICTING packaging forward-port. PR 83 already extracted the sim profile |
| 36 | CONFLICTING fleet-bus smoke. Not reviewed line-by-line |
| 44 | H-024 assessment. ASP-774 owns it. BLOCKED on the review rule |
| 51 | Learning doc, BEHIND. Not a register split |
| 59 | Stalled ADR-0008 rule-4 gate. ASP-672 owns it |
| 61 | ASP-733 host paths. BEHIND. ASP-769 owns the re-QA |
| 79 | Memory loader. ASP-788 owns the SHA rule |
| 80 | Nightly record. ASP-791 owns it |
| 81 | Anomaly hardening. ASP-780 owns it. Service stays off |
| 82 | H-017 scrub. ASP-801 owns it. Needs a human review |
| 83 | sim_only D1 profile. ASP-796 owns it. Assignment needs Jo |

Closed and still closed: 40, 50, 64, 66.

---

## 8. Follow-ups

1. **ASP-774** (already open, child of ASP-773) — land the H-024 assessment. Do not duplicate.
2. **ASP-801** (new, child of this review) — land the H-017 scrub from PR 82. Do not merge PR 18. Do not rotate live NATS. Do not print secret values.
3. No other new architecture ticket.
4. Do not open a third re-QA of ASP-733. Do not start ASP-777, ASP-796, ASP-780, ASP-725, or ASP-672 from this review.
5. Do not file next week's review. The routine fires 2026-10-26T09:00Z.

---

## 9. Freeze-aware next week

**Do**

- Land this review on `origin/master` only with a human approving review if the protection rule still requires one. Do not bypass it.
- Keep dual-human, vault-on-physical-only, H-018, fleet ACL, the nightly flock, and the QA pin fail-closed text.
- Treat a QA PASS as void when `sourceIssueId` is neither the issue nor its parent.
- Treat Auditor `done` on a QA gate as a contract break (CHG-0029).
- Treat board `done` as void when `git ls-tree origin/master` does not contain the file (ASP-434, ASP-365).

**Don't**

- Physical arm, live `aa-enforce`, SSH/UFW apply, NATS rotate, or a new credential domain.
- Accept ADR-0012 or file ADR-0011.
- Delete dual-publish.
- Mark ASP-736 done. Use `board.key` to force a status or a merge.
- Approve Summarizer. Revive Reflection Coach. Wake Grok Build. Unarchive ABSA or Content. Wake ABS.
- Merge PR 18, 29, 36, 44, 59, 61, 79, 80, 81, 82, or 83 from this review.
- Set GitHub branch protection from an agent heartbeat.
- Invoke OpenCode, Aider, or Auditor from this review.

---

## 10. Sign-off

Architecture is coherent. The 10-12 decisions hold. Master did not move. The correction is authority: ASP-736's worker text is present and its ticket close was reverted; two board-done security files are still not on master. Green PRs are waiting on a human review, not on a new design.

**Next weekly:** 2026-10-26T09:00Z. Confirm this file is on `origin/master`. Confirm ADR-0012 is still Proposed. Confirm ASP-736 was not closed with `board.key`. Confirm ASP-774 and ASP-801 were not marked done without `git ls-tree` evidence.
