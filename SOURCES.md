# Public Source Plugins

DatosEnOrden uses source plugins as local metadata declarations for public data sources. A plugin does not fetch data and does not mutate the database. It describes what a source contributes so Ecosistema, Descubre, Buscar, Expediente, Dashboard, CLI docs, and readiness reports can speak the same language.

## Contract

Plugins live in:

```text
src/datosenorden/maintenance/source_plugins.py
```

Each `PublicSourcePlugin` declares:

- `id`
- `display_name`
- `status`: `active`, `prototype`, or `planned`
- `description`
- `category`
- `coverage`
- `concepts`
- `relationships`
- `compatible_source_ids`
- `commands`
- `evidence_types`
- `timeline_contribution`
- `search_hints`
- `discovery_hints`
- `technical_metadata`

## Status Meanings

- `active`: local loader and working local data path are available for the MVP.
- `prototype`: local prototype metadata, loader, or sample path exists, but it is not a production connector.
- `planned`: source is documented but has no loader or sample data requirement yet.

## Current Sources

- `chilecompra`: ChileCompra
- `dipres`: DIPRES
- `lobby`: Lobby
- `transparencia_activa`: Transparencia Activa
- `contraloria`: Contraloria
- `municipalidades`: Municipalidades
- `servel`: SERVEL
- `diario_oficial`: Diario Oficial
- `registro_empresas`: Registro Empresas

## Planned Sources

- `declaraciones_intereses`: Declaraciones de intereses
- `sanciones_procedimientos`: Sanciones y procedimientos

## How To Add A Source

1. Add one `PublicSourcePlugin` entry in `source_plugins.py`.
2. Pick a stable lowercase `id` using underscores.
3. Add concepts and relationships in neutral descriptive language.
4. Add compatible source ids for cross-source navigation.
5. Add local commands only if scripts already exist.
6. Add `search_hints` and `discovery_hints`.
7. Add tests for the source metadata.
8. Run:

```powershell
python scripts/source_readiness_report.py
python -m pytest -q --basetemp .pytest-tmp
python -m reflex compile --dry --no-rich
```

## Optional Loader And Summary Scripts

Prototype or active sources should usually have:

- `scripts/load_<source>_sample.py`
- `scripts/<source>_summary.py`
- `tests/test_<source>_prototype.py` or equivalent

Planned sources do not need scripts yet.

## How Sources Connect To Expediente

Expediente uses source contribution metadata to explain:

- what each source contributes
- which concepts it connects
- which evidence types it can provide
- how it contributes to the timeline
- whether the source is active, prototype, or planned

The data remains local and descriptive. Source plugins do not imply completeness, risk, or wrongdoing.

## Readiness Report

Run:

```powershell
python scripts/source_readiness_report.py
```

The report lists source status, concepts, commands, script availability, sample/demo data availability, tests, and missing items.
