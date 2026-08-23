"""Citizen-facing source coverage derived from persisted provenance."""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from datosenorden.application.provenance.service import build_provenance_snapshot
from datosenorden.models import Source, SourceRecord


def public_source_catalog(session: Session, technical_sources: list[dict[str, Any]]) -> dict[str, object]:
    """Return only sources with persisted, public REAL records.

    Connector state is read from the existing technical registry and is never
    inferred from the presence of records.
    """
    metrics_by_source_name = {
        str(row["source_name"]): row
        for row in build_provenance_snapshot(session).source_metrics
        if int(row.get("available_real_records", 0) or 0)
    }
    record_types: dict[str, list[str]] = defaultdict(list)
    for source_name, record_type in session.execute(
        select(Source.name, SourceRecord.record_type)
        .join(SourceRecord, SourceRecord.source_id == Source.id)
        .order_by(Source.name, SourceRecord.record_type)
    ):
        record_types[str(source_name)].append(str(record_type))

    technical_by_name = {
        str(row.get("name", "")).casefold(): dict(row)
        for row in technical_sources
    }
    rows = []
    for source_name, metric in metrics_by_source_name.items():
        technical = technical_by_name.get(str(metric.get("source_label", "")).casefold(), {})
        connector_code = str(technical.get("connector_status", ""))
        rows.append(
            {
                "name": str(metric.get("source_label", source_name)),
                "description": _information_description(record_types.get(source_name, [])),
                "coverage_status": "Datos disponibles",
                "coverage_detail": (
                    f"{int(metric.get('available_real_records', 0) or 0)} registros incorporados; "
                    "la cobertura puede ser parcial."
                ),
                "connector_status": _connector_label(connector_code),
                "connector_active": connector_code == "active_local_connector",
                "record_count": int(metric.get("available_real_records", 0) or 0),
                "relationship_count": int(metric.get("real_relationships", 0) or 0),
                "limitation": "Los registros incorporados no representan cobertura completa de la institución.",
            }
        )
    rows.sort(key=lambda row: str(row["name"]).casefold())
    return {
        "sources": rows,
        "source_count": len(rows),
        "connector_active_count": sum(bool(row["connector_active"]) for row in rows),
    }


def _information_description(record_types: list[str]) -> str:
    labels = {
        "chilecompra:purchase_order": "Órdenes de compra y contratación pública incorporadas.",
        "dipres:execution_total_program": "Información de ejecución presupuestaria incorporada.",
        "legislature:matter_observation": "Documentos y observaciones legislativas incorporadas.",
    }
    unique = list(dict.fromkeys(record_types))
    if len(unique) == 1 and unique[0] in labels:
        return labels[unique[0]]
    return "Información pública incorporada en esta publicación."


def _connector_label(connector_code: str) -> str:
    if connector_code == "active_local_connector":
        return "Conector activo local"
    if connector_code:
        return "Conector registrado; su estado no equivale a datos disponibles"
    return "Sin conector activo declarado"
