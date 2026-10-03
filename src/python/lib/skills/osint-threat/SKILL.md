# OSINT Threat Actor

Open-source threat actor intelligence for security operations.

## Capabilities
- Monitor open sources for threat actors targeting infrastructure
- Correlate indicators (IPs, domains, TTPs) with internal telemetry
- Generate threat reports and triage alerts
- Store findings as SEMANTIC / EPISODIC memories via the memory service

## Usage
- "scan for new threat actors on our infra"
- "OSINT on APT group X"
- "threat intel report"

## Dependencies
- web_search / http tools
- Optional: LanceDB-backed agent memory via `services/memory.py` (falls back to flat
  files when `lancedb` is not installed) for recall across sessions — not an intel
  store of its own

## Not this skill
- There is no `hybrid_intel` service and no `osint_sensor` service. Do not import,
  call, or invent one.
- If fleet OSINT ingest is wanted, the contract is the ADR-0007 subject
  `aspen.sentinel.osint.ingest` (publish-only data diode). This skill does not
  publish to it.
- This skill has no dashboard pane, no sweep scheduler, and no `/api/intel` API.
  Analysis is ad hoc, driven by the requester.
