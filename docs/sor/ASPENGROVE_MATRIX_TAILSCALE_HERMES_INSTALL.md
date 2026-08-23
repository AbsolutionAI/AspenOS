# AspenGrove — Matrix + Tailscale + Hermes Gateway Install Guide
**Aligned to AspenGrove Master Spec v4.0**  
**Linear:** BEL-198  
**Date:** 2026-08-06  

**Goal:** Operators can talk to and develop with the AspenGrove stack from a phone (or any device) while away from a PC, over a private mesh, with zero public federation.

---

## Architecture (locked)

```
Phone / Laptop
    │
    │ Tailscale mesh (WireGuard)
    ▼
Ubuntu 24.04 Server
    ├── Tailscale
    ├── Conduit (private Matrix homeserver)  ← matrix.aspen.local or TS MagicDNS
    ├── Hermes Messaging Gateway (Matrix adapter)
    ├── Paperclip (routes to Aspen Architect + roles)
    └── AspenOS agents / NATS / OpenCode
```

- **Tailscale** = private mesh foundation (already preferred)
- **Matrix (Conduit)** = structured multi-room conversation surface preferred over SimpleX for multi-agent rooms and phone UX
- **Hermes** = messaging gateway that maps Matrix rooms / DMs to Hermes roles and Paperclip companies
- **No public federation** — homeserver is non-federating

Room topology recommendation:
- `#aspen-architect` — primary CEO / Aspen Architect
- `#aspen-proxy` — engineering / security
- `#aspen-ergo` — planning / orchestration
- `#aspen-romi` — personal / creative
- `#aspen-ops` — fleet / plant status
- `#aspen-authz` — dual-human authorization requests (RED/BLACK)

---

## 1. Prerequisites

- Ubuntu 24.04 LTS server with Docker + Compose
- Tailscale account and auth key (or interactive login)
- Existing Paperclip + Hermes + AspenOS stack running (or at least Hermes binary available)
- Domain or MagicDNS name (e.g. `matrix.aspen.ts.net` or internal `matrix.aspen.local`)

---

## 2. Tailscale (mesh foundation)

```bash
# Install
curl -fsSL https://tailscale.com/install.sh | sh

# Authenticate (interactive or auth-key)
sudo tailscale up --hostname=aspen-server --accept-routes

# Optional: advertise routes if other subnets needed
# sudo tailscale up --advertise-routes=10.0.0.0/24

# Verify
tailscale status
tailscale ip -4
```

Install Tailscale on phone (iOS/Android) and log into the same tailnet.  
Prefer **MagicDNS** so the homeserver is reachable as `matrix.<tailnet>.ts.net` or a custom DNS name.

---

## 3. Private Conduit Matrix Homeserver (Docker)

Create directory:

```bash
sudo mkdir -p /opt/aspen/matrix/{data,config}
cd /opt/aspen/matrix
```

`docker-compose.yml`:

```yaml
services:
  conduit:
    image: matrixconduit/matrix-conduit:latest
    container_name: aspen-conduit
    restart: unless-stopped
    volumes:
      - ./data:/var/lib/conduit
      - ./config:/etc/conduit
    environment:
      CONDUIT_SERVER_NAME: "matrix.aspen.local"   # or your MagicDNS name
      CONDUIT_DATABASE_PATH: "/var/lib/conduit"
      CONDUIT_PORT: "6167"
      CONDUIT_ADDRESS: "0.0.0.0"
      CONDUIT_ALLOW_REGISTRATION: "false"         # invite-only / token later
      CONDUIT_ALLOW_FEDERATION: "false"           # CRITICAL — private only
      CONDUIT_MAX_REQUEST_SIZE: "20000000"
      CONDUIT_TRUSTED_SERVERS: "[]"
    ports:
      - "6167:6167"   # bind only on Tailscale IP in production if desired
    networks:
      - aspen-net

networks:
  aspen-net:
    external: true   # or create if not present
```

Start:

```bash
# Create network if needed
docker network create aspen-net || true

docker compose up -d
docker logs -f aspen-conduit
```

**Registration:** With `ALLOW_REGISTRATION=false`, create the first user via Conduit admin tools or temporary enable + disable. Prefer invite-only after bootstrap.

**TLS:** For phone clients over Tailscale you can start with plain HTTP on the mesh (WireGuard already encrypts). For production add Caddy or nginx reverse-proxy with internal CA or Tailscale HTTPS certificates.

