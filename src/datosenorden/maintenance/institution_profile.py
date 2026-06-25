from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from datosenorden.db.session import SessionLocal
from datosenorden.maintenance.dipres_prototype import read_budget_summary
from datosenorden.maintenance.entity_comparison import build_entity_comparison
from datosenorden.maintenance.investigation_story import build_investigation_story
from datosenorden.maintenance.investigation_view import build_investigation_view
from datosenorden.maintenance.safe_access import _field
from datosenorden.maintenance.source_trace import build_source_trace
from datosenorden.maintenance.timeline_explorer import build_entity_timeline
from datosenorden.models import Claim, Entity


def build_institution_profile(entity_name: str) -> dict[str, object]:
    cleaned = entity_name.strip()
    if not cleaned:
        return _empty_profile(entity_name)

    with SessionLocal() as session:
        entity = _find_entity(session, cleaned)
        if entity is None:
            return _empty_profile(cleaned)

        entity_id = str(entity.id)
        view = build_investigation_view(session, entity_id)
        comparison = build_entity_comparison(entity_id)
        story = build_investigation_story(entity_id)
        trace = build_source_trace(entity_id)
        timeline = build_entity_timeline(session, entity_id)
        budget_rows = _budget_rows(session, cleaned)

    if view is None:
        return _empty_profile(cleaned)

    return {
        "entidad": {
            "id": str(entity.id),
            "nombre": entity.name,
            "tipo": entity.entity_type,
            "fuentes": list(_field(comparison, "datasets_present", [])),
        },
        "presupuesto": {
            "total": sum(row["executed_budget"] or row["approved_budget"] for row in budget_rows),
            "moneda": _budget_currency(budget_rows),
            "resumen": _budget_summary_text(budget_rows, entity.name),
            "registros": budget_rows,
        },
        "contratos": _procurement_section(view),
        "reuniones": _lobby_section(view),
        "autoridades": _authorities_section(view),
        "publicaciones": _publications_section(timeline),
        "evidencia": _evidence_section(view),
        "relaciones": _relations_section(trace, view),
        "resumen": _field(story, "summary", ""),
        "hallazgos": list(_field(story, "key_findings", [])),
        "fuentes_consultadas": list(_field(story, "sources_consulted", [])),
    }


def _find_entity(session: Session, name: str) -> Entity | None:
    exact = session.scalar(
        select(Entity)
        .where(Entity.name.ilike(name))
        .order_by(Entity.entity_type.asc(), Entity.name.asc())
    )
    if exact is not None:
        return exact
    partial = session.scalar(
        select(Entity)
        .where(Entity.name.ilike(f"%{name}%"))
        .order_by(Entity.entity_type.asc(), Entity.name.asc())
    )
    return partial


def _budget_rows(session: Session, entity_name: str) -> list[dict[str, object]]:
    rows = []
    for row in read_budget_summary(session):
        if entity_name.lower() not in row.organization_name.lower() and entity_name.lower() not in row.budget_entity_name.lower():
            continue
        rows.append(
            {
                "organization_name": row.organization_name,
                "budget_entity_name": row.budget_entity_name,
                "fiscal_year": row.fiscal_year,
                "approved_budget": row.approved_budget,
                "executed_budget": row.executed_budget,
                "purchase_orders": row.purchase_orders,
                "suppliers": row.suppliers,
                "currency": row.currency,
            }
        )
    return rows


def _budget_currency(rows: list[dict[str, object]]) -> str:
    for row in rows:
        currency = row.get("currency")
        if currency:
            return str(currency)
    return "CLP"


def _budget_summary_text(rows: list[dict[str, object]], entity_name: str) -> str:
    if not rows:
        return f"No se encontraron registros presupuestarios para {entity_name}."
    total = sum(int(row["executed_budget"] or row["approved_budget"]) for row in rows)
    years = ", ".join(str(row["fiscal_year"]) for row in rows if row.get("fiscal_year") is not None)
    return f"Se encontraron {len(rows)} registros presupuestarios de muestra para {entity_name}. Total observado: {total}. Años: {years}."


def _procurement_section(view) -> list[dict[str, object]]:  # noqa: ANN001
    return [
        {
            "dataset": _field(item, "dataset", ""),
            "contract_name": _field(item, "contract_name", ""),
            "supplier": _field(item, "supplier", ""),
            "evidence_count": _field(item, "evidence_count", 0),
            "evidence_links": [_jsonify(link) for link in _field(item, "evidence_links", ())],
        }
        for item in _field(view, "procurement_items", ())
    ]


