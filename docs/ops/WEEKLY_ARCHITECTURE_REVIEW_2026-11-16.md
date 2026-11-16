# Weekly Architecture Review — 2026-11-16

**Issue:** ASP-916
**Reviewer:** aspen (Architect)
**Routine fire:** 2026-11-16T09:00Z (local 2026-11-16 02:00 MST)
**Period:** 2026-10-12 → 2026-11-16 (delta vs the last review **on `origin/master`**, ASP-773). ASP-800, ASP-818, ASP-841, and ASP-872 are incorporated here because none of those files are on master.
**Tree reviewed:** `origin/master` `7403cca98a7d180916dc04dcde1df7148487ebac` (2026-11-14). Confirmed this wake by `git ls-remote https://github.com/AbsolutionAI/AspenOS.git HEAD`. SSH fetch failed (`publickey`). The HTTPS read is the tip.
**SoR:** `docs/sor/MASTER_SPEC.md` (AspenGrove v4.0 — Three Organs)
**Fiscal posture:** unchanged. ASP $50 + BTH $50. Sim-only fleet. Wake-on-demand. Grok for architecture gates only. Grok Build stays terminated.

---

## 1. Executive verdict

| Area | Health | Delta vs 2026-10-12 (master) |
|------|--------|------------------------------|
| Product triad (OS / Sentinel / aspen-dev) | **Green (locked)** | Unchanged. No fourth organ |
| Platform ADRs 0001–0006 | **Green** | Hold |
| ADR-0007 / 0008 / 0009 | **Green (Accepted)** | Hold. No redesign |
| ADR-0010 C11 | **Amber** | Master nightly record still the only fail (p50 3.655 ms at `f179faf`). Do not retune |
| ADR-0011 sunset candidate | **Amber** | Still not filed. No consumer-share measurement |
| ADR-0012 operator-of-record | **Amber (Proposed, steps 1–2 on master)** | Registry + non-sim enrollment check landed (`7403cca`). That is not acceptance. Enrollment is not a proof |
| ADR-0013 worktree isolation | **Green record / policy unchanged** | Live policy re-read. `pin_owner_ok` contract unchanged. Worker file hash moved 2026-11-11. Do not re-decide |
| Agent mesh | **Amber** | CHG-0029 text is on master. Do not invoke. Do not approve Summarizer |
| Fleet / swarm / RRM | **Green (sim)** | Hold. PR 83 / PR 97 are not on master and do not unblock ASP-418 |
| Act gate | **Green (sim) / Amber (binding)** | `light-cell` still skips the registry. `full-plant` requires an enrolled active `human_id`. Missing profile still defaults to `light-cell` |
| Sentinel anomaly (H-015) | **Green (fail-open)** | On master. Still investigate, not a deny |
| LangGraph (ADR-0005) | **Green/Amber** | Hold |
| Memory (ADR-0006) | **Green** | T1 only. PR 79 merged. Loader is not a new organ |
| Update integrity (F-014) | **Green (CI dep)** | PR 50 stayed closed |
| Branch protection | **Red on this read** | Anonymous and authenticated `GET /branches/master` both say `protected: false`. Protection endpoint 404. Rulesets empty. Not edited |
| NATS TLS templates (H-024 P0-2) | **Green (templates)** | Unchanged. Not a live rotate. Not ADR-0012 |
| Packaging / physical cell | **Deferred** | ASP-418 stays blocked. sim_only software only |
| Nightly | **Green on master, record lagging** | `NIGHTLY_LATEST.md` is still ASP-764 PASS 158/159 at `f179faf`. Later nightly PRs are open. ASP-917 finished this wake; its file is not this tree |
| Register hygiene | **Amber** | Four weekly reviews and several board-done claims are still not the tree. This file supersedes those reviews |

**Overall:** The 10-12 decisions hold. The fact those later reviews could not see is that master moved. PR 79 and ADR-0012 steps 1–2 are on `7403cca`. Neither is an acceptance and neither is a new organ. The new hole is the GitHub rule: master reads unprotected. This review does not turn that rule back on.

