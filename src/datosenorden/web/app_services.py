from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
import json
from pathlib import Path
from typing import Any, Iterator
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from datosenorden.db.session import SessionLocal
from datosenorden.maintenance.cross_dataset_explorer import list_cross_dataset_organizations
from datosenorden.maintenance.dataset_registry import list_datasets
from datosenorden.maintenance.dataset_registry import summarize_real_dataset_registry
from datosenorden.maintenance.demo_pack import build_demo_status
from datosenorden.maintenance.discovery_cases import get_discovery_cases as _get_discovery_cases
from datosenorden.maintenance.citizen_dashboard import build_citizen_dashboard
from datosenorden.maintenance.citizen_reports import build_citizen_report_demo
from datosenorden.maintenance.citizen_reports import citizen_report_to_dict
from datosenorden.maintenance.citizen_reports import export_citizen_report_demo as _export_citizen_report_demo
from datosenorden.maintenance.citizen_reports import get_citizen_report as _get_citizen_report
from datosenorden.maintenance.citizen_reports import list_citizen_reports as _list_citizen_reports
from datosenorden.maintenance.ecosystem_registry import build_ecosystem_registry
from datosenorden.maintenance.entity_comparison import build_entity_comparison
from datosenorden.maintenance.entity_resolution import ResolutionResult
from datosenorden.maintenance.entity_resolution import resolve_entity as _resolve_platform_entity
from datosenorden.maintenance.investigation_export import export_investigation_markdown
from datosenorden.maintenance.investigation_knowledge import build_investigation_knowledge
from datosenorden.maintenance.investigation_knowledge import investigation_knowledge_to_dict
from datosenorden.maintenance.investigation_story import build_investigation_story
from datosenorden.maintenance.entity_explorer import search_buyers
from datosenorden.maintenance.entity_explorer import search_suppliers
from datosenorden.maintenance.explanations import relationship_explanation
from datosenorden.maintenance.investigation_graph import build_investigation_graph
from datosenorden.maintenance.investigation_report import export_investigation_report as _export_investigation_report
from datosenorden.maintenance.investigation_view import build_investigation_view
from datosenorden.maintenance.investigation_view import investigation_explanation_text
from datosenorden.maintenance.investigation_timeline import build_investigation_timeline
from datosenorden.maintenance.knowledge_engine import list_knowledge_documents as _list_knowledge_documents
from datosenorden.maintenance.knowledge_engine import official_document_to_dict
from datosenorden.studio.publication_engine import document_view_payload
from datosenorden.studio.publication_engine import publish_document
from datosenorden.studio.actualidad_engine import get_current_topic as _get_current_topic
from datosenorden.studio.actualidad_engine import list_current_topics as _list_current_topics
from datosenorden.maintenance.guided_questions import get_guided_questions as _get_guided_questions
from datosenorden.maintenance.institution_profile import build_institution_profile
from datosenorden.maintenance.platform_config import get_default_platform_config
from datosenorden.maintenance.platform_config import load_platform_config
from datosenorden.maintenance.platform_config import summarize_platform_config
from datosenorden.maintenance.product_navigation import get_guided_discovery_options as _get_guided_discovery_options
from datosenorden.maintenance.product_navigation import get_home_navigation_examples as _get_home_navigation_examples
from datosenorden.maintenance.product_navigation import get_record_context as _get_record_context
from datosenorden.maintenance.product_navigation import resolve_canonical_expediente_target as _resolve_canonical_expediente_target
from datosenorden.maintenance.search_workspace import search_workspace as _search_workspace
from datosenorden.maintenance.source_contributions import build_source_contributions
from datosenorden.maintenance.source_trace import build_source_trace
from datosenorden.maintenance.tracking import build_tracking_demo
from datosenorden.maintenance.tracking import export_tracking_demo_report as _export_tracking_demo_report
from datosenorden.maintenance.tracking import get_tracking_item as _get_tracking_item
from datosenorden.maintenance.tracking import get_tracking_timeline as _get_tracking_timeline
from datosenorden.maintenance.tracking import list_tracking_items as _list_tracking_items
from datosenorden.maintenance.tracking import tracking_to_dict
from datosenorden.models import Entity


