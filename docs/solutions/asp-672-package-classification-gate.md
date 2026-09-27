# ASP-672: CI gate for package `classification` declaration (H-020)

## Problem

ADR-0008 rule 4 states: *"All packages must declare `classification` in `pyproject.toml` /
`Cargo.toml` / `package.json`."* Nothing enforced it. On tip, one of two packages declared
anything at all:

```
$ for f in plugins/*/pyproject.toml; do grep -n classification "$f"; done
plugins/aspen-gatekeeper/pyproject.toml:23:classification = "plugin"
```

`plugins/hello-world/` — the example plugin — declared no tier anywhere, so it was invisible to
H-019 (which catches Dev-only names *leaking out* into production, not a package that never
declared a tier in the first place). `docs/PACKAGES.md` calls itself the classification source of
truth, but no gate cross-checked any package against it, so a reclassification could drift
silently.

This is the mirror image of H-019/ASP-574, whose own "Future improvements" section predicted it:
*"Onboard Dev-only markers from package manifests (`pyproject.toml` `classification =
"dev-only"`) as package-catalog enforcement lands (BEL-164)."* H-020 does the other direction —
manifest → SoR agreement.

## Solution

`scripts/check-package-classification.sh` — a fail-closed gate, structured exactly like its
sibling `check-no-devonly-in-prod.sh` (marker build → scan → report → `--self-test`):

1. **Package roots** — each immediate subdirectory of `plugins/` (overridable via
   `PACKAGE_ROOTS`) that holds a supported manifest.
2. **Declaration sources**, in precedence order: `pyproject.toml` (`[tool.aspen]`),
   `plugin.json`, `package.json`, `Cargo.toml` (`[package.metadata.aspen]`), `manifest.json`.
   Valid values are exactly `core`, `plugin`, `dev-only`.
3. **Structural parsing, not grep.** The gate logic is a `python3` block using stdlib `tomllib`
   and `json`. This is load-bearing, not stylistic: `grep classification` matches a *dependency
   named* `classification-utils` and a key under `[project.optional-dependencies]`, both of
   which are false passes. Pinned by `test_dependency_named_classification_is_not_a_declaration`.
4. **SoR cross-check** against `docs/PACKAGES.md` (overridable via `PACKAGES_MD`) — two
   independent checks:
   - *coverage*: the package name must appear in the SoR at all;
   - *agreement*: every **markdown table row whose tier cell is a valid tier** asserts a tier
     for the names in the cells after it; the declared tier must be in that set.
5. **Wired as a merge gate and a nightly gate** — CI job `security-package-classification`
   (push + PR) and `scripts/check-nightly.sh` Section 23.

## Key findings / gotchas

- **A self-test that scans nothing always fails, so it proves nothing.** The first draft of
  `--self-test` set `PACKAGE_ROOTS="$FIXTURE_ROOT"` as an *environment variable* while `run_gate`
  read its roots from `"$@"` — so the python block got `roots = []`, exited 0, and the self-test
  correctly reported "package with no classification was NOT detected" and exited 1. It looked
  like a working self-test and was actually a permanently-red one. Two fixes: make `run_gate`
  take the source of truth as its first positional argument so the fixture wiring is explicit,
  and run a **positive control first** — a compliant package must be accepted *before* asserting
  an undeclared one is detected. A detection-only self-test is satisfied by a gate that rejects
  everything, which is the same class of bug in the opposite direction.
- **Prose mentions are not tier claims.** `docs/PACKAGES.md` has a `## Plugin: aspen-gatekeeper`
  section whose `| **classification** | \`plugin\` |` row must not be read as a second, competing
  tier assertion. Scoping the tier regex to `^\|\s*\*{0,2}(core|plugin|dev-only)\*{0,2}\s*\|` and
  only collecting names from cells *after* the tier cell keeps prose out of the comparison.
  `aspen-gatekeeper` is asserted by the matrix row alone and the gate passes.
- **Which SoR surface you write to decides whether a check is live.** Adding `hello-world` to the
  "Dev-only Examples (internal only)" bullet list satisfies the *coverage* check but leaves
  *agreement* vacuous — nothing would catch reclassifying it to `plugin`. Adding it to the
  **matrix row's Examples cell** gives a real tier assertion, and that matrix cell is also the
  source H-019 builds its Dev-only marker list from. Before editing it, confirm the new name
  appears in no H-019 production root, or H-019 breaks the build: `hello-world` is absent from all
  of them, and `check-no-devonly-in-prod.sh` still passes (asserted by nightly §16).
