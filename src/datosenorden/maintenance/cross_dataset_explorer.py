from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import distinct, or_, select
from sqlalchemy.orm import Session, joinedload

from datosenorden.maintenance.explanations import dataset_display_name
from datosenorden.models import Claim, Dataset, Entity, Evidence, RelationshipPublic, SourceRecord

LOBBY_ORGANIZATION_PREDICATE = "ORGANIZATION_HELD_LOBBY_MEETING"
LOBBY_COUNTERPARTY_PREDICATE = "COUNTERPARTY_PARTICIPATED_IN_LOBBY"
PROCUREMENT_ORGANIZATION_PREDICATE = "ISSUES_PURCHASE_ORDER"
PROCUREMENT_SUPPLIER_PREDICATE = "RECEIVES_CONTRACT"


@dataclass(frozen=True)
class CrossDatasetConnection:
    entity_id: str
    entity_type: str
    name: str
    relationship_type: str


@dataclass(frozen=True)
class CrossDatasetOrganizationSummary:
    organization_id: str
    organization_name: str
    datasets: tuple[str, ...]
    contracts: int
    lobby_meetings: int
    evidence: int
    relationships: int
    lobby_connections: tuple[CrossDatasetConnection, ...]
    procurement_connections: tuple[CrossDatasetConnection, ...]
    explanation: str


def list_cross_dataset_organizations(session: Session) -> tuple[CrossDatasetOrganizationSummary, ...]:
    organization_ids = _organization_ids_in_multiple_datasets(session)
    summaries = [
        summary
        for organization_id in organization_ids
        if (summary := get_cross_dataset_organization_summary(session, str(organization_id))) is not None
    ]
    return tuple(sorted(summaries, key=lambda item: item.organization_name.lower()))


def get_cross_dataset_organization_summary(
    session: Session,
    organization_id: str,
) -> CrossDatasetOrganizationSummary | None:
    organization = session.get(Entity, UUID(organization_id))
    if organization is None:
        return None
    datasets = _datasets_for_entity(session, organization.id)
    if len(datasets) < 2:
        return None

    claim_ids = _claim_ids_for_entity(session, organization.id)
    contracts = _count_distinct_claim_objects(
        session,
        organization.id,
        PROCUREMENT_ORGANIZATION_PREDICATE,
        dataset_group="chilecompra",
    )
    lobby_meetings = _count_distinct_claim_objects(
        session,
        organization.id,
        LOBBY_ORGANIZATION_PREDICATE,
        dataset_group="lobby",
    )
    return CrossDatasetOrganizationSummary(
        organization_id=str(organization.id),
        organization_name=organization.name,
        datasets=tuple(sorted(datasets)),
        contracts=contracts,
        lobby_meetings=lobby_meetings,
        evidence=_count_evidence(session, organization.id, claim_ids),
        relationships=_count_relationships(session, organization.id, claim_ids),
        lobby_connections=_lobby_connections(session, organization.id),
        procurement_connections=_procurement_connections(session, organization.id),
        explanation=citizen_friendly_explanation(),
    )


def citizen_friendly_explanation() -> str:
    return "\n".join(
        [
            "This organization appears in more than one public dataset.",
            "",
            "The available records show:",
            "* procurement activity in ChileCompra",
            "* registered lobby meetings",
            "* administrative role records in Transparencia Activa when sample data is loaded",
            "* additional local prototype datasets when they are loaded",
            "* public relationships and supporting evidence",
            "",
            "The platform only presents stored records and does not imply any relationship beyond the available public information.",
        ]
    )


def render_cross_dataset_summary_text(rows: tuple[CrossDatasetOrganizationSummary, ...]) -> str:
    lines = [
        "cross_dataset_summary:",
        "",
        "organizations_in_multiple_datasets:",
        str(len(rows)),
    ]
    for row in rows:
        lines.extend(
            [
                "",
                "organization:",
                row.organization_name,
                "",
                "datasets:",
                "",
                *[f"* {dataset_display_name(dataset)}" for dataset in row.datasets],
                "",
                f"lobby_meetings:",
                str(row.lobby_meetings),
                "",
                "contracts:",
                str(row.contracts),
                "",
                "relationships:",
                str(row.relationships),
                "",
                "evidence:",
                str(row.evidence),
            ]
        )
    return "\n".join(lines)