LEGISLATIVE_PROJECT_ENTITY_TYPE = "PUBLIC_PROJECT"
LEGISLATIVE_SOURCE_LABEL = "Datos Abiertos Legislativos"
SOURCE_POPULATION_PATH = Path(__file__).resolve().parents[3] / "data" / "source_population" / "infolobby_minimal.json"
CONNECTORS_ROOT = Path(__file__).resolve().parents[3] / "data" / "connectors"
REAL_DOCUMENT_PUBLICATION_PATH = (
    Path(__file__).resolve().parents[3]
    / "data"
    / "official_documents"
    / "published"
    / "senado-docto-9000-mensaje_mocion"
    / "publication.json"
)
LEGISLATIVE_LIMITATION_TEXT = (
    "Este expediente contiene votaciones oficiales asociadas al boletín, "
    "pero aún no incorpora el texto completo del proyecto."
)


def search_entities(query: str, limit: int = 10) -> list[dict[str, Any]]:
    cleaned = query.strip()
    if not cleaned:
        return []
    if limit < 1:
        raise ValueError("limit must be greater than zero")

    with _session_scope() as session:
        merged: dict[str, dict[str, Any]] = {}
        for result in (*search_suppliers(session, cleaned, limit=limit), *search_buyers(session, cleaned, limit=limit)):
            item = _jsonify(result)
            existing = merged.get(item["id"])
            if existing is None:
                item["entity_type_label"] = _entity_type_label(str(item.get("entity_type", "")))
                item["datasets_involved"] = []
                item["explanation"] = _search_result_explanation(item)
                item["technical_details"] = {
                    "entity_id": item["id"],
                    "external_id": item.get("external_id"),
                }
                merged[item["id"]] = item
                continue
            existing["purchase_orders"] = max(existing["purchase_orders"], item["purchase_orders"])
            existing["claims"] = max(existing["claims"], item["claims"])
            existing["relationships"] = max(existing["relationships"], item["relationships"])
            existing["explanation"] = _search_result_explanation(existing)

    return sorted(
        merged.values(),
        key=lambda item: (-int(item["purchase_orders"]), str(item["name"]).lower(), str(item["id"])),
    )[:limit]


def resolve_investigation_target(value: str) -> dict[str, Any]:
    platform_resolution = _resolve_entity_for_investigation(value)
    platform_entity = platform_resolution.entity if platform_resolution.found else None

    canonical = _resolve_canonical_expediente_target(value)
    if not canonical.get("found", False) and platform_entity is not None:
        canonical = _resolve_canonical_expediente_target(platform_entity.canonical_name)
    if not canonical.get("found", False) and platform_entity is not None:
        canonical = _resolve_canonical_expediente_target(platform_entity.id)
    if not canonical.get("found", False):
        if platform_entity is not None:
            return {
                "found": True,
                "entity_id": str(platform_entity.id),
                "entity_name": str(platform_entity.canonical_name),
                "matched_by": _investigation_match_method(platform_resolution, "entity_resolution"),
                "warning": str(canonical.get("warning", "")),
                "canonical": canonical,
                "entity_resolution": platform_resolution.to_dict(),
            }
        return {
            "found": False,
            "entity_id": "",
            "entity_name": str(canonical.get("original_entity_name", value)),
            "matched_by": "",
            "warning": str(canonical.get("warning", "")),
            "canonical": canonical,
            "entity_resolution": platform_resolution.to_dict(),
        }
    entity_id = str(canonical.get("canonical_entity_id", ""))
    entity_name = str(canonical.get("canonical_entity_name", ""))
    return {
        "found": True,
        "entity_id": entity_id,
        "entity_name": entity_name,
        "matched_by": _investigation_match_method(platform_resolution, str(canonical.get("matched_by", ""))),
        "warning": str(canonical.get("warning", "")),
        "canonical": canonical,
        "entity_resolution": platform_resolution.to_dict(),
    }


def _resolve_entity_for_investigation(value: str) -> ResolutionResult:
    try:
        return _resolve_platform_entity(value)
    except Exception:  # noqa: BLE001
        return ResolutionResult(False, str(value or ""), 0.0, "", reason="platform_resolution_unavailable")


def _investigation_match_method(platform_resolution: ResolutionResult, fallback_method: str) -> str:
    if not platform_resolution.found:
        return fallback_method
    if platform_resolution.method == "identifier":
        return "entity_id"
    if platform_resolution.method == "exact":
        return "exact_name"
    if platform_resolution.method == "canonical":
        return "case_insensitive_name"
    if platform_resolution.method == "alias":
        return "alias"
    return platform_resolution.method or fallback_method


