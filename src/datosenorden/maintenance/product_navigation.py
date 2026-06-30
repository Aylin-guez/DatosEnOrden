from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any
import unicodedata
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from datosenorden.db.session import SessionLocal
from datosenorden.maintenance.entity_comparison import build_entity_comparison
from datosenorden.maintenance.safe_access import _field
from datosenorden.models import Claim, Entity, Evidence, RelationshipPublic


MAIN_ENTITY_TYPES = {"PUBLIC_ORGANIZATION", "PERSON", "COMPANY", "SUPPLIER", "AUTHORITY"}
RECORD_ENTITY_TYPES = {
    "BUDGET",
    "CONTRACT",
    "PURCHASE_ORDER",
    "LOBBY_MEETING",
    "PUBLICATION",
    "OFFICIAL_PUBLICATION",
    "EVIDENCE",
    "ROLE",
    "CONTROL_REPORT",
    "PUBLIC_OBSERVATION",
    "ADMINISTRATIVE_PROCEDURE",
    "ADMINISTRATIVE_RESOLUTION",
}
CANONICAL_PRIORITY = {"PUBLIC_ORGANIZATION": 0, "COMPANY": 1, "PERSON": 2, "SUPPLIER": 1, "AUTHORITY": 2}


@dataclass(frozen=True)
class _ResolvedEntity:
    entity: Entity
    matched_by: str
    warning: str = ""


def resolve_canonical_expediente_target(value: str) -> dict[str, Any]:
    cleaned = str(value or "").strip()
    if not cleaned:
        return _not_found("", "No se recibio un identificador o nombre de entidad.")

    with SessionLocal() as session:
        resolved = _resolve_entity(session, cleaned)
        if resolved is None:
            return _not_found(cleaned, "No se encontro una entidad local para ese identificador o nombre.")

        original = resolved.entity
        if original.entity_type in MAIN_ENTITY_TYPES:
            canonical = original
            relation = "self"
        else:
            canonical, relation = _canonical_neighbor(session, original)
            if canonical is None:
                canonical = original
                relation = "self_no_canonical_found"

        return {
            "found": True,
            "canonical_entity_id": str(canonical.id),
            "canonical_entity_name": canonical.name,
            "canonical_entity_type": canonical.entity_type,
            "original_entity_id": str(original.id),
            "original_entity_name": original.name,
            "original_entity_type": original.entity_type,
            "relation_to_original": relation,
            "matched_by": resolved.matched_by,
            "is_record": original.entity_type in RECORD_ENTITY_TYPES,
            "record_label": _record_label(original.entity_type),
            "warning": resolved.warning,
        }


def get_record_context(value: str) -> dict[str, Any]:
    resolved = resolve_canonical_expediente_target(value)
    if not resolved.get("found"):
        return resolved
    if not resolved.get("is_record"):
        return {
            **resolved,
            "summary": "Entidad principal. Abre su expediente directamente.",
            "related_label": "",
        }
    return {
        **resolved,
        "summary": "Registro especifico guardado localmente. El expediente canonico muestra la entidad principal relacionada.",
        "related_label": f"Relacionado con: {resolved['canonical_entity_name']}",
    }


def get_home_navigation_examples(limit: int = 6) -> list[dict[str, Any]]:
    with SessionLocal() as session:
        rows = _entities_by_types(session, ("PUBLIC_ORGANIZATION",), limit=limit)
        if not rows:
            rows = _top_entities(session, limit=limit)
        return [_option_for_entity(session, entity, "Organismo con registros locales disponibles.") for entity in rows]


def get_guided_discovery_options(category: str, limit: int = 8) -> list[dict[str, Any]]:
    normalized = _normalize_category(category)
    with SessionLocal() as session:
        entities = _category_entities(session, normalized, limit=limit)
        return [_option_for_entity(session, entity, _why_for_category(normalized, entity)) for entity in entities]


def _category_entities(session: Session, category: str, *, limit: int) -> list[Entity]:
    if category in {"public_organizations", "organismos", "who_sells_to_this_body"}:
        return _entities_by_types(session, ("PUBLIC_ORGANIZATION",), limit=limit, name_hint="ARAUCO")
    if category in {"suppliers", "which_suppliers_appear", "which_related_companies_exist"}:
        return _entities_by_types(session, ("COMPANY",), limit=limit, preferred_names=("ACME", "CONSULTORA", "SERVICIOS NORTE"))
    if category in {"authorities", "public_offices", "which_authorities_appear"}:
        return _entities_by_types(session, ("PERSON", "ROLE"), limit=limit, preferred_names=("SOFIA", "ANA", "JUAN", "LAURA", "MARIA", "PEDRO"))
    if category in {"budgets"}:
        return _entities_by_types(session, ("BUDGET",), limit=limit, name_hint="DIPRES")
    if category in {"procurement"}:
        return _entities_by_types(session, ("CONTRACT", "PURCHASE_ORDER"), limit=limit)
    if category in {"meetings", "which_meetings_were_recorded"}:
        return _entities_by_types(session, ("LOBBY_MEETING",), limit=limit)
    if category in {"which_official_publications_exist", "publications"}:
        return _entities_by_name_patterns(session, ("N 12", "12.801", "Diario", "Directora"), limit=limit)
    return _top_entities(session, limit=limit)


