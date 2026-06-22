# DatosEnOrden web architecture

## Current goal

Prepare DatosEnOrden for two parallel paths:

1. Static public landing page for datosenorden.cl.
2. Future Python web app using Reflex or another frontend over a frontend-independent service layer.

## Security notes

- Do not expose the local PostgreSQL database publicly.
- Do not deploy .env.
- Do not commit secrets.
- Do not expose database credentials in frontend code.
- Public web apps should use a hosted database or read-only API layer.
- Demo/sample data must remain clearly labeled when applicable.

## Current folders

- web/landing/: static landing page.
- web/reflex_app/: future Reflex prototype.
- src/datosenorden/web/: future frontend-independent service layer.
