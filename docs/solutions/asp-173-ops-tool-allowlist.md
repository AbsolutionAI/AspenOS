# Ops role minimum-necessary tool allowlist (ASP-173 / H-005)

**Date:** 2026-08-24
**Tickets:** ASP-173 (H-005)

## Problem

`config/policy.default.json` defined `roles.ops.tools.allow: []`. The C11
policyexec gate treats a non-empty allow list as a whitelist and an empty one
as "no restriction" — so every agent running as fleet team/role `ops` (the
default identity) had unrestricted tool access.

## Solution

Policy-only change; no runtime code changes required:

1. **Explicit ops tool allowlist** — 30 tools across filesystem, diagnostics,
   shell, network, delegation, memory, scheduling, and goals/planning categories.
   Anything unlisted is denied by policyexec ("not in allowlist").
2. **Expanded deny lists** — role-level `roles.ops.tools.deny` blocks
   `opencode`, `opendesign`, `vault_approve`, `vault_deny`. Global
   `commands.blocklist` expanded with high-blast-radius system tools
   (`fdisk`, `parted`, `modprobe`, `kexec`, `useradd`, `crontab`, etc.).
3. **Policy contract version** bumped 2.1 → 2.2.
4. **Test coverage** for all three layers (allow pass, deny fail, red-team
   unchanged, expanded blocklist).

## Patterns to reuse

1. **Policy-only hardening is the cheapest.** No code change means no regression
   surface beyond the policy file itself. Both gates (Python fleet_policy and C11
   policyexec) read the same JSON contract.
2. **Fail-closed by default on missing allowlist entries.** A non-empty allow list
   denies everything unlisted. Future tools must be explicitly added.
3. **Defense-in-depth with role-level deny.** Even if a tool is in the allow list,
   a role-level deny blocks it first. This catches cases where a tool was added
   for one role but shouldn't be available to ops.

## Verification

- `tests/test_ops_tool_policy.py` — 51 tests run the real policyexec binary
  against the real `config/policy.default.json`: ops allowed set passes, denied
  set fails, red-team behavior unchanged, no-role behavior unchanged, expanded
  blocklist denies new entries while keeping old ones.
- Python bridge: `policy_native.check_tool` under `STARSHIP_FLEET_ROLES=ops`
  denies `vault_approve` / allows `shell`.

## Remaining

- Agents without `STARSHIP_FLEET_TEAM`/`STARSHIP_FLEET_ROLES`/`fleet-node.yaml`
  are unaffected (no role → top-level policy only). This is intentional — it
  matches the existing authz model where unconfigured agents get the default
  top-level policy.
