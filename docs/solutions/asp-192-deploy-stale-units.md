# Learning: `deploy/` was a stale unit set — `systemd/` is the only canonical location

**Ticket:** ASP-192 (source: ASP-10 finding #9, re-flagged by the ASP-187 nightly packaging check)

## Problem

`deploy/` held 5 systemd units from an older layout that were never synced with
the canonical `systemd/` directory. Installing both sets produced broken
dependency chains:

- `deploy/agnetic-agent-mesh.target` required `nats.service` and
  `staragent.service` — names that do not exist anywhere (canonical units are
  `agnetic-nats.service` / `agnetic-staragent.service`), so the target could
  never start.
- `deploy/agnetic-agent@.service` used the legacy `Type=forking` + PIDFile +
  `User=tech` pattern; canonical is `Type=simple` as `User=agnetic`.
- Duplicate targets (`agnetic-agent-mesh.target`, `agnetic-dashboard.target`)
  competed with `systemd/agnetic-mesh.target`.

Nothing in Makefile, scripts, packaging, debian, iso, or CI referenced
`deploy/` — it was dead weight kept only out of caution ("Architect decision"
deferred in ASP-10 #9 / ASP-15 / ASP-16 / ASP-18).

## Fix

- Deleted the whole `deploy/` directory (5 files).
- Updated `docs/ARCHITECTURE_COMPLETE.md`: removed §2.8 (`deploy/`) and its
  §7 config-reference row; rewrote the §8.3 mesh service graph around the
  canonical `systemd/agnetic-mesh.target`; renumbered subsequent §2.x sections.

## Patterns to reuse

1. **One canonical home per artifact class.** When a second directory starts
   holding variants of the same artifacts (here: systemd units), decide the
   canonical location early and delete or archive the other — "alternative /
   advanced" copies rot within weeks.
2. **Unit-name drift breaks dependency chains silently.** A target requiring
   `nats.service` when only `agnetic-nats.service` exists fails at
   `systemctl start`, not in CI. Grep for `Requires=`/`After=` names against
   actual unit files when auditing.
3. **Dead directories still cost review attention** — multiple tickets spent
   effort explicitly scoping them out before the deletion landed.

## Verification

- `git grep -l 'agnetic-agent-mesh\|agnetic-dashboard-web'` → empty (outside
  historical plan/solution notes)
- No build/packaging path referenced `deploy/` before removal (grepped
  Makefile, scripts/, packaging/, debian/, iso/, .github/)
- Remaining units live solely under `systemd/` (9 files)

## Related

- `docs/plans/ASP-192-deploy-stale-units-cleanup.md`
- `docs/solutions/asp-15-install-systemd-path.md`,
  `docs/solutions/asp-16-health-checker-path.md` (both deferred this cleanup)
- `docs/ops/NIGHTLY_PACKAGING_DEPLOY_CHECK.md` (ASP-187 check that re-flagged it)
