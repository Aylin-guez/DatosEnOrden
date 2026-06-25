# Next Steps

## Done

- Complete local demo case exists for `SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO`.
- Home, Ecosistema, Descubre, Buscar, Dashboard, and Expediente routes exist in Reflex.
- Local prototype datasets cover ChileCompra, DIPRES, Registro Empresas, Diario Oficial, Transparencia Activa, Lobby, and Contraloria.
- Expediente services build summary, source trace, timeline, source contributions, graph, evidence, and report exports.
- MVP verification script exists: `python scripts/verify_mvp_demo.py`.
- Non-destructive load helper exists: `python scripts/reset_and_load_mvp_demo.py`.

## Missing

- Real source connectors are not part of the MVP demo.
- The UI is functional but not polished.
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
5. Open `/search?q=Servicio%20de%20Salud%20Arauco` and then open Expediente.
6. Open `/investigation?id=SERVICIO%20DE%20SALUD%20ARAUCO%20HOSPITAL%20DE%20ARAUCO` directly.
7. Record screenshots or notes for any empty section that should contain data.

## Recommended Next Phases With Codex

1. Add browser-level smoke tests for the Reflex routes.
2. Tighten presentation copy and Spanish accents after behavior is stable.
3. Consolidate duplicate UI components between Descubre and Buscar.
4. Add richer trace grouping by dataset and source record.
5. Add import/export fixtures for a repeatable demo database snapshot.

## Demo Rule

Keep the demo neutral and local. Do not add risk scores, accusation language, scraping, external APIs, or schema changes until the MVP is stable.
