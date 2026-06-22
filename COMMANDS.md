# Commands

## Environment

```powershell
py -0p
py -3.14 -m pip install -e .
py -3.14 -m pip show reflex
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

## Streamlit

```powershell
py -3.14 -m streamlit run streamlit_app.py
```

## Git

```powershell
git status --short
git log --oneline -10
git add ...
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

## Project Scripts

```powershell
python scripts/load_servel_sample.py
python scripts/servel_summary.py
python scripts/load_lobby_sample.py
python scripts/lobby_summary.py
python scripts/load_contraloria_sample.py
python scripts/contraloria_summary.py
python scripts/load_municipalidades_sample.py
python scripts/municipalidades_summary.py
python scripts/load_transparencia_sample.py
python scripts/transparencia_summary.py
python scripts/load_dipres_sample.py
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
