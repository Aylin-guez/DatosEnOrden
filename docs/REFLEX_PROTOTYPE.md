# Reflex Prototype

## Purpose

Phase 12.0 adds a frontend-independent service layer and a minimal Reflex app for
DatosEnOrden. The prototype proves that Home, Search, and Investigation views can
read plain dict/list data from `datosenorden.web.app_services` without importing
SQLAlchemy models or Streamlit code.

Streamlit remains the current local prototype. This Reflex app is additive.

## Install

Install project dependencies in your local environment:

```powershell
python -m pip install -e ".[dev]"
```

The base project dependencies include Reflex for this prototype.

## Run

From the repository root:

```powershell
cd web\reflex_app
$env:PYTHONPATH="..\..\src"
reflex run
```

Then open the local Reflex URL printed by the command.

## Environment Variables

The Reflex prototype uses the same environment as the rest of DatosEnOrden:

- `DATABASE_URL`: local PostgreSQL connection string.
- `DEMO_MODE`: optional local flag used by the existing demo tooling.

No external APIs are called by the prototype.

## Limitations

- This is a first local prototype, not a production deployment.
- Investigation navigation is state-based: select an entity from Search, then the
  app opens the Investigation page.
- The app intentionally uses simple cards and text summaries instead of a custom
  graph renderer.
- Sample/demo data must stay clearly labeled in the underlying loaders and
  dataset registry.

## Relationship To Streamlit

Streamlit is not removed or replaced. It remains compatible and continues to use
the existing maintenance modules directly.

The new service layer sits between frontend code and existing project logic. It
returns JSON-like dict/list structures that can be consumed by Reflex, Streamlit,
FastAPI, or another future frontend.

## Security Notes

- Never expose a local PostgreSQL instance publicly.
- Never commit `.env` or private connection strings.
- Keep PostgreSQL as the source of truth.
- Deploy later with a hosted, read-only database or read-only credentials.
- Do not add public datasets or external API calls through the frontend.
