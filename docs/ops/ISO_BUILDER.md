# ISO / Debian Builder Notes

**Option B — control-plane host policy:** ISO and Debian builds are **SKIP by design** on
the control-plane host (`option_b`). This host performs static checks only; no source→image
build runs here.

## Why

- ISO builds require root / nested virtualization, which is not feasible in CI or on the
  control-plane host.
- The nightly check suite (`docs/ops/NIGHTLY_PACKAGING_DEPLOY_CHECK.md`) therefore statically
  verifies the ISO build structure (autoinstall profiles, chroot hooks, package lists) and
  Debian packaging metadata instead of invoking the live builders.
- See `docs/ops/NIGHTLY_PACKAGING_DEPLOY_CHECK.md` → "What is NOT checked" for the full
  list of build steps that are intentionally not exercised on this host.

## What is checked instead

- ISO build structure: `autoinstall/user-data.{edge,server,ops}.yaml` profiles, chroot hooks,
  package lists (Section 14 of the nightly check).
- Debian metadata: `debian/DEBIAN/{control,postinst,postrm,prerm}` (Section 9).
- Debian package build is exercised by Section 5 of `scripts/check-nightly.sh` and produces
  `dist/starship-os_<ver>_amd64.deb` when a builder host runs it.

## Build steps that remain out of scope on this host

| Step | Reason |
| --- | --- |
| ISO build from source | Requires root / nested virt |
| Windows packaging build from source | No CI build host; artifacts are pre-built |
| Docker image build (`make docker`) | Not part of nightly surface |
| Performance benchmarks (`make bench`) | Run on demand, not nightly |