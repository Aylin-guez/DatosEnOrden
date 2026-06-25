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
- Web service facade: `src/datosenorden/web/app_services.py`
- Reflex UI: `reflex_app/reflex_app.py`

## Current Routes

- `/` - Inicio. Home page with demo status, dataset cards, and highlighted examples.
- `/ecosystem` - Ecosistema. Source map and metadata.
- `/discover` - Descubre. Guided questions and categories.
- `/search` - Buscar. Direct search and results.
- `/investigation` - Expediente. Entity investigation page; uses query parameter `id`.
- `/dashboard` - Dashboard citizen summary.

## Current Datasets And Prototypes

The complete MVP demo uses these local prototype datasets:

- ChileCompra
- DIPRES
- Registro Empresas
- Diario Oficial
- Transparencia Activa
- Lobby
- Contraloria

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
