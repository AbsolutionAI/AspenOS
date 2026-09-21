# ASP-630 — aspen-gatekeeper plugin skeleton (monorepo, no image)

## Problem

ASP-628 recorded the packaging decision (gatekeeper = plugin, profile-default ON for
actuator plants) but left no installable shape: PACKAGES.md named a production target
`aspen-gatekeeper` with no skeleton, and a future extract had nothing to build on.

## Approach

Cut an **in-monorepo** plugin skeleton under `plugins/aspen-gatekeeper/`, shelf-stable
until a packaging-sprint extract:

- `pyproject.toml` with `[tool.aspen] classification = "plugin"` (declared, tomllib-readable).
- `manifest.json` — capabilities (capability_tokens, credential_strip_proxy,
  safety_subject_enforcement, dual_human_gate, rate_limiting), NATS subjects (from
  `nats_client.py`: request/decision/grant/audit), version synced to `pyproject.toml`.
- Thin `aspen_gatekeeper/__init__.py` that re-exports the monorepo `gatekeeper` `__all__`
  (no fork of the ~2k LOC; SoR untouched).
- `Makefile` with `make smoke` — prefers the monorepo venv python, puts both
  `plugins/aspen-gatekeeper` and `src/python` on `PYTHONPATH`, runs the skeleton tests +
  an import assertion (classification=plugin).
- `tests/test_skeleton.py` (4 tests) — plugin shell imports the monorepo gatekeeper,
  re-exports are identity-identical, pyproject + manifest agree on version/classification.
- README + SECURITY one-pagers (docs-lite, mirroring aspen-edge-rrm).
- `docs/PACKAGES.md` extract-status line updated: skeleton exists; **no image matrix**.

## Verification

- `make smoke` — 4 passed, smoke ok.
- Existing gatekeeper suites — 133 passed (dual-human / nats / phase2 / rate-limiting), no regressions.
- No production image / deb / ISO change; no new repo; no live NATS work.

## Learnings

- A plugin-classification field must be machine-readable via stdlib before the packaging
  mesh exists: `[tool.aspen] classification` in pyproject + mirror in manifest.json is
  cheap and testable with `tomllib`.
- re-exporting `from gatekeeper import *` honors the module's own `__all__`, so the thin
  shell stays honest with the SoR exports for free.
- Makefile should resolve the monorepo venv via an absolute path; a relative
  `../../.venv/bin/python` triggers a harmless-but-noisy `sys.prefix` RuntimeWarning.
- Keep the manifest subject list derived from the real NATS client constants, not a
  hand-drawn copy, to avoid subject drift.

## Out of scope (correctly deferred)

- Package extract to its own repository / Paperclip catalog install hook (packaging sprint).
- Image matrix / profile-assertion CI (H-019 follow-up, needs Captain sign-off for image work).
- Durable token backend (Redis/PG).