def _option_for_entity(session: Session, entity: Entity, why: str) -> dict[str, Any]:
    canonical = resolve_canonical_expediente_target(str(entity.id))
    datasets = _datasets_for_entity(str(canonical.get("canonical_entity_id") or entity.id))
    return {
        "title": entity.name,
        "type": entity.entity_type,
        "type_label": _record_label(entity.entity_type),
        "sources": datasets,
        "sources_text": " | ".join(datasets) if datasets else "Fuentes locales",
        "why_it_appears": why,
        "entity_id": str(entity.id),
        "canonical_entity_id": str(canonical.get("canonical_entity_id") or entity.id),
        "canonical_entity_name": str(canonical.get("canonical_entity_name") or entity.name),
        "is_record": bool(canonical.get("is_record", entity.entity_type in RECORD_ENTITY_TYPES)),
        "record_context": str(canonical.get("relation_to_original", "")),
    }


def _resolve_entity(session: Session, value: str) -> _ResolvedEntity | None:
    try:
        entity_uuid = UUID(value)
    except ValueError:
        entity_uuid = None
    if entity_uuid is not None:
        entity = session.get(Entity, entity_uuid)
        return _ResolvedEntity(entity, "entity_id") if entity is not None else None

    exact = session.scalars(select(Entity).where(Entity.name == value)).all()
    if exact:
        return _ResolvedEntity(_best_entity(session, exact), "exact_name", _ambiguity_warning(exact))

    lowered = value.lower()
    insensitive = session.scalars(select(Entity).where(func.lower(Entity.name) == lowered)).all()
    if insensitive:
        return _ResolvedEntity(_best_entity(session, insensitive), "case_insensitive_name", _ambiguity_warning(insensitive))

    normalized = _normalize_lookup(value)
    if not normalized:
        return None
    candidates = session.scalars(select(Entity)).all()
    matches = [entity for entity in candidates if _normalize_lookup(entity.name) == normalized]
    if matches:
        return _ResolvedEntity(_best_entity(session, matches), "normalized_name", _ambiguity_warning(matches))
    return None


def _canonical_neighbor(session: Session, entity: Entity) -> tuple[Entity | None, str]:
    neighbors: list[tuple[Entity, str]] = []
    relationships = session.scalars(
        select(RelationshipPublic)
        .where(or_(RelationshipPublic.source_entity_id == entity.id, RelationshipPublic.target_entity_id == entity.id))
        .options(joinedload(RelationshipPublic.source_entity), joinedload(RelationshipPublic.target_entity))
    ).all()
    for relationship in relationships:
        neighbor = relationship.target_entity if relationship.source_entity_id == entity.id else relationship.source_entity
        if neighbor is not None and neighbor.entity_type in CANONICAL_PRIORITY:
            neighbors.append((neighbor, relationship.relationship_type))

    claims = session.scalars(
        select(Claim)
        .where(or_(Claim.subject_entity_id == entity.id, Claim.object_entity_id == entity.id))
        .options(joinedload(Claim.subject_entity), joinedload(Claim.object_entity))
    ).all()
    for claim in claims:
        for neighbor in (claim.subject_entity, claim.object_entity):
            if neighbor is not None and neighbor.id != entity.id and neighbor.entity_type in CANONICAL_PRIORITY:
                neighbors.append((neighbor, claim.predicate))

    if not neighbors:
        return None, ""
    best = _best_entity(session, [neighbor for neighbor, _relation in neighbors])
    same_named = session.scalars(
        select(Entity).where(Entity.entity_type == best.entity_type, func.lower(Entity.name) == best.name.lower())
    ).all()
    if same_named:
        best = _best_entity(session, same_named)
    relation = next((relation for neighbor, relation in neighbors if neighbor.id == best.id), "related")
    return best, relation


def _best_entity(session: Session, entities: list[Entity]) -> Entity:
    return sorted(
        entities,
        key=lambda entity: (
            CANONICAL_PRIORITY.get(entity.entity_type, 9),
            -_activity_score(session, entity),
            entity.name.lower(),
            str(entity.id),
        ),
    )[0]


