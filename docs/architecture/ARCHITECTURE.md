# DatosEnOrden Architecture

DatosEnOrden is a PostgreSQL-backed civic data explorer. It connects loaded
public records to entities, claims, evidence, and navigable relationships.

## Current Read Path

```text
Browser
  |
  v
Reflex Frontend
  |
  v
Service Layer
  |
  v
PostgreSQL Database
```

The service layer lives in `src/datosenorden/web/app_services.py`. It returns
plain dict/list data so that Reflex, Streamlit, FastAPI, or another future
frontend can consume the same project logic without importing persistence
details.

## Component Roles

### Browser

The browser only receives rendered frontend assets and application responses. It
must never receive PostgreSQL credentials or direct database connection details.

### Reflex Frontend

The Reflex app is the first frontend prototype for a future public interface. It
handles navigation, investigation layout, and presentation formatting.

### Service Layer

The service layer wraps existing DatosEnOrden maintenance/explorer logic. It is
frontend-independent and should remain focused on public read operations.

### Database

PostgreSQL remains the source of truth. It stores datasets, import jobs, source
records, claims, evidence, entities, and public relationship projections.

## Future API Layer Concept

A future public API can be added between frontend/client applications and the
service layer:

```text
Browser or API client
  |
  v
Public API Layer
  |
  v
Service Layer
  |
  v
PostgreSQL Database
```

The API layer would handle authentication, rate limits, request validation,
public response contracts, and operational logging. It should still avoid direct
database exposure and should use read-only credentials for public endpoints.

## Deployment Boundary

The deployment boundary should protect the database:

```text
Public internet
  |
  v
Reverse proxy / TLS
  |
  v
Frontend or API service
  |
  v
Private database network
```

This keeps the public surface small while preserving PostgreSQL as the internal
source of truth.
