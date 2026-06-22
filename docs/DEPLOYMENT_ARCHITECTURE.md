# Deployment Architecture

This document describes a future public deployment path for DatosEnOrden. It is
not a deployment runbook and does not expose the current local PostgreSQL
database.

## Local Development Architecture

Local development currently runs on one machine:

```text
Developer browser
  |
  | localhost
  v
Streamlit prototype or Reflex prototype
  |
  v
Frontend-independent service layer
  |
  v
Local PostgreSQL database
```

In local mode, PostgreSQL remains the source of truth. The Streamlit prototype,
the Reflex prototype, scripts, and tests all read through project code and local
configuration. This is appropriate for development but not for public exposure.

## Public Deployment Architecture

A future public deployment should separate the public web surface from database
storage:

```text
Public browser
  |
  | HTTPS datosenorden.cl
  v
Cloudflare / DNS / TLS / basic protection
  |
  v
Reverse proxy
  |
  v
Reflex frontend service
  |
  v
DatosEnOrden service layer
  |
  v
Hosted PostgreSQL with private network access and read-only credentials
```

The current Streamlit prototype can remain a local/internal tool. The public
site should use a dedicated frontend process and a controlled service boundary.

## Separation Of Responsibilities

### Database

- Stores normalized public records, claims, evidence, and projected
  relationships.
- Must not accept direct public internet traffic.
- Should use a hosted PostgreSQL instance or private database host for future
  deployment.
- Public application credentials should be read-only unless a specific ingestion
  process needs a separate write credential.

### Services

- Load data from PostgreSQL through existing project code.
- Convert internal dataclasses/models into plain dict/list structures.
- Enforce the public read path and keep persistence details out of frontend
  components.
- Provide a future API boundary if DatosEnOrden needs public machine-readable
  access.

### Frontend

- Renders public pages, search, investigation views, and explanations.
- Does not connect directly to PostgreSQL.
- Does not contain database credentials.
- Should display neutral language and evidence-first warnings.

## Security Considerations

- Never expose local PostgreSQL to the public internet.
- Never commit `.env` files or connection strings.
- Use TLS for public traffic.
- Keep database credentials out of browser-delivered code.
- Use read-only database users for public services.
- Keep ingestion/write workflows separate from public read services.
- Log operational failures without exposing secrets.
- Treat sample/demo datasets as clearly labeled non-production data.

## Why PostgreSQL Should Never Be Directly Exposed

PostgreSQL is a storage engine, not a public web interface. Exposing it directly
would create unnecessary risk:

- Attackers could attempt credential brute force or protocol-level attacks.
- Misconfigured users could read, write, or delete data.
- Schema details and operational metadata could leak.
- Rate limiting, request validation, and audit controls are harder to enforce.
- Browser clients should never receive database credentials.

The safer model is always:

```text
Browser -> Frontend -> Service Layer -> PostgreSQL
```

Future public APIs, if added, should sit between the browser/client and the
database, never beside or below the database boundary.
