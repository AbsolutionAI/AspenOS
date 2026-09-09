# ASP-575: AppArmor deployment gap — verified, not fixed

## Problem

`docs/SECURITY_THREAT_MODEL_v2.2.md` H-014 (6.5, AV:L/AC:M) suspects profiles
in `security/apparmor/` never reach deployed hosts because "install script may
not run". Task ASP-575 was a VERIFY-only slice (no `aa-enforce`, no CHG, no
sudo): inventory repo profiles vs host-loaded profiles, map every deployment
target, document the gap, plan the fix.

## What we verified

- **Source is fine:** 3 profiles (`agnetic-agent`, `nats`, `ollama`) + a
  correct standalone installer
  (`scripts/install-apparmor.sh`: copy → `/etc/apparmor.d`, `apparmor_parser -r`,
  `aa-enforce`).
- **Every deployment target is blind:** `install-daemon.sh`, the `.deb`
  (`build-deb.sh` + `postinst`), the ISO chroot hook, and CI/nightly all have
  **zero** AppArmor wiring. Nothing calls the installer. Nothing verifies
  loaded profiles. Nothing fails the build when a source profile is missing on
  target.
- **Live host proves the point:** AppArmor enabled (309 profiles loaded), yet
  `agnetic-agent`/`nats`/`ollama` absent — and `ollama` running **unconfined**
  (pid 11167 at verify time).

## Key learnings

1. **"Standalone script + docs mention" is not deployment.** Writing a correct
   installer and telling humans to run it (`SECURITY.md:45`) ships nothing. The
   threat model's instinct that `install-daemon.sh` "may not copy them" was
   correct; the same applies to `.deb` staging, the ISO live-build hook, and
   CI. Distribution must be wired per-target, and verified per-target.
2. **Path drift silently defeats AppArmor.** The `ollama` profile attaches
   `/usr/bin/ollama`, but the official installer (used by the ISO hook) puts it
   at `/usr/local/bin/ollama` — the profile never attaches, with no error.
   Profile attachment paths must be reconciled with the actual install paths of
   every target, not assumed.
3. **Risk posture worsens without AppArmor (H-010 link).** Confinement is what
   makes short-lived gatekeeper tokens (ASP-564) defensible: the profiles deny
   `ptrace`, `cap_sys_ptrace`, `cap_sys_admin`, raw sockets, and writes to
   `/home` `/root` `/etc` `/var/lib`. Unconfined agents can dump credentials
   from peer processes. AppArmor is a prerequisite control, not an optional
   extra.
4. **The fix is purely mechanical but cross-cutting:** call `install-apparmor.sh`
   from `install-daemon.sh`, stage profiles into the `.deb` + `postinst`, add
   `apparmor` + parser to the ISO hook, and add a
   `scripts/check-apparmor.sh` gate to `check-nightly.sh` + CI.

## Follow-up (recommended, NOT done here)

- Implement the wiring plan in `docs/plans/ASP-575.md` (installer + `.deb` +
  ISO + nightly/CI gate), fix `ollama`/`agnetic-agent` path drift, then flip
  H-014 status in the threat model to closed.
- Separate small slice: profile syntax/parse CI check (`apparmor_parser -p`
  or `apparmor_parser -Q` in CI) so profile edits can't silently break.

## Related

- Threat model H-014, H-010; `docs/SECURITY_THREAT_MODEL_v2.2.md` §8 P0#3.
- Plan: `docs/plans/ASP-575.md`; report:
  `docs/asp-575-apparmor-verification-report.md`.