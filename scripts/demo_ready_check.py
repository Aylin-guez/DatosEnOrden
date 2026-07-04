from __future__ import annotations

from pathlib import Path
import sys
from urllib.parse import quote_plus

from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from datosenorden.db.session import SessionLocal
from datosenorden.maintenance.source_plugins import get_source_plugins
from datosenorden.web.app_services import export_citizen_report_demo
from datosenorden.web.app_services import export_tracking_demo_report
from datosenorden.web.app_services import get_citizen_report_demo
from datosenorden.web.app_services import get_investigation
from datosenorden.web.app_services import get_tracking_demo
from datosenorden.web.app_services import resolve_investigation_target


MAIN_ENTITY = "SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO"
LOCAL_BASE_URL = "http://localhost:3000"


def main() -> int:
    checks: list[tuple[str, bool, str]] = []
    checks.append(_database_check())
    resolved = resolve_investigation_target(MAIN_ENTITY)
    entity_id = str(resolved.get("entity_id", ""))
    checks.append(("canonical name resolves", bool(resolved.get("found")) and bool(entity_id), entity_id or str(resolved.get("warning", ""))))

    investigation = get_investigation(MAIN_ENTITY)
    metrics = _field(investigation, "compact_metrics", {})
    checks.extend(
        [
            ("investigation found", bool(_field(investigation, "found", False)), str(_field(investigation, "resolution", {}))),
            ("sources non-zero", int(_field(metrics, "datasets_involved", 0) or 0) > 0, str(_field(metrics, "datasets_involved", 0))),
            ("evidence non-zero", int(_field(metrics, "evidence_count", 0) or 0) > 0, str(_field(metrics, "evidence_count", 0))),
            ("relationships non-zero", int(_field(metrics, "relationship_count", 0) or 0) > 0, str(_field(metrics, "relationship_count", 0))),
            ("source plugins available", len(get_source_plugins()) >= 11, str(len(get_source_plugins()))),
        ]
    )
    tracking = get_tracking_demo()
    tracking_report = export_tracking_demo_report()
    checks.extend(
        [
            ("tracking demo available", bool(_field(_field(tracking, "item", {}), "id", "")), str(_field(_field(tracking, "item", {}), "id", ""))),
            ("tracking timeline non-empty", len(_field(tracking, "events", []) or []) > 0, str(len(_field(tracking, "events", []) or []))),
            ("tracking report export", Path(tracking_report).exists(), tracking_report),
        ]
    )
    citizen_report = get_citizen_report_demo()
    citizen_report_export = export_citizen_report_demo()
    checks.extend(
        [
            ("citizen report available", bool(_field(citizen_report, "id", "")), str(_field(citizen_report, "id", ""))),
            ("citizen report sections non-empty", len(_field(citizen_report, "sections", []) or []) > 0, str(len(_field(citizen_report, "sections", []) or []))),
            ("citizen report export", Path(citizen_report_export).exists(), citizen_report_export),
        ]
    )

    _print_report(checks, entity_id)
    return 1 if any(not ok for _, ok, _ in checks) else 0


def _database_check() -> tuple[str, bool, str]:
    try:
        with SessionLocal() as session:
            session.execute(text("select 1"))
        return ("database reachable", True, "ok")
    except Exception as exc:  # noqa: BLE001
        return ("database reachable", False, f"{type(exc).__name__}: {exc}")


def _field(obj: object, key: str, fallback: object = None) -> object:
    if isinstance(obj, dict):
        return obj.get(key, fallback)
    return getattr(obj, key, fallback)


def _print_report(checks: list[tuple[str, bool, str]], entity_id: str) -> None:
    print("demo_ready_check:")
    for label, ok, detail in checks:
        print(f"  {'ok' if ok else 'FAIL'} - {label}: {detail}")
    print("demo_urls:")
    print(f"  Inicio: {LOCAL_BASE_URL}/")
    print(f"  Ecosistema: {LOCAL_BASE_URL}/ecosystem")
    print(f"  Descubre: {LOCAL_BASE_URL}/discover")
    print(f"  Seguimiento: {LOCAL_BASE_URL}/tracking")
    print(f"  Reportes: {LOCAL_BASE_URL}/reports")
    print(f"  Buscar interno: {LOCAL_BASE_URL}/search?q={quote_plus('Servicio de Salud Arauco')}")
    print(f"  Expediente por nombre: {LOCAL_BASE_URL}/investigation?id={quote_plus(MAIN_ENTITY)}")
    if entity_id:
        print(f"  Expediente por UUID: {LOCAL_BASE_URL}/investigation?id={entity_id}")
    print("reflex_compile:")
    print("  python -m reflex compile --dry --no-rich")


if __name__ == "__main__":
    raise SystemExit(main())