def get_investigation(entity_id: str) -> dict[str, Any]:
    resolved = resolve_investigation_target(entity_id)
    with _session_scope() as session:
        resolved_id = resolve_entity_uuid_for_investigation(session, str(resolved.get("entity_id") or entity_id))
        if resolved_id is None:
            resolved_id = resolve_entity_uuid_for_investigation(session, str(entity_id))
        if resolved_id is None:
            return {
                "found": False,
                "entity_id": str(entity_id),
                "resolution": resolved,
                "warning": _investigation_not_found_warning(resolved, entity_id),
            }
        resolved = {**resolved, "found": True, "entity_id": resolved_id}
        view = build_investigation_view(session, resolved_id)
    if view is None:
        return {"found": False, "entity_id": resolved_id, "resolution": resolved}

    profile = view.profile
    compact_metrics = _compact_metrics(view)
    relationship_cards = _relationship_cards(profile.direct_neighbors)
    payload = {
        "found": True,
        "resolution": resolved,
        "entity": _jsonify(profile.entity),
        "entity_type_label": view.entity_type_label,
        "summary": view.summary,
        "narrative_summary": _narrative_summary(view),
        "dataset_badges": list(view.dataset_badges),
        "key_metrics": _jsonify(view.metrics),
        "compact_metrics": compact_metrics,
        "timeline": _jsonify(view.timeline.events if view.timeline is not None else ()),
        "connections": {
            "summary": view.graph_explanation,
            "graph": _jsonify(view.graph),
            "relationship_counts": _jsonify(profile.relationship_counts),
            "direct_neighbors": _jsonify(profile.direct_neighbors),
            "relationship_cards": relationship_cards,
        },
        "contracts_compras": _jsonify(view.procurement_items),
        "lobby": _jsonify(view.lobby_items),
        "transparencia": _jsonify(view.role_items),
        "registro_empresas": _jsonify(getattr(view, "registry_items", ())),
        "evidence": _jsonify(view.evidence_groups),
        "neutral_explanation": investigation_explanation_text(),
        "technical_details": {
            "entity_id": profile.entity.id,
            "external_id": profile.entity.external_id,
            "entity_type": profile.entity.entity_type,
            "relationship_counts": _jsonify(profile.relationship_counts),
        },
    }
    if _is_legislative_bill_view(view):
        payload.update(_legislative_payload(view))
    payload["knowledge"] = get_investigation_knowledge(payload)
    return payload


def _is_uuid(value: str) -> bool:
    try:
        UUID(str(value))
    except (TypeError, ValueError):
        return False
    return True

def resolve_entity_uuid_for_investigation(session: Session, target: str) -> str | None:
    cleaned = str(target or "").strip()
    if not cleaned:
        return None
    if _is_uuid(cleaned):
        return cleaned

    for candidate in _investigation_uuid_candidates(cleaned):
        if _is_uuid(candidate):
            return candidate
        entity_id = _entity_uuid_by_external_id_or_name(session, candidate)
        if entity_id:
            return entity_id
    return None


def _investigation_uuid_candidates(target: str) -> tuple[str, ...]:
    candidates: list[str] = [target]
    resolved = resolve_investigation_target(target)
    if resolved.get("found", False):
        candidates.append(str(resolved.get("entity_id", "")))
        canonical = resolved.get("canonical", {})
        if isinstance(canonical, dict):
            candidates.append(str(canonical.get("canonical_entity_id", "")))
            candidates.append(str(canonical.get("original_entity_id", "")))
    platform_resolution = _resolve_entity_for_investigation(target)
    if platform_resolution.found and platform_resolution.entity is not None:
        candidates.append(str(platform_resolution.entity.id))
        candidates.append(str(platform_resolution.entity.canonical_name))
        candidates.extend(str(identifier.value) for identifier in platform_resolution.entity.identifiers)
        candidates.extend(str(alias.value) for alias in platform_resolution.entity.aliases)
    return tuple(dict.fromkeys(candidate.strip() for candidate in candidates if candidate and candidate.strip()))


def _entity_uuid_by_external_id_or_name(session: Session, value: str) -> str | None:
    if not hasattr(session, "scalar"):
        return None
    cleaned = str(value or "").strip()
    if not cleaned:
        return None
    entity_id = session.scalar(select(Entity.id).where(Entity.external_id == cleaned).limit(1))
    if entity_id is not None:
        return str(entity_id)
    entity_id = session.scalar(select(Entity.id).where(func.lower(Entity.name) == cleaned.lower()).limit(1))
    if entity_id is not None:
        return str(entity_id)
    return None


def _investigation_not_found_warning(resolved: dict[str, Any], target: str) -> str:
    warning = str(resolved.get("warning", "")).strip()
    if warning:
        return warning
    return f"No se encontro una entidad local para abrir el expediente: {target}"

def get_investigation_knowledge(investigation: dict[str, Any]) -> dict[str, Any]:
    return investigation_knowledge_to_dict(build_investigation_knowledge(investigation))



