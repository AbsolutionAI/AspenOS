# GitHub CI / smoke-test inbox review

**For:** Josiah (morning review)  
**Prepared:** 2026-08-24 22:30 MDT  
**Org / identity:** `AbsolutionAI` (user, not an org) — 35 public repos  
**Unread notifications at snapshot:** 50 (all `ci_activity` / CheckSuite)

This is a **review document**, not a fix pass. No workflows were disabled and no notifications were marked read.

---

## Bottom line

The inbox is **not** 35 repos all red right now.

| What it looks like | What it actually is |
|---|---|
| “Everything is failing smoke” | **Default-branch latest run is green on 31/35 repos.** Only **`agnetic-os` is still red** on `main`. |
| 50 unread GitHub emails | **43 are AspenOS** CheckSuite failures on **Hermes/agent PR branches**, plus a handful of **stale product-kit failures from Aug 2–6** that already have a later green run. |
| Smoke is “broken” | Two **real, clustered defects** (AspenOS NATS + C11 help-text; product-kit CI too strict / incomplete scaffolds). Most were **fixed on `master` after the fact**; open PRs and unread mail were not cleaned up. |

**Recommended morning decision:** treat this as an **inbox + PR hygiene** problem first, then a **small CI contract** fix — not a grove-wide rewrite.

---

## Inbox composition (live unread)

Snapshot via `GET /notifications` (1 page, 50 items, all unread):

| Repo | Unread | What they are |
|---|---:|---|
| `AbsolutionAI/AspenOS` | **43** | “Starship OS CI workflow run failed for \<branch\>” — almost all `hermes/*`, plus `docs/asp-427-land-sor-adrs`, `ox/packaging-hygiene` |
| `AbsolutionAI/saas-starter-kit` | 4 | Master CI failures **2026-08-02** (later master run **green** 2026-08-06) |
| `AbsolutionAI/api-boilerplate` | 2 | Master CI failures **2026-08-02 / 08-06** (later master run **green**) |
| `AbsolutionAI/aspen-contracts` | 1 | Master smoke fail **2026-08-06** (later master run **green**) |

GitHub does **not** auto-dismiss CheckSuite failure mail when a later commit on another branch goes green. Watching the user `AbsolutionAI` means every failed run on every PR is a notification.

**Open AspenOS PRs:** **25** (issues+PRs count 25). Almost all `hermes/*` from the Aug 23 implementation-sweep farm. Each PR to `master` retriggers Starship OS CI even for docs-only titles.

---

## Default-branch health (latest run)

Inventory: last 20 workflow runs per repo (`gh` API, 2026-08-24 night).

