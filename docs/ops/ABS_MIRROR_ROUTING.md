# ABS Mirror Deliverable Routing (ASP-36)

**Paperclip:** [ASP-36](/ASP/issues/ASP-36)  
**Date:** 2026-08-22  
**Decided by:** Aspen Architect (aspen)  
**Status:** Active

## Decision (summary)

| Option | Chosen? | Why |
|--------|---------|-----|
| Commit under ASP with silent ASP ownership | **No** | Public repo `AbsolutionAI/AspenOS`; multi-company artifacts must stay labeled |
| Move to a separate ABS-company git workspace | **No** | ABS agents share cwd `/home/tech/aspen-dev/repos/aspen-os`; ABS company is **paused $0** under fiscal freeze; no alternate ABS product repo |
| **Keep on disk in monorepo + explicit ownership + ignore non-ASP paths** | **Yes** | Matches live adapter workspaces; protects public remote; freeze-safe |

**Rule:** AspenOS monorepo remains the **shared execution workspace** for ASP and dormant ABS agents. Ownership is path-scoped, not company-directory-scoped. Non-ASP and secret material stays **local-only** (gitignored) until a private company repo exists or freeze lifts.

## Preconditions that drove the call

1. `gh repo view AbsolutionAI/AspenOS` → **public**.
2. ABS Paperclip company (`9b183445-abef-48b2-a45f-52950b04da49`, prefix ABS) is **paused / $0** (see `docs/COMPANY_MAP.md`).
3. ABS-7…ABS-10 are already **done** mirrors of BEL-153/113/114/154; evidence lives under this tree by design (`docs/ops/FOUNDATION.md`).
4. `services/memory.py` uncommitted delta is **ASP-98 prospective memory** (ASP product), not an ABS-only fork — despite historical BEL-154 / ABS-10 labeling on the base memory layer.

## Ownership table

### A. ASP product — eligible for AspenOS commits (when a deliberate PR lands)

| Path | Notes | Tickets |
|------|-------|---------|
| `services/memory.py` (+ prospective managers) | Core memory service; ASP-98 delta uncommitted | BEL-154 / ABS-10 base; **ASP-98** delta |
| `services/memory-api.py`, `Dockerfile.memory-api`, `tests/test_memory_api.py` | Memory HTTP surface | ASP memory program |
| `memory_pkg/`, `memory/` | Access layer already partially on master | BEL-154 |
| `docs/adr/ADR-0001`…`0005` | Grove packaging, fleet, plugins | BEL fleet/package |
| `docs/sor/` | Master Spec / Matrix install | SoR v4 |
| `docs/FLEET.md`, fleet solutions under `docs/solutions/bel-182*`, `bel-191*` | Fleet program | BEL-179+ |
| `docs/PACKAGE_MAP.md`, `docs/PRODUCT_PRINCIPLES.md`, packaging plans | Package mesh | BEL-164 |
| `docs/MODEL_ROUTING.md`, `docs/COMPOUND_ENGINEERING.md` | Stack ops (already or should be public-safe) | BEL-132/133 |
| `docs/architecture/MEMORY_LAYER.md` | Product architecture | BEL-154 |

### B. Shared foundation / ABS mirror **proof** — stay in monorepo; commit only with ABS/BEL labels in body

These are dual-company ops artifacts. ABS-7…10 are closed; keep as historical proof + live checklist. When committing, PR title/body must say **ABS mirror / multi-company ops**, not “Aspen feature”.

| Path | Mirror | Notes |
|------|--------|-------|
| `docs/FOUNDATION.md` | ABS-7…10 table | Shared snapshot (ASP + ABS rosters) |
| `docs/AGENTS.md` | ABS-8 CE block | Opencode/agent context; CE gates BEL-113 |
| `docs/ops/FOUNDATION.md` | ABS-7 proof ticket | Paperclip proof |
| `docs/ops/AGENT_SKILLS_MATRIX.md`, `MORNING_BRIEF.md`, `LINEAR_MCP_PAPERCLIP.md`, … | Multi-co ops | ASP board + stack |
| `docs/security/AUDITOR_BASELINE.md` + sibling drafts | ABS-9 / BEL-114 | Read-only baselines; no apply |
| `docs/solutions/BEL-130-first-ce-cycle.md` | CE compound | BEL-130 / ABS-8 family |
| `docs/plans/BEL-135-appflowy-knowledge-layer.md` | Stack | BEL-135 (deferred under freeze) |
| `docs/plans/paperclip-multi-company-alignment.md` | Multi-co | BEL-142+ |
| `docs/COMPANY_MAP.md` | Map only | **No secrets** |
| `tests/smoke_test_bel_abs.py`, `tests/thorough_test_bel_abs.py` | ABS-7…10 smoke | Validates paths in this tree |

### C. Non-ASP company material — **local-only** (gitignored; do not publish to AspenOS)

| Path | Owning company | Notes |
|------|----------------|-------|
| `docs/commerce/**` | **ABSA** (Absolution Digital Commerce) | Gumroad/affiliate research |
| `docs/marketing/**` | **Content Studio / ABSA** | X umbrella, Gumroad upload runbooks, scheduled drafts |
| `docs/COMPANY_CREDENTIALS.md` | Board / all cos | Credential **inventory** — never commit (even READY rows) |
| `docs/architecture/OSINT_*`, `WORLDMONITOR_*`, `UNIFIED_PLATFORM.md` | **ABS** deferred verticals | OSINT/C2 — keep local until ABS unpaused + private surface |

### D. Out of scope for ASP-36 (leave as existing dirty tree; separate tickets)

| Path | Why |
|------|-----|
| `Makefile`, `scripts/bench-sandbox.sh`, `src/c/sandbox_spike/*`, `docs/ISO_TESTING.md` | Unrelated sandbox/ISO WIP |
| Unrelated solution notes (`asp-98-prospective-memory-manager.md`) | Pair with ASP-98 when that ships |

## Enforcement

1. **`.gitignore`** blocks class C paths from accidental `git add` into public AspenOS.
2. Agents MUST NOT `git add -A` at repo root.
3. ABS company remains **dormant** under freeze; do not open ABS spend to “relocate” trees.
4. If a private multi-company docs repo is created later, class C moves there first; class B can stay or be split by PR.

## ABS-7 / 8 / 9 / 10 disposition

| ABS | Linear | Disposition under this decision |
|-----|--------|----------------------------------|
| ABS-7 | BEL-153 | Proof in `docs/ops/FOUNDATION.md` + shared `docs/FOUNDATION.md` — **remain** |
| ABS-8 | BEL-113 | CE text in `docs/AGENTS.md` + `docs/COMPOUND_ENGINEERING.md` + BEL-130 solution — **remain** |
| ABS-9 | BEL-114 | `docs/security/*` baselines — **remain local until hygiene PR**; security drafts OK public if sanitized |
| ABS-10 | BEL-154 | Product memory code is **ASP-owned path A**; ABS-10 was mirror proof of shared memory layer — **remain** |

No file moves required for closed ABS mirrors. Routing = ownership + ignore rules, not a second checkout.

## Acceptance (ASP-36)

- [x] Decision recorded (this file)
- [x] Non-ASP / secret paths gitignored
- [x] `docs/FOUNDATION.md` and `docs/COMPANY_MAP.md` point here
- [x] ASP-36 commented with decision; status **done**

## Follow-ups (not blocking ASP-36)

- Deliberate ASP PRs for class A product deltas (memory prospective / ASP-98, ADRs, SoR) — separate issues.
- Optional hygiene PR for class B proof docs with multi-company labeling.
- Private docs repo if class C volume grows past gitignore comfort.