def get_dataset_summary() -> dict[str, Any]:
    with _session_scope() as session:
        datasets = [_jsonify(row) for row in list_datasets(session)]

    return {
        "datasets": datasets,
        "totals": {
            "datasets": len(datasets),
            "active_datasets": sum(1 for row in datasets if row["health"] == "active"),
            "source_records": sum(int(row["source_records"]) for row in datasets),
            "entities": sum(int(row["entities"]) for row in datasets),
            "claims": sum(int(row["claims"]) for row in datasets),
            "evidence": sum(int(row["evidence"]) for row in datasets),
            "relationships": sum(int(row["relationships"]) for row in datasets),
        },
    }


def get_real_data_readiness() -> dict[str, Any]:
    with _session_scope() as session:
        return _jsonify(summarize_real_dataset_registry(session))


def get_data_ecosystem() -> dict[str, Any]:
    with _session_scope() as session:
        ecosystem = _jsonify(build_ecosystem_registry(session))
    ecosystem = _apply_source_population_to_ecosystem(ecosystem)
    return _apply_connectors_to_ecosystem(ecosystem)


def get_discovery_cases() -> dict[str, Any]:
    return _jsonify(_get_discovery_cases())


def get_guided_questions() -> dict[str, Any]:
    return _jsonify(_get_guided_questions())


def get_guided_discovery_options(category: str) -> list[dict[str, Any]]:
    return _jsonify(_get_guided_discovery_options(category))


def get_home_navigation_examples() -> list[dict[str, Any]]:
    return _jsonify(_get_home_navigation_examples())


def resolve_canonical_expediente_target(value: str) -> dict[str, Any]:
    return _jsonify(_resolve_canonical_expediente_target(value))


def get_record_context(value: str) -> dict[str, Any]:
    return _jsonify(_get_record_context(value))


def get_institution_profile(entity_name: str) -> dict[str, Any]:
    return _jsonify(build_institution_profile(entity_name))


def get_cross_dataset_connections() -> list[dict[str, Any]]:
    with _session_scope() as session:
        return [_jsonify(row) for row in list_cross_dataset_organizations(session)]


def get_entity_comparison(entity_id: str) -> dict[str, Any]:
    return _jsonify(build_entity_comparison(entity_id))


def get_investigation_story(entity_id: str) -> dict[str, Any]:
    return _jsonify(build_investigation_story(entity_id))


def search_workspace(query: str) -> dict[str, Any]:
    workspace = _jsonify(_search_workspace(query))
    matches = []
    for row in workspace.get("matches", []):
        canonical = resolve_canonical_expediente_target(str(row.get("entity_id", "")))
        record_context = get_record_context(str(row.get("entity_id", "")))
        enriched = {
            **row,
            "canonical_entity_id": canonical.get("canonical_entity_id", row.get("entity_id", "")),
            "canonical_entity_name": canonical.get("canonical_entity_name", row.get("entity_name", "")),
            "canonical_entity_type": canonical.get("canonical_entity_type", row.get("entity_type", "")),
            "is_record": bool(canonical.get("is_record", False)),
            "record_label": canonical.get("record_label", ""),
            "relation_to_original": canonical.get("relation_to_original", ""),
            "related_label": record_context.get("related_label", ""),
        }
        if _is_legislative_search_row(enriched):
            enriched.update(
                {
                    "result_type": "Proyecto legislativo / Boletin",
                    "entity_type_label": "Proyecto legislativo / Boletin",
                    "source_hint": "dato oficial cargado",
                    "official_status": "dato oficial cargado",
                    "source_label": LEGISLATIVE_SOURCE_LABEL,
                    "datasets": [LEGISLATIVE_SOURCE_LABEL],
                    "action_label": "Abrir expediente",
                    "action_href": f"/investigation?id={enriched.get('canonical_entity_id') or enriched.get('entity_id')}",
                }
            )
        matches.append(enriched)
    matches.extend(_source_population_search_matches(query))
    matches.extend(_connector_search_matches(query))
    workspace["matches"] = matches
    return workspace


def get_source_trace(entity_id: str) -> dict[str, Any]:
    return _jsonify(build_source_trace(entity_id))


def get_investigation_markdown(entity_id: str) -> str:
    return export_investigation_markdown(entity_id)


def get_investigation_graph(entity_id: str) -> dict[str, Any]:
    return _jsonify(build_investigation_graph(entity_id))


