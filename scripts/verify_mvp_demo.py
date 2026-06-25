from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from datosenorden.db.session import SessionLocal
from datosenorden.maintenance.complete_demo_case import load_complete_demo_case_payload
from datosenorden.web.app_services import get_entity_comparison
from datosenorden.web.app_services import get_guided_discovery_options
from datosenorden.web.app_services import get_investigation
from datosenorden.web.app_services import get_investigation_story
from datosenorden.web.app_services import get_investigation_timeline
from datosenorden.web.app_services import get_record_context
from datosenorden.web.app_services import get_source_trace
from datosenorden.web.app_services import resolve_investigation_target
from datosenorden.web.app_services import resolve_canonical_expediente_target
from datosenorden.web.app_services import search_workspace
from datosenorden.maintenance.source_plugins import SourceStatus
from datosenorden.maintenance.source_plugins import get_source_plugin
from datosenorden.maintenance.source_plugins import get_source_plugins
from validate_source_plugin import validate_all


MAIN_ENTITY = "SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO"


def main() -> int:
    checks: list[tuple[str, bool, str]] = []

    checks.append(_check_database())
    plugins = get_source_plugins()
    checks.append(("source plugin registry loads", len(plugins) > 0, str(len(plugins))))
    checks.append(("source plugin count", len(plugins) == 11, str(len(plugins))))
    declaraciones_plugin = get_source_plugin("declaraciones_intereses")
    checks.append(
        (
            "declaraciones_intereses is prototype",
            declaraciones_plugin is not None and declaraciones_plugin.status == SourceStatus.PROTOTYPE,
            str(declaraciones_plugin.status.value if declaraciones_plugin is not None else "missing"),
        )
    )
    readiness = validate_all()
    readiness_failures = [
        result.source_id
        for result in readiness
        if result.status in {"active", "prototype"} and result.critical_failures
    ]
    checks.append(("source readiness critical failures", not readiness_failures, ", ".join(readiness_failures) or "none"))
    payload = load_complete_demo_case_payload()
    checks.append(("demo payload", payload["main_entity"]["name"] == MAIN_ENTITY, payload["main_entity"]["name"]))

    resolved = resolve_investigation_target(MAIN_ENTITY)
    entity_id = str(resolved.get("entity_id", ""))
    checks.append(("main entity found", bool(resolved.get("found")) and bool(entity_id), entity_id or str(resolved.get("warning", ""))))
    uuid_resolved = resolve_canonical_expediente_target(entity_id)
    name_resolved = resolve_canonical_expediente_target(MAIN_ENTITY)
    checks.append(("main organization resolves by UUID", str(uuid_resolved.get("canonical_entity_id", "")) == entity_id, str(uuid_resolved)))
    checks.append(("main organization resolves by name", str(name_resolved.get("canonical_entity_id", "")) == entity_id, str(name_resolved)))

    investigation = get_investigation(entity_id or MAIN_ENTITY)
    metrics = _field(investigation, "compact_metrics", {})
    checks.extend(
        [
            ("investigation service", bool(_field(investigation, "found", False)), str(_field(investigation, "resolution", {}))),
            ("datasets for entity", int(_field(metrics, "datasets_involved", 0) or 0) >= 3, str(_field(metrics, "datasets_involved", 0))),
            ("evidence count", int(_field(metrics, "evidence_count", 0) or 0) > 0, str(_field(metrics, "evidence_count", 0))),
            ("relationship count", int(_field(metrics, "relationship_count", 0) or 0) > 0, str(_field(metrics, "relationship_count", 0))),
        ]
    )

    comparison = get_entity_comparison(entity_id)
    checks.append(("claims count", "claims" in str(_field(comparison, "coverage_summary", "")).lower(), str(_field(comparison, "coverage_summary", ""))))

    trace = get_source_trace(entity_id)
    checks.append(("source trace returns sources", len(_field(trace, "sources", []) or []) >= 3, str(len(_field(trace, "sources", []) or []))))

    timeline = get_investigation_timeline(entity_id)
    event_count = sum(len(_field(year_group, "items", []) or []) for year in _field(timeline, "years", []) for year_group in _field(year, "categories", []))
    checks.append(("timeline returns events", event_count >= 5, str(event_count)))

    story = get_investigation_story(entity_id)
    checks.append(("story returns summary", bool(str(_field(story, "summary", "")).strip()), str(_field(story, "summary", ""))[:120]))

    search = search_workspace("Servicio de Salud Arauco")
    search_found = any(str(_field(match, "entity_id", "")) == entity_id for match in _field(search, "matches", []))
    checks.append(("search can find main entity", search_found, entity_id))
    canonical_search = all(str(_field(match, "canonical_entity_id", "")).strip() for match in _field(search, "matches", []))
    checks.append(("search result buttons have canonical ids", canonical_search, str(len(_field(search, "matches", [])))))

    for category in ("public_organizations", "suppliers", "authorities", "budgets", "procurement", "meetings", "which_official_publications_exist"):
        options = get_guided_discovery_options(category)
        checks.append((f"guided category has options: {category}", len(options) > 0, str(len(options))))

    budget_options = get_guided_discovery_options("budgets")
    budget_context = get_record_context(str(_field(budget_options[0], "entity_id", ""))) if budget_options else {}
    checks.append(
        (
            "budget record resolves to main organization",
            str(_field(budget_context, "canonical_entity_id", "")) == entity_id and bool(_field(budget_context, "is_record", False)),
            str(budget_context),
        )
    )

    checks.append(_check_reflex_import())

    failed = [row for row in checks if not row[1]]
    _print_report(checks)
    return 1 if failed else 0


def _check_database() -> tuple[str, bool, str]:
    try:
        with SessionLocal() as session:
            session.execute(text("select 1"))
        return ("database reachable", True, "ok")
    except Exception as exc:  # noqa: BLE001
        return ("database reachable", False, f"{type(exc).__name__}: {exc}")


def _check_reflex_import() -> tuple[str, bool, str]:
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        __import__("reflex_app.reflex_app")
        return ("Reflex import smoke test", True, "ok")
    except Exception as exc:  # noqa: BLE001
        return ("Reflex import smoke test", False, f"{type(exc).__name__}: {exc}")


def _field(obj: object, key: str, fallback: object = None) -> object:
    if isinstance(obj, dict):
        return obj.get(key, fallback)
    return getattr(obj, key, fallback)


def _print_report(checks: list[tuple[str, bool, str]]) -> None:
    print("mvp_demo_verification:")
    for label, ok, detail in checks:
        status = "ok" if ok else "FAIL"
        print(f"  {status} - {label}: {detail}")


if __name__ == "__main__":
    raise SystemExit(main())
