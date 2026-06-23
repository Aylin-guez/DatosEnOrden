# Commands

## Environment

```powershell
py -0p
py -3.14 -m pip install -e .
py -3.14 -m pip show reflex
```

- Prefer Python 3.14 when available. Use `py -3.14` first, and fall back to the direct Python 3.14 executable if the launcher is unavailable.

## Root Run

```powershell
powershell -ExecutionPolicy Bypass -File scripts/web/run_reflex_dev.ps1
```

## Tests

```powershell
py -3.14 -m pytest -q --basetemp .pytest-tmp
```

## Reflex

```powershell
py -3.14 -m reflex compile --dry --no-rich
py -3.14 -m reflex run
py -3.14 -m reflex run --frontend-port 3001 --backend-port 8001
```

## Investigation

```powershell
python scripts/source_trace.py "DIVISION LOGISTICA DEL EJERCITO"
python scripts/investigation_story.py "DIVISION LOGISTICA DEL EJERCITO"
python scripts/entity_comparison.py "DIVISION LOGISTICA DEL EJERCITO"
python scripts/export_investigation_markdown.py "DIVISION LOGISTICA DEL EJERCITO" --output reports/investigation_entity.md
python scripts/export_investigation_report.py "DIVISION LOGISTICA DEL EJERCITO"
```

## Streamlit

```powershell
py -3.14 -m streamlit run streamlit_app.py
```

## Git

```powershell
git status --short
git log --oneline -10
git diff --stat
git add <files>
git commit -m "..."
git push
```

## Backup

```powershell
powershell -ExecutionPolicy Bypass -File I:\DatosEnOrden\scripts\backup_after_push.ps1
```

## Recovery / Safety

```powershell
git fsck --full
git rev-parse HEAD
```

## Safe Git Flow

```powershell
git status --short
git diff --stat
git add <only-the-files-you-changed>
git commit -m "..."
git push
```

- Prefer Python 3.14 when available: use `py -3.14` first, and fall back to the direct Python 3.14 executable if the launcher is unavailable.
- Do not use `git reset --hard` or `git checkout --` for routine work.

## Project Scripts

```powershell
python scripts/load_servel_sample.py
python scripts/servel_summary.py
python scripts/source_trace.py "DIVISION LOGISTICA DEL EJERCITO"
python scripts/export_investigation_markdown.py "DIVISION LOGISTICA DEL EJERCITO" --output reports/investigation_entity.md
python scripts/export_investigation_report.py "DIVISION LOGISTICA DEL EJERCITO"
python scripts/load_lobby_sample.py
python scripts/lobby_summary.py
python scripts/load_contraloria_sample.py
python scripts/contraloria_summary.py
python scripts/load_municipalidades_sample.py
python scripts/municipalidades_summary.py
python scripts/load_transparencia_sample.py
python scripts/transparencia_summary.py
python scripts/load_dipres_sample.py
python scripts/load_registro_empresas_sample.py
python scripts/registro_empresas_summary.py
python scripts/load_diario_oficial_sample.py
python scripts/diario_oficial_summary.py
python scripts/discovery_cases.py
python scripts/load_complete_demo_case.py
python scripts/demo_case_summary.py
python scripts/dataset_summary.py
python scripts/dataset_details.py
python scripts/list_datasets.py
python scripts/list_entities.py
python scripts/search_buyer.py
python scripts/search_supplier.py
python scripts/entity_comparison.py
python scripts/investigation_story.py
python scripts/entity_timeline.py
python scripts/web/check_reflex_environment.py
powershell -ExecutionPolicy Bypass -File scripts/web/run_reflex_dev.ps1
python -m reflex compile --dry --no-rich
python -m reflex run
```

## Smoke Test

```powershell
py -3.14 -m py_compile reflex_app/reflex_app.py src/datosenorden/web/app_services.py src/datosenorden/maintenance/registro_empresas_prototype.py src/datosenorden/maintenance/guided_questions.py src/datosenorden/maintenance/institution_profile.py src/datosenorden/maintenance/citizen_dashboard.py
py -3.14 -m pytest -q --basetemp .pytest-tmp
py -3.14 -m reflex compile --dry --no-rich
```

## Never Commit These

- `.pytest-tmp/`
- `.pytest_cache/`
- `__pycache__/`
- `*.pyc`
- `.web/`
- `.states/`
- `node_modules/`
- `.env`
- `private/`
