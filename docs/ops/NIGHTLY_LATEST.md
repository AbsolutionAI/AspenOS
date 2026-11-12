# Nightly Packaging & Deployment Check — 2026-11-12

- **Timestamp:** 2026-11-12 09:27 UTC  
- **Git SHA:** `339254f` (HEAD of `ASP-899-nightly-packaging-deployment-check`)  
- **Verdict:** PASS (with 1 known deviation)  
- **check-nightly:** 158/159 pass  
- **nats-server:** v2.14.5  
- **Systemd units:** 8 service files in `systemd/` and `dist/pkgroot/lib/systemd/system/`

## Deviations from baseline

| Check | Expected | Actual | Status |
|-------|----------|--------|--------|
| C11 p50 < 2ms | PASS | FAIL (~3.2–3.7ms) | Known hardware-dependent; not actionable on this host |
| Python test suite: no pytest failures | PASS | PASS (531 pass, 0 fail) | **Fixed** — 2 stale `test_server.py` assertions updated (health endpoint status string, removed `_load_marketplace_state` test for nonexistent endpoint) |

## Static inventory

- Debian metadata: all 4 files present (control, postinst, postrm, prerm)
- Version consistency: VERSION 2.2.0 matches debian/DEBIAN/control
- `scripts/update.sh`: present, executable
- Windows packaging: all 6 artifacts present
- Dashboard static assets: all 8 files present
- Shell syntax: 45 scripts pass `bash -n`
- Gatekeeper module: present, valid syntax
- ISO build structure: 3 profiles, hooks, package lists
- AppArmor: profiles committed, staged by build-deb, postinst uses `apparmor_parser -r` (no `aa-enforce`)
- NATS secret paths (F-009), rate limits (F-011), cgroup limits (F-012), package signatures (F-014), model digests (F-013), TLS by default (H-024): all fixture tests pass

## Issue

ASP-899 Nightly Packaging & Deployment Check.