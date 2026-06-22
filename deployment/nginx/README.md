# nginx

Purpose: future reverse-proxy configuration for `datosenorden.cl`.

Expected responsibilities:

- Terminate or forward HTTPS traffic from an upstream TLS provider.
- Route public requests to the Reflex frontend service.
- Keep PostgreSQL unreachable from the public internet.
- Add conservative request size and timeout defaults.

No nginx config is active yet.
