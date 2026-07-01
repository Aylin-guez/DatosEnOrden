from __future__ import annotations

from pathlib import Path
import subprocess
import sys
from urllib.parse import quote_plus

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from datosenorden.db.session import SessionLocal
from datosenorden.maintenance.source_plugins import get_source_plugins
from datosenorden.web.app_services import get_data_ecosystem
from datosenorden.web.app_services import get_guided_questions
from datosenorden.web.app_services import get_investigation
from datosenorden.web.app_services import get_investigation_timeline
from datosenorden.web.app_services import get_real_data_readiness
from datosenorden.web.app_services import export_citizen_report_demo
from datosenorden.web.app_services import export_investigation_report
from datosenorden.web.app_services import export_tracking_demo_report
from datosenorden.web.app_services import resolve_investigation_target
from datosenorden.web.app_services import search_workspace
from datosenorden.web.app_services import get_citizen_report_demo
from datosenorden.web.app_services import get_knowledge_demo
from datosenorden.web.app_services import get_knowledge_documents
from datosenorden.web.app_services import get_tracking_demo


MAIN_ENTITY = "SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO"
LOCAL_BASE_URL = "http://localhost:3000"
MIN_SOURCES = 5
MIN_EVIDENCE = 8
MIN_RELATIONSHIPS = 8


def main() -> int:
    checks: list[tuple[str, bool, str]] = []
    checks.append(_check_database())

    resolved = resolve_investigation_target(MAIN_ENTITY)
    entity_id = str(_field(resolved, "entity_id", ""))
    checks.append(("demo entity resolves by name", bool(_field(resolved, "found", False)) and bool(entity_id), entity_id or str(_field(resolved, "warning", ""))))

    by_name = get_investigation(MAIN_ENTITY)
    by_uuid = get_investigation(entity_id) if entity_id else {}
    name_metrics = _field(by_name, "compact_metrics", {})
    uuid_metrics = _field(by_uuid, "compact_metrics", {})
    name_entity = str(_field(_field(by_name, "entity", {}), "name", ""))
    uuid_entity = str(_field(_field(by_uuid, "entity", {}), "name", ""))

    checks.extend(
        [
            ("expediente by name works", _investigation_ok(by_name), _metrics_detail(name_metrics, name_entity)),
            ("expediente by UUID works", _investigation_ok(by_uuid), _metrics_detail(uuid_metrics, uuid_entity)),
            ("name and UUID resolve same entity", name_entity.upper() == uuid_entity.upper() == MAIN_ENTITY, f"name={name_entity} uuid={uuid_entity}"),
            (f"sources >= {MIN_SOURCES}", int(_field(name_metrics, "datasets_involved", 0) or 0) >= MIN_SOURCES, str(_field(name_metrics, "datasets_involved", 0))),
            (f"evidence >= {MIN_EVIDENCE}", int(_field(name_metrics, "evidence_count", 0) or 0) >= MIN_EVIDENCE, str(_field(name_metrics, "evidence_count", 0))),
            (f"relationships >= {MIN_RELATIONSHIPS}", int(_field(name_metrics, "relationship_count", 0) or 0) >= MIN_RELATIONSHIPS, str(_field(name_metrics, "relationship_count", 0))),
        ]
    )
    report_path = export_investigation_report(entity_id) if entity_id else ""
    checks.append(("export report generated", bool(report_path) and Path(report_path).exists(), report_path))
    tracking = get_tracking_demo()
    tracking_events = _field(tracking, "events", []) or []
    tracking_report_path = export_tracking_demo_report()
    checks.extend(
        [
            ("tracking demo available", bool(_field(_field(tracking, "item", {}), "id", "")), str(_field(_field(tracking, "item", {}), "id", ""))),
            ("tracking timeline non-empty", len(tracking_events) > 0, str(len(tracking_events))),
            ("tracking report generated", bool(tracking_report_path) and Path(tracking_report_path).exists(), tracking_report_path),
        ]
    )
    citizen_report = get_citizen_report_demo()
    citizen_sections = _field(citizen_report, "sections", []) or []
    citizen_report_path = export_citizen_report_demo()
    checks.extend(
        [
            ("citizen report available", bool(_field(citizen_report, "id", "")), str(_field(citizen_report, "id", ""))),
            ("citizen report sections non-empty", len(citizen_sections) > 0, str(len(citizen_sections))),
            ("citizen report generated", bool(citizen_report_path) and Path(citizen_report_path).exists(), citizen_report_path),
        ]
    )

    search = search_workspace("Servicio de Salud Arauco")
    matches = _field(search, "matches", []) or []
    checks.append(("search finds Servicio de Salud Arauco", any(str(_field(match, "canonical_entity_id", "")) == entity_id for match in matches), str(len(matches))))
    partial_search = search_workspace("arauco")
    partial_matches = _field(partial_search, "matches", []) or []
    checks.append(
        (
            "partial search arauco finds related results",
            len(partial_matches) > 0
            and any("arauco" in str(_field(match, "entity_name", "")).lower() for match in partial_matches)
            and any(str(_field(match, "action_label", "")) for match in partial_matches),
            str(len(partial_matches)),
        )
    )

    automatic_timeline = get_investigation_timeline(entity_id) if entity_id else {}
    timeline_years = _field(automatic_timeline, "years", []) or []
    checks.append(("automatic investigation timeline non-empty", len(timeline_years) > 0, str(len(timeline_years))))

    knowledge_documents = get_knowledge_documents()
    knowledge_demo = get_knowledge_demo()
    knowledge_questions = _field(knowledge_demo, "citizen_questions", []) or []
    checks.append(("library has documents", len(knowledge_documents) > 0, str(len(knowledge_documents))))
    checks.append(("library has citizen questions", len(knowledge_questions) > 0, str(len(knowledge_questions))))

    guided = get_guided_questions()
    checks.append(("discover has guided questions", len(_field(guided, "questions", []) or []) > 0 and len(_field(guided, "categories", []) or []) > 0, f"questions={len(_field(guided, 'questions', []) or [])} categories={len(_field(guided, 'categories', []) or [])}"))

    ecosystem = get_data_ecosystem()
    sources = _field(ecosystem, "sources", []) or []
    active_or_prototype = [source for source in sources if str(_field(source, "status", "")) in {"active", "prototype"}]
    plugin_sources = get_source_plugins()
    checks.append(("ecosystem has active/prototype sources", len(active_or_prototype) >= MIN_SOURCES, str(len(active_or_prototype))))
    checks.append(("source plugins available", len(plugin_sources) >= 11, str(len(plugin_sources))))
    readiness = get_real_data_readiness()
    readiness_totals = _field(readiness, "totals", {}) or {}
    checks.append(("real data readiness has connected source", int(_field(readiness_totals, "ready", 0) or 0) >= 1, str(_field(readiness_totals, "ready", 0))))

    checks.append(_check_reflex_compile())

    _print_report(checks, entity_id)
    return 1 if any(not ok for _, ok, _ in checks) else 0


