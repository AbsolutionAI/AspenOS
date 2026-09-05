# ASP-527: ISO builder missing starship-* systemd units

## Problem

`scripts/build-iso.sh` copied only `agnetic-*.service` / `agnetic-*.target`
into the live-build chroot, so ISO-installed systems were missing
`starship-fleet.service` and `starship-health-checker.service`:

```bash
cp "$REPO_DIR/systemd/agnetic-"*.service "$LB_DIR/config/includes.chroot/lib/systemd/system/" 2>/dev/null || true
cp "$REPO_DIR/systemd/agnetic-"*.target  "$LB_DIR/config/includes.chroot/lib/systemd/system/" 2>/dev/null || true
```

Both units were already shipped by the .deb (`scripts/build-deb.sh` lines
142-145 list the full canonical unit set), creating a runtime layout
mismatch between .deb-installed and ISO-installed systems.

## Solution

Expanded both `cp` globs with bash brace expansion so they cover the
`starship-*` prefix as well:

```bash
cp "$REPO_DIR/systemd/"{agnetic-,starship-}*.service "$LB_DIR/config/includes.chroot/lib/systemd/system/" 2>/dev/null || true
cp "$REPO_DIR/systemd/"{agnetic-,starship-}*.target  "$LB_DIR/config/includes.chroot/lib/systemd/system/" 2>/dev/null || true
```

## Files Changed

| File | Change |
|------|--------|
| `scripts/build-iso.sh` | Lines 109-110: copy globs include `{agnetic-,starship-}` prefixes |

## Verification

- Simulated the copy step end-to-end: all 9 canonical units land in the
  chroot (7 `agnetic-*` + `starship-fleet.service` + `starship-health-checker.service`),
  matching the .deb unit list exactly.
- PR #37 merged (`ed95dc2`), CI green (build-c11, build-go, build-rust,
  lint, smoke all pass).

## Related

- `scripts/build-deb.sh` is the source of truth for the canonical unit set.
- ASP-151/ASP-190/ASP-454 track the health-checker shipping history in the .deb.