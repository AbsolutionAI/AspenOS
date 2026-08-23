# BEL-182 Fleet E2E

**Proof:** https://github.com/AbsolutionAI/aspen-edge-rrm `make smoke` / `examples/fleet_e2e.py`

In-process bus proves register → heartbeat → ops.status, propose_act, estop refuse.

**Verified (2026-08-23):** aspen-edge-rrm `@aa3f84d` smoke green (fleet_e2e + mqtt + audit + status_cli).  
aspen-swarm-manager `@e662807` smoke green (mission + plant ACL + mock_cobot).  
Note: in-process E2E ≠ production JetStream; optional NATS/paho paths skip when deps/broker absent.
