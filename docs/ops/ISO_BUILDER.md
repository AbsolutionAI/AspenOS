# ISO Builder — Host Role Decision

**Issue:** ASP-356 / ASP-358
**Decision date:** 2026-08-23
**Status:** Final — Implemented
**Owner:** packndeploy

## Decision: Option B — Separate ISO builder host

**BT-ASP-SRV is a control-plane node and is NOT an ISO builder.**

The ISO build toolchain (`live-build` + `qemu-system-x86_64`) is **not** installed on the
control-plane host. The nightly packaging check explicitly skips ISO build and boot-probe
steps with a documented `SKIP`. The `make iso` and `make iso-boot` targets gracefully
skip when toolchain is absent.

## Rationale

| Factor | Weight | Reasoning |
|--------|--------|-----------|
| Build duration | high | `lb build` takes 30–60 minutes — too heavy for a control-plane nightly routine |
| Root requirement | high | `build-iso.sh` requires root (apt install live-build + chroot work); control plane should minimise code running as root |
| Attack surface | medium | live-build + qemu add ~30 packages with elevated capabilities on a host holding Paperclip API keys + Hermes credentials |
| Docker available | low | Docker 29.7 is present but running the full live-build pipeline inside a container on the control plane still consumes the same CPU/RAM/I/O and root time |
| Reproducibility | medium | A separate builder VM can be destroyed and re-provisioned without touching the control plane |

## Host roles

| Host | Role | Builder toolchain | Nightly ISO check |
|------|------|-------------------|-------------------|
| **BT-ASP-SRV** | Control plane (Paperclip API, Postgres, Hermes agents) | ❌ Not installed | `SKIP` — documented, non-blocking |
| **ISO builder** (TBD) | Dedicated ISO build + boot-probe host | ✅ live-build + qemu-system-x86_64 | Full `iso-smoke` + `iso-boot` |

## Prerequisites for a builder host

Any Ubuntu 24.04+ machine (bare metal, VM, or cloud instance) with:

### Hardware minimums
- 4 GB RAM (8 GB recommended)
- 2 vCPUs
- 20 GB free disk
- amd64 architecture

### Software
```bash
sudo apt update
sudo apt install -y live-build xorriso squashfs-tools grub-pc-bin grub-efi-amd64-bin \
                     qemu-system-x86 qemu-utils golang-go
```

### Verifying the toolchain
```bash
lb --version          # live-build
qemu-system-x86_64 --version
qemu-img --version
go version            # needed by build-iso.sh (pre-flight check)
rustc --version       # needed for staragent build (build-agent target)
cargo --version       # needed for staragent build
```

## Build workflow on a builder host

### Clone and build (builder host only)
```bash
git clone https://github.com/AbsolutionAI/AspenOS.git
cd AspenOS
make iso              # builds ISO (requires root, 30–60 min)
```

The ISO lands at `dist/agnet-os-<version>-amd64.iso`.

### Static smoke (no QEMU required — runs on any host)
```bash
make iso-smoke        # static autoinstall + firstboot profile checks
```

### Boot probe (requires qemu)
```bash
make iso-boot         # static checks + QEMU probe if qemu-system-x86_64 present
# Or directly:
scripts/iso-boot-smoke.sh
```

## Nightly routine

On the builder host, the nightly check runs the full sequence:

```bash
cd /home/tech/projects/aspen-dev/repos/aspen-os
git pull --ff-only
make build build-agent         # rebuild binaries
make iso                       # build ISO (~30–60 min)
make iso-boot                  # static smoke on built ISO
# Optional: scripts/iso-boot-smoke.sh for qemu probe
```

On the control plane (BT-ASP-SRV), ISO steps are explicitly skipped.

## Transfer artifacts (optional)

If the builder host is not the primary development machine, copy artifacts:

```bash
# From builder to dev machine
scp dist/agnet-os-*-amd64.iso user@dev-machine:~/isos/

# Or publish to a release
# (future: CI integration with GitHub Releases)
```