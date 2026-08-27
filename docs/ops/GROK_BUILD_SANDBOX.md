# Grok Build sim-prod sandbox

Isolated **build / launch / test** lane for Paperclip pipeline work.  
SoR: `docs/adr/ADR-0009-grok-build-sim-prod-sandbox.md`

## What this is

Grok Build (`grok_local`, grok-4.6) runs against a **git worktree**, not the live operator checkout. Kernel Landlock profile `aspen-sim` limits writes. `ASPEN_SIM=1` + plant-range. Captain + Grok audit; GitHub issues are Aspen's review queue.

## Paths

| Role | Path |
|------|------|
| Live AspenOS | `/home/tech/projects/aspen-dev/repos/aspen-os` |
| Sim-prod worktree | `/home/tech/projects/aspen-dev/sandboxes/aspen-os-sim` |
| Scratch | `/tmp/aspen-sim` |
| Grok sandbox profile | `/home/tech/.grok/sandbox.toml` (`aspen-sim`) |

Paperclip: company **Aspen OS Development** · project **Grok Build Sim-Prod** · agent **Grok Build** `b02d3fba-6393-41bf-befe-c7fe9144a6c2` · env **Sim-Prod Sandbox**.

## Promote a ticket into the lane

1. CE plan exists (`docs/plans/<id>.md`) or the issue already has `CE-GATE` waiver.
2. Success check is named (`make smoke`, a test file, or a launch command).
3. Description includes `Linear: BEL-N` when program-level.
4. Create/move issue on project **Grok Build Sim-Prod**, assign Grok Build, `status: in_progress`.
5. **Do not** also `heartbeat:invoke`. `in_progress` auto-wakes.
6. One wake. If `plan_only` / `missing_disposition`, stop — see `paperclip-board-ops` `references/grok-local-board.md`.

## What Grok Build does on wake

```text
1. Confirm cwd is the sandbox worktree (refuse live asp-* trees).
2. git fetch origin; note HEAD SHA.
3. Build the ticket target.
4. Launch only under ASPEN_SIM=1 / plant-range (no plant-alpha, no hardware).
5. Run the named success check (default: make smoke).
6. Comment a sandbox report on the Paperclip issue (commands, SHA, pass/fail).
7. Set in_review. Do not merge. Do not file GitHub unless the issue says AUDIT: file
   or Captain/Grok already audited.
```

## Captain + Grok audit → GitHub

After the report:

```bash
# from anywhere with gh auth (AbsolutionAI)
/home/tech/projects/aspen-dev/sandboxes/aspen-os-sim/scripts/sandbox-file-github-issue.sh \
  --title "sim-prod: <short finding>" \
  --body-file /tmp/aspen-sim/issue.md
```

Labels applied: `sandbox-audit`, `grok-build`, `sim-prod`, `needs-aspen-review`.  
Template: `.github/ISSUE_TEMPLATE/sandbox-audit.md`.

Aspen reviews those GitHub issues. That is the handoff.

## Refresh the worktree

```bash
cd /home/tech/projects/aspen-dev/sandboxes/aspen-os-sim
git fetch origin
git reset --hard origin/master   # only when no in-flight sandbox commits to keep
```

Do not `git worktree remove` this path — Paperclip cwd depends on it.

## Safety

- `ASPEN_SIM=1` required. Unset → refuse launch.
- plant-range only. Cross-plant schedule into alpha/edge is an architecture fail.
- Landlock deny: Paperclip keys, Hermes `.env`, `~/.ssh`.
- Fiscal freeze: wake-on-demand, no timer heartbeats, no new agent hire.

## Proof

```bash
HOME=/home/tech GROK_HOME=/home/tech/.grok \
  grok inspect   # cwd = worktree; sandbox profile aspen-sim via env

HOME=/home/tech GROK_HOME=/home/tech/.grok GROK_SANDBOX=aspen-sim \
  grok -p "Reply SANDBOX_OK and cwd only." --sandbox aspen-sim \
  --cwd /home/tech/projects/aspen-dev/sandboxes/aspen-os-sim \
  --always-approve --no-plan --max-turns 2 --permission-mode bypassPermissions
```
