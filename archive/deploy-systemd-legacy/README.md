# Legacy deploy/ systemd units (archived)

These units are **historical** and are **not used by the packager**
(`scripts/build-deb.sh`, `scripts/install-daemon.sh`) or any other build path.
They were moved here from `deploy/` and preserved for reference only.

Why they are stale:

- `agnetic-agent-mesh.target` / `agnetic-agent@.service` require
  `nats.service` and `staragent.service` — unit names that never existed in
  the canonical tree (`systemd/agnetic-nats.service`,
  `systemd/agnetic-staragent.service`).
- `agnetic-agent@.service` uses the legacy `Type=forking` + PIDFile pattern
  with `User=tech`; the canonical unit is `Type=simple` as `User=agnetic`.
- Duplicate targets (`agnetic-agent-mesh.target`,
  `agnetic-dashboard.target`) competed with `systemd/agnetic-mesh.target`.

The live systemd units are in [`../../systemd/`](../../systemd/).
Closed under ASP-352 / ASP-152 / ASP-192.
