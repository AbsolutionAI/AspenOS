# Plan: BEL-134 — Aider + Agent Zero under Paperclip

## Problem
Need specialized coding workers beyond OpenCode/Hermes: Aider (repo-native pair programmer) and Agent Zero (general autonomous agent runtime).

## Constraints
- No first-class Paperclip adapters for aider or agent-zero
- process adapter: one-shot command with PAPERCLIP_* env + API key
- Hire approval required on company
- CE gates mandatory for code edits
- Aider already installed (0.86.2) with ollama/qwen2.5-coder:7b
- Agent Zero typically Docker-based (agent0ai/agent-zero); large image pull may need time/disk

## Approach
1. **Aider worker (process adapter)**
   - Wrapper: `aspen-dev/scripts/paperclip-aider-worker.py`
   - On heartbeat: inbox → CE-GATE check → checkout → aider --yes-always --message-file --exit → comment + in_review
   - cwd: aspen-os git root; model: ollama/qwen2.5-coder:7b
   - reportsTo: aspen

2. **Agent Zero worker (process adapter)**
   - Wrapper: `aspen-dev/scripts/paperclip-agent-zero-worker.py`
   - Lifecycle: ensure docker container on 127.0.0.1:50080, data volume under aspen-dev/agent-zero/data
   - Report status on assigned issues; full prompt bridge = follow-up after UI config
   - Pull image if missing (best-effort; block with CE/ops note if pull denied)

3. **Proof**
   - ASP ticket assigned to Aider with Spec+Plan: tiny docs-only change
   - ASP ticket for A0: status/install verification

## Non-goals
- Replacing OpenCode as primary implementer
- Public exposure of Agent Zero UI (bind localhost only)
- Auto-posting social content

## Risks
- process adapter may not inject PAPERCLIP_TASK_ID → wrappers use inbox-lite fallback
- Ollama model quality/latency for Aider
- Docker image size for Agent Zero

## Disposition

**DEFERRED** (ASP-482 sweep — 2026-08-26) — Aider/Agent Zero integration deferred. Key blockers: Docker image size (~12GB disk), Ollama model quality/latency, fiscal freeze. Revisit when budget and infra constraints are resolved.