### Confirmations prior reviews asked for

| Check | Result this wake |
|-------|------------------|
| 10-12 review file on `origin/master` | Yes. `docs/ops/WEEKLY_ARCHITECTURE_REVIEW_2026-10-12.md` is in `7403cca` |
| 10-19 / 10-26 / 11-02 / 11-09 review files on `origin/master` | **No.** `git ls-tree` empty for all four. PR 84, PR 87, PR 90, and PR 93 are OPEN, `merged` false. Heads `2c7dbe1`, `e9b198c`, `ddd1433`, `5fc2712` are not ancestors of `7403cca` |
| ADR-0012 still Proposed | Yes. Status line on `7403cca` still Proposed |
| ASP-733 not closed on the 2026-10-04 PASS | Yes. Still `blocked`. PR 61 still OPEN |
| PR 64 stayed closed | Not re-listed in the open-PR page this wake. Not merged from here |
| ASP-736 not closed since CHG-0034 | Yes. Still `in_review`, unassigned |
| H-024 assessment file on master | **No.** `git ls-tree` empty for `docs/security/H-024-iec-62443-4-2-cell-assessment.md`. ASP-774 still `todo`. PR 44 still OPEN |
| PR 79 landed | **Yes.** API `merged: true`. Master commit `91bb8ff` (GitHub committer). Named head `023c412` is not an ancestor because the land was not a fast-forward of that SHA |
| ADR-0012 step 1+2 landed as `39e720d` | **No.** `39e720d` is not an ancestor. The landed commits are `145477d` and `0a0b26d`, merged at `7403cca`. Binding files match `39e720d`. Do not merge PR 94 |

---

## 2. ADR register

| ADR | Decision | Still valid? | Action |
|-----|----------|--------------|--------|
| ADR-0001 Packaging | Grove layers, MIT/Apache | Yes | Keep |
| ADR-0002 Swarm/RRM | propose_act only; no joint stream from C2 | Yes — hard | Keep sim-only |
| ADR-0003 Bus + G8 | Prefer `aspen.*`; dual-human authorize | Yes | Keep |
| ADR-0004 Light core | Kernel vs plugins | Yes | Gatekeeper stays monorepo shim until extract |
| ADR-0005 LangGraph | Cognitive plugin; Paperclip stays SoR | Yes | Hold |
| ADR-0006 Memory | T1 default; T2 optional | Yes | No PG under freeze. Loader on master is still T1 |
| ADR-0007 Sentinel/C2 subjects | Additive `aspen.sentinel.*` / `aspen.authz.*` | Accepted | Anomaly subject stays fail-open. Not a new ADR |
| ADR-0008 Classification | core / plugin / dev-only | Accepted | H-019 gate stays. PR 59 is not a status flip |
| ADR-0009 Gatekeepers | No broad keys; P1+P2 accepted | Accepted | Packaging target remains plugin `aspen-gatekeeper` |
| ADR-0010 C11 | Spike sandbox | Yes | p50 hw-debt. Do not retune the SLO |
| ADR-0011 (candidate) | Sunset dual-publish | **Not filed** | Still wait for consumer share or an external pilot |
| ADR-0012 OoR binding | NATS `human_id` is SoR; auth binding required before non-sim arm | **Proposed** | **Do not Accept.** Steps 1–2 on master are an enrollment check, not a proof |
| ADR-0013 Worktree isolation | Per-issue `git_worktree`; Hermes `.worktrees/hermes-*` does not count | **Accepted, on master** | Do not re-accept. Do not treat the worker hash move as a design reopen |

### ADR-0012 evidence (this review)

On `7403cca`:

