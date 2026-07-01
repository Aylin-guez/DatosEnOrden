from __future__ import annotations

from dataclasses import dataclass
import unicodedata
import re

from sqlalchemy import or_, select

from datosenorden.db.session import SessionLocal
from datosenorden.maintenance.entity_comparison import build_entity_comparison
from datosenorden.maintenance.entity_explorer import get_entity_profile
from datosenorden.maintenance.entity_matching import match_entity_candidates
from datosenorden.maintenance.entity_resolution import resolve_entity
from datosenorden.maintenance.knowledge_engine import list_knowledge_documents
from datosenorden.maintenance.citizen_reports import list_citizen_reports
from datosenorden.maintenance.tracking import list_tracking_items
from datosenorden.models import Entity


@dataclass(frozen=True)
class SearchWorkspaceMatch:
    entity_id: str
    entity_name: str
    entity_type: str
    datasets: tuple[str, ...]
    evidence_count: int
    relationship_count: int
    score: float
    result_type: str = "entidad"
    action_label: str = "Abrir expediente"
    action_href: str = ""


def search_workspace(query: str, limit: int = 12) -> dict[str, object]:
    cleaned = query.strip()
    if not cleaned:
        return {"matches": []}
    if limit < 1:
        raise ValueError("limit must be greater than zero")

    with SessionLocal() as session:
        matches = _collect_matches(session, cleaned, limit=limit)

    return {
        "matches": [
            {
                "entity_id": item.entity_id,
                "entity_name": item.entity_name,
                "entity_type": item.entity_type,
                "datasets": list(item.datasets),
                "evidence_count": item.evidence_count,
                "relationship_count": item.relationship_count,
                "result_type": item.result_type,
                "action_label": item.action_label,
                "action_href": item.action_href or f"/investigation?id={item.entity_id}",
            }
            for item in matches
        ]
    }


def _collect_matches(session, query: str, *, limit: int) -> tuple[SearchWorkspaceMatch, ...]:  # noqa: ANN001
    merged: dict[str, SearchWorkspaceMatch] = {}
    normalized_limit = max(limit, 20)

    entity_types = session.scalars(select(Entity.entity_type).distinct().order_by(Entity.entity_type.asc())).all()
    resolved = resolve_entity(query)
    if resolved.found and resolved.entity is not None:
        entity = session.get(Entity, resolved.entity.id)
        if entity is not None:
            _merge_candidate(merged, session, str(entity.id), entity.name, entity.entity_type, 1.0)

    for entity_type in entity_types:
        for candidate in match_entity_candidates(session, entity_type=str(entity_type), name=query, limit=normalized_limit):
            _merge_candidate(merged, session, candidate.candidate_entity_id, candidate.candidate_name, candidate.entity_type, candidate.score)

    pattern = f"%{query}%"
    direct_rows = session.scalars(
        select(Entity)
        .where(or_(Entity.name.ilike(pattern), Entity.external_id.ilike(pattern)))
        .order_by(Entity.name.asc(), Entity.id.asc())
    ).all()
    for entity in direct_rows:
        _merge_candidate(merged, session, str(entity.id), entity.name, entity.entity_type, 0.75)

    normalized_query = _normalize(query)
    if normalized_query:
        rows = session.scalars(select(Entity)).all()
        for entity in rows:
            if normalized_query in _normalize(entity.name) or normalized_query in _normalize(str(getattr(entity, "external_id", "") or "")):
                _merge_candidate(merged, session, str(entity.id), entity.name, entity.entity_type, 0.7)

    for extra in _document_matches(query):
        merged[f"document:{extra.entity_id}"] = extra
    for extra in _report_matches(query):
        merged[f"report:{extra.entity_id}"] = extra
    for extra in _tracking_matches(query):
        merged[f"tracking:{extra.entity_id}"] = extra

    return tuple(
        sorted(
            merged.values(),
            key=lambda item: (-item.score, item.entity_name.lower(), item.entity_id),
        )[:limit]
    )


def _merge_candidate(
    merged: dict[str, SearchWorkspaceMatch],
    session,
    entity_id: str,
    entity_name: str,
    entity_type: str,
    score: float,
) -> None:  # noqa: ANN001
    profile = get_entity_profile(session, entity_id)
    comparison = build_entity_comparison(entity_id)
    datasets = tuple(str(dataset) for dataset in comparison.get("datasets_present", ()))
    evidence_count = len(profile.evidences) if profile is not None else 0
    relationship_count = len(profile.relationships) if profile is not None else 0
    existing = merged.get(entity_id)
    if existing is None or score > existing.score:
        merged[entity_id] = SearchWorkspaceMatch(
            entity_id=entity_id,
            entity_name=entity_name,
            entity_type=entity_type,
            datasets=datasets,
            evidence_count=evidence_count,
            relationship_count=relationship_count,
            score=score,
            result_type=_result_type(entity_type),
            action_label="Abrir expediente",
            action_href=f"/investigation?id={entity_id}",
        )


def _document_matches(query: str) -> tuple[SearchWorkspaceMatch, ...]:
    normalized_query = _normalize(query)
    matches: list[SearchWorkspaceMatch] = []
    for document in list_knowledge_documents():
        haystack = _normalize(
            " ".join(
                [
                    document.title,
                    document.summary,
                    document.source,
                    document.document_type,
                    document.official_status,
                    document.classification,
                    document.related_expediente_target,
                    document.official_url,
                ]
            )
        )
        if normalized_query and normalized_query in haystack:
            matches.append(
                SearchWorkspaceMatch(
                    entity_id=document.id,
                    entity_name=document.title,
                    entity_type="DOCUMENT",
                    datasets=(document.source,),
                    evidence_count=len(document.sections),
                    relationship_count=1,
                    score=0.66,
                    result_type="documento",
                    action_label="Ver documento",
                    action_href="/library",
                )
            )
    return tuple(matches)


def _report_matches(query: str) -> tuple[SearchWorkspaceMatch, ...]:
    normalized_query = _normalize(query)
    matches: list[SearchWorkspaceMatch] = []
    for report in list_citizen_reports():
        haystack = _normalize(" ".join([report.title, report.summary, report.subject]))
        if normalized_query and normalized_query in haystack:
            matches.append(
                SearchWorkspaceMatch(
                    entity_id=report.id,
                    entity_name=report.title,
                    entity_type="CITIZEN_REPORT",
                    datasets=tuple(report.sources),
                    evidence_count=len(report.evidence_refs),
                    relationship_count=1,
                    score=0.64,
                    result_type="reporte",
                    action_label="Ver reporte",
                    action_href="/reports",
                )
            )
    return tuple(matches)


def _tracking_matches(query: str) -> tuple[SearchWorkspaceMatch, ...]:
    normalized_query = _normalize(query)
    matches: list[SearchWorkspaceMatch] = []
    for item in list_tracking_items():
        haystack = _normalize(" ".join([item.title, item.summary, item.related_expediente_target]))
        if normalized_query and normalized_query in haystack:
            matches.append(
                SearchWorkspaceMatch(
                    entity_id=item.id,
                    entity_name=item.title,
                    entity_type="TRACKING",
                    datasets=tuple(item.related_sources),
                    evidence_count=0,
                    relationship_count=1,
                    score=0.62,
                    result_type="seguimiento",
                    action_label="Ver seguimiento",
                    action_href="/tracking",
                )
            )
    return tuple(matches)


def _result_type(entity_type: str) -> str:
    if entity_type in {"COMPANY", "SUPPLIER"}:
        return "proveedor"
    if entity_type in {"DOCUMENT", "OFFICIAL_PUBLICATION", "PUBLICATION"}:
        return "documento"
    if entity_type in {"CONTRACT", "PURCHASE_ORDER", "BUDGET", "LOBBY_MEETING"}:
        return "fuente/registro"
    return "entidad"


def _normalize(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").strip().lower())
    text = "".join(character for character in text if not unicodedata.combining(character))
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())
