# ASP-620 — Plugin local-path update()

## Problem

`PluginManager.update(name)` in `services/plugin_manager.py` was a placeholder
that always printed "Marketplace update not yet implemented." and returned
`False`. Yet `install_from_path` rejects re-installs with "Use update instead"
— a dead-end: an installed plugin could never be replaced with a newer version.

## Approach

Implemented a local-path update that mirrors the existing offline/local-first
install model:

- `update(name, source=None, force=False)`:
  - `source=None` keeps the marketplace stub message (no backend exists).
  - `source=<dir>` validates the manifest, requires matching plugin name, refuses
    downgrades and same-version no-ops unless `force=True`, then stages the new
    tree to a temp sibling, runs python deps + setup hook against the staging
    copy, and atomically swaps (existing dir → `.bak`, staging → live, rollback
    on failure, `.bak` removed on success).
- Follows `install_from_path` semantics and reuses existing helpers
  (`_parse_manifest`, `_install_python_deps`, `_run_setup_hook`,
  `discover`, `_persist_enabled_state`).
- Added a `_version_key` tuple-comparison helper consistent with the existing
  `_check_version_compat` pattern; wired the `update <name> <path>` CLI command.
- 12 new unit tests in `tests/test_plugin_manager.py` (tmp-dir plugins, no live
  system paths). Full suite: 350 passed / 4 skipped.

## Learnings

- The plugin manager defaults to `/opt/agnetic/plugins` unless either `./plugins`
  exists (dev) or the config `plugins.dir` is set — tests must pin a tmp dir via
  `config_path` to stay hermetic.
- Version "downgrade" vs "rebuild" is a product decision, not a technical one:
  same-version and lower-version updates are refused by default and require an
  explicit `force=True`, which also covers rebuild-from-source flows.

## Out of scope (escalated)

- Network marketplace fetch from `MARKETPLACE_URL` (`marketplace.agnetic.ai`)
  remains a documented stub: no backend exists, and enabling remote plugin
  supply-chain updates is an architecture/security decision for Aspen Architect.