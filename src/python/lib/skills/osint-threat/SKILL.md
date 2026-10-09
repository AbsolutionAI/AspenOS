# OSINT Threat Actor

OSINT sensor and threat actor intelligence for security operations.

## Capabilities
- Monitor open sources for threat actors targeting infrastructure
- Correlate indicators (IPs, domains, TTPs) with internal telemetry
- Generate threat reports and triage alerts
- Publish raw/ref findings to `aspen.sentinel.osint.ingest` (publish-only diode, ADR-0007)
- Store findings as DECISION / SEMANTIC memories

## Usage
- "scan for new threat actors on our infra"
- "OSINT on APT group X"
- "threat intel report"

## Dependencies
- web_search / http tools
- NATS publisher for `aspen.sentinel.osint.ingest` (publish-only; no subscribe)
- LanceDB for intel storage
