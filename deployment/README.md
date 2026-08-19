# Deployment Pack

This folder contains the first public deployment pack for DatosEnOrden.

Use it together with `docs/VPS_GO_LIVE_STEPS.md` during the first VPS deploy.
The current pack assumes:

- Ubuntu 24.04 LTS or any host with Python `>=3.12`
- Reflex backend-only on loopback, consuming PREPARE-exported artifacts
- Caddy serving the immutable frontend and proxying `/api` to Reflex
- PostgreSQL kept private on localhost or a private network
- systemd as the process supervisor

Current rule: do not expose local PostgreSQL publicly.

`../docker-compose.yml` is a local development database convenience only and is not an authorized production deployment path.
