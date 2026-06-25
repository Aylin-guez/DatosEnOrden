from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from datosenorden.db.session import SessionLocal
from datosenorden.maintenance.complete_demo_case import load_complete_demo_case_payload
from datosenorden.web.app_services import get_entity_comparison
from datosenorden.web.app_services import get_investigation
from datosenorden.web.app_services import get_investigation_story
from datosenorden.web.app_services import get_investigation_timeline
from datosenorden.web.app_services import get_source_trace
from datosenorden.web.app_services import resolve_investigation_target
from datosenorden.web.app_services import search_workspace


MAIN_ENTITY = "SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO"


def main() -> int:
    checks: list[tuple[str, bool, str]] = []

    checks.append(_check_database())
    payload = load_complete_demo_case_payload()
    checks.append(("demo payload", payload["main_entity"]["name"] == MAIN_ENTITY, payload["main_entity"]["name"]))

    resolved = resolve_investigation_target(MAIN_ENTITY)
    entity_id = str(resolved.get("entity_id", ""))
    checks.append(("main entity found", bool(resolved.get("found")) and bool(entity_id), entity_id or str(resolved.get("warning", ""))))

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
