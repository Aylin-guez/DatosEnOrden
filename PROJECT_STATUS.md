# Project Status

Last checkpoint: 2026-06-25, before final MVP stabilization work.

## Current Architecture

DatosEnOrden is a local-first Python application. Data is loaded into the local database through maintenance/demo loaders, exposed through service functions in `src/datosenorden/web/app_services.py`, and rendered by the Reflex app in `reflex_app/reflex_app.py`.

The project keeps demo data local and descriptive. It does not call external APIs during the MVP demo flow, does not scrape, and does not infer wrongdoing or risk.

Main layers:

- Database/session: `src/datosenorden/db/session.py`
- SQLAlchemy models: `src/datosenorden/models.py`
- Demo loaders/prototypes: `src/datosenorden/maintenance/*_prototype.py` and `src/datosenorden/maintenance/complete_demo_case.py`
- Investigation builders: `src/datosenorden/maintenance/investigation_view.py`, `investigation_story.py`, `source_trace.py`, `source_contributions.py`, `investigation_graph.py`, `investigation_timeline.py`
- Product navigation: `src/datosenorden/maintenance/product_navigation.py`
- Tracking / internal TraceFlow layer: `src/datosenorden/maintenance/tracking.py`
- Citizen reports layer: `src/datosenorden/maintenance/citizen_reports.py`
- Source plugin registry: `src/datosenorden/maintenance/source_plugins.py`
- Web service facade: `src/datosenorden/web/app_services.py`
- Reflex UI: `reflex_app/reflex_app.py`

## Current Routes

- `/` - Inicio. Home page with demo status, dataset cards, and highlighted examples.
- `/ecosystem` - Ecosistema. Source map and metadata.
- `/discover` - Descubre. Guided questions and categories.
- `/investigation` - Expediente. Entity investigation page; uses query parameter `id`.
- `/tracking` - Seguimiento. Local tracking demo for proposals, documents, status changes, evidence, related expedientes, and future subscription placeholders.
- `/reports` - Reportes ciudadanos. Local read-only reports connected to expediente, tracking and evidence.
- `/search` - Internal direct search utility. It is not a primary navigation item.
- `/dashboard` - Dashboard citizen summary.

## Tracking / Seguimiento

DatosEnOrden no solo busca entidades: permite seguir la historia publica de documentos, propuestas y expedientes conectados por evidencia.

The first tracking layer is local and read-only. Internally it acts as the DatosEnOrden TraceFlow engine: it models `TrackableItem`, `TrackingEvent`, `TrackingStatus`, `OfficialDocumentRef`, `EvidenceAnchor`, `FollowTarget`, and `TrackingTimeline` in `src/datosenorden/maintenance/tracking.py`. The visible product name remains `Seguimiento`.

Current demo:

`Programa / propuesta de fortalecimiento hospitalario Arauco`

It connects a proposal with official-document metadata, budget, procurement, provider context, publication/role records, control follow-up, source metadata, and the existing expediente for `SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO`.

Rules:

- All tracking demo content is `LOCAL_TEST_DATA` and `NOT_OFFICIAL_DATA`.
- It stores no heavy PDFs; it keeps metadata, local/official URL references, optional hashes, summaries, source names, and evidence anchors.
- It does not call external APIs, scrape, send emails, or mutate the database.
- Subscription support is represented only as disabled placeholders.

## Citizen Reports

`src/datosenorden/maintenance/citizen_reports.py` adds a local report engine for citizen-readable summaries. It follows the same pattern as tracking: typed dataclasses, no schema migration, JSON-safe service functions in `app_services.py`, and HTML export under `reports/`.

Current demo:

`Reporte ciudadano demo: Servicio de Salud Arauco`

It connects the Arauco expediente, tracking item, source list, sections, and evidence references. It is `LOCAL_TEST_DATA` / `NOT_OFFICIAL_DATA` and does not assert causalidad, irregularidad, culpa or responsabilidad.

Future API planning is documented in `docs/API_FUTURE.md`. Reusable-engine findings are documented in `docs/REUSABLE_ENGINES_AUDIT.md`.

## Current Datasets And Prototypes

The complete MVP demo uses these local prototype datasets:

- ChileCompra
- DIPRES
- Registro Empresas
- Diario Oficial
- Transparencia Activa
- Lobby
- Contraloria

Source plugins now centralize source metadata for Ecosistema, Descubre, Expediente, CLI docs, and readiness checks. See `SOURCES.md`.

Other prototypes also exist in the repository, including SERVEL and municipal data, but they are not required for the complete Arauco MVP case.

## Current Demo Case

Main demo entity:

`SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO`

Expected complete case load summary:

- datasets: 7
- claims: 37
- evidence: 33
- entities: 27
- relationships: 34

Demo case payload:

`data/demo_cases/servicio_salud_arauco_complete.json`

Loader:

```powershell
python scripts/load_complete_demo_case.py
```

## Expediente vs Registro

- Expediente: the canonical profile for a main public entity such as an organization, company, or person.
- Registro: a specific local record such as a budget item, contract, lobby meeting, role, publication, report, or evidence item.

Product rule:

- `Abrir expediente` opens the canonical main entity.
- `Ver registro` is reserved for a future specific-record page. It can appear as a placeholder today.