def _lobby_section(view) -> list[dict[str, object]]:  # noqa: ANN001
    return [
        {
            "dataset": _field(item, "dataset", ""),
            "date": _field(item, "date", "").isoformat() if isinstance(_field(item, "date", None), date) else "",
            "organization": _field(item, "organization", ""),
            "counterparty": _field(item, "counterparty", ""),
            "subject": _field(item, "subject", ""),
            "evidence_count": _field(item, "evidence_count", 0),
            "evidence_links": [_jsonify(link) for link in _field(item, "evidence_links", ())],
        }
        for item in _field(view, "lobby_items", ())
    ]


def _authorities_section(view) -> list[dict[str, object]]:  # noqa: ANN001
    return [
        {
            "dataset": _field(item, "dataset", ""),
            "holder": _field(item, "holder", ""),
            "role_title": _field(item, "role_title", ""),
            "period": _field(item, "period", ""),
            "evidence_count": _field(item, "evidence_count", 0),
            "evidence_links": [_jsonify(link) for link in _field(item, "evidence_links", ())],
        }
        for item in _field(view, "role_items", ())
    ]


def _publications_section(timeline) -> list[dict[str, object]]:  # noqa: ANN001
    events = _field(timeline, "events", ())
    rows: list[dict[str, object]] = []
    for event in events:
        if "official" not in str(_field(event, "dataset_name", "")).lower() and "public" not in str(_field(event, "predicate", "")).lower() and "decree" not in str(_field(event, "predicate", "")).lower():
            continue
        rows.append(
            {
                "date": _field(event, "event_date", "").isoformat() if isinstance(_field(event, "event_date", None), date) else "",
                "dataset": _field(event, "dataset", ""),
                "label": _field(event, "title", ""),
                "explanation": _field(event, "explanation", ""),
                "predicate": _field(event, "predicate", ""),
            }
        )
    return rows


def _evidence_section(view) -> list[dict[str, object]]:  # noqa: ANN001
    rows: list[dict[str, object]] = []
    for group in _field(view, "evidence_groups", ()):
        for link in _field(group, "links", ()):
            rows.append(
                {
                    "dataset": _field(group, "dataset", ""),
                    "title": _field(link, "title", ""),
                    "url": _field(link, "url", ""),
                    "published_at": _field(link, "published_at", "").isoformat() if isinstance(_field(link, "published_at", None), date) else "",
                }
            )
    return rows


def _relations_section(trace: dict[str, object], view) -> list[dict[str, object]]:  # noqa: ANN001
    rows: list[dict[str, object]] = []
    for connection in _field(trace, "connections", []):
        rows.append(
            {
                "dataset": _field(connection, "from_source", ""),
                "entity": _field(connection, "to_entity", ""),
                "meaning": _field(connection, "meaning", ""),
                "evidence_count": _field(connection, "evidence_count", 0),
            }
        )
    if rows:
        return rows
    fallback_rows: list[dict[str, object]] = []
    for neighbor in _field(_field(view, "profile", {}), "direct_neighbors", ()):
        item = _jsonify(neighbor)
        if not isinstance(item, dict):
            continue
        fallback_rows.append(
            {
                "dataset": str(item.get("dataset", "")),
                "entity": str(item.get("name", item.get("entity", ""))),
                "meaning": str(item.get("relationship_meaning", "")),
                "evidence_count": int(item.get("evidence_count", 0) or 0),
            }
        )
    return fallback_rows


def _empty_profile(entity_name: str) -> dict[str, object]:
    return {
        "entidad": {"id": "", "nombre": entity_name, "tipo": "", "fuentes": []},
        "presupuesto": {"total": 0, "moneda": "CLP", "resumen": "No se encontraron registros presupuestarios.", "registros": []},
        "contratos": [],
        "reuniones": [],
        "autoridades": [],
        "publicaciones": [],
        "evidencia": [],
        "relaciones": [],
        "resumen": "",
        "hallazgos": [],
        "fuentes_consultadas": [],
    }


def _jsonify(value: object) -> object:
    if is_dataclass(value) and not isinstance(value, type):
        return {key: _jsonify(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): _jsonify(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [_jsonify(item) for item in value]
    if isinstance(value, date | datetime):
        return value.isoformat()
    return value

