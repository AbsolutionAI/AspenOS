# ASP-370 / F-021 / H-HOST-01: AUDITOR_BASELINE SSH+UFW apply script (lockout-safe)

**Status:** READY_FOR_AIDER_QA
**Mode:** IMPLEMENTATION
**Source:** Security Threat Model v2.2 / F-021 — HIGH; host findings on `bt-asp-srv`
**Plan:** `docs/plans/ASP-370.md`
**Updated:** 2026-09-21

## Summary

The control plane allowed `PermitRootLogin yes`, `PasswordAuthentication yes`,
and had no default-deny firewall. F-021 calls for closing those host surfaces.
Captain approved the apply window on 2026-09-21; because the host has no
passwordless sudo, the deliverable is a **self-guarding apply script** whose
default mode is `--dry-run`. The agent produces the script + hermetic tests;
the human runs `--apply` with sudo after proof.

## Decision (recorded)

**Ship `scripts/apply-auditor-baseline.sh`: dry-run by default, sudo-only
`--apply`, lockout allowlist gate that fails closed.**

| Concern | Decision | Why |
|---------|----------|-----|
| Default mode | `--dry-run` | A plain run must never touch the live control plane |
| Apply | `--apply`; non-root refused with clear error | Headless host, no passwordless sudo |
| Allowlist gate | Refuse apply unless every lockout port is in the planned ruleset | Never risk losing SSH/Tailscale on a remote control plane |
| SSH changes | Drop-in `/etc/ssh/sshd_config.d/99-aspen-baseline.conf`, not the whole file | Scratching the whole `sshd_config` would break host-specific settings |
| Firewall changes | UFW default-deny + explicit allowlist (22, 443, 3100 TS, 8788, 3000 TS, `tailscale0`) | F-021 default-allow-incoming closes off |
| `ufw enable` / sshd reload | Never executed by the script — printed as the human's final sudo steps | The agent cannot hold the sudo window open safely; Captain directive |
| Tests | Hermetic fixture; never shell out to live `ufw`/`sshd`; never apply as root | Prevents the checker itself from locking out the host |

### Lockout allowlist (enforced by the gate)

- SSH `:22` (pubkey only, `PasswordAuthentication no`)
- nginx `:443` (Matrix/frozen)
- Paperclip `:3100` on Tailscale `100.78.55.13`
- Hermes dashboard `:8788`
- Buzz `:3000` (Tailscale + loopback via `100.64.0.0/10`)
- Tailscale interface `tailscale0` open on the interface

## Threat-model checklist — F-021 marked

- [x] **F-021 / H-HOST-01 SSH+UFW baseline** — `scripts/apply-auditor-baseline.sh`
      lands the hardening with a fail-closed allowlist gate; dry-run default;
      sshd drop-in (`PermitRootLogin no`, `PasswordAuthentication no`,
      `PubkeyAuthentication yes`, `AllowUsers` restricted); UFW
      default-deny incoming + explicit allowlist. 11 hermetic tests.
- [ ] **Live apply on `bt-asp-srv`** — captain/aspen run
      `sudo scripts/apply-auditor-baseline.sh --apply` after proof, then
      `sudo ufw --force enable` and `sudo systemctl reload ssh` (human steps).

## Changes

- `docs/plans/ASP-370.md` — plan (problem, decision, allowlist, verification)
- `scripts/apply-auditor-baseline.sh` — new apply script (dry-run default)
- `tests/test_apply_auditor_baseline.py` — new hermetic suite (11 tests)
- `docs/solutions/asp-370-ssh-ufw.md` — this compound note

## Lessons

1. **Lockout-safe apply scripting has three layers:** dry-run default, a
   fail-closed allowlist gate over the *planned* ruleset, and leaving
   irreversible steps (`ufw enable`, service reload) as explicit human sudo
   steps. The script that audits the firewall must never be able to brick the
   host it runs on.
2. **AllowUsers must come from the operator env, not a hard-coded user:** the
   script resolves `$SUDO_USER`/`$USER` by default and honors
   `ASPEN_SSH_ALLOW_USERS` so applying on a different host cannot lock out the
   wrong account.
3. **Hermetic, not just mocked:** the test suite does not need to fake ufw —
   it sources the script to exercise pure functions (`render_ufw_rules`,
   `check_allowlist_in_rules`) and runs the dry-run subprocess, asserting no
   system file changes. Root-apply tests are skipped when the suite is root.

## Handoff

`READY_FOR_AIDER_QA` — Aider (3dc7889f-57a8-4db1-b67b-ed044f88f2d0). Auditor
approves; captain/aspen run live `--apply` + enable/reload steps with sudo.