def _check_database() -> tuple[str, bool, str]:
    try:
        with SessionLocal() as session:
            session.execute(text("select 1"))
        return ("DB connected", True, "ok")
    except Exception as exc:  # noqa: BLE001
        return ("DB connected", False, f"{type(exc).__name__}: {exc}")


def _check_reflex_compile() -> tuple[str, bool, str]:
    command = [sys.executable, "-m", "reflex", "compile", "--dry", "--no-rich"]
    try:
        result = subprocess.run(command, cwd=ROOT, check=False, capture_output=True, text=True, timeout=180)
    except Exception as exc:  # noqa: BLE001
        return ("Reflex compile", False, f"{type(exc).__name__}: {exc}")
    detail = (result.stdout or result.stderr or "").strip().splitlines()
    return ("Reflex compile", result.returncode == 0, detail[-1] if detail else f"exit={result.returncode}")


def _investigation_ok(data: object) -> bool:
    metrics = _field(data, "compact_metrics", {})
    return (
        bool(_field(data, "found", False))
        and int(_field(metrics, "datasets_involved", 0) or 0) >= MIN_SOURCES
        and int(_field(metrics, "evidence_count", 0) or 0) >= MIN_EVIDENCE
        and int(_field(metrics, "relationship_count", 0) or 0) >= MIN_RELATIONSHIPS
    )


def _metrics_detail(metrics: object, entity_name: str) -> str:
    return (
        f"{entity_name}; fuentes={_field(metrics, 'datasets_involved', 0)} "
        f"evidencia={_field(metrics, 'evidence_count', 0)} "
        f"relaciones={_field(metrics, 'relationship_count', 0)}"
    )


def _field(obj: object, key: str, fallback: object = None) -> object:
    if isinstance(obj, dict):
        return obj.get(key, fallback)
    return getattr(obj, key, fallback)


def _print_report(checks: list[tuple[str, bool, str]], entity_id: str) -> None:
    print("run_demo_check:")
    for label, ok, detail in checks:
        print(f"  {'ok' if ok else 'FAIL'} - {label}: {detail}")
    print("demo URLs:")
    print(f"  Inicio: {LOCAL_BASE_URL}/")
    print(f"  Ecosistema: {LOCAL_BASE_URL}/ecosystem")
    print(f"  Descubre: {LOCAL_BASE_URL}/discover")
    print(f"  Seguimiento: {LOCAL_BASE_URL}/tracking")
    print(f"  Reportes: {LOCAL_BASE_URL}/reports")
    print(f"  Buscar interno: {LOCAL_BASE_URL}/search?q={quote_plus('Servicio de Salud Arauco')}")
    print(f"  Expediente por nombre: {LOCAL_BASE_URL}/investigation?id={quote_plus(MAIN_ENTITY)}")
    if entity_id:
        print(f"  Expediente por UUID: {LOCAL_BASE_URL}/investigation?id={entity_id}")


if __name__ == "__main__":
    raise SystemExit(main())