def _activity_score(session: Session, entity: Entity) -> int:
    claims = int(
        session.scalar(
            select(func.count()).select_from(Claim).where(or_(Claim.subject_entity_id == entity.id, Claim.object_entity_id == entity.id))
        )
        or 0
    )
    relationships = int(
        session.scalar(
            select(func.count())
            .select_from(RelationshipPublic)
            .where(or_(RelationshipPublic.source_entity_id == entity.id, RelationshipPublic.target_entity_id == entity.id))
        )
        or 0
    )
    evidence = int(
        session.scalar(
            select(func.count())
            .select_from(Evidence)
            .join(Claim, Evidence.claim_id == Claim.id)
            .where(or_(Claim.subject_entity_id == entity.id, Claim.object_entity_id == entity.id))
        )
        or 0
    )
    return claims + relationships + evidence


def _entities_by_types(
    session: Session,
    entity_types: tuple[str, ...],
    *,
    limit: int,
    name_hint: str = "",
    preferred_names: tuple[str, ...] = (),
) -> list[Entity]:
    statement = select(Entity).where(Entity.entity_type.in_(entity_types))
    if name_hint:
        statement = statement.where(Entity.name.ilike(f"%{name_hint}%"))
    rows = session.scalars(statement).all()
    if preferred_names:
        rows = [
            entity
            for entity in rows
            if any(preferred.lower() in entity.name.lower() for preferred in preferred_names)
        ] or rows
    return _dedupe_entities(sorted(rows, key=lambda entity: (-_activity_score(session, entity), entity.name.lower(), str(entity.id))))[:limit]


def _entities_by_name_patterns(session: Session, patterns: tuple[str, ...], *, limit: int) -> list[Entity]:
    rows: list[Entity] = []
    for pattern in patterns:
        rows.extend(session.scalars(select(Entity).where(Entity.name.ilike(f"%{pattern}%"))).all())
    return _dedupe_entities(sorted(rows, key=lambda entity: (-_activity_score(session, entity), entity.name.lower(), str(entity.id))))[:limit]


def _top_entities(session: Session, *, limit: int) -> list[Entity]:
    rows = session.scalars(select(Entity)).all()
    return _dedupe_entities(sorted(rows, key=lambda entity: (-_activity_score(session, entity), entity.name.lower(), str(entity.id))))[:limit]


def _dedupe_entities(rows: list[Entity]) -> list[Entity]:
    seen: set[tuple[str, str]] = set()
    deduped: list[Entity] = []
    for entity in rows:
        key = (entity.entity_type, _normalize_lookup(entity.name))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(entity)
    return deduped


def _datasets_for_entity(entity_id: str) -> list[str]:
    try:
        comparison = build_entity_comparison(entity_id)
    except Exception:  # noqa: BLE001
        return []
    return [str(dataset) for dataset in _field(comparison, "datasets_present", [])]


def _record_label(entity_type: str) -> str:
    labels = {
        "PUBLIC_ORGANIZATION": "Organismo publico",
        "COMPANY": "Empresa",
        "PERSON": "Persona",
        "BUDGET": "Registro especifico",
        "CONTRACT": "Registro especifico",
        "PURCHASE_ORDER": "Registro especifico",
        "LOBBY_MEETING": "Registro especifico",
        "PUBLICATION": "Registro especifico",
        "OFFICIAL_PUBLICATION": "Registro especifico",
        "ROLE": "Registro especifico",
        "CONTROL_REPORT": "Registro especifico",
        "PUBLIC_OBSERVATION": "Registro especifico",
        "ADMINISTRATIVE_PROCEDURE": "Registro especifico",
        "ADMINISTRATIVE_RESOLUTION": "Registro especifico",
    }
    return labels.get(entity_type, entity_type.replace("_", " ").title())


def _why_for_category(category: str, entity: Entity) -> str:
    if entity.entity_type in RECORD_ENTITY_TYPES:
        return "Aparece como registro especifico del caso demo local."
    if category in {"suppliers", "which_suppliers_appear", "which_related_companies_exist"}:
        return "Aparece como proveedor o empresa conectada a compras y registros locales."
    if category in {"authorities", "public_offices", "which_authorities_appear"}:
        return "Aparece como persona o cargo en fuentes administrativas locales."
    return "Aparece en datos locales cargados para el demo MVP."


def _normalize_category(category: str) -> str:
    return str(category or "").strip().lower().replace("-", "_")


def _normalize_lookup(value: str) -> str:
    text = unicodedata.normalize("NFKD", value.strip().lower())
    text = "".join(character for character in text if not unicodedata.combining(character))
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def _ambiguity_warning(matches: list[Entity]) -> str:
    if len(matches) <= 1:
        return ""
    return f"Se encontraron {len(matches)} entidades con ese nombre; se eligio la que tiene mas datos navegables."


def _not_found(value: str, warning: str) -> dict[str, Any]:
    return {
        "found": False,
        "canonical_entity_id": "",
        "canonical_entity_name": "",
        "canonical_entity_type": "",
        "original_entity_id": "",
        "original_entity_name": value,
        "original_entity_type": "",
        "relation_to_original": "",
        "matched_by": "",
        "is_record": False,
        "record_label": "",
        "warning": warning,
    }