def render_cross_dataset_connections_text(row: CrossDatasetOrganizationSummary) -> str:
    lines = [
        row.organization_name,
        "",
        "Lobby connections:",
    ]
    lines.extend(f"* {connection.name}" for connection in row.lobby_connections)
    if not row.lobby_connections:
        lines.append("* No lobby connections available")
    lines.extend(["", "Procurement connections:"])
    lines.extend(f"* {connection.name}" for connection in row.procurement_connections)
    if not row.procurement_connections:
        lines.append("* No procurement connections available")
    lines.extend(["", row.explanation])
    return "\n".join(lines)


def _organization_ids_in_multiple_datasets(session: Session) -> tuple[UUID, ...]:
    rows = session.execute(
        select(Entity.id, Dataset.name)
        .select_from(Claim)
        .join(Entity, Claim.subject_entity_id == Entity.id)
        .join(SourceRecord, Claim.source_record_id == SourceRecord.id)
        .join(Dataset, SourceRecord.dataset_id == Dataset.id)
        .where(Entity.entity_type == "PUBLIC_ORGANIZATION")
    ).all()
    grouped: dict[UUID, set[str]] = {}
    for entity_id, dataset_name in rows:
        dataset = _dataset_group(str(dataset_name))
        if dataset is not None:
            grouped.setdefault(entity_id, set()).add(dataset)
    return tuple(entity_id for entity_id, datasets in grouped.items() if len(datasets) > 1)


def _datasets_for_entity(session: Session, entity_id: UUID) -> set[str]:
    rows = session.execute(
        select(distinct(Dataset.name))
        .select_from(Claim)
        .join(SourceRecord, Claim.source_record_id == SourceRecord.id)
        .join(Dataset, SourceRecord.dataset_id == Dataset.id)
        .where(or_(Claim.subject_entity_id == entity_id, Claim.object_entity_id == entity_id))
    ).all()
    return {
        dataset
        for (dataset_name,) in rows
        if (dataset := _dataset_group(str(dataset_name))) is not None
    }


def _claim_ids_for_entity(session: Session, entity_id: UUID) -> tuple[UUID, ...]:
    return tuple(
        session.scalars(
            select(Claim.id).where(or_(Claim.subject_entity_id == entity_id, Claim.object_entity_id == entity_id))
        ).all()
    )


def _count_distinct_claim_objects(
    session: Session,
    entity_id: UUID,
    predicate: str,
    *,
    dataset_group: str,
) -> int:
    rows = session.execute(
        select(distinct(Claim.object_entity_id), Dataset.name)
        .select_from(Claim)
        .join(SourceRecord, Claim.source_record_id == SourceRecord.id)
        .join(Dataset, SourceRecord.dataset_id == Dataset.id)
        .where(Claim.subject_entity_id == entity_id, Claim.predicate == predicate)
    ).all()
    return sum(
        1
        for object_entity_id, dataset_name in rows
        if object_entity_id is not None and _dataset_group(str(dataset_name)) == dataset_group
    )


def _count_evidence(session: Session, entity_id: UUID, claim_ids: tuple[UUID, ...]) -> int:
    involved_claim_ids = _cross_dataset_claim_ids(session, entity_id, claim_ids)
    if not involved_claim_ids:
        return 0

    source_record_ids = _source_record_ids_for_claims(session, involved_claim_ids)
    evidence_ids: set[UUID] = set()
    evidence_ids.update(_claim_evidence_ids(session, involved_claim_ids))
    evidence_ids.update(_evidence_ids_for_claims(session, involved_claim_ids))
    evidence_ids.update(_evidence_ids_for_source_records(session, source_record_ids))
    return len(evidence_ids)


def _cross_dataset_claim_ids(session: Session, entity_id: UUID, claim_ids: tuple[UUID, ...]) -> tuple[UUID, ...]:
    collected: set[UUID] = set(claim_ids)
    collected.update(
        session.scalars(
            select(RelationshipPublic.claim_id).where(
                or_(
                    RelationshipPublic.source_entity_id == entity_id,
                    RelationshipPublic.target_entity_id == entity_id,
                    RelationshipPublic.claim_id.in_(claim_ids) if claim_ids else False,
                )
            )
        ).all()
    )
    meeting_ids = tuple(
        session.scalars(
            select(Claim.object_entity_id).where(
                Claim.subject_entity_id == entity_id,
                Claim.predicate == LOBBY_ORGANIZATION_PREDICATE,
            )
        ).all()
    )
    if meeting_ids:
        collected.update(
            session.scalars(
                select(RelationshipPublic.claim_id).where(
                    RelationshipPublic.target_entity_id.in_(meeting_ids),
                    RelationshipPublic.relationship_type == LOBBY_COUNTERPARTY_PREDICATE,
                )
            ).all()
        )
    contract_ids = tuple(
        session.scalars(
            select(Claim.object_entity_id).where(
                Claim.subject_entity_id == entity_id,
                Claim.predicate == PROCUREMENT_ORGANIZATION_PREDICATE,
            )
        ).all()
    )
    if contract_ids:
        collected.update(
            session.scalars(
                select(RelationshipPublic.claim_id).where(
                    RelationshipPublic.target_entity_id.in_(contract_ids),
                    RelationshipPublic.relationship_type == PROCUREMENT_SUPPLIER_PREDICATE,
                )
            ).all()
        )
    return tuple(sorted(collected, key=str))