| Bucket | Repos |
|---|---|
| Latest run **success** | 31 (AspenOS `master` included — last green `1ccf0009` merge of PR **#15** `ox/packaging-hygiene` at 2026-08-24 19:09 UTC) |
| Latest run **failure** | **`agnetic-os`** only |
| No Actions at all | `fleetmdm`, `gumroad-assets`, `worldmonitor` |

Recent-fail *history* (still useful — these are what filled the inbox):

| Repo | Fails in last 20 | Latest now | Dominant cause (from job logs) |
|---|---:|---|---|
| AspenOS | 15 | **success** | smoke `nats-server` + C11 `--help` grep |
| agnetic-os | 19 | **failure** | `ruff check` 75 errors; tests actually pass |
| saas-starter-kit | 8 | success | `npm ci` without lockfile (old workflow) |
| api-boilerplate | 7 | success | ESM `require is not defined` in `scripts/smoke.js` |
| pygame-platformer | 3 | success | flake8 F403/F405 star-imports (style gate) |
| social-automation | 3 | success | flake8 E402/F401/F541 (style gate) |
| tailwind-component-pack | 2 | success | logs 404 (expired); later green |
| aspen-contracts | 1 | success | missing `schemas/examples/heartbeat.json` |
| aspen-swarm-manager | 1 | success | extra Makefile smoke assert `MissionState.FAILED` after unit tests OK |

---

## Cluster A — AspenOS: why 43 mails, same two jobs

Failed jobs on representative runs (`32709682383` master 2026-08-24 09:06 UTC, and PR runs the same morning):

1. **`smoke` → step “Smoke”**  
   `scripts/smoke-test.sh` result: **56 passed, 1 failed**.  
   Failed check: **`gen accounts conf valid`**.  
   Log: `bash: line 1: nats-server: command not found`.

   The check is:

   ```bash
   export PATH="$HOME/go/bin:/root/go/bin:$PATH"
   … bash scripts/gen-nats-accounts.sh …
   nats-server -c "$OUT/fleet-accounts.conf" -t
   ```

   CI *does* try to install `nats-server` v2.14.3 into `/usr/local/bin`, but the check’s PATH rewrite + silent `curl | tar` makes the binary easy to miss. GHA job-level `PATH` override also does not guarantee the child `bash -c` sees `/usr/local/bin` if the tarball copy failed.

   NATS connection refused on `127.0.0.1:4222` in the same log is **noise from the same missing broker**, not a second product bug.

2. **`build-c11` →**  
   `./src/c/sandbox_spike/sandbox_run --help | grep -q built-in`  
   Actual usage printed:

   ```
   Usage: ./src/c/sandbox_spike/sandbox_run [--timeout SECS] [--no-seccomp] [--no-ns] -- COMMAND [ARGS...]
   ```

   CLI help no longer contains the string `built-in`. **The binary built; the assertion is stale.** Current `master` `.github/workflows/ci.yml` **still has this grep**. It passed after PR #15 only because help text on that tip contains `built-in` again — the assertion is still brittle.

**Current `master` is green** (all five jobs: lint, smoke, build-go, build-rust, build-c11) after merging PR #15. Open Hermes PRs are **not rebased**, so they keep failing the same two checks and keep mailing.

Workflow trigger on current master is already narrowed:

```yaml
on:
  push:
    branches: [main, master]
  pull_request:
    branches: [main, master]
```

That still fires a full matrix on **every** PR into master — including 20+ docs-only Hermes PRs.

---

## Cluster B — Product kits: “smoke” that is not product smoke

These are Gumroad/template repos. Later `master` is green after packaging-normalize (Aug 6). Inbox items are **leftover failure mail**.

| Repo | Failed run | Exact failure | Class |
|---|---|---|---|
| `api-boilerplate` | 31065366142 (2026-08-06) | `scripts/smoke.js`: `ReferenceError: require is not defined in ES module scope` (`"type":"module"`) | Known mesh pitfall (ESM). Fixed later; current `ci.yml` still `on: [push, pull_request]` + `make smoke`. |
| `aspen-contracts` | 31064388871 | `FileNotFoundError: schemas/examples/heartbeat.json` | Smoke asserted a fixture that was not published yet. File exists on current tip; Makefile still loads it. |
| `saas-starter-kit` | 30734889208 | `npm ci` in `backend/` and `frontend/` — **no `package-lock.json`**. Matches Linear BEL-125 history (empty frontend). Later workflow is a single **smoke** job and is green. |
| `pygame-platformer` | 30723197944 | flake8: `from config import *` (F403/F405), unused imports, E302 | **Style linter used as CI gate** — not a runtime smoke. |
| `social-automation` | 30723175869 | flake8 E402 (imports after `sys.path` hack), unused imports, F541, E501 | Same — style, not “does the product boot”. |
| `aspen-swarm-manager` | 31073381612 | `unittest` 6/6 OK, then Makefile extra assert `m.state.value == "running"` got `MissionState.FAILED` | Scripted demo after tests; likely missing sim/env on GHA. Later master green. |
| `tailwind-component-pack` | 30723158634 | Log zip **404** (expired). Later master green. | Stale notification only. |

---

## Cluster C — `agnetic-os` (still red, not in the 50 unread)

Latest `main` run **29447963978** (2026-07-15):

- **lint failed:** `ruff check agents/ dashboard/ services/` → **75 errors** (unused import, formatting, etc.).
- **test job succeeded** (including coverage upload, which then failed tokenless Codecov — warning only).
- Workflow **still `state: active`**. Defined as `andromi-hash/agnetic-os` in the log (fork lineage). Last push Jul 15.

This is a **legacy fork**, not the AspenOS `master` line. It will keep going red if anything retriggers. It is **not** what is flooding the inbox today.

---

## Why the inbox keeps refilling

1. **Hermes/OpenCode hourly sweeps open a PR per ticket** (`hermes/hermes-*`, `hermes/asp-*`). 25 still open.
2. Each PR targets `master` → full Starship CI (smoke clones sibling repos, builds Go CLI, installs NATS).
3. Unrebased PR tips fail the **same two checks** → CheckSuite notification to `AbsolutionAI`.
4. Product-kit failures from the Aug 1–6 normalize week were never marked read.
5. No notification filter: watching the account, not “default branch only”.

This matches Paperclip activity on Aug 23: Opencode hourly sweep minting ASP-40x and landing PRs #17 etc.

---

## What is *not* a current smoke outage

- Package-mesh control repos (`aspen-grove`, `aspen-dev`, `aspen-langgraph-worker`, `aspen-edge-rrm`, personas, CE gates, matrix-ops, …): latest CI **green**.
- `epos-human`, `aspen-pcake`: latest **green**.
- AspenOS **`master` after PR #15**: **green**.
- No pending Paperclip hire approvals; this is not an ABSA budget incident.

---

## Recommended actions (for you to approve)

### Inbox (10 minutes, human or agent-with-ok)

1. Mark the 50 unread CheckSuite notifications **read** (or “Done” in GitHub inbox). They are not a live master outage.
2. GitHub → Settings → Notifications → **Actions**: prefer “failed workflows on default branch only” (or unwatch repos you do not operate daily; watch `AspenOS` + `aspen-grove` only).
3. Optional: `gh api -X PUT notifications` mark-all-read after you skim this doc.

### Stop the refill (highest leverage)

4. **Close or convert-to-draft** the 20+ stale `hermes/*` PRs that are docs/residuals already mirrored in Linear (BEL-192/177/164 children). Keep a short allow-list (e.g. #15 already merged; #17 fleet hardening if you still want it; #18 NATS cred scrub).
5. Require Hermes/OpenCode to **not open a GitHub PR** for docs-only ASP tickets, or label `skip-ci` and add:

   ```yaml
   concurrency:
     group: ${{ github.workflow }}-${{ github.ref }}
     cancel-in-progress: true
   ```

   plus `paths-ignore` for `docs/**` on the smoke/build jobs.

6. Disable Actions on **`agnetic-os`** (or archive the repo). It cannot go green without a ruff campaign nobody is staffing.

### Real CI contract fixes (small, if you want a coding pass)

7. **AspenOS smoke:** install `nats-server` with `set -euo pipefail` + `command -v nats-server`; in `smoke-test.sh` prepend `/usr/local/bin` (do not replace PATH with only `go/bin`). Skip `gen accounts conf valid` if `nats-server` is missing rather than fail the whole suite.
8. **AspenOS C11:** replace `grep -q built-in` with a real invocation, e.g. `sandbox_run --help >/dev/null` and `sandbox_run --timeout 1 -- echo ok`.
9. **Product kits:** CI job name `smoke` should mean `make smoke` (compile/parse), **not** flake8-as-gate. Keep flake8 in a non-blocking job. ESM smoke must use `import`. Never `npm ci` without a lockfile (`npm install` already used on the green tip).

---

## Evidence index (local)

| Artifact | Path |
|---|---|
| Repo list | `/tmp/gh_repos.json` |
| Per-repo run inventory | `/tmp/gh_ci_inventory.json` |
| Failed-run log zips | `/tmp/gh-fail-logs/*.zip` |
| AspenOS green master | https://github.com/AbsolutionAI/AspenOS/actions/runs/32766560555 |
| AspenOS red master (pre-#15) | https://github.com/AbsolutionAI/AspenOS/actions/runs/32709682383 |
| AspenOS smoke check | `scripts/smoke-test.sh` line ~36 (`nats-server -c … -t`) |

---

## Suggested ask-back

- Approve **inbox mark-read + close stale Hermes PRs** (no code)?
- Approve the **two AspenOS CI assertion fixes** (NATS path + sandbox_run)?
- Leave product kits alone (already green on master)?

Prepared by Aspen Architect. No secrets in this document.
