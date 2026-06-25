# Debugging

## Reflex Fails To Start

Run:

```powershell
python -m reflex compile --dry --no-rich
```

If that fails, inspect the first Python traceback. Most failures are import errors, missing dependencies, or state fields referenced by the UI but not declared in `AppState`.

Then run:

```powershell
python -m py_compile reflex_app/reflex_app.py src/datosenorden/web/app_services.py
```

## Bun Cache Issues

If Reflex frontend tooling fails around Bun or cached frontend assets, stop Reflex and remove only generated caches after checking paths:

```powershell
git status --short
```

Generated directories that should not be committed:

- `.web/`
- `.states/`
- `.bun-cache/`
- `reflex.lock/`

Do not delete source directories.

## Python 3.14 vs Python 3.10

Check installed Python launchers:

```powershell
py -0p
```

Prefer:

```powershell
py -3.14 -m pytest -q --basetemp .pytest-tmp
py -3.14 -m reflex compile --dry --no-rich
```

If `py` is unavailable, use the direct Python executable or:

```powershell
python -m pytest -q --basetemp .pytest-tmp
python -m reflex compile --dry --no-rich
```

## Demo Data Loaded But Expediente Empty

Run:

```powershell
python scripts/verify_mvp_demo.py
```

If the main entity is missing, load the complete demo:

```powershell
python scripts/load_complete_demo_case.py
python scripts/verify_mvp_demo.py
```

Direct Expediente URLs:

```text
/investigation?id=SERVICIO%20DE%20SALUD%20ARAUCO%20HOSPITAL%20DE%20ARAUCO
/investigation?id=<entity_id_from_verify_script>
```

The backend investigation builders expect an entity UUID. The web service resolver accepts UUID, exact name, case-insensitive name, and normalized name.

## Typed Object Has No `.get`

This means a view/export layer is treating a dataclass or typed object as a dict.

Use the presentation helper:

```python
from datosenorden.maintenance.safe_access import _field, _as_text, _as_list
```

Use it only in view/formatting/export code. Do not use it to hide persistence errors in loaders.

## Git Safe Recovery Notes

Inspect first:

```powershell
git status --short
git diff --stat
git log --oneline -5
```

Do not use `git reset --hard` or `git checkout --` unless you intentionally want to discard local work.

To see changes in one file:

```powershell
git diff -- path/to/file.py
```

To stage only final MVP files:

```powershell
git add PROJECT_STATUS.md NEXT_STEPS.md DEBUGGING.md COMMANDS.md reflex_app/reflex_app.py src/datosenorden/web/app_services.py src/datosenorden/maintenance/safe_access.py src/datosenorden/maintenance/investigation_story.py src/datosenorden/maintenance/source_trace.py src/datosenorden/maintenance/source_contributions.py src/datosenorden/maintenance/institution_profile.py src/datosenorden/maintenance/investigation_export.py src/datosenorden/maintenance/investigation_report.py src/datosenorden/maintenance/investigation_graph.py scripts/verify_mvp_demo.py scripts/reset_and_load_mvp_demo.py tests/test_investigation_resolution.py tests/test_mvp_demo_scripts.py
```

## Backup Command

```powershell
powershell -ExecutionPolicy Bypass -File I:\DatosEnOrden\scripts\backup_after_push.ps1
```
