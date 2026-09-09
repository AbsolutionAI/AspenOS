# ASP-374: H-010 — Install AppArmor profiles in deb postinst

**Status:** READY_FOR_AIDER_QA
**Mode:** IMPLEMENTATION (follow-on to ASP-575 verify)

## Summary

Wired AppArmor profiles from `security/apparmor/` into the Debian package build
and install lifecycle. The ASP-575 verification report confirmed profiles exist
in source but are staged into zero deployment targets. This issue closes H-014
at the Debian package layer.

## Changes

### 1. `scripts/build-deb.sh`

- Added `mkdir -p "$PKG_ROOT/etc/apparmor.d"` in the assembly section.
- Added copy loop: for each profile (`agnetic-agent`, `nats`, `ollama`), copy
  from `security/apparmor/` into `$PKG_ROOT/etc/apparmor.d/` with `chmod 644`.
- Added `etc/apparmor.d/agnetic-agent` and `etc/apparmor.d/nats` to the layout
  validation list (layout assert fails if profiles are missing from the .deb).

### 2. `debian/DEBIAN/postinst`

- Added Section 6 (before GPU detection): runs `apparmor_parser -r` on each
  profile in `/etc/apparmor.d/` on the **installed target**.
- Graceful skip if `apparmor_parser` not available.
- No `aa-enforce` — profiles load in complain mode on install; firstboot
  (or operator) sets enforce.

### 3. `tests/test_ci_assertions.py`

- `test_build_deb_stages_apparmor_profiles` — greps build-deb.sh for profile
  copy commands and validation entries.
- `test_postinst_has_apparmor_parser` — verifies postinst has parser call and
  does NOT have `aa-enforce`.
- `test_nightly_section_17_apparmor_deb_present` — confirms nightly section 17.

### 4. `scripts/check-nightly.sh`

- New Section 17 checks: profiles exist in source, build-deb stages them,
  postinst has parser, postinst avoids aa-enforce.

## Files changed

| File | Change |
|------|--------|
| `scripts/build-deb.sh` | +13 lines (dir, copy, validation) |
| `debian/DEBIAN/postinst` | +20 lines (apparmor_parser section) |
| `tests/test_ci_assertions.py` | +37 lines (3 new tests) |
| `scripts/check-nightly.sh` | +5 lines (Section 17) |
| `docs/plans/ASP-374.md` | Plan document |
| `docs/solutions/asp-374-apparmor-deb-postinst.md` | This compound note |

## Verification

On the installed target (NOT this dev host):
```bash
# Profiles land at:
/etc/apparmor.d/agnetic-agent
/etc/apparmor.d/nats
/etc/apparmor.d/ollama

# postinst runs (idempotent):
apparmor_parser -r /etc/apparmor.d/agnetic-agent
apparmor_parser -r /etc/apparmor.d/nats
apparmor_parser -r /etc/apparmor.d/ollama
```

If `apparmor_parser` is absent, profiles are staged but not loaded — the
operator sees a WARN message advising manual `apparmor_parser -r` or
`apt-get install apparmor-utils`. The profiles are ready for firstboot to
`aa-enforce`.