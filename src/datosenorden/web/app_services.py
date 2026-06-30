from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from typing import Any, Iterator

from sqlalchemy.orm import Session

from datosenorden.db.session import SessionLocal
from datosenorden.maintenance.cross_dataset_explorer import list_cross_dataset_organizations
from datosenorden.maintenance.dataset_registry import list_datasets
from datosenorden.maintenance.demo_pack import build_demo_status
from datosenorden.maintenance.discovery_cases import get_discovery_cases as _get_discovery_cases
from datosenorden.maintenance.citizen_dashboard import build_citizen_dashboard
from datosenorden.maintenance.ecosystem_registry import build_ecosystem_registry
from datosenorden.maintenance.entity_comparison import build_entity_comparison
from datosenorden.maintenance.investigation_export import export_investigation_markdown
from datosenorden.maintenance.investigation_story import build_investigation_story
from datosenorden.maintenance.entity_explorer import search_buyers
from datosenorden.maintenance.entity_explorer import search_suppliers
from datosenorden.maintenance.explanations import relationship_explanation
from datosenorden.maintenance.investigation_graph import build_investigation_graph
from datosenorden.maintenance.investigation_report import export_investigation_report as _export_investigation_report
from datosenorden.maintenance.investigation_view import build_investigation_view
from datosenorden.maintenance.investigation_view import investigation_explanation_text
from datosenorden.maintenance.investigation_timeline import build_investigation_timeline
from datosenorden.maintenance.guided_questions import get_guided_questions as _get_guided_questions
from datosenorden.maintenance.institution_profile import build_institution_profile
from datosenorden.maintenance.product_navigation import get_guided_discovery_options as _get_guided_discovery_options
from datosenorden.maintenance.product_navigation import get_home_navigation_examples as _get_home_navigation_examples
from datosenorden.maintenance.product_navigation import get_record_context as _get_record_context
from datosenorden.maintenance.product_navigation import resolve_canonical_expediente_target as _resolve_canonical_expediente_target
from datosenorden.maintenance.search_workspace import search_workspace as _search_workspace
from datosenorden.maintenance.source_contributions import build_source_contributions
from datosenorden.maintenance.source_trace import build_source_trace


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
    canonical = _resolve_canonical_expediente_target(value)
    if not canonical.get("found", False):
        return {
            "found": False,
            "entity_id": "",
            "entity_name": str(canonical.get("original_entity_name", value)),
            "matched_by": "",
            "warning": str(canonical.get("warning", "")),
            "canonical": canonical,
        }
    entity_id = str(canonical.get("canonical_entity_id", ""))
    entity_name = str(canonical.get("canonical_entity_name", ""))
    return {
        "found": True,
        "entity_id": entity_id,
        "entity_name": entity_name,
        "matched_by": str(canonical.get("matched_by", "")),
        "warning": str(canonical.get("warning", "")),
        "canonical": canonical,
    }


def get_investigation(entity_id: str) -> dict[str, Any]:
    resolved = resolve_investigation_target(entity_id)
    if not resolved.get("found", False):
        resolved = {
            "found": True,
            "entity_id": entity_id,
            "entity_name": entity_id,
            "matched_by": "input",
            "warning": str(resolved.get("warning", "")),
            "canonical": resolved.get("canonical", {}),
        }

    resolved_id = str(resolved["entity_id"])
    with _session_scope() as session:
        view = build_investigation_view(session, resolved_id)
    if view is None:
        return {"found": False, "entity_id": resolved_id, "resolution": resolved}

    profile = view.profile
    compact_metrics = _compact_metrics(view)
    relationship_cards = _relationship_cards(profile.direct_neighbors)
    return {
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


def get_data_ecosystem() -> dict[str, Any]:
    with _session_scope() as session:
        return _jsonify(build_ecosystem_registry(session))


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
        matches.append(
            {
                **row,
                "canonical_entity_id": canonical.get("canonical_entity_id", row.get("entity_id", "")),
                "canonical_entity_name": canonical.get("canonical_entity_name", row.get("entity_name", "")),
                "canonical_entity_type": canonical.get("canonical_entity_type", row.get("entity_type", "")),
                "is_record": bool(canonical.get("is_record", False)),
                "record_label": canonical.get("record_label", ""),
                "relation_to_original": canonical.get("relation_to_original", ""),
                "related_label": record_context.get("related_label", ""),
            }
        )
    workspace["matches"] = matches
    return workspace


def get_source_trace(entity_id: str) -> dict[str, Any]:
    return _jsonify(build_source_trace(entity_id))


def get_investigation_markdown(entity_id: str) -> str:
    return export_investigation_markdown(entity_id)


def get_investigation_graph(entity_id: str) -> dict[str, Any]:
    return _jsonify(build_investigation_graph(entity_id))


def get_investigation_timeline(entity_id: str) -> dict[str, Any]:
    return _jsonify(build_investigation_timeline(entity_id))


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
        "PUBLIC_PROJECT": "Proyecto publico",
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
    if available:
        parts.append("Los registros disponibles incluyen " + ", ".join(available) + ".")
    parts.append("Esto no afirma causalidad, irregularidad ni responsabilidad; cada conexion debe revisarse en su evidencia original.")
    return " ".join(parts)


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
