#!/usr/bin/env bash
# Starship OS — Nightly Packaging & Deployment Check
# Runs unattended in CI (GitHub Actions scheduled workflow).
# Reports pass/fail summary; exits non-zero on any failure.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"

PASS=0
FAIL=0
TIMING_BEGIN=$(date +%s%N)

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

check() {
  local name="$1"; shift
  echo -ne "  ${BLUE}RUN${NC}    $name ... "
  if "$@" >/tmp/nightly-check.log 2>&1; then
    echo -e "${GREEN}PASS${NC}"
    PASS=$((PASS+1))
  else
    echo -e "${RED}FAIL${NC}"
    echo "  └─ Output (last 20 lines):"
    tail -20 /tmp/nightly-check.log | sed 's/^/      /'
    FAIL=$((FAIL+1))
  fi
}

echo ""
echo -e "${BLUE}╔══════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Starship OS — Nightly Check                 ║${NC}"
echo -e "${BLUE}║  $(date -u '+%Y-%m-%d %H:%M:%S UTC')${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo "Version: $(cat VERSION 2>/dev/null || echo unknown)"
echo ""

# ─── Pre-flight tooling ─────────────────────────────────────
check "go toolchain" command -v go
check "cargo toolchain" bash -c 'command -v cargo || command -v ~/.cargo/bin/cargo'
check "gcc + seccomp" bash -c 'gcc --version >/dev/null && dpkg -l libseccomp-dev 2>/dev/null | grep -q ^ii'

# ─── Section 1: Go build ────────────────────────────────────
echo -e "\n${YELLOW}── Section 1: Go build ──${NC}"
check "starshipctl builds" make build
check "starshipctl version" bash -c './starshipctl/starshipctl version 2>/dev/null'

# ─── Section 2: Rust build ───────────────────────────────────
echo -e "\n${YELLOW}── Section 2: Rust agent build ──${NC}"
check "staragent builds" make build-agent

# ─── Section 3: C11 components ───────────────────────────────
echo -e "\n${YELLOW}── Section 3: C11 components ──${NC}"
check "sandbox_spike builds" make -C src/c/sandbox_spike all
check "policyexec builds" make -C src/c/policyexec all
check "starshipd builds" make -C src/c/starshipd all
check "heald builds" make -C src/c/heald all

# ─── Section 4: Smoke tests ──────────────────────────────────
echo -e "\n${YELLOW}── Section 4: Smoke tests ──${NC}"
check "smoke test suite" bash scripts/smoke-test.sh

# ─── Section 5: Debian package ───────────────────────────────
echo -e "\n${YELLOW}── Section 5: Debian package ──${NC}"
check "deb package builds" bash scripts/build-deb.sh
DEB_FILE=$(ls dist/starship-os_*.deb 2>/dev/null | head -1)
if [[ -n "$DEB_FILE" ]]; then
  check "deb package size > 1MB" bash -c "test \"\$(stat -c%s '$DEB_FILE' 2>/dev/null)\" -gt 1048576"
else
  check "deb package exists" false
fi

# ─── Section 6: Systemd units ────────────────────────────────
echo -e "\n${YELLOW}── Section 6: Systemd unit validation ──${NC}"
check "nats unit exists" test -f systemd/agnetic-nats.service
check "staragent unit exists" test -f systemd/agnetic-staragent.service
check "agent template exists" test -f systemd/agnetic-agent@.service
check "dashboard unit exists" test -f systemd/agnetic-dashboard.service
check "fleet unit exists" test -f systemd/starship-fleet.service
check "health-checker unit exists" test -f systemd/starship-health-checker.service
check "mesh target exists" test -f systemd/agnetic-mesh.target
check "status bridge unit exists" test -f systemd/agnetic-status-bridge.service
check "message history unit exists" test -f systemd/agnetic-message-history.service

# ─── Section 7: Shell syntax ─────────────────────────────────
echo -e "\n${YELLOW}── Section 7: Shell syntax check ──${NC}"
for script in scripts/*.sh; do
  [[ -f "$script" ]] || continue
  name=$(basename "$script")
  check "bash -n $name" bash -n "$script"
done

# ─── Section 8: Key file presence ────────────────────────────
echo -e "\n${YELLOW}── Section 8: Key file presence ──${NC}"
check "VERSION file" test -f VERSION
check "Makefile" test -f Makefile
check "config/fleet.yaml" test -f config/fleet.yaml
check "config/profiles.yaml" test -f config/profiles.yaml
check "config/policy.default.json" test -f config/policy.default.json
check "nats/agent-bus.conf" test -f nats/agent-bus.conf
check "nats/fleet-bus.conf" test -f nats/fleet-bus.conf
check "nats/subjects.yaml" test -f nats/subjects.yaml
check "third_party/pins.json" test -f third_party/pins.json
check "VERSION matches debian/control" bash -c 'v=$(cat VERSION 2>/dev/null); grep -q "^Version: $v$" debian/DEBIAN/control 2>/dev/null'

# ─── Section 9: Debian metadata ─────────────────────────────
echo -e "\n${YELLOW}── Section 9: Debian metadata ──${NC}"
check "debian control file" test -f debian/DEBIAN/control
check "debian postinst" test -f debian/DEBIAN/postinst
check "debian postrm" test -f debian/DEBIAN/postrm
check "debian prerm" test -f debian/DEBIAN/prerm
check "debian control declares starship-os" grep -q '^Package: starship-os' debian/DEBIAN/control

# ─── Section 10: Windows packaging ──────────────────────────
echo -e "\n${YELLOW}── Section 10: Windows packaging ──${NC}"
check "windows install.bat" test -f packaging/windows/install.bat
check "windows configure.bat" test -f packaging/windows/configure.bat
check "windows uninstall.bat" test -f packaging/windows/uninstall.bat
check "windows staragent.exe" test -f packaging/windows/staragent.exe
check "windows staragent.yaml" test -f packaging/windows/staragent.yaml
check "windows README.txt" test -f packaging/windows/README.txt

# ─── Section 11: Update mechanism ───────────────────────────
echo -e "\n${YELLOW}── Section 11: Update mechanism ──${NC}"
check "update.sh exists" test -f scripts/update.sh
check "update.sh executable" test -x scripts/update.sh

# ─── Summary ─────────────────────────────────────────────────
TIMING_END=$(date +%s%N)
ELAPSED_MS=$(( (TIMING_END - TIMING_BEGIN) / 1000000 ))
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════${NC}"
if [[ "$FAIL" -eq 0 ]]; then
  echo -e "${GREEN}  NIGHTLY CHECK PASSED${NC}"
else
  echo -e "${RED}  NIGHTLY CHECK FAILED (${FAIL} failures)${NC}"
fi
echo -e "${BLUE}═══════════════════════════════════════════════${NC}"
echo ""
echo -e "  Passed: ${GREEN}${PASS}${NC}"
echo -e "  Failed: ${RED}${FAIL}${NC}"
echo -e "  Time:   ${ELAPSED_MS}ms"
echo ""
exit "$FAIL"