def _source_record_ids_for_claims(session: Session, claim_ids: tuple[UUID, ...]) -> tuple[UUID, ...]:
    if not claim_ids:
        return ()
    return tuple(
        source_record_id
        for source_record_id in session.scalars(
            select(distinct(Claim.source_record_id)).where(Claim.id.in_(claim_ids))
        ).all()
        if source_record_id is not None
    )


def _claim_evidence_ids(session: Session, claim_ids: tuple[UUID, ...]) -> tuple[UUID, ...]:
    if not claim_ids:
        return ()
    return tuple(
        evidence_id
        for evidence_id in session.scalars(
            select(distinct(Claim.evidence_id)).where(Claim.id.in_(claim_ids))
        ).all()
        if evidence_id is not None
    )


def _evidence_ids_for_claims(session: Session, claim_ids: tuple[UUID, ...]) -> tuple[UUID, ...]:
    if not claim_ids:
        return ()
    return tuple(
        evidence_id
        for evidence_id in session.scalars(
            select(distinct(Evidence.id)).where(Evidence.claim_id.in_(claim_ids))
        ).all()
        if evidence_id is not None
    )


def _evidence_ids_for_source_records(session: Session, source_record_ids: tuple[UUID, ...]) -> tuple[UUID, ...]:
    if not source_record_ids:
        return ()
    return tuple(
        evidence_id
        for evidence_id in session.scalars(
            select(distinct(Evidence.id)).where(Evidence.source_record_id.in_(source_record_ids))
        ).all()
        if evidence_id is not None
    )


def _count_relationships(session: Session, entity_id: UUID, claim_ids: tuple[UUID, ...]) -> int:
    relationship_ids = set(
        session.scalars(
            select(RelationshipPublic.id).where(
                or_(
                    RelationshipPublic.source_entity_id == entity_id,
                    RelationshipPublic.target_entity_id == entity_id,
                    RelationshipPublic.claim_id.in_(claim_ids) if claim_ids else False,
                )
            )
        ).all()
    )
    meeting_ids = tuple(
        session.scalars(
            select(Claim.object_entity_id).where(
                Claim.subject_entity_id == entity_id,
                Claim.predicate == LOBBY_ORGANIZATION_PREDICATE,
            )
        ).all()
    )
    if meeting_ids:
        relationship_ids.update(
            session.scalars(
                select(RelationshipPublic.id).where(
                    RelationshipPublic.target_entity_id.in_(meeting_ids),
                    RelationshipPublic.relationship_type == LOBBY_COUNTERPARTY_PREDICATE,
                )
            ).all()
        )
    contract_ids = tuple(
        session.scalars(
            select(Claim.object_entity_id).where(
                Claim.subject_entity_id == entity_id,
                Claim.predicate == PROCUREMENT_ORGANIZATION_PREDICATE,
            )
        ).all()
    )
    if contract_ids:
        relationship_ids.update(
            session.scalars(
                select(RelationshipPublic.id).where(
                    RelationshipPublic.target_entity_id.in_(contract_ids),
                    RelationshipPublic.relationship_type == PROCUREMENT_SUPPLIER_PREDICATE,
                )
            ).all()
        )
    return len(relationship_ids)


def _lobby_connections(session: Session, organization_id: UUID) -> tuple[CrossDatasetConnection, ...]:
    meeting_ids = tuple(
        session.scalars(
            select(Claim.object_entity_id).where(
                Claim.subject_entity_id == organization_id,
                Claim.predicate == LOBBY_ORGANIZATION_PREDICATE,
            )
        ).all()
    )
    if not meeting_ids:
        return ()
    relationships = session.scalars(
        select(RelationshipPublic)
        .where(
            RelationshipPublic.target_entity_id.in_(meeting_ids),
            RelationshipPublic.relationship_type == LOBBY_COUNTERPARTY_PREDICATE,
        )
        .options(joinedload(RelationshipPublic.source_entity))
        .order_by(RelationshipPublic.created_at, RelationshipPublic.id)
    ).all()
    return _unique_connections(
        CrossDatasetConnection(
            entity_id=str(relationship.source_entity.id),
            entity_type=relationship.source_entity.entity_type,
            name=relationship.source_entity.name,
            relationship_type=relationship.relationship_type,
        )
        for relationship in relationships
        if relationship.source_entity_id != organization_id
    )