- **The `VOCABULARY` filter matters.** Tier rows contain the words `core`, `dev-only`, `only`,
  and `name` in their Definition / Ownership / Visibility cells, which are scanned as candidate
  package names. Without an explicit stop-list these get registered as packages with tiers.
- Append nightly sections at the end. `tests/test_ci_assertions.py` asserts on section *numbers*,
  so inserting §23 before §24 would renumber later sections and fail the contract for no reason.
  `test_nightly_section_23_appended_after_22` pins the ordering.

## Test evidence

| Case | Result |
|------|--------|
| Clean repo | exit 0 — `plugin aspen-gatekeeper`, `dev-only hello-world` |
| Package with no `classification` | exit 1, names the package + "no `classification` declared" |
| `classification = "internal"` | exit 1, "is not one of core, plugin, dev-only" |
| Valid tier, absent from SoR | exit 1, "not mentioned in docs/PACKAGES.md" |
| Declares `plugin`, SoR row says `dev-only` | exit 1, "classifies it as ['dev-only']" |
| `dependencies = ["classification-utils"]` | exit 1 (grep would have passed this) |
| `[tool.aspen].classification = "plugin"` | exit 0 |
| `--self-test` | exit 0 (positive control then detection) |
| `python3 -m pytest tests/ -q` | 481 passed, 4 skipped, 0 failed (nightly §13 needs ≥ 150) |
| `scripts/smoke-test.sh` | 61 passed, 1 failed — `C11 p50 under 2ms` only, the known hardware deviation in `docs/ops/NIGHTLY_LATEST.md`; no C code touched |
| `check-no-devonly-in-prod.sh` + `--self-test` | exit 0 — no H-019 regression from the PACKAGES.md edit |

**Mutation check** (the tests are load-bearing, not decorative): a no-op gate that always exits 0
fails 6 of 12 fixture tests; a reject-everything gate fails 9.

## Files

| File | Purpose |
|------|---------|
| `scripts/check-package-classification.sh` | Gate script (H-020 / ADR-0008 rule 4) |
| `plugins/hello-world/plugin.json` | Declares `classification = "dev-only"` (was missing) |
| `docs/PACKAGES.md` | Dev-only matrix row now asserts `hello-world` |
| `.github/workflows/ci.yml` | New `security-package-classification` job |
| `scripts/check-nightly.sh` | New Section 23 (appended, no renumbering) |
| `tests/test_package_classification.py` | 12 fixture tests over `PACKAGE_ROOTS` / `PACKAGES_MD` overrides |
| `tests/test_ci_assertions.py` | 4 tests: §23 present, §23 after §22, CI job wired |
| `docs/plans/ASP-672-package-classification-gate.md` | Plan (CE plan-first) |

## Open questions for the Architect

Neither is attempted here — both are data-model / scope calls, not implementation details:

1. **ASP-628 item 2 — "wire plant-profile default: actuator profiles include plugin."**
   `config/profiles.yaml` has hardware tiers (`edge` / `server` / `ops`) and no actuator axis, so
   "actuator profiles" does not exist as a concept in the profile SoR. Adding an `actuators:` axis
   is a data-model decision.
2. **ADR-0008 rule-4 scope beyond `plugins/`.** `agent/` (Rust) and `starshipctl/` (Go) are
   shipped product trees that declare no classification. This gate covers `plugins/*/` only,
   because ADR-0008 speaks in package terms and those two are not packages in the catalog sense.

## Future improvements

- Close the BEL-164 loop: have the packaging tool read the `classification` this gate validates
  rather than duplicating the tier list in `scripts/build-deb.sh`.
- Extend `PACKAGE_ROOTS` to the shipped product trees once the Architect rules on question 2, so
  `agent/` and `starshipctl/` declare tiers too.
- Retire the separate `prod` root list in `check-no-devonly-in-prod.sh` in favour of reading
  `classification` directly, so the two gates can never disagree about what is Dev-only.