- `src/python/services/operator_registry.py` — local JSON registry, mode `0600`, atomic replace, case-fold uniqueness, corrupt file refuses to write.
- `scripts/operator-registry.py` — enrollment CLI.
- `src/python/gatekeeper/minimal_shim.py` `_check_operator_binding` — `light-cell` returns valid (free strings). Any other profile requires an enrolled `active` operator. Missing or corrupt registry returns `operator_registry_unavailable` (fail-closed for that path).
- Default when profile is omitted is still `light-cell` (`proposal.get("profile", "light-cell")` and `request_capability`). That is the existing sim default, not a new exemption.
- ADR status line and the acceptance checkbox are still Proposed / unchecked.
- Follow-ups 3–6 in the ADR (authorize-subject ACLs, HMI session resolve, Matrix resolve, G9 dry-run) are not on master.

A bus peer who knows an enrolled `human_id` can still publish it. The ADR's threat ("invented principal IDs") is only partly closed. That is why this review does not Accept.

PR 94 (`39e720d`) must not merge. Binding files are identical to `0a0b26d`. The PR tree is not that commit. It also carries `docs/solutions/asp-837-operator-registry.md`, which is not on master. Merging it is not the land.

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

`/home/tech/aspen-dev/scripts/paperclip-aider-worker.py` still fail-closes: missing `executionWorkspaceId` raises `QA_ABORT`; `sourceIssueId` must be the issue or its parent. File mtime 2026-11-11, sha256 `b3686ad1012c9b5fdc583d2fccc8ae3a550684f73f529d163902d8763e8f4098` (was `5ba33fc1…` on 11-09). Contract text matches. Script not edited. ASP-736 stays `in_review`. Do not close it from here.

This wake's cwd is a Hermes worktree (`hermes/hermes-5638311b`). It does not satisfy ADR-0013. The review files are written in `.paperclip/worktrees/ASP-916-weekly-architecture-review`.

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
  │            dashboard/Sentinel, gatekeeper shim (+ vault_gate),
  │            operator registry (local JSON, not a new organ),
  │            tool-anomaly
  └── drivers: MQTT / OPC-UA / ROS2 (last mile)
        ▼
Hardware / sim (ASPEN_SIM=1 · plant-range sim_only until G9)
```

**Boundary violations this period:** none that add an organ.

**Placement, reconfirmed:**

- Operator registry sits in `src/python/services/` and is imported by the gatekeeper shim. It is not a fourth product organ and not the edge-rrm DualHumanGate. Packaging target remains plugin `aspen-gatekeeper`.
- Holographic catalog loader (`91bb8ff`, PR 79) is a MemoryStore read-back. ADR-0006 T1. Not a new store.
- Tool-anomaly consumer stays fail-open. It does not sit on the estop or authorize path.
- H-022 vault gate stays on physical cell acts only.
- Host-path derivation (ASP-733 / PR 61) is still an install boundary, not a new organ. Not closed.
- NATS TLS-by-default remains templates. Not a live listener rotate.

**Sticky risk (unchanged):** `src/python/services` can shadow root `services/`. The new registry lives on the shim import path (`services.operator_registry`). Do not "fix" the shadow inside a safety ticket.

---

## 4. Agent-mesh and bus contracts

| Contract | Canonical | Status |
|----------|-----------|--------|
| Execution workspace | Paperclip `isolated_workspace` + `git_worktree` | **Live.** Unchanged. Hermes session worktrees do not satisfy ADR-0013 |
| QA evidence | Pin `sourceIssueId` is the issue or its parent | **Live in the worker.** Hash moved; contract text did not |
| QA handoff | CHG-0029 encoding in `docs/COMPOUND_ENGINEERING.md` | **On master** since ASP-773. Auditor does not set the gate `done` |
| Control-plane URL | Bound listen address | **Live this run.** `PAPERCLIP_API_URL` = `http://100.78.55.13:3100`. Health `ok`. Do not reorder the allowlist |
| Branch protection | Was 10 required checks, `strict`, `enforce_admins`, 1 review | **This read: unprotected.** Anonymous `protected: false`. Do not edit from an agent heartbeat |
| Fleet register/HB/ops | `aspen.fleet.*` | Monorepo still dual-publishes legacy. Sunset not ready |
| Missions | `aspen.fleet.mission.*` | Unchanged |
| Edge propose / authorize / command | `aspen.edge.<node>.*` | Unchanged |
| Safety estop / clear | `aspen.safety.*` | Dual clear. Watchdog is a second latch |
| Authz | `aspen.authz.*` | Gatekeeper P1+P2. Non-sim authorize now also checks registry enrollment. Not a capability proof |
| Sentinel | `aspen.sentinel.*` | Additive finding subject stays fail-open |
| LangGraph | `aspen.worker.langgraph.*` | propose_act out only |
| Cross-plant ACL | edge → alpha denied | Hold |
| NATS transport | TLS in cell firstboot templates | **Templates on master.** Live rotate stays frozen |