def get_investigation_timeline(entity_id: str) -> dict[str, Any]:
    resolved = resolve_investigation_target(entity_id)
    target = str(resolved.get("entity_id", entity_id)) if resolved.get("found", False) else entity_id
    return _jsonify(build_investigation_timeline(target))


def get_source_contributions(entity_id: str) -> dict[str, Any]:
    return _jsonify(build_source_contributions(entity_id))


def get_citizen_dashboard() -> dict[str, Any]:
    return _jsonify(build_citizen_dashboard())


def export_investigation_report(entity_id: str) -> str:
    return _export_investigation_report(entity_id)


def get_demo_status() -> dict[str, Any]:
    try:
        with _session_scope() as session:
            report = build_demo_status(session)
    except Exception as exc:  # noqa: BLE001
        return {
            "ready": False,
            "database_connected": False,
            "required_datasets_loaded": False,
            "dataset_statuses": [],
            "cross_dataset_organization": None,
            "timeline_entity": None,
            "streamlit_app_available": False,
            "missing": [
                {
                    "label": "PostgreSQL connection.",
                    "commands": ("check DATABASE_URL and local PostgreSQL",),
                }
            ],
            "error": f"{type(exc).__name__}: {exc}",
        }

    report_dict = _jsonify(report)
    report_dict["ready"] = (
        report.database_connected
        and report.required_datasets_loaded
        and report.cross_dataset_organization is not None
        and report.timeline_entity is not None
        and report.streamlit_app_available
    )
    report_dict["missing"] = report_dict.pop("repairs")
    return report_dict


def get_tracking_demo() -> dict[str, Any]:
    return _apply_connectors_to_tracking(_jsonify(tracking_to_dict(build_tracking_demo())))


def get_tracking_items() -> list[dict[str, Any]]:
    return _jsonify([tracking_to_dict(_get_tracking_timeline(item.id))["item"] for item in _list_tracking_items()])


def get_tracking_item(item_id: str) -> dict[str, Any]:
    timeline = _get_tracking_item(item_id)
    return _apply_connectors_to_tracking(_jsonify(tracking_to_dict(timeline))) if timeline is not None else {}


def get_tracking_timeline(item_id: str) -> dict[str, Any]:
    timeline = _get_tracking_timeline(item_id)
    return _apply_connectors_to_tracking(_jsonify(tracking_to_dict(timeline))) if timeline is not None else {}


def export_tracking_demo_report() -> str:
    return _export_tracking_demo_report()


def get_knowledge_demo() -> dict[str, Any]:
    real_document = _load_real_document_publication()
    if real_document:
        return real_document
    return _jsonify(document_view_payload(publish_document()))


def get_knowledge_digest(document_id: str) -> dict[str, Any]:
    try:
        return _jsonify(document_view_payload(publish_document(document_id)))
    except ValueError:
        return {}


def get_knowledge_documents() -> list[dict[str, Any]]:
    return _jsonify([official_document_to_dict(document) for document in _list_knowledge_documents()])


def _load_connector(connector_id: str) -> dict[str, Any]:
    path = CONNECTORS_ROOT / f"{connector_id}_connector.json"
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    return payload if isinstance(payload, dict) else {}


def _loaded_connectors() -> list[dict[str, Any]]:
    return [connector for connector in (_load_connector("chilecompra"),) if connector]


def _apply_connectors_to_ecosystem(ecosystem: dict[str, Any]) -> dict[str, Any]:
    connectors = {str(connector.get("id", "")): connector for connector in _loaded_connectors()}
    for source in ecosystem.get("sources", []):
        connector = connectors.get(str(source.get("slug", "")))
        if not connector:
            continue
        source["connector_status"] = str(connector.get("status", ""))
        source["connector_summary"] = str(connector.get("summary", ""))
        source["connector_entities"] = len(connector.get("entities", []))
        source["connector_relationships"] = len(connector.get("relationships", []))
        source["connector_events"] = len(connector.get("events", []))
    return ecosystem


