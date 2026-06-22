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
from datosenorden.maintenance.entity_comparison import build_entity_comparison
from datosenorden.maintenance.investigation_story import build_investigation_story
from datosenorden.maintenance.entity_explorer import search_buyers
from datosenorden.maintenance.entity_explorer import search_suppliers
from datosenorden.maintenance.explanations import relationship_explanation
from datosenorden.maintenance.investigation_view import build_investigation_view
from datosenorden.maintenance.investigation_view import investigation_explanation_text


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


def get_investigation(entity_id: str) -> dict[str, Any]:
    with _session_scope() as session:
        view = build_investigation_view(session, entity_id)
    if view is None:
        return {"found": False, "entity_id": entity_id}

    profile = view.profile
    compact_metrics = _compact_metrics(view)
    relationship_cards = _relationship_cards(profile.direct_neighbors)
    return {
        "found": True,
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


def get_cross_dataset_connections() -> list[dict[str, Any]]:
    with _session_scope() as session:
        return [_jsonify(row) for row in list_cross_dataset_organizations(session)]


def get_entity_comparison(entity_id: str) -> dict[str, Any]:
    return _jsonify(build_entity_comparison(entity_id))


def get_investigation_story(entity_id: str) -> dict[str, Any]:
    return _jsonify(build_investigation_story(entity_id))


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