## Canonical Routing

Canonical routing is handled by `resolve_canonical_expediente_target(value)`.

It accepts UUIDs or names. If the target is already a main entity, it opens itself. If the target is record-like, it follows stored claims/relationships to find a related organization, company, or person, prioritizing public organizations when available.

This means users can click cards by name and do not need to know UUIDs.

Open the demo without UUID:

```text
/investigation?id=SERVICIO%20DE%20SALUD%20ARAUCO%20HOSPITAL%20DE%20ARAUCO
```

The current enriched canonical UUID in this local database is:

```text
338d160c-8d5d-47e1-9c37-038ed5043ba1
```

## Commands To Run Tests

```powershell
python -m py_compile reflex_app/reflex_app.py src/datosenorden/web/app_services.py src/datosenorden/maintenance/complete_demo_case.py scripts/verify_mvp_demo.py scripts/reset_and_load_mvp_demo.py
python -m pytest -q --basetemp .pytest-tmp
```

If `python` is not Python 3.14, use:

```powershell
py -3.14 -m pytest -q --basetemp .pytest-tmp
```

## Commands To Run Reflex

```powershell
python -m reflex compile --dry --no-rich
python -m reflex run
```

Or with the project helper:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/web/run_reflex_dev.ps1
```

## Commands To Load Complete Demo

```powershell
python scripts/load_complete_demo_case.py
python scripts/verify_mvp_demo.py
```

## Source Readiness

```powershell
python scripts/source_readiness_report.py
python scripts/validate_source_plugin.py --all
```

The report checks plugin metadata, commands, sample/demo data, summary scripts, loader scripts, tests, and missing items.

Source factory scripts now exist:

- `scripts/create_source_plugin.py`
- `scripts/validate_source_plugin.py`
- `scripts/load_all_prototype_sources.py`
- `scripts/prototype_sources_summary.py`

`Declaraciones de Intereses` is now a scaffolded local prototype. It remains local `LOCAL_TEST_DATA` / `NOT_OFFICIAL_DATA` and does not add schema or external fetching.

For the final MVP helper:

```powershell
python scripts/reset_and_load_mvp_demo.py
```

## Known Issues Before This Phase

- Expediente could show zero values or stale empty panels even when the complete demo data was loaded.
- Previous failure: `AttributeError: 'InvestigationEvidenceLink' object has no attribute 'get'`.
- Investigation services expect entity UUIDs, but some UI entry points may pass names or unstable display values.
- `/investigation` reads query parameter `id`; bad or missing values were not surfaced clearly to the user.
- Some view formatting code still assumed dictionaries and used `.get(...)` on objects that may be dataclasses.
- `Buscar` and `Descubre` overlap; `Descubre` should guide, while `Buscar` should be direct search.
- Local git status before this phase already included modified and untracked files. Do not assume a clean worktree.
- `git status --short` warned that `.pytest-tmp/` could not be opened due to permission denied.

## Known UX Limitations

- `Ver registro` is a placeholder; full record pages are not implemented yet.
- The top metrics count sources directly attached to the canonical entity. The source map can show all 7 complete demo sources, including related-record sources.
- Repeated non-destructive demo loads can create duplicate names. Canonical routing chooses the entity with the richest navigable data.
- Visual polish is still secondary to local demo correctness and traceability.

## Final MVP Demo Readiness

Ready for local presentation:

- Canonical expediente by name:

```text
http://localhost:3000/investigation?id=SERVICIO+DE+SALUD+ARAUCO+HOSPITAL+DE+ARAUCO
```

- Canonical expediente by UUID, when this local database contains the current demo ID:

```text
http://localhost:3000/investigation?id=338d160c-8d5d-47e1-9c37-038ed5043ba1
```

- Single demo check:

```powershell
python scripts/run_demo_check.py
```

Important behavior:

- `/investigation?id=<name>` and `/investigation?id=<uuid>` rebuild the expediente from the local backend.
- A missing `id` shows the empty state.
- A transient empty backend response does not replace a previously loaded investigation.
- Technical details remain available but do not dominate the main presentation flow.

## Source Status

Active:

- ChileCompra

Prototype:

- DIPRES
- Lobby
- Transparencia Activa
- Contraloria
- Municipalidades
- SERVEL
- Diario Oficial
- Registro Empresas
- Declaraciones de Intereses

Planned:

- Sanciones y Procedimientos

## Missing For A Real Pilot

- Official data ingestion strategy and source-by-source legal/operational review.
- Repeatable production-grade data refresh process.
- Record pages for individual purchases, budgets, meetings, publications, roles and evidence.
- Browser-level end-to-end tests against the Reflex frontend.
- Deployment, backups, access control, and monitoring.
- Human review of Spanish copy, accessibility, and public communication limits.

## Git Checkpoint

Recent history before this phase:

```text
589494c Fix typed evidence link handling
05f0096 Add complete local demo investigation case
c48af30 Add company registry prototype and guided investigation services
9b1a102 Add Diario Oficial prototype and guided discovery
5754f64 Improve product shell and guided empty states
```

Pre-existing local changes were present before this phase. Use `git status --short` and `git diff --stat` before staging.
