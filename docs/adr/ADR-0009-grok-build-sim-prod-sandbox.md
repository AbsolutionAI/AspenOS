# ADR-0009: Grok Build sim-prod sandbox (Paperclip pipeline QA lane)

## Status
Accepted — 2026-08-27  
**Captain directive:** Grok Build builds / launches / tests Paperclip pipeline work in simulated production; Captain + Grok audit last word; GitHub issues are Aspen's review queue.  
**Linear:** BEL-223 (parent eval) · child filed with this ADR  
**Paperclip:** ASP company · agent `Grok Build` (`b02d3fba-…`) · project **Grok Build Sim-Prod**

## Context

Paperclip is the agent control plane. Coding tickets currently land in the live AspenOS checkout (often a dirty feature branch). That is not a production-shaped test surface:

- Live tree ≠ `origin/master`
- No plant-range / `ASPEN_SIM=1` isolation
- Grok Build (`grok_local`) can write the operator checkout
- Failures have no durable audit intake except Paperclip comments

Captain asked for a **sandbox** where **Grok Build** can **build, launch, and test** everything that comes through the Paperclip pipeline, with **Captain + Grok as last-word audit**, filing **GitHub issues** for **Aspen Architect** to review.

Grok Build CLI 1.0.5 already provides kernel sandbox profiles (`--sandbox` / `GROK_SANDBOX`) and git worktrees. Paperclip `grok_local` supports `local` environments; its `sandbox` driver has no usable provider (`fake` unsupported) — do **not** pretend Paperclip leases a VM.

## Decision

### Lane

```
Paperclip pipeline (ASP issues)
        │  assign / promote to Sim-Prod project
        ▼
┌─────────────────────────────────────────────────────────┐
│  Grok Build  (grok_local · grok-4.6)                    │
│  cwd: /home/tech/projects/aspen-dev/sandboxes/aspen-os-sim
│  env: ASPEN_SIM=1  ASPEN_PLANT=plant-range              │
│       GROK_SANDBOX=aspen-sim                            │
│  Landlock profile: ~/.grok/sandbox.toml [aspen-sim]     │
│  Actions: fetch → build → launch sim → smoke/QA         │
│  Never: merge master · arm plant-alpha · physical cell  │
└───────────────────────────────┬─────────────────────────┘
                                │ sandbox report on Paperclip issue
                                ▼
                    Captain + Grok audit (last word)
                                │
                                ▼
              GitHub AbsolutionAI/AspenOS
              labels: sandbox-audit · grok-build · sim-prod · needs-aspen-review
                                │
                                ▼
                    Aspen Architect reviews / ports
```

### Boundaries (do not collapse)

| Layer | Owner | Does |
|-------|-------|------|
| Org / cost SoR | Paperclip + Linear | Tickets, budgets, wake-on-demand |
| Implementation (live tree) | OpenCode / aspen | Feature work on real git roots |
| Sim-prod build/launch/test | **Grok Build** | Isolated worktree + Landlock + `ASPEN_SIM=1` |
| Last-word audit | **Captain + Grok** | Accept / reject sandbox report |
| Review queue | **GitHub issues** | Durable findings for Aspen |
| Architecture / port | **Aspen Architect** | Review GH issues; merge to grove |

This is **not** a fourth product organ. It is a QA execution plugin on aspen-dev (Paperclip company), same layering as ADR-0004/0005.

### Hard rules

1. **Sim only.** `ASPEN_SIM=1`. Origin plant **plant-range**. No physical cell (BEL-192). Safety path remains `propose_act` only.
2. **Isolated checkout.** Grok Build `cwd` is the sandbox worktree, never the live `asp-*` operator branch.
3. **No auto-merge.** Sandbox may commit on `sandbox/*` branches. Master / production refs require Aspen after GH review.
4. **No auto-GitHub without audit.** Grok Build writes a sandbox report on the Paperclip issue. Captain + Grok file (or authorize filing) the GitHub issue.
5. **Wake discipline.** One of `in_progress` assign **or** `heartbeat:invoke` — not both. `wakeOnDemand: true`. Do not loop `plan_only`.
6. **Secrets.** Landlock deny of Paperclip keys, Hermes `.env`, `~/.ssh`. Never paste secrets into issues.
7. **Fiscal freeze.** No new agent hire. Grok Build budget stays the existing ~$15 envelope. Timer heartbeats stay off.

### Host paths

| What | Path |
|------|------|
| Live AspenOS (OpenCode / aspen) | `/home/tech/projects/aspen-dev/repos/aspen-os` |
| Sim-prod worktree | `/home/tech/projects/aspen-dev/sandboxes/aspen-os-sim` |
| Scratch | `/tmp/aspen-sim` |
| Grok profile | `/home/tech/.grok/sandbox.toml` → `aspen-sim` |
| Paperclip env | Instance allows **one** `local` env (existing **Local**). Sim-prod isolation is agent env + worktree + Landlock, not a second Paperclip environment. |

### Promotion contract (Paperclip → sandbox)

A coding ticket is ready for this lane when it has:

1. Spec + `docs/plans/<id>.md` (CE gate) **or** an explicit `CE-GATE` waiver on the issue
2. A concrete success check (`make smoke` target, test path, or launch command)
3. Linear ID when the work is program-level (`Linear: BEL-N`)

Then: create or move a Sim-Prod issue, assign **Grok Build**, set `in_progress` (auto-wake). Do **not** also `heartbeat:invoke`.

### Audit → GitHub

After sandbox report:

- **Pass:** comment evidence (commands, SHA, mtimes); leave `in_review` for Captain.
- **Fail / finding:** Captain + Grok file `AbsolutionAI/AspenOS` issue with labels `sandbox-audit, grok-build, sim-prod, needs-aspen-review` using `.github/ISSUE_TEMPLATE/sandbox-audit.md`.
- Aspen reviews those issues — that is the handoff. Do not silent-recode in the live tree from a sandbox fail.

## Consequences

- Live operator checkout is protected from unattended Grok writes.
- Sim-prod is honest: in-process / worktree ≠ JetStream plant (say so in reports).
- Extra disk for the worktree; refresh with `git fetch` + reset to `origin/master` between tickets unless testing a specific SHA.
- Paperclip `driver=sandbox` remains unused until a real provider exists — do not enable `fake`.

## Alternatives

| Option | Why not |
|--------|---------|
| Point Grok Build at live aspen-os + `--sandbox workspace` | Writes the operator branch; not sim-prod |
| Paperclip `driver=sandbox` | Provider `fake` cannot execute runs |
| New Paperclip company | Fourth organ; freeze forbids staffing |
| Auto-file GitHub from every heartbeat | Skips Captain + Grok last-word audit |

## Follow-ups

- Optional Paperclip **pipeline** `sim-prod` stages (queued → sim_build → audit → github → aspen_review) once ingest is worth automating.
- Extend `/home/tech/projects/aspen-dev/sandboxes/<repo>` for grove packages (swarm, edge-rrm) with the same profile.
- First green `make smoke` on the worktree is the operational proof, not this ADR text.