def _connector_search_matches(query: str) -> list[dict[str, Any]]:
    normalized_query = _normalize_for_population(query)
    if not normalized_query:
        return []
    matches: list[dict[str, Any]] = []
    for connector in _loaded_connectors():
        for entity in _jsonify(connector.get("entities", [])):
            haystack = _normalize_for_population(" ".join([str(entity.get("name", "")), str(entity.get("id", "")), str(entity.get("entity_type", "")), str(connector.get("display_name", ""))]))
            if not _population_query_matches(normalized_query, haystack):
                continue
            matches.append(
                {
                    "entity_id": entity.get("id", ""),
                    "entity_name": entity.get("name", ""),
                    "entity_type": entity.get("model_entity_type", entity.get("entity_type", "")),
                    "datasets": [connector.get("display_name", "ChileCompra Connector")],
                    "evidence_count": len(connector.get("evidence", [])),
                    "relationship_count": len(connector.get("relationships", [])),
                    "result_type": f"connector: {entity.get('entity_type', 'entidad')}",
                    "official_status": connector.get("official_status", ""),
                    "source_label": connector.get("display_name", "ChileCompra Connector"),
                    "source_hint": connector.get("status", ""),
                    "canonical_entity_id": entity.get("id", ""),
                    "canonical_entity_name": entity.get("name", ""),
                    "canonical_entity_type": entity.get("model_entity_type", entity.get("entity_type", "")),
                    "action_label": "Buscar expediente",
                    "action_href": f"/search?q={str(entity.get('name', '')).replace(' ', '+')}",
                }
            )
    return matches


def _connector_pulse_events() -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for connector in _loaded_connectors():
        for row in _jsonify(connector.get("events", []))[:1]:
            events.append(
                {
                    "id": row.get("id", ""),
                    "title": row.get("title", ""),
                    "summary": row.get("pulse_summary", row.get("description", "")),
                    "status": "Connector activo",
                    "updated_at": row.get("date", ""),
                    "organization": row.get("source", connector.get("display_name", "")),
                    "source": row.get("source", connector.get("display_name", "")),
                    "href": "/search?q=SERVICIO+DE+SALUD+ARAUCO+HOSPITAL+DE+ARAUCO",
                }
            )
    return events


def _apply_connectors_to_tracking(timeline: dict[str, Any]) -> dict[str, Any]:
    if not timeline:
        return timeline
    existing_ids = {str(event.get("id", "")) for event in timeline.get("events", [])}
    for connector in _loaded_connectors():
        for row in _jsonify(connector.get("events", [])):
            event_id = str(row.get("id", ""))
            if not event_id or event_id in existing_ids:
                continue
            timeline.setdefault("events", []).append(
                {
                    "id": event_id,
                    "date": row.get("date", ""),
                    "status": row.get("status", "published"),
                    "title": row.get("title", ""),
                    "description": row.get("description", ""),
                    "source": row.get("source", connector.get("display_name", "")),
                    "evidence_ids": row.get("evidence_ids", []),
                    "document_ids": [],
                    "related_entity_names": row.get("related_entity_names", []),
                }
            )
            existing_ids.add(event_id)
    if "overview" in timeline and "progress" in timeline["overview"]:
        timeline["overview"]["progress"]["total_events"] = len(timeline.get("events", []))
    return timeline

