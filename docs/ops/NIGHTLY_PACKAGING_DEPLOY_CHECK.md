# Nightly Packaging & Deployment Health Check

**Runbook:** BT-ASP-SRV (control-plane host)
**Frequency:** Nightly (automated via Paperclip liveness continuation)
**Last run:** 2026-08-25 (ASP-466)

## Objective

Verify the build, packaging, and deployment toolchain is healthy by running
static checks and smoke tests. ISO build steps are **SKIP** on this host
(see [ISO_BUILDER.md](ISO_BUILDER.md) — Option B).

## Checklist

### 1. Workspace Verification

```bash
cd /home/tech/projects/aspen-dev/repos/aspen-os
git rev-parse --show-toplevel   # must be aspen-os root
git remote -v                   # must point to AbsolutionAI/AspenOS.git
```

### 2. Toolchain

```bash
export PATH="$HOME/go/bin:$HOME/.local/bin:$PATH"
which nats-server               # must be on PATH
nats-server --version           # must print version (no error)
```

### 3. Build Smoke

```bash
make smoke                      # full smoke suite — all PASS expected
make iso-smoke                  # ISO static checks — all PASS expected
```

**Verdict:** Record pass/fail counts for each suite.

### 4. Static Inventory

| Artifact | Expected | Status |
|----------|----------|--------|
| systemd units | `systemd/*.service` + `*.target` | Count and log |
| Debian metadata | `debian/DEBIAN/{control,postinst,postrm,prerm}` | All present |
| `scripts/update.sh` | Present, executable | Verify |
| Windows packaging | `packaging/windows/*` | All present |

### 5. ISO Build

**SKIP** on this host. The `make iso` and `make iso-boot` targets are not
expected to work (toolchain absent per ISO_BUILDER.md). This SKIP is
documented and non-blocking.

## Results Format

Post to the run issue as a comment:

```
## Nightly Check — YYYY-MM-DD

**Verdict:** PASS / FAIL

### Smoke Results
- `make smoke`: X passed, 0 failed
- `make iso-smoke`: X passed, 0 failed

### Static Inventory
- systemd units: 9
- Debian metadata: OK (control, postinst, postrm, prerm)
- scripts/update.sh: present
- Windows packaging: OK (configure.bat, install.bat, README.txt,
  staragent.exe, staragent.yaml, uninstall.bat)

### Toolchain
- nats-server: v2.14.5
- go: go1.26.0

### Deviations from Baseline
(none / list any)
```
