# aspen-gatekeeper

**License:** MIT
**Issue:** ASP-630 · Parent ASP-628 (packaging decision)
**ADR:** ADR-0008 (Core/Plugin/Dev-only) · ADR-0009 (capability-based gatekeepers)
**Classification:** plugin

In-monorepo plugin skeleton for the **ADR-0009 capability-based authorization gatekeeper**:
capability tokens, credential-strip proxy, safety-subject enforcement, dual-human gate on
safety proposals, and rate limits. Per the [ASP-628 decision](../../docs/plans/ASP-628-gatekeeper-packaging.md)
it is a loadable **plugin** (profile-default ON for actuator plants), **not** a second
always-on core-edge binary.

## Source of truth

This shell re-exports the monorepo package at `src/python/gatekeeper/` — the ~2k LOC stays
there until a later package extract. No fork.

## Smoke

```bash
make smoke
```

Wires the monorepo `src/python` onto `PYTHONPATH`, imports the plugin shell, and asserts
`classification == "plugin"` plus a working gatekeeper import.

## Subjects

| Direction | Subject |
|-----------|---------|
| subscribe | `aspen.authz.gate.request`, `aspen.authz.gate.decision` |
| publish   | `aspen.authz.gate.decision`, `aspen.authz.capability.grant`, `aspen.sentinel.audit.event` |

## Out of scope (hard stops)

No production image / deb / ISO change, no new public repo, no extract, no live NATS work.
See [docs/PACKAGES.md](../../docs/PACKAGES.md) row and [docs/plans/ASP-630.md](../../docs/plans/ASP-630.md).