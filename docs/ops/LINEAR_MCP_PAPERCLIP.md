# Linear MCP ↔ Paperclip wiring

**Updated:** 2026-08-04

## What was installed
For **each** Paperclip company (ASP, ABSA, Content/BEL, ABS):

1. Secret `LINEAR_MCP_TOKEN` (local encrypted) — bearer from Hermes aspen Linear OAuth token  
2. Tool connection **Linear MCP** → `https://mcp.linear.app/mcp` (mcp_remote + Authorization header)  
3. Catalog refresh → **62** Linear tools  
4. Profiles:
   - `linear-full` — include whole connection (read+write)
   - `linear-read` — connection minus write/destructive tool names
5. Bindings:
   - Company default → linear-full
   - Agents: full for CEO/CTO/engineers/marketers/etc.; read for Summarizer, Reflection Coach, Dashboard, Compliance
6. Connection **installs** for company + each non-process agent

## Verified
- `test-calls` aspen → `list_teams` **allowed**, returned BellahTech + Family teams  
- Effective profile aspen: **62** allowed tools  

## Rotate token
When Hermes Linear OAuth is refreshed:
```text
POST /api/secrets/{secretId}/rotate  {"value":"<new access_token>"}
POST /api/tool-connections/{connectionId}/health-check
POST /api/tool-connections/{connectionId}/catalog/refresh
```
Token source: Hermes `HERMES_HOME=.../profiles/aspen` mcp-tokens/linear.json (do not commit).

## Limits
- Process adapters (Aider, Agent Zero) are not on the tool gateway path  
- Gateway session required for direct `/api/tool-gateway/tools/call` outside agent test-calls  
- Prefer Linear SoR for human visibility; agents should still comment Linear IDs on Paperclip issues  

## Connection IDs (reference)
[
  {
    "company": "Absolution Studios",
    "connectionId": "b8d06a05-6a8d-4dda-b909-5a8110b353a8",
    "installs": 3,
    "sampleAgent": "Reflection Coach",
    "allowed": 62
  },
  {
    "company": "Bellah Content Studio",
    "connectionId": "0382557b-8150-4172-bb03-7638496389a3",
    "installs": 5,
    "sampleAgent": "Content Lead",
    "allowed": 62
  },
  {
    "company": "Aspen OS Development Company",
    "connectionId": "d72c869d-dc45-4d72-ac6f-3be72a76a3b6",
    "installs": 12,
    "sampleAgent": "Reflection Coach",
    "allowed": 62
  },
  {
    "company": "Absolution Digital Commerce",
    "connectionId": "f0760031-e363-4bc2-a8e8-779fdfcaf90e",
    "installs": 7,
    "sampleAgent": "Digital CEO",
    "allowed": 62
  }
]
