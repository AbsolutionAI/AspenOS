SHELL := /bin/bash
CARGO := $(shell command -v cargo 2>/dev/null || echo "$(HOME)/.cargo/bin/cargo")
GO := go
export PATH := $(HOME)/.cargo/bin:$(HOME)/.local/bin:$(PATH)

.PHONY: all build build-agent cli install uninstall run dev stop clean status profile sandbox smoke fleet-smoke bench iso-smoke policyexec starshipd heald c11 iso-boot

all: build build-agent

# ─── Build ──────────────────────────────────────────────────────────
build:
	@command -v $(GO) >/dev/null 2>&1 || { echo "ERROR: go not found in PATH (install: sudo apt install golang-go)"; exit 1; }
	cd starshipctl && $(GO) build -o starshipctl .
	@ln -sf starshipctl starshipctl/agneticctl 2>/dev/null || true

build-agent:
	cd agent && $(CARGO) build --release

cli: build
	mkdir -p ~/.local/bin
	cp starshipctl/starshipctl ~/.local/bin/starshipctl
	ln -sf starshipctl ~/.local/bin/agneticctl

# ─── Install (requires root) ────────────────────────────────────────
install:
	@echo "Building binaries..."
	@$(MAKE) build build-agent
	@echo ""
	sudo bash scripts/install-daemon.sh

uninstall:
	sudo bash scripts/uninstall-daemon.sh

# ─── Dev mode (user-level, no root) ────────────────────────────────
# H-001: bus authenticates with multi-tenant accounts even in dev.
dev: cli
	@echo "Starting services in dev mode..."
	@if [ ! -f nats/fleet-accounts.conf ]; then \
		echo "Generating local NATS accounts creds (H-001)..."; \
		bash scripts/gen-nats-accounts.sh --out nats >/dev/null; \
	fi
	setsid nats-server -c nats/fleet-accounts.conf > /dev/null 2>&1 < /dev/null &
	sleep 1
	set -a; . ./nats/nats.env; set +a; \
	setsid .venv/bin/python3 agents/agent_daemon.py proxy > logs/agents-proxy.log 2>&1 < /dev/null &
	set -a; . ./nats/nats.env; set +a; \
	setsid .venv/bin/python3 agents/agent_daemon.py romi > logs/agents-romi.log 2>&1 < /dev/null &
	set -a; . ./nats/nats.env; set +a; \
	setsid .venv/bin/python3 agents/agent_daemon.py ergo > logs/agents-ergo.log 2>&1 < /dev/null &
	set -a; . ./nats/nats.env; set +a; \
	setsid .venv/bin/python3 tray/agnetic-status.py > logs/status-bridge.log 2>&1 < /dev/null &
	set -a; . ./nats/nats.env; set +a; \
	setsid .venv/bin/python3 scripts/message_history.py > logs/message-history.log 2>&1 < /dev/null &
	DASHBOARD_PORT=8788 setsid .venv/bin/python3 dashboard/server.py > logs/dashboard.log 2>&1 < /dev/null &
	sleep 2
	@$(MAKE) status

stop:
	-pkill nats-server 2>/dev/null
	-pkill staragent 2>/dev/null
	-pkill -f "agent_daemon.py" 2>/dev/null
	-pkill -f "agnetic-status.py" 2>/dev/null
	-pkill -f "message_history.py" 2>/dev/null
	-pkill -f "dashboard/server.py" 2>/dev/null
	@echo "All services stopped"

status:
	@echo ""
	@echo "=== Starship OS — Service Status ==="
	@echo ""
	@pgrep nats-server > /dev/null && echo "  ● nats-server        — running" || echo "  ● nats-server        — stopped"
	@pgrep staragent > /dev/null && echo "  ● staragent          — running" || echo "  ● staragent          — stopped"
	@pgrep -f "agent_daemon.py proxy" > /dev/null && echo "  ● agent proxy        — running" || echo "  ● agent proxy        — stopped"
	@pgrep -f "agent_daemon.py romi" > /dev/null && echo "  ● agent romi         — running" || echo "  ● agent romi         — stopped"
	@pgrep -f "agent_daemon.py ergo" > /dev/null && echo "  ● agent ergo         — running" || echo "  ● agent ergo         — stopped"
	@pgrep -f "agent_daemon.py robotics" > /dev/null && echo "  ● agent robotics     — running" || echo "  ● agent robotics     — stopped"
	@pgrep -f "agnetic-status.py" > /dev/null && echo "  ● status-bridge      — running" || echo "  ● status-bridge      — stopped"
	@pgrep -f "message_history.py" > /dev/null && echo "  ● message-history    — running" || echo "  ● message-history    — stopped"
	@ss -tlnp 2>/dev/null | grep -q 8788 && echo "  ● dashboard          — running (:8788)" || echo "  ● dashboard          — stopped"
	@ss -tlnp 2>/dev/null | grep -q 8790 && echo "  ● dashboard-dev      — running (:8790 fleet UI)" || true
	@pgrep -f "fleet.py daemon" > /dev/null && echo "  ● fleet-daemon       — running" || echo "  ● fleet-daemon       — stopped"
	@echo ""
	@echo "=== Ollama Models ==="
	@$(HOME)/.local/bin/ollama list 2>/dev/null || ollama list 2>/dev/null || echo "  (ollama not available)"
	@echo ""

# ─── Hardware profile ───────────────────────────────────────────────
profile:
	@bash scripts/select-profile.sh $(PROFILE)

# ─── C11 sandbox spike (ADR 0001) ───────────────────────────────────
sandbox:
	$(MAKE) -C src/c/sandbox_spike all test

policyexec:
	$(MAKE) -C src/c/policyexec all test

starshipd:
	$(MAKE) -C src/c/starshipd all test

heald:
	$(MAKE) -C src/c/heald all test

c11: sandbox policyexec starshipd heald

bench:
	@bash scripts/bench-sandbox.sh $(or $(N),200)

nats-accounts:
	@bash scripts/gen-nats-accounts.sh --out $(or $(OUT),nats/creds)

# ─── Smoke tests ────────────────────────────────────────────────────
smoke:
	@bash scripts/smoke-test.sh

fleet-smoke:
	@PYTHONPATH=agents:../aspen-swarm-manager:../aspen-edge-rrm ASPEN_SIM=1 python3 scripts/smoke-fleet-bus.py --repo-root "$$(pwd)"

iso-smoke:
	@bash scripts/iso-firstboot-smoke.sh

iso-boot:
	@command -v qemu-system-x86_64 >/dev/null 2>&1 || { echo "  SKIP  ISO boot smoke — qemu-system-x86_64 not installed (control-plane host)."; echo "        Static checks only via: make iso-smoke"; exit 0; }
	@bash scripts/iso-boot-smoke.sh

# ─── Clean ──────────────────────────────────────────────────────────
clean:
	rm -f starshipctl/starshipctl starshipctl/agneticctl
	rm -rf agent/target
	rm -rf __pycache__ agents/__pycache__ dashboard/__pycache__

# ─── Debian package ──────────────────────────────────────────────────
deb: build build-agent
	@bash scripts/build-deb.sh

# ─── ISO image (requires builder host toolchain — SKIP on control plane) ──
iso: build build-agent
	@command -v lb >/dev/null 2>&1 || { echo "  SKIP  ISO build — live-build (lb) not installed. This is a control-plane host."; echo "        See docs/ops/ISO_BUILDER.md"; exit 0; }
	@echo "Building ISO (requires root)..."
	sudo bash scripts/build-iso.sh

docker:
	docker build -t agnetic-os .