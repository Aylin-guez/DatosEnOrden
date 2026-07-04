from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from datosenorden.maintenance.safe_access import _field


NEUTRALITY_NOTICE = "No afirma causalidad, irregularidad ni responsabilidad; cada afirmacion debe revisarse con la evidencia original."


@dataclass(frozen=True)
class InvestigationKeyPoint:
    text: str
    source_ids: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class InvestigationKnowledge:
    citizen_summary: str
    key_points: tuple[InvestigationKeyPoint, ...]
    suggested_questions: tuple[str, ...]
    limitations: tuple[str, ...]
    neutrality_notice: str = NEUTRALITY_NOTICE


def build_investigation_knowledge(investigation: dict[str, Any]) -> InvestigationKnowledge:
    entity_name = _text(_field(_field(investigation, "entity", {}), "name"), "La entidad")
    dataset_badges = _string_list(_field(investigation, "dataset_badges", []))
    compact_metrics = _field(investigation, "compact_metrics", {})
    sources_count = _int(_field(compact_metrics, "datasets_involved", len(dataset_badges)))
    evidence_count = _int(_field(compact_metrics, "evidence_count", 0))
    relationship_count = _int(_field(compact_metrics, "relationship_count", 0))
    connected_count = _int(_field(compact_metrics, "connected_entities", 0))

    information_types = _information_types(investigation)
    citizen_summary = _build_summary(
        entity_name=entity_name,
        sources_count=sources_count,
        information_types=information_types,
        evidence_count=evidence_count,
        relationship_count=relationship_count,
        connected_count=connected_count,
    )

    return InvestigationKnowledge(
        citizen_summary=citizen_summary,
        key_points=tuple(_build_key_points(investigation, dataset_badges)[:6]),
        suggested_questions=_build_suggested_questions(),
        limitations=_build_limitations(dataset_badges, investigation),
    )


def investigation_knowledge_to_dict(knowledge: InvestigationKnowledge) -> dict[str, Any]:
    return {
        "citizen_summary": knowledge.citizen_summary,
        "key_points": [asdict(point) for point in knowledge.key_points],
        "suggested_questions": list(knowledge.suggested_questions),
        "limitations": list(knowledge.limitations),
        "neutrality_notice": knowledge.neutrality_notice,
    }


def _build_summary(
    *,
    entity_name: str,
    sources_count: int,
    information_types: list[str],
    evidence_count: int,
    relationship_count: int,
    connected_count: int,
) -> str:
    source_text = f"{sources_count} fuente" if sources_count == 1 else f"{sources_count} fuentes"
    type_text = _join_human(information_types) if information_types else "registros y evidencia disponible"
    return (
        f"Este expediente revisa a {entity_name} a partir de {source_text} locales. "
        f"Reune {type_text}; incluye {evidence_count} evidencias, {relationship_count} relaciones y "
        f"{connected_count} entidades conectadas cuando esos datos existen. Permite entender que informacion "
        "esta disponible, de donde proviene y que conexiones aparecen en los registros. "
        f"{NEUTRALITY_NOTICE}"
    )


def _build_key_points(investigation: dict[str, Any], dataset_badges: list[str]) -> list[InvestigationKeyPoint]:
    points: list[InvestigationKeyPoint] = []
    evidence_refs = _evidence_refs(investigation)
    relationship_refs = _relationship_refs(investigation)
    timeline_refs = _timeline_refs(investigation)
    source_ids = tuple(dataset_badges)

    if dataset_badges:
        points.append(
            InvestigationKeyPoint(
                text=f"El expediente combina informacion de {len(dataset_badges)} fuentes locales: {_join_human(dataset_badges)}.",
                source_ids=source_ids,
                evidence_ids=evidence_refs[:3],
            )
        )
    if evidence_refs:
        points.append(
            InvestigationKeyPoint(
                text=f"Hay evidencia asociada para revisar afirmaciones y volver a los registros originales.",
                source_ids=source_ids,
                evidence_ids=evidence_refs[:5],
            )
        )
    if relationship_refs:
        points.append(
            InvestigationKeyPoint(
                text="Existen relaciones registradas con otras entidades o documentos que ayudan a leer el contexto.",
                source_ids=source_ids,
                evidence_ids=relationship_refs[:5],
            )
        )
    if timeline_refs:
        points.append(
            InvestigationKeyPoint(
                text="La informacion incluye hitos ordenables en el tiempo, utiles para revisar cambios y secuencia.",
                source_ids=source_ids,
                evidence_ids=timeline_refs[:5],
            )
        )
    if not points:
        points.append(
            InvestigationKeyPoint(
                text="El expediente contiene informacion minima; antes de concluir se deben revisar fuentes y evidencia original.",
                source_ids=source_ids,
                evidence_ids=evidence_refs[:3],
            )
        )
    points.append(
        InvestigationKeyPoint(
            text="Las conexiones muestran apariciones en registros; no prueban causalidad, intencion ni responsabilidad.",
            source_ids=source_ids,
            evidence_ids=evidence_refs[:3],
        )
    )
    return points


def _build_suggested_questions() -> tuple[str, ...]:
    return (
        "Que fuente respalda esta afirmacion?",
        "Que cambio en el tiempo?",
        "Que entidades aparecen conectadas?",
        "Que documentos deberia revisar antes de concluir?",
        "Que informacion falta para tener una lectura mas completa?",
    )


def _build_limitations(dataset_badges: list[str], investigation: dict[str, Any] | None = None) -> tuple[str, ...]:
    limitations = [
        "Datos locales de prueba cuando el expediente proviene del demo.",
        "Fuentes incompletas o con cobertura parcial.",
        "Algunas fuentes pueden estar en estado prototipo.",
        "No reemplaza la revision documental original.",
        "No permite concluir causalidad, irregularidad ni responsabilidad por si solo.",
    ]
    investigation = investigation or {}
    entity = _field(investigation, "entity", {})
    is_legislative = (
        _field(entity, "entity_type", "") == "PUBLIC_PROJECT"
        and str(_field(entity, "external_id", "")).startswith("cl-congreso-boletin-")
    )
    if is_legislative:
        limitations.insert(
            0,
            "Este expediente contiene votaciones oficiales asociadas al boletín, pero aún no incorpora el texto completo del proyecto.",
        )
    if not dataset_badges:
        limitations.insert(0, "No hay fuentes suficientes para una lectura completa.")
    return tuple(limitations)


def _information_types(investigation: dict[str, Any]) -> list[str]:
    types: list[str] = []
    if _field(investigation, "evidence", []):
        types.append("evidencia")
    if _field(_field(investigation, "connections", {}), "relationship_cards", []) or _field(_field(investigation, "connections", {}), "direct_neighbors", []):
        types.append("relaciones")
    if _field(investigation, "timeline", []):
        types.append("hitos en el tiempo")
    if _field(investigation, "contracts_compras", []):
        types.append("registros operativos")
    if _field(investigation, "lobby", []):
        types.append("reuniones o interacciones registradas")
    if _field(investigation, "transparencia", []):
        types.append("roles o informacion administrativa")
    if _field(investigation, "registro_empresas", []):
        types.append("registros de entidades relacionadas")
    return types


def _evidence_refs(investigation: dict[str, Any]) -> tuple[str, ...]:
    refs: list[str] = []
    for group in _as_list(_field(investigation, "evidence", [])):
        for link in _as_list(_field(group, "links", [])):
            ref = _text(_field(link, "evidence_id")) or _text(_field(link, "id")) or _text(_field(link, "title"))
            if ref:
                refs.append(ref)
    return tuple(_dedupe(refs))


def _relationship_refs(investigation: dict[str, Any]) -> tuple[str, ...]:
    refs: list[str] = []
    connections = _field(investigation, "connections", {})
    for row in _as_list(_field(connections, "relationship_cards", [])) or _as_list(_field(connections, "direct_neighbors", [])):
        ref = _text(_field(row, "relationship_id")) or _text(_field(row, "id")) or _text(_field(row, "entity_id")) or _text(_field(row, "name"))
        if ref:
            refs.append(ref)
    return tuple(_dedupe(refs))


def _timeline_refs(investigation: dict[str, Any]) -> tuple[str, ...]:
    refs: list[str] = []
    for row in _as_list(_field(investigation, "timeline", [])):
        ref = _text(_field(row, "event_id")) or _text(_field(row, "id")) or _text(_field(row, "title")) or _text(_field(row, "label"))
        if ref:
            refs.append(ref)
    return tuple(_dedupe(refs))


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


def _string_list(value: Any) -> list[str]:
    return [str(item) for item in _as_list(value) if str(item).strip()]


def _text(value: Any, fallback: str = "") -> str:
    text = str(value or "").strip()
    return text if text else fallback


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        key = value.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def _join_human(values: list[str]) -> str:
    cleaned = [value for value in values if value]
    if not cleaned:
        return ""
    if len(cleaned) == 1:
        return cleaned[0]
    if len(cleaned) == 2:
        return f"{cleaned[0]} y {cleaned[1]}"
    return f"{', '.join(cleaned[:-1])} y {cleaned[-1]}"