def _procurement_connections(session: Session, organization_id: UUID) -> tuple[CrossDatasetConnection, ...]:
    contract_ids = tuple(
        session.scalars(
            select(Claim.object_entity_id).where(
                Claim.subject_entity_id == organization_id,
                Claim.predicate == PROCUREMENT_ORGANIZATION_PREDICATE,
            )
        ).all()
    )
    if not contract_ids:
        return ()
    relationships = session.scalars(
        select(RelationshipPublic)
        .where(
            RelationshipPublic.target_entity_id.in_(contract_ids),
            RelationshipPublic.relationship_type == PROCUREMENT_SUPPLIER_PREDICATE,
        )
        .options(joinedload(RelationshipPublic.source_entity))
        .order_by(RelationshipPublic.created_at, RelationshipPublic.id)
    ).all()
    return _unique_connections(
        CrossDatasetConnection(
            entity_id=str(relationship.source_entity.id),
            entity_type=relationship.source_entity.entity_type,
            name=relationship.source_entity.name,
            relationship_type=relationship.relationship_type,
        )
        for relationship in relationships
        if relationship.source_entity_id != organization_id
    )


def _unique_connections(connections) -> tuple[CrossDatasetConnection, ...]:  # noqa: ANN001
    unique: dict[str, CrossDatasetConnection] = {}
    for connection in connections:
        unique.setdefault(connection.entity_id, connection)
    return tuple(sorted(unique.values(), key=lambda item: (item.name.lower(), item.entity_id)))


def _dataset_group(dataset_name: str) -> str | None:
    cleaned = dataset_name.strip()
    if not cleaned:
        return None
    if dataset_group := _dataset_group_from_registry(cleaned):
        return dataset_group
    normalized = cleaned.lower()
    if normalized.startswith("chilecompra"):
        return "chilecompra"
    if "lobby" in normalized:
        return "lobby"
    if "transparencia" in normalized:
        return "transparencia"
    if "contraloria" in normalized:
        return "contraloria"
    if "municipal" in normalized:
        return "municipalidades"
    return None


def _dataset_group_from_registry(dataset_name: str) -> str | None:
    rows = (
        (definition.dataset_slug, definition.dataset_names, definition.source_names, definition.aliases)
        for definition in _dataset_catalog()
    )
    cleaned = dataset_name.strip().lower()
    for slug, dataset_names, source_names, aliases in rows:
        if cleaned == slug.lower():
            return slug
        if cleaned in {name.lower() for name in dataset_names}:
            return slug
        if cleaned in {name.lower() for name in source_names}:
            return slug
        if cleaned in {alias.lower() for alias in aliases}:
            return slug
    return None


def _dataset_catalog():
    from datosenorden.datasets import dataset_catalog

    return dataset_catalog()


_ORIGINAL_CITIZEN_FRIENDLY_EXPLANATION = citizen_friendly_explanation
_ORIGINAL_DATASET_GROUP = _dataset_group


def citizen_friendly_explanation() -> str:  # type: ignore[override]
    return "\n".join(
        [
            "This organization appears in more than one public dataset.",
            "",
            "The available records show:",
            "* procurement activity in ChileCompra",
            "* registered lobby meetings",
            "* administrative role records in Transparencia Activa when sample data is loaded",
            "* elected authority records and electoral periods in SERVEL when sample data is loaded",
            "* additional local prototype datasets when they are loaded",
            "* public relationships and supporting evidence",
            "",
            "The platform only presents stored records and does not imply any relationship beyond the available public information.",
        ]
    )


def _dataset_group(dataset_name: str) -> str | None:  # type: ignore[override]
    cleaned = dataset_name.strip()
    if not cleaned:
        return None
    if dataset_group := _dataset_group_from_registry(cleaned):
        return dataset_group
    normalized = cleaned.lower()
    if normalized.startswith("chilecompra"):
        return "chilecompra"
    if "lobby" in normalized:
        return "lobby"
    if "transparencia" in normalized:
        return "transparencia"
    if "contraloria" in normalized:
        return "contraloria"
    if "municipal" in normalized:
        return "municipalidades"
    if "servel" in normalized:
        return "servel"
    return None