**Mesh roster (this wake):** Grok Build absent. Summarizer still `pending_approval` — do not approve. Reflection Coach is not on the roster. Auditor paused. Aider idle. OpenCode idle after ASP-917 (finished 2026-11-16T09:03Z). This run is the only live heartbeat.

Parallel routines are allowed. Same-issue double-invoke is still a checkout bug. Do not remove the ASP-659 flock.

---

## 5. Pending design decisions

| # | Decision | Recommendation | Urgency |
|---|----------|----------------|---------|
| D1 | Accept ADR-0012? | **No.** Steps 1–2 landed. Steps 3–6 and a non-sim dry-run have not. Enrollment ≠ proof | High only before G9 |
| D2 | File ADR-0011? | **No.** No new consumer-share data | Low |
| D3 | Re-accept ADR-0013? | **No.** Policy and pin contract already match | Closed |
| D4 | Retune C11 p50? | **No** | Deferred |
| D5 | Live GPIO / physical arm / NATS rotate? | **No.** ASP-418 stays blocked | Deferred |
| D6 | Merge PR 94 (ADR-0012 step 2 at `39e720d`)? | **No.** Land already on master as `0a0b26d` via `7403cca`. Binding files match. The PR tree is not that commit | High (wrong land) |
| D7 | Merge PR 84 / 87 / 90 / 93? | **No.** Superseded weeklies. Standing rule. Do not GitHub-close them from this wake | High (register split) |
| D8 | Restore master branch protection from this heartbeat? | **No.** Agent must not edit repo rules unasked. The read says it is off. Jo confirms | High |
| D9 | Treat ASP-434 `done` as the H-024 assessment record? | **No.** File still absent on master. ASP-774 owns the land | Hold |
| D10 | Close ASP-733 on the 2026-10-04 PASS? | **No.** Still blocked. PR 61 still open | Hold |
| D11 | New ADR for the operator registry? | **No.** It is follow-up 1–2 of Proposed ADR-0012 | Closed |
| D12 | Widen the `light-cell` exemption to other sim profile names? | **No.** A future sim profile that is not the string `light-cell` will fail-closed. That is correct until someone files the alias. Do not start it here | Low |

---

## 6. Open issue map (architecture-relevant)

| Cluster | Issues | Disposition |
|---------|--------|-------------|
| This review | **ASP-916** | Docs this heartbeat. Not done until the file is on `origin/master` |
| Prior landed review | ASP-773 | Done. File is on master. Decisions hold |
| Superseded weeklies | ASP-800, ASP-818, ASP-841 cancelled. **ASP-872** blocked on **ASP-844** | Cancel both. Point at ASP-916. Do not merge PR 93 |
| ADR-0012 land | ASP-882 blocked; PR 94 open at `39e720d` | Do not merge. Steps 1–2 are already `145477d`+`0a0b26d` on master |
| ADR-0012 remaining | ASP-777 todo | Still the implementation parent for steps 3–6. Do not start it from this review. Do not Accept |
| Loader land | ASP-788 `in_review`; PR 79 `merged: true` | Do not open a second PR. Ancestor check fails because the land SHA is `91bb8ff`, not `023c412` |
| QA pin | ASP-736 `in_review` | Do not re-close. CHG-0034 stands |
| Host paths | ASP-733 blocked; PR 61 open | Not a new architecture ticket |
| H-024 assessment | ASP-774 todo; PR 44 open | File missing on master. Do not blind-merge |
| H-017 scrub | ASP-801 todo; PR 82 open | `nats/server.conf` on master still has credential keys (1 `token` line plus `users` blocks). Values not printed. Do not merge from here |
| Branch protection | new board child | Jo confirms the unprotected read. Agent does not set the rule |
| Physical / host | ASP-418/435 blocked, ASP-796 todo | Not this review |
| Nightly in flight | ASP-917 done this wake | Not the master record |

