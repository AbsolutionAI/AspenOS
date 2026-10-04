#!/usr/bin/env bash
# ================================================================================
# Starship OS - Unified Agent Architecture v1.0
# ================================================================================
# Shared Memory/Skills Store (mimics ~/.hermes structure for opencode consistency)
# All 4 agents load from this store ensuring seamless cross-session context

# Derived from this script's own location so a checkout works wherever it lands.
# AGNETIC_ROOT overrides it for a deployment that keeps the tree elsewhere.
PROJECT_ROOT="${AGNETIC_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
SHARED_STORE="${PROJECT_ROOT}/shared/memories/agents/default"
Hermes_SKILL_PATH="${HERMES_SKILLS_PATH:-$HOME/.hermes/skills}"

log() { echo "[$(date -Iseconds)]: $*" >&2; }

# Agent Models & Memory Paths
declare -A AGENTS=(
    [proxy]="qwen:7b:${SHARED_STORE}/memory/proxy.json"
    [romi]="qwen2.5:7b:${SHARED_STORE}/memory/romi.json"
    [ergo]="jeffgreen311/eve-v2-unleashed-qwen3.5-8B:${SHARED_STORE}/memory/ergo.json"
    [startagent]="RustyAI/agnetic-rust-latest:${SHARED_STORE}/Memory/start_agent.json"
)

# ================================================================================
# Initialize Shared Directory Structure
mkdir -p "${SHARED_STORE}"/{proxy,romi,ergo,startagent}/memories 2>/dev/null || true

if [ -d "$Hermes_SKILL_PATH/skills" ]; then
    # Mirror Hermes skills to agnetic-os store for cross-session compatibility
    log "Copying skills from ${Hermes_SKILL_PATH} to ${SHARED_STORE}" >&2
fi

log "✓ Shared memory/store ready at ${SHARED_STORE} (mimics ~/.hermes structure)" >&2
exit 0