def _load_source_population() -> dict[str, Any]:
    if not SOURCE_POPULATION_PATH.exists():
        return {}
    try:
        payload = json.loads(SOURCE_POPULATION_PATH.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    return payload if isinstance(payload, dict) else {}


def _apply_source_population_to_ecosystem(ecosystem: dict[str, Any]) -> dict[str, Any]:
    population = _load_source_population()
    source_id = str(population.get("source_id", ""))
    if not source_id:
        return ecosystem
    records = _jsonify(population.get("records", []))
    for source in ecosystem.get("sources", []):
        if source.get("slug") != source_id:
            continue
        source["display_name_populated"] = str(population.get("display_name", source.get("name", "")))
        source["population_mode"] = str(population.get("population_mode", ""))
        source["population_status_label"] = str(population.get("status_label", ""))
        source["population_summary"] = str(population.get("summary", ""))
        source["population_records"] = len(records)
        source["coverage"] = "partial" if records else source.get("coverage", "")
    return ecosystem


def _source_population_search_matches(query: str) -> list[dict[str, Any]]:
    normalized_query = _normalize_for_population(query)
    if not normalized_query:
        return []
    population = _load_source_population()
    matches: list[dict[str, Any]] = []
    for row in _jsonify(population.get("ui", {}).get("search_entities", [])):
        haystack = _normalize_for_population(" ".join([str(row.get("entity_name", "")), str(row.get("entity_id", "")), " ".join(row.get("datasets", []))]))
        if not _population_query_matches(normalized_query, haystack):
            continue
        matches.append(
            {
                **row,
                "canonical_entity_id": row.get("entity_id", ""),
                "canonical_entity_name": row.get("entity_name", ""),
                "canonical_entity_type": row.get("entity_type", ""),
                "source_hint": str(population.get("status_label", "")),
                "official_status": str(population.get("official_status", "")),
                "source_label": str(population.get("display_name", "InfoLobby")),
            }
        )
    return matches


def _population_query_matches(normalized_query: str, haystack: str) -> bool:
    if normalized_query in haystack:
        return True
    tokens = [token for token in normalized_query.split() if token]
    return bool(tokens) and all(token in haystack for token in tokens)


def _source_population_pulse_events() -> list[dict[str, Any]]:
    population = _load_source_population()
    event = population.get("ui", {}).get("pulse_event", {}) if isinstance(population.get("ui", {}), dict) else {}
    return [_jsonify(event)] if event else []


def _normalize_for_population(value: str) -> str:
    return " ".join(str(value or "").strip().lower().split())

def _load_real_document_publication() -> dict[str, Any]:
    if not REAL_DOCUMENT_PUBLICATION_PATH.exists():
        return {}
    try:
        payload = json.loads(REAL_DOCUMENT_PUBLICATION_PATH.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    if not isinstance(payload, dict):
        return {}
    document_view = payload.get("document_view", {})
    if not isinstance(document_view, dict) or not document_view:
        return {}
    return _jsonify(document_view)


def get_current_topics(limit: int = 3) -> list[dict[str, Any]]:
    topics = _jsonify(_list_current_topics(limit=limit))
    for event in [*_connector_pulse_events(), *_source_population_pulse_events()]:
        if len(topics) >= limit:
            break
        topics.append(event)
    return topics[:limit]


def get_current_topic(slug: str) -> dict[str, Any]:
    return _jsonify(_get_current_topic(slug))


def get_citizen_report_demo() -> dict[str, Any]:
    return _jsonify(citizen_report_to_dict(build_citizen_report_demo()))


def get_citizen_reports() -> list[dict[str, Any]]:
    return _jsonify([citizen_report_to_dict(report) for report in _list_citizen_reports()])


def get_citizen_report(report_id: str) -> dict[str, Any]:
    report = _get_citizen_report(report_id)
    return _jsonify(citizen_report_to_dict(report)) if report is not None else {}


def export_citizen_report_demo() -> str:
    return _export_citizen_report_demo()


def get_platform_config_summary() -> dict[str, Any]:
    return _jsonify(summarize_platform_config(get_default_platform_config()))


def get_platform_examples() -> list[dict[str, Any]]:
    examples = [
        get_default_platform_config(),
        load_platform_config("config/platform/client_example.json"),
    ]
    return _jsonify([summarize_platform_config(config) for config in examples])


@contextmanager
def _session_scope() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session


def _jsonify(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return {key: _jsonify(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): _jsonify(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [_jsonify(item) for item in value]
    if isinstance(value, date | datetime):
        return value.isoformat()
    return value


def _entity_type_label(entity_type: str) -> str:
    labels = {
        "PUBLIC_ORGANIZATION": "Organismo publico",
        "COMPANY": "Empresa",
        "PERSON": "Persona",
        "CONTRACT": "Contrato",
        "ROLE": "Cargo publico",
        "LOBBY_MEETING": "Reunion de lobby",
        "CONTROL_REPORT": "Informe de control",
        "PUBLIC_OBSERVATION": "Observacion publica",
        "ADMINISTRATIVE_PROCEDURE": "Procedimiento administrativo",
        "ADMINISTRATIVE_RESOLUTION": "Resolucion administrativa",
        "MUNICIPALITY": "Municipio",
        "PUBLIC_PROJECT": "Proyecto legislativo / Boletin",
        "SPENDING_ITEM": "Item de gasto",
    }
    return labels.get(entity_type, entity_type.replace("_", " ").title())


def _search_result_explanation(item: dict[str, Any]) -> str:
    claims = int(item.get("claims", 0) or 0)
    relationships = int(item.get("relationships", 0) or 0)
    if claims or relationships:
        return (
            "Entidad encontrada en la base local con registros publicos cargados, "
            f"{claims} afirmaciones y {relationships} relaciones navegables."
        )
    return "Entidad encontrada en la base local. Abre la investigacion para revisar fuentes disponibles."


def _narrative_summary(view: Any) -> str:
    entity_name = view.profile.entity.name
    datasets = ", ".join(view.dataset_badges) if view.dataset_badges else "las fuentes disponibles"
    parts = [f"{entity_name} aparece en {datasets}."]
    available: list[str] = []
    if view.procurement_items:
        available.append("actividad de compras publicas")
    if view.role_items:
        available.append("registros de transparencia administrativa")
    if view.lobby_items:
        available.append("registros de lobby")
    if view.graph is not None:
        available.append("relaciones institucionales")
    if view.evidence_groups:
        available.append("evidencia asociada")
    if _is_legislative_bill_view(view):
        available.append("votaciones oficiales asociadas al boletin")
    if available:
        parts.append("Los registros disponibles incluyen " + ", ".join(available) + ".")
    if _is_legislative_bill_view(view):
        parts.append(LEGISLATIVE_LIMITATION_TEXT)
    parts.append("Esto no afirma causalidad, irregularidad ni responsabilidad; cada conexion debe revisarse en su evidencia original.")
    return " ".join(parts)


def _is_legislative_search_row(row: dict[str, Any]) -> bool:
    datasets = " ".join(str(item) for item in row.get("datasets", []))
    return (
        str(row.get("entity_type", "")) == LEGISLATIVE_PROJECT_ENTITY_TYPE
        and ("Datos Abiertos Legislativos" in datasets or "congreso" in datasets.lower())
    ) or str(row.get("entity_id", "")).startswith("cl-congreso-boletin-") or str(row.get("canonical_entity_id", "")).startswith("cl-congreso-boletin-")


def _is_legislative_bill_view(view: Any) -> bool:
    entity = view.profile.entity
    return (
        str(getattr(entity, "entity_type", "")) == LEGISLATIVE_PROJECT_ENTITY_TYPE
        and str(getattr(entity, "external_id", "") or "").startswith("cl-congreso-boletin-")
    )


def _legislative_payload(view: Any) -> dict[str, Any]:
    source_records = _jsonify(getattr(view, "source_records", ()))
    vote_count = len(getattr(view, "legislative_vote_items", ()))
    if not vote_count:
        vote_count = len([event for event in getattr(getattr(view, "timeline", None), "events", ()) if getattr(event, "predicate", "") == "LEGISLATIVE_BILL_HAS_VOTE"])
    return {
        "entity_type_label": "Proyecto legislativo / Boletin",
        "official_source": LEGISLATIVE_SOURCE_LABEL,
        "official_status": "dato oficial cargado",
        "legislative": {
            "type": "Proyecto legislativo",
            "source": LEGISLATIVE_SOURCE_LABEL,
            "votes_found": vote_count,
            "source_records_count": len(source_records),
            "source_records": source_records,
            "limitations": [LEGISLATIVE_LIMITATION_TEXT],
        },
        "limitations": [LEGISLATIVE_LIMITATION_TEXT],
    }


def _compact_metrics(view: Any) -> dict[str, int]:
    return {
        "datasets_involved": len(view.dataset_badges),
        "evidence_count": int(view.metrics.evidence),
        "connected_entities": len(view.profile.direct_neighbors),
        "relationship_count": int(view.metrics.relationships),
    }


def _relationship_cards(neighbors: Any) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    for row in neighbors:
        cards.append(
            {
                "who": row.neighbor.name,
                "entity_type": _entity_type_label(row.neighbor.entity_type),
                "relationship_meaning": relationship_explanation(row.relationship_type),
                "source_dataset": "Grafo publico local",
                "technical_details": {
                    "relationship_id": row.relationship_id,
                    "relationship_type": row.relationship_type,
                    "direction": row.direction,
                    "neighbor_id": row.neighbor.id,
                },
            }
        )
    return cards


_ORIGINAL_ENTITY_TYPE_LABEL = _entity_type_label
_ORIGINAL_NARRATIVE_SUMMARY = _narrative_summary


def _entity_type_label(entity_type: str) -> str:  # type: ignore[override]
    if entity_type == "ELECTORAL_PERIOD":
        return "Periodo electoral"
    return _ORIGINAL_ENTITY_TYPE_LABEL(entity_type)


def _narrative_summary(view: Any) -> str:  # type: ignore[override]
    entity_name = view.profile.entity.name
    datasets = ", ".join(view.dataset_badges) if view.dataset_badges else "las fuentes disponibles"
    parts = [f"{entity_name} aparece en {datasets}."]
    available: list[str] = []
    if view.procurement_items:
        available.append("actividad de compras publicas")
    if view.role_items:
        if any(getattr(item, "dataset", "") == "SERVEL" for item in view.role_items):
            available.append("registros de autoridades electas")
        else:
            available.append("registros de transparencia administrativa")
    if view.lobby_items:
        available.append("registros de lobby")
    if view.graph is not None:
        available.append("relaciones institucionales")
    if view.evidence_groups:
        available.append("evidencia asociada")
    if available:
        parts.append("Los registros disponibles incluyen " + ", ".join(available) + ".")
    parts.append("Esto no afirma causalidad, irregularidad ni responsabilidad; cada conexion debe revisarse en su evidencia original.")
    return " ".join(parts)
