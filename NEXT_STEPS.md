# Next Steps

## Done

- Complete local demo case exists for `SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO`.
- Home, Ecosistema, Descubre, Seguimiento, Reportes, Demo, Dashboard, Search utility, and Expediente routes exist in Reflex.
- Local prototype datasets cover ChileCompra, DIPRES, Registro Empresas, Diario Oficial, Transparencia Activa, Lobby, and Contraloria.
- Expediente services build summary, source trace, timeline, source contributions, graph, evidence, and report exports.
- MVP verification script exists: `python scripts/verify_mvp_demo.py`.
- Non-destructive load helper exists: `python scripts/reset_and_load_mvp_demo.py`.
- Canonical navigation service exists: `src/datosenorden/maintenance/product_navigation.py`.
- Search and guided discovery expose canonical expediente targets.
- Source plugin registry exists: `src/datosenorden/maintenance/source_plugins.py`.
- Tracking prototype exists: `src/datosenorden/maintenance/tracking.py`, `/tracking`, and tracking demo/export scripts.
- Citizen reports prototype exists: `src/datosenorden/maintenance/citizen_reports.py`, `/reports`, and HTML export.
- Future API contract is documented in `docs/API_FUTURE.md`.
- Reusable local-engine audit is documented in `docs/REUSABLE_ENGINES_AUDIT.md`.
- Source readiness report exists: `python scripts/source_readiness_report.py`.
- Source factory scripts exist for scaffolding, validating, loading, and summarizing prototype sources.
- `Declaraciones de Intereses` is scaffolded as a local prototype.

## Missing

- Real source connectors are not part of the MVP demo.
- The UI is functional but not polished.
- Specific record pages are not built yet; `Ver registro` is a placeholder.
- Tracking subscriptions are placeholders only; no emails or alert delivery exist yet.
- Reports are local HTML only; PDF export is intentionally not integrated yet.
- Public API endpoints are documented but not implemented or exposed.
- Demo data is local test data and must not be represented as official live data.
- Some older scripts and Streamlit paths may still use earlier examples.

## Safest Order

1. Fix expediente.
2. Verify demo.
3. Inspect UX with real loaded demo data.
4. Only then polish UI.
5. Later connect real sources.

## Recommended Next Phases Without Codex

1. Run `python scripts/reset_and_load_mvp_demo.py`.
2. Run `python scripts/verify_mvp_demo.py`.
3. Run `python -m reflex compile --dry --no-rich`.
4. Start Reflex with `python -m reflex run`.
5. Open `/demo` as the recommended presentation route.
6. Open `/investigation?id=SERVICIO%20DE%20SALUD%20ARAUCO%20HOSPITAL%20DE%20ARAUCO` directly.
7. Open `/tracking` to show how a proposal/document history connects to the expediente.
8. Open `/reports` to show the citizen report connected to the same case.
9. Record screenshots or notes for any empty section that should contain data.

## Opening Demo Without UUID

Use Demo, Descubre, Seguimiento, Reportes, or the header search action and click `Abrir expediente`.

Direct URL:

```text
/investigation?id=SERVICIO%20DE%20SALUD%20ARAUCO%20HOSPITAL%20DE%20ARAUCO
```

UUIDs are only diagnostic output from scripts.

## Expediente vs Registro

- Expediente: canonical profile for an organization, company, or person.
- Registro: specific budget, contract, meeting, role, publication, report, or evidence item.
- `Abrir expediente` routes to the canonical entity.
- `Ver registro` is a future page and currently appears only as a placeholder.

## Recommended Next Phases With Codex

1. Add browser-level smoke tests for the Reflex routes, including `/tracking` and `/reports`.
2. Add richer trace grouping by dataset and source record.
3. Add import/export fixtures for a repeatable demo database snapshot.
4. Build specific record pages for `Ver registro`.
5. Design persisted tracking records only after the read-only prototype is stable.
6. Add real subscription storage/alerts later, without email sending until explicitly scoped.
7. Use source plugins as the first step before adding any new source loader.
8. Implement API endpoints only after `app_services.py` contracts are stable.

## Adding Sources

1. Run `python scripts/create_source_plugin.py <source_id> --display-name "<Display Name>" --status prototype --dry-run`.
2. Run it again without `--dry-run` when the file list is correct.
3. Add or refine plugin metadata in `source_plugins.py`.
4. Add neutral sample records marked `LOCAL_TEST_DATA` and `NOT_OFFICIAL_DATA`.
5. Implement or refine local loader/summary behavior.
6. Run `python scripts/validate_source_plugin.py <source_id>`.
7. Run `python scripts/source_readiness_report.py`.
8. Add source-specific tests.
9. Then expose the source in discovery or expediente flows.

## Recommended Next Sources

1. Sanciones y Procedimientos
2. CMF
3. Poder Judicial
4. Mercado Publico avanzado

## Final MVP Status

Ready:

- Local Arauco demo loads and verifies.
- Expediente can be opened by canonical name without requiring UUID knowledge.
- Source plugin registry and source factory are in place.
- Guided discovery and search route to canonical expediente targets.
- Seguimiento and Reportes connect to the canonical Arauco expediente.
- `python scripts/run_demo_check.py` verifies the presentation path and Reflex compile.

Missing for a real pilot:

- Real source refresh process.
- Official-source validation and governance.
- Browser-level route tests.
- Specific record pages for `Ver registro`.
- Deployment and operational monitoring.

## Next 5 Technical Tasks

1. Add Playwright or equivalent browser smoke tests for Inicio, Ecosistema, Descubre, Seguimiento, Reportes and Expediente.
2. Create a deterministic demo database snapshot or fixture restore command.
3. Implement read-only record pages for purchases, budgets, meetings and publications.
4. Add source-by-source ingestion contracts before connecting real public sources.
5. Prepare deployment configuration, backups, logs and monitoring for a private pilot.

## Demo Rule

Keep the demo neutral and local. Do not add risk scores, accusation language, scraping, external APIs, or schema changes until the MVP is stable.