---

## 4. Hermes Matrix Gateway Configuration

Assuming Hermes is already installed (from prior stack work). Example `.env` / config fragment for Matrix:

```bash
# /opt/aspen/hermes/.env  (or profile from aspen-hermes-profile-template)

MATRIX_HOMESERVER=http://127.0.0.1:6167
# or http://matrix.aspen.local:6167 if DNS resolves inside the host

MATRIX_ACCESS_TOKEN=<bot-or-service-user-access-token>
MATRIX_USER_ID=@hermes:matrix.aspen.local

# Hard allow-list — only these Matrix users may talk to agents
MATRIX_ALLOWED_USERS=@you:matrix.aspen.local,@ops:matrix.aspen.local

# Optional room → role mapping
MATRIX_ROOM_ARCHITECT=!xxxx:matrix.aspen.local
MATRIX_ROOM_PROXY=!yyyy:matrix.aspen.local
# ... etc
```

Generate access token:
1. Create a dedicated Matrix user for Hermes (e.g. `@hermes:matrix.aspen.local`)
2. Log in once with Element or `curl` login API
3. Capture the access token and store only in the secret env file (never commit)

Start / restart Hermes with the Matrix adapter enabled (exact flag depends on your Hermes build — see aspen-hermes-profile-template).

---

## 5. Systemd units (reliability)

Example for Conduit (if not already managed by Docker restart policy alone):

```ini
# /etc/systemd/system/aspen-conduit.service
[Unit]
Description=Aspen Conduit Matrix Homeserver
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/aspen/matrix
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
```

Hermes systemd unit (adjust paths):

```ini
# /etc/systemd/system/aspen-hermes.service
[Unit]
Description=Aspen Hermes Messaging Gateway
After=network-online.target aspen-conduit.service
Wants=network-online.target

[Service]
Type=simple
User=aspen
WorkingDirectory=/opt/aspen/hermes
EnvironmentFile=/opt/aspen/hermes/.env
ExecStart=/opt/aspen/hermes/hermes gateway --config /opt/aspen/hermes/config.yaml
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now aspen-conduit aspen-hermes
```

---

## 6. Phone client setup

1. Install **Element** (or any Matrix client) on phone
2. Connect to the same Tailscale tailnet
3. Homeserver URL: `http://matrix.<your-tailnet>.ts.net:6167` (or the MagicDNS / local name)
4. Log in with your allowed user
5. Join the Aspen rooms (or accept invites from Hermes / admin)

Test: send “status” or a simple command in `#aspen-architect` and confirm Paperclip/Hermes routes a response.

---

## 7. Security checklist

- [ ] `CONDUIT_ALLOW_FEDERATION=false`
- [ ] Registration disabled after bootstrap
- [ ] `MATRIX_ALLOWED_USERS` hard allow-list set
- [ ] Tailscale ACLs restrict who can reach port 6167 if desired
- [ ] Hermes runs as non-root user
- [ ] Access tokens only in env files with 600 permissions
- [ ] Dual-human authorization rooms for RED/BLACK actions (Aspen Sentinel path)

---

## 8. Alignment with AspenGrove products

| Component | Owner product |
|-----------|---------------|
| Conduit + Matrix ops docs | aspen-matrix-ops (plugin) + aspen-dev |
| Hermes profiles / personas | aspen-dev (canonical) |
| Paperclip routing of messages to agents | aspen-dev / AspenOS runtime |
| Phone UX & authorization modals | Aspen Sentinel (future surface) |

---

## 9. Next after green path

1. Mark BEL-198 acceptance criteria met once phone → agent round-trip works
2. Add Caddy or Tailscale HTTPS certificates for cleaner client config
3. Wire `#aspen-authz` room into the dual-human `propose_act` flow
4. Document room ACLs and power levels in aspen-matrix-ops

---

**Reference packages**  
- https://github.com/AbsolutionAI/aspen-matrix-ops  
- https://github.com/AbsolutionAI/aspen-hermes-profile-template  
- https://github.com/AbsolutionAI/aspen-dev  

**End of install guide**

---

**Project path (SoR):** `docs/sor/`  
**Ingested:** 2026-08-06T17:10:44-06:00  
**Rule:** Treat as authoritative; update via versioned revision, do not silently fork.