---

## 7. Doc hygiene this heartbeat

1. This file.
2. `docs/plans/ASP-916.md`.
3. `docs/architecture/overview.md` last-review pointer. ADR-0012 sentence notes steps 1–2 on master, still Proposed.
4. ADR index: 0012 stays Proposed; weekly pointer moves to this file.
5. ADR-0012 reconfirmation line. No status flip.
6. Do not Accept ADR-0012. Do not file ADR-0011. Do not PATCH execution workspace policy. Do not edit branch protection. Do not edit the Aider worker.

### PRs that must not merge from this review

| PR | Why |
|----|-----|
| 93 | Superseded 2026-11-09 review. This file replaces it |
| 90, 87, 84 | Older superseded weeklies. Already not on master |
| 94 | ADR-0012 step 2 already on master at a different SHA. Binding files match. Merging the old tree is not the land |

Left open on purpose: PR 61 (ASP-733), PR 59 (stalled rule-4 gate), PR 44 (assessment not on master), PR 82 (credential scrub), PR 83/97 (sim_only, not a physical unblock), nightly record PRs. Do not merge them from this wake. Do not GitHub-close any of them.

---

## 8. Follow-ups

1. **Board land of this review only** (child): Jo squash-merges the ASP-916 PR after required checks are green. No admin bypass. A Paperclip confirmation is not a merge. Do not merge PR 84, 87, 90, 93, or 94 in that same click.
2. **Board confirm of master protection** (child): this wake's read says unprotected. If that was not intentional, Jo restores the previous rule. Agent must not set it.
3. No new implementation ticket. ASP-777 remains the ADR-0012 remainder. Do not start it.
4. No new H-024 or H-017 ticket. ASP-774 and ASP-801 already own those lands.

---

## 9. Freeze-aware next week

**Do**

- Land this review on `origin/master` in the same cycle, by Jo squash-merge, not by agent bypass.
- Keep dual-human, vault-on-physical-only, H-018, fleet ACL, the nightly flock, and the QA pin fail-closed.
- Treat ADR-0012 as Proposed until a review Accepts it after a proof, not after an enrollment lookup.
- Treat a QA PASS as void when `sourceIssueId` is neither the issue nor its parent.

**Don't**

- Physical arm, live `aa-enforce`, SSH/UFW apply, NATS rotate, or a new credential domain.
- Accept ADR-0012 or file ADR-0011.
- Delete dual-publish.
- Approve Summarizer. Revive Reflection Coach. Wake Grok Build. Unarchive ABSA or Content. Wake ABS.
- Merge PR 94, 93, 90, 87, or 84.
- Set GitHub branch protection from an agent heartbeat.
- Invoke OpenCode, Aider, or Auditor from this review.

---

## 10. Sign-off

Architecture is coherent. The grove did not gain an organ. Two commits landed that the unmerged weeklies could not see, and neither flips an ADR. The open hole is the register plus the GitHub rule: superseded reviews are still open PRs, and master currently reads unprotected.

**Next weekly:** ~2026-11-23. Confirm this file is on `origin/master`. Confirm ADR-0012 is still Proposed. Confirm PR 94 and PR 93 were not merged. Confirm the branch-protection read was either restored by Jo or explicitly accepted as off.
