# ASP-173 / H-005 — Ops role minimum-necessary tool allowlist

Status: implemented
Priority: HIGH (Security Threat Model v2.1, finding F-004)

## Problem

`config/policy.default.json` defines `roles.ops.tools.allow: []`. The C11
policyexec gate (`src/c/policyexec/policyexec.c`, `check_tool()`) treats a
non-empty allow list as a whitelist and an empty one as "no restriction" —
so every agent running as fleet team/role `ops` (the **default** identity,
see `fleet_policy.current_context()`) has unrestricted tool access.

## Approach

Policy-only change; no runtime code changes required. Both gates
(`fleet_policy.check_tool` Python-side and `policy_native.check_tool` →
policyexec C-side) read the same shared JSON contract, so populating
`roles.ops` restricts both enforcement paths at once.

### 1. Explicit ops tool allowlist (criterion 1)

Ops = plant operations & diagnostics. Allowlist derived from the union of
capabilities the fleet's default-team agents actually declare in their
toolsets (`agents/*.yaml`: terminal, file_operations, web_search, memory,
nats-adjacent scheduling, planning, delegation) mapped onto
`TOOL_DEFINITIONS` in `agents/tools.py`:

- filesystem / diagnostics: `read_file`, `write_file`, `list_dir`,
  `search_files`
- operational commands: `shell` (command blocklist still applies via
  `check-command`)
- network: `http_get`, `http_post` (cross-plant ACL still constrains
  targeted egress)
- delegation: `delegate_to_agent`, `delegate`
- memory: `memory_note`, `user_profile`, `archive_search`,
  `temporal_graph`, `temporal_chain`, `temporal_snapshot`, `kg_query`,
  `kg_store`, `preference_note`, `preference_query`
- scheduling: `create_schedule`, `list_schedules`, `remove_schedule`
- goals/planning: `goal_create`, `goal_list`, `goal_update`,
  `mission_create`, `mission_list`, `task_create`, `task_list`,
  `task_complete`

With a non-empty role allow list, anything unlisted is denied by policyexec
("not in allowlist") — fail closed for future tools until deliberately
added here.

### 2. Expanded deny lists (criterion 2)

Role-level `roles.ops.tools.deny` (defense-in-depth over the global deny):

- `opencode`, `opendesign` — OS expansion / design generation is not an
  operations capability
- `vault_approve`, `vault_deny` — HITL vault approval decisions are
  human-only; agent self-approval would be privilege escalation
  (`vault_sync`/`vault_list`/`vault_note`/`vault_stats` are simply not in
  the allow list — no current fleet workflow uses them; add back when one
  does)

Top-level `commands.blocklist` expanded with non-essential system tools
(high blast radius, none needed for day-to-day ops): `fdisk`, `sfdisk`,
`parted`, `blockdev`, `losetup`, `swapon`, `swapoff`, `insmod`, `rmmod`,
`modprobe`, `kexec`, `useradd`, `userdel`, `usermod`, `passwd`, `visudo`,
`crontab` (scheduling goes through the `create_schedule` tool instead).

### 3. Validation against existing agent capabilities (criterion 3)

- `tests/test_ops_tool_policy.py` runs the real policyexec binary against
  the real `config/policy.default.json`: ops allowed set passes, denied set
  fails, red-team behavior unchanged, no-role behavior unchanged, expanded
  blocklist denies new entries while keeping old ones.
- Python bridge check: `policy_native.check_tool` under
  `STARSHIP_FLEET_ROLES=ops` denies `vault_approve` / allows `shell`.
- `make policyexec` CLI smoke extended with ops-role assertions.

## Compatibility notes

- Agents without `STARSHIP_FLEET_TEAM` / `STARSHIP_FLEET_ROLES` /
  `fleet-node.yaml` are unaffected (no role → top-level policy only).
- `services/policy.py` PolicyManager reads a different schema
  (`command_blocklist` etc.) from other paths — untouched.
- Future tools must be added to the ops allowlist explicitly; that is the
  intended fail-closed posture.

Contract version bumped 2.1 → 2.2.
