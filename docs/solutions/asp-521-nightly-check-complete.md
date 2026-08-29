# Learning: Nightly check must cover Debian metadata, Windows packaging, and update mechanism

**Ticket:** ASP-521

## Problem

The nightly check (ASP-512/ASP-518) validated Go/Rust/C11 builds, smoke tests, systemd units, shell syntax, and key files — but missed several deployment-critical artifacts:

1. **Debian package metadata** (`debian/DEBIAN/{control,postinst,postrm,prerm}`) was not checked. A missing `postinst` or `prerm` would silently break install/upgrade/removal on deployed systems.
2. **Windows packaging artifacts** (`packaging/windows/`) were not checked. These ship to downstream consumers but had no automated presence validation.
3. **Update mechanism** (`scripts/update.sh`) was not checked for existence or executability. Deployed systems rely on this for self-update.
4. **Version consistency** between `VERSION` and `debian/DEBIAN/control` was not checked. Drift between the two would cause confusing version reporting.
5. **Ops doc** was a static description with no baseline table — operators had no reference for expected pass/fail counts, versions, or file inventories.

## Fix

1. **`scripts/check-nightly.sh`** gained three new sections:
   - Section 9 (Debian metadata): validates control, postinst, postrm, prerm exist and control declares `starship-os`
   - Section 10 (Windows packaging): validates all 6 artifacts in `packaging/windows/`
   - Section 11 (Update mechanism): validates `scripts/update.sh` exists and is executable
   - Section 8 gained a version consistency check: VERSION file content must match the `Version:` field in `debian/DEBIAN/control`
2. **`docs/ops/NIGHTLY_PACKAGING_DEPLOY_CHECK.md`** was rewritten as a runbook with:
   - Clear procedure steps for an operator to follow
   - Section table listing all 11 check groups
   - Baseline table with expected pass/fail counts, versions, and file inventories
   - ISO builder context reference

## Patterns to reuse

- **Validate all shipping artifacts in the nightly check, not just builds.** Debian metadata and Windows packaging files are equally important to the deployment pipeline as compiled binaries.
- **Cross-reference version strings.** A simple grep check that `VERSION` matches `debian/DEBIAN/control` catches version drift early.
- **Check executability, not just existence.** `test -x` catches permission regressions that `test -f` would miss.
- **Maintain a baseline table in the ops doc.** When the smoke suite gains or loses checks, the baseline table must be updated so operators can quickly spot deviations.
- **Write the ops doc as a runbook, not a reference.** Clear numbered steps reduce the chance of missed actions during a live incident.
