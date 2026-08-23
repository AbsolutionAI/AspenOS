# Aspen OS — product principles (draft lock)

**Linear:** BEL-113  
**Audience:** SME manufacturers / dark-factory operators

## Pillars
1. **Local-first** — plant floor keeps working offline; cloud is optional acceleration
2. **Modular light core** — small coherent kernel; capability via plugins/agents
3. **Interoperability** — OPC-UA / MQTT / ROS2 / UNS as first-class edges
4. **SME speed** — time-to-resolution for shop issues beats feature breadth
5. **Auditability** — every agent action explainable; Linear SoR for humans
6. **Safety over autonomy** — human gates for physical actuators and spend

## Non-goals (now)
- Full MES replacement in v1
- Heavy local LLM on low VRAM as default control plane
- Multi-tenant SaaS before plant single-tenant works

## Success metric (principle test)
Can a plant manager see what broke, who/what is fixing it, and when it is safe — in under 5 minutes?
