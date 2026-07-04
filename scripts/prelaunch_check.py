from __future__ import annotations

from pathlib import Path
import importlib
import subprocess
import sys

from sqlalchemy import text


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from datosenorden.db.session import SessionLocal
from datosenorden.maintenance.source_plugins import get_source_plugins
from datosenorden.web.app_services import export_citizen_report_demo
from datosenorden.web.app_services import export_investigation_report
from datosenorden.web.app_services import export_tracking_demo_report
from datosenorden.web.app_services import get_citizen_report_demo
from datosenorden.web.app_services import get_investigation
from datosenorden.web.app_services import get_knowledge_demo
from datosenorden.web.app_services import get_knowledge_documents
from datosenorden.web.app_services import get_tracking_demo
from datosenorden.web.app_services import resolve_investigation_target
from datosenorden.maintenance.knowledge_engine import export_knowledge_demo_report


MAIN_ENTITY = "SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO"
MIN_PYTHON = (3, 12)
DEPENDENCIES = ("reflex", "sqlalchemy", "fastapi", "psycopg", "uvicorn")


def main() -> int:
    checks: list[tuple[str, bool, str]] = []
    checks.append(_python_version_check())
    checks.extend(_dependency_checks())
    checks.append(_database_check())
    checks.append(_demo_loaded_check())
    checks.append(_source_plugins_check())
    checks.append(_knowledge_check())
    checks.append(_tracking_check())
    checks.append(_citizen_report_check())
    checks.append(_investigation_by_name_check())
    checks.append(_export_html_check())
    checks.append(_script_check("run_demo_check", ROOT / "scripts" / "run_demo_check.py"))
    checks.append(_script_check("demo_ready_check", ROOT / "scripts" / "demo_ready_check.py"))

    _print_report(checks)
    return 1 if any(not ok for _, ok, _ in checks) else 0


def _python_version_check() -> tuple[str, bool, str]:
    current = sys.version_info[:3]
    ok = current >= MIN_PYTHON
    return ("python version", ok, ".".join(str(part) for part in current))


def _dependency_checks() -> list[tuple[str, bool, str]]:
    checks: list[tuple[str, bool, str]] = []
    for name in DEPENDENCIES:
        try:
            module = importlib.import_module(name)
            checks.append((f"dependency import: {name}", True, getattr(module, "__version__", "importable")))
        except Exception as exc:  # noqa: BLE001
            checks.append((f"dependency import: {name}", False, f"{type(exc).__name__}: {exc}"))
    return checks


def _database_check() -> tuple[str, bool, str]:
    try:
        with SessionLocal() as session:
            session.execute(text("select 1"))
        return ("DB reachable", True, "ok")
    except Exception as exc:  # noqa: BLE001
        return ("DB reachable", False, f"{type(exc).__name__}: {exc}")


def _demo_loaded_check() -> tuple[str, bool, str]:
    resolved = resolve_investigation_target(MAIN_ENTITY)
    entity_id = str(_field(resolved, "entity_id", ""))
    return ("demo loaded", bool(_field(resolved, "found", False)) and bool(entity_id), entity_id or str(_field(resolved, "warning", "")))


def _source_plugins_check() -> tuple[str, bool, str]:
    plugins = get_source_plugins()
    active = [plugin for plugin in plugins if plugin.status in {"active", "prototype"}]
    return ("source plugins load", len(plugins) >= 11 and len(active) >= 5, f"total={len(plugins)} active_or_prototype={len(active)}")


def _knowledge_check() -> tuple[str, bool, str]:
    demo = get_knowledge_demo()
    documents = get_knowledge_documents()
    ok = bool(_field(_field(demo, "document", {}), "id", "")) and len(documents) > 0
    return ("knowledge demo exists", ok, str(_field(_field(demo, "document", {}), "id", "")))


def _tracking_check() -> tuple[str, bool, str]:
    demo = get_tracking_demo()
    events = _field(demo, "events", []) or []
    ok = bool(_field(_field(demo, "item", {}), "id", "")) and len(events) > 0
    return ("tracking demo exists", ok, f"events={len(events)}")


def _citizen_report_check() -> tuple[str, bool, str]:
    report = get_citizen_report_demo()
    sections = _field(report, "sections", []) or []
    ok = bool(_field(report, "id", "")) and len(sections) > 0
    return ("citizen reports exist", ok, f"id={_field(report, 'id', '')} sections={len(sections)}")


def _investigation_by_name_check() -> tuple[str, bool, str]:
    investigation = get_investigation(MAIN_ENTITY)
    metrics = _field(investigation, "compact_metrics", {})
    ok = bool(_field(investigation, "found", False)) and int(_field(metrics, "evidence_count", 0) or 0) > 0
    return (
        "/investigation by name returns data",
        ok,
        f"found={_field(investigation, 'found', False)} evidence={_field(metrics, 'evidence_count', 0)}",
    )


def _export_html_check() -> tuple[str, bool, str]:
    try:
        resolved = resolve_investigation_target(MAIN_ENTITY)
        entity_id = str(_field(resolved, "entity_id", ""))
        paths = [
            export_tracking_demo_report(),
            export_citizen_report_demo(),
            export_knowledge_demo_report(),
        ]
        if entity_id:
            paths.append(export_investigation_report(entity_id))
        ok = all(Path(path).exists() for path in paths)
        return ("export HTML works", ok, " | ".join(paths))
    except Exception as exc:  # noqa: BLE001
        return ("export HTML works", False, f"{type(exc).__name__}: {exc}")


def _script_check(label: str, script: Path) -> tuple[str, bool, str]:
    result = subprocess.run([sys.executable, str(script)], cwd=ROOT, check=False, capture_output=True, text=True, timeout=240)
    output = (result.stdout or result.stderr or "").strip().splitlines()
    detail = output[-1] if output else f"exit={result.returncode}"
    return (f"{label} OK", result.returncode == 0, detail)


def _field(obj: object, key: str, fallback: object = None) -> object:
    if isinstance(obj, dict):
        return obj.get(key, fallback)
    return getattr(obj, key, fallback)


def _print_report(checks: list[tuple[str, bool, str]]) -> None:
    print("prelaunch_check:")
    for label, ok, detail in checks:
        print(f"  {'ok' if ok else 'FAIL'} - {label}: {detail}")


if __name__ == "__main__":
    raise SystemExit(main())
