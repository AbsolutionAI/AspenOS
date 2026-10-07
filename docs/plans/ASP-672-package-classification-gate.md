# ASP-672: H-020 — enforce ADR-0008 rule 4 (package `classification` declaration)

**Issue:** ASP-672 (Daily implementation sweep — queue empty, picked architect-approved follow-up)
**ADRs:** ADR-0008 (Core / Plugin / Dev-only) · ADR-0009 residual (ASP-628 §5 follow-up eng #3)
**Author:** aspen (implementation) · **Date:** 2026-09-27
**Mode:** Follow-up eng item already written down by aspen — no new architecture

---

## 1. Why this, and why now

The daily sweep found no actionable `todo` coding item on the board (all open work is
`blocked`/`in_review` on aspen, Auditor, or ASP-650's explicit captain hold). Rather than
park the heartbeat, this sweep picked the highest-priority **already-approved** implementation
residual from the most recent architecture review.

`docs/plans/ASP-628-gatekeeper-packaging.md` §5 "Follow-up eng (not started here)" item 3:

> 3. H-019 / nightly: assert actuator profile images do not ship without gatekeeper; assert core
>    image does not pull dev-only paths.

Item 3 is a **CI/nightly assertion** task, and item 1 (plugin skeleton) is already landed
(ASP-630, `plugins/aspen-gatekeeper/`). This plan implements the enforcement half that does not
require a production image matrix: the classification invariant ADR-0008 rule 4 already mandates
but nothing checks.

## 2. Problem

ADR-0008 rule 4 (line 27):

> All packages must declare `classification` in `pyproject.toml` / `Cargo.toml` / `package.json`.

Nothing in CI or nightly enforces it. Today, on tip:

```
$ for f in plugins/*/pyproject.toml; do grep -n classification "$f"; done
plugins/aspen-gatekeeper/pyproject.toml:23:classification = "plugin"
```

`plugins/hello-world/` ships **no** `pyproject.toml` and **no** `classification` in its
`plugin.json` — a live ADR-0008 rule-4 violation. And `docs/PACKAGES.md` line 56 states
"PACKAGES.md is the single source of truth for classification", yet no gate cross-checks the
declared value against that SoR, so a reclassification can drift silently.

The existing H-019 gate (`scripts/check-no-devonly-in-prod.sh`) covers the *other* direction —
Dev-only names leaking into production surfaces. It cannot catch a package that never declares a
tier, or one whose declared tier contradicts PACKAGES.md.

## 3. Success criteria

1. `scripts/check-package-classification.sh` exits 0 on a compliant repo and non-zero, with a
   named package and reason, on each of:
   - a package with no `classification` declaration in any supported manifest;
   - a package declaring a value outside `core | plugin | dev-only`;
   - a package absent from `docs/PACKAGES.md` (SoR coverage);
   - a package whose declared tier contradicts its PACKAGES.md tier row.
2. `plugins/hello-world` declares `classification` and is listed in `docs/PACKAGES.md`.
3. Gate is invoked by `scripts/check-nightly.sh` (new section 23) **and** by a CI job, so a
   violation blocks merge, not just the nightly run.
4. `tests/test_package_classification.py` covers clean-repo pass, all three failure modes, and
   `--self-test`, mirroring `tests/test_devonly_isolation.py`.
5. `tests/test_ci_assertions.py` gains a regression assertion that nightly §23 and the CI job
   stay wired (the repo's existing CI-contract convention).
6. `bash scripts/check-no-devonly-in-prod.sh` and its `--self-test` still pass after the
   PACKAGES.md edit — the new Dev-only token must not break the H-019 marker parser.
7. No product/runtime code change; no image-matrix change (Captain gate untouched).

## 4. Implementation

### 4.1 `scripts/check-package-classification.sh`

Follows the H-019 gate's structure (marker build → scan → report → `--self-test`), not a new
pattern.

- **Package roots:** each immediate subdirectory of `plugins/`. A directory counts as a package
  when it contains any of the supported manifests. Extension point: `PACKAGE_ROOTS` array.
- **Supported declaration sources,** in precedence order, matching ADR-0008 rule 4 verbatim:
  `pyproject.toml` (`[tool.aspen]` table), `plugin.json`, `package.json`, `Cargo.toml`
  (`[package.metadata.aspen]`), `manifest.json`.
  Parsed with a small `python3` reader rather than `grep` so nested JSON/TOML is handled and a
  key inside a *dependency* name can never be mistaken for a declaration. TOML is read with
  `tomllib` (stdlib since 3.11; the repo already requires `>=3.11`).
- **Valid values:** exactly `core`, `plugin`, `dev-only`.
- **PACKAGES.md cross-check:**
  - *coverage* — the package `name` must appear in `docs/PACKAGES.md`; else fail.
  - *agreement* — for every PACKAGES.md **table row** that names the package, the row's tier cell
    must equal the declared value. Row-scoped, so a passing mention in prose (e.g. the
    aspen-gatekeeper section body) is not misread as a conflicting tier.
- **Self-test:** the shell `--self-test` uses a temp `PACKAGE_ROOTS` **and** a temp
  `PACKAGES_MD`, so it asserts the gate's own parsing rather than depending on what
  `docs/PACKAGES.md` happens to say. It runs a **positive control first** (a compliant package
  must be accepted) before requiring that an undeclared one is detected — a detection-only
  self-test is satisfied by a gate that rejects everything, which is exactly the bug the first
  implementation shipped with (see §4.6). `run_gate` therefore takes the source of truth as its
  first positional argument.

### 4.2 `plugins/hello-world/plugin.json`

Add `"classification": "dev-only"`. Rationale: tagged `example` / `demo` / `tutorial`, never
staged by `scripts/build-deb.sh`, and not part of any plant image — i.e. internal tooling, which
is ADR-0008's Dev-only definition. **Flagged for aspen** in the handoff comment: this is the one
classification call in the change, and it is a one-line revert if Architect disagrees.

### 4.3 `docs/PACKAGES.md`

Add `hello-world` to the **Dev-only row of the classification matrix** (Examples cell) so the
gate gets a real tier assertion to cross-check, not merely a mention. The matrix row is the
only surface `scripts/check-package-classification.sh` parses as a tier claim; a bullet in
"Dev-only Examples (internal only)" would satisfy the *coverage* check but leave the
*agreement* check vacuous, so reclassifying `hello-world` to `plugin` would not be caught.

> **Deviation from the first draft of this plan** (recorded 2026-09-27, after implementation):
> §4.3 originally said to add the bullet to "Dev-only Examples (internal only)". The matrix row
> is used instead, because it is the machine-readable assertion surface. Both surfaces are read;
> only the matrix row asserts a tier.

Verified this adds no H-019 false positive: the Dev-only matrix Examples cell is the source
H-019 builds its marker list from, so `hello-world` becomes a Dev-only marker — and
`hello-world` appears in no production root (`agents config dashboard debian iso nats packaging
services skills souls systemd tray` plus the six `RUNTIME_SCRIPTS`). `bash
scripts/check-no-devonly-in-prod.sh` and its `--self-test` both still pass.

### 4.4 Nightly + CI wiring

- `scripts/check-nightly.sh`: new **Section 23: Package classification gate (H-020)**, appended
  after §22 so existing section numbers — which `tests/test_ci_assertions.py` asserts on — do not
  shift. Three checks: gate script executable, gate passes, fixture tests pass.
- `.github/workflows/ci.yml`: new `package-classification` job next to
  `security-devonly-isolation`, running the gate plus `tests/test_package_classification.py`.

### 4.5 Tests

`tests/test_package_classification.py`, structured like `tests/test_devonly_isolation.py`:
clean-repo pass; compliant fixture pass; missing declaration detected; invalid value detected;
PACKAGES.md coverage missing detected; PACKAGES.md tier disagreement detected;
`--self-test` passes. Failure-mode tests use the `PACKAGE_ROOTS` / `PACKAGES_MD` override so they
never write into the real `plugins/` tree.

Two tests exist to keep the suite honest rather than to widen coverage:

- `test_dependency_named_classification_is_not_a_declaration` plants a `pyproject.toml` with
  `classification-utils` in `dependencies` and `classification` under
  `[project.optional-dependencies]`. This is the exact false pass that motivated parsing with
  `tomllib` instead of `grep`, so it is pinned by a test.
- `test_nested_aspen_table_declaration_accepted` pins `[tool.aspen].classification` as a real
  declaration site, so the gate cannot be tightened into rejecting valid Python packages.

### 4.6 Defect found in the pre-handoff draft

The first implementation of `--self-test` (lost to a `process_lost_retry` wake) called
`run_gate` with **no root arguments**, so the python block received `roots = []`, scanned
nothing, exited 0 — and the self-test then reported `self-test: package with no classification
was NOT detected` while exiting **1**. A self-test that can only ever fail is not a self-test.
Fixed by making `run_gate` take the source of truth positionally and passing the fixture root,
and by adding the positive control. Verified by mutation: a no-op gate now fails 6 of the 12
fixture tests, and a reject-everything gate fails 9.

## 5. Scope

**In:** `scripts/check-package-classification.sh`, `scripts/check-nightly.sh` (§23 only),
`.github/workflows/ci.yml` (one job), `plugins/hello-world/plugin.json`,
`docs/PACKAGES.md` (one matrix cell — see §4.3 deviation), `tests/test_package_classification.py`
(new, 12 tests), `tests/test_ci_assertions.py` (4 tests), `docs/solutions/asp-672-package-classification-gate.md`
(new), this plan.

**Out:** the actuator-profile default and image matrix (ASP-628 items 2 and 3-image-half — those
need a plant-profile data model that does not exist yet and a Captain image-matrix decision);
`src/python/gatekeeper/` → `plugins/aspen-gatekeeper/` extraction; any change to
`scripts/build-deb.sh`; any ADR acceptance; any H-019 gate behavior change.

## 6. Escalation note (architectural, for Aspen Architect)

Two items in this sweep need an Architect call and are **not** attempted here:

1. **ASP-628 item 2 — "wire plant-profile default: actuator profiles include plugin".**
   `config/profiles.yaml` has hardware tiers (`edge` / `server` / `ops`) with no actuator axis, so
   "actuator profiles" does not exist as a concept in the profile SoR. Adding an `actuators:`
   axis is a data-model decision for the Architect, not an implementation detail.
2. **ADR-0008 rule-4 scope for non-`plugins/` trees.** `agent/` (Rust) and `starshipctl/` (Go)
   are shipped product trees that declare no `classification` today. This gate covers
   `plugins/*/` only, because ADR-0008 speaks in package terms and those two are not packages in
   the catalog sense. Whether they should be brought under the rule is an Architect question.

## 7. QA (as run, 2026-09-27)

- `bash scripts/check-package-classification.sh` → PASS (2 packages: `plugin aspen-gatekeeper`,
  `dev-only hello-world`)
- `bash scripts/check-package-classification.sh --self-test` → PASS
- `python3 -m pytest tests/test_package_classification.py tests/test_ci_assertions.py tests/test_devonly_isolation.py -q` → 32 passed
- `python3 -m pytest tests/ -q` → **481 passed, 4 skipped**, 0 failed (nightly §13 needs ≥ 150)
- `bash scripts/check-no-devonly-in-prod.sh` and `--self-test` → PASS (no H-019 regression)
- Nightly §23 replayed check-by-check → 5/5 PASS
- `bash scripts/smoke-test.sh` → 61 passed, 1 failed — `C11 p50 under 2ms` only, the same known
  hardware deviation recorded in `docs/ops/NIGHTLY_LATEST.md` (3.651 ms vs the 2 ms ADR-0001
  threshold). No C code touched.
- Mutation check: no-op gate → 6/12 fixture tests fail; reject-everything gate → 9/12 fail
- `git diff --name-only` matches the §5 in-scope list, plus the §4.3 / §4.5 deviations recorded
  above
