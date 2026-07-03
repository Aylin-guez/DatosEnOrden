from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from datosenorden.maintenance.cross_dataset_explorer import _dataset_group
from datosenorden.maintenance.explanations import dataset_display_name
from datosenorden.maintenance.explanations import graph_explanation_for_chain
from datosenorden.maintenance.entity_explorer import EntityGraphNodeSummary
from datosenorden.maintenance.entity_explorer import EntityProfile
from datosenorden.maintenance.entity_explorer import build_entity_graph
from datosenorden.maintenance.entity_explorer import get_entity_profile
from datosenorden.maintenance.human_readable import entity_type_display_label
from datosenorden.maintenance.timeline_explorer import EntityTimeline
from datosenorden.maintenance.timeline_explorer import build_entity_timeline
from datosenorden.models import Claim, Dataset, Evidence, RelationshipPublic, SourceRecord

PROCUREMENT_PREDICATES = {
    "ISSUES_PURCHASE_ORDER",
    "RECEIVES_CONTRACT",
    "PUBLISHED_TENDER",
    "AWARDS_CONTRACT",
}
LOBBY_PREDICATES = {
    "ORGANIZATION_HELD_LOBBY_MEETING",
    "COUNTERPARTY_PARTICIPATED_IN_LOBBY",
    "LOBBY_MEETING_ABOUT_SUBJECT",
}
TRANSPARENCIA_PREDICATES = {
    "ORGANIZATION_HAS_PUBLIC_ROLE",
    "PERSON_HOLDS_PUBLIC_ROLE",
    "ROLE_BELONGS_TO_ORGANIZATION",
    "PERSON_APPOINTED_TO_PUBLIC_OFFICE",
    "PERSON_RESIGNED_FROM_PUBLIC_OFFICE",
    "PUBLIC_OFFICE_BELONGS_TO_ORGANIZATION",
}
REGISTRY_PREDICATES = {
    "PERSON_REPRESENTS_COMPANY",
    "PERSON_OWNS_COMPANY",
    "COMPANY_REGISTERED_ON",
    "COMPANY_MODIFIED_ON",
}

@dataclass(frozen=True)
class InvestigationEvidenceLink:
    title: str
    url: str
    published_at: date | None


@dataclass(frozen=True)
class InvestigationProcurementItem:
    dataset: str
    contract_name: str
    supplier: str
    evidence_count: int
    evidence_links: tuple[InvestigationEvidenceLink, ...]


@dataclass(frozen=True)
class InvestigationLobbyItem:
    dataset: str
    date: date | None
    organization: str
    counterparty: str
    subject: str
    evidence_count: int
    evidence_links: tuple[InvestigationEvidenceLink, ...]


@dataclass(frozen=True)
class InvestigationRoleItem:
    dataset: str
    holder: str
    role_title: str
    period: str
    evidence_count: int
    evidence_links: tuple[InvestigationEvidenceLink, ...]


@dataclass(frozen=True)
class InvestigationRegistryItem:
    dataset: str
    company: str
    person: str
    relation: str
    rut: str
    status: str
    ownership_percentage: str
    evidence_count: int
    evidence_links: tuple[InvestigationEvidenceLink, ...]


@dataclass(frozen=True)
class InvestigationEvidenceGroup:
    dataset: str
    links: tuple[InvestigationEvidenceLink, ...]


@dataclass(frozen=True)
class InvestigationSourceRecordItem:
    id: str
    external_id: str
    record_type: str
    source: str
    dataset: str
    official_url: str
    retrieved_at: str


@dataclass(frozen=True)
class InvestigationLegislativeVoteItem:
    dataset: str
    vote_id: str
    date: date | None
    source: str
    official_url: str
    evidence_count: int
    evidence_links: tuple[InvestigationEvidenceLink, ...]


@dataclass(frozen=True)
class InvestigationMetrics:
    contracts: int
    suppliers: int
    lobby_meetings: int
    public_roles: int
    evidence: int
    relationships: int
    datasets_involved: int = 0
    connected_entities: int = 0


@dataclass(frozen=True)
class InvestigationView:
    profile: EntityProfile
    entity_type_label: str
    summary: str
    dataset_badges: tuple[str, ...]
    metrics: InvestigationMetrics
    timeline: EntityTimeline | None
    graph: EntityGraphNodeSummary | None
    graph_explanation: str
    procurement_items: tuple[InvestigationProcurementItem, ...]
    lobby_items: tuple[InvestigationLobbyItem, ...]
    role_items: tuple[InvestigationRoleItem, ...]
    registry_items: tuple[InvestigationRegistryItem, ...]
    evidence_groups: tuple[InvestigationEvidenceGroup, ...]
    explanation: str
    source_records: tuple[InvestigationSourceRecordItem, ...] = ()
    legislative_vote_items: tuple[InvestigationLegislativeVoteItem, ...] = ()


def build_investigation_view(session: Session, entity_id: str) -> InvestigationView | None:
    if not _is_uuid(entity_id):
        return None
    profile = get_entity_profile(session, entity_id)
    if profile is None:
        return None

    entity = profile.entity
    claims = _load_entity_claims(session, entity.id)
    claim_ids = tuple(str(claim.id) for claim in claims)
    source_record_ids = tuple({claim.source_record_id for claim in claims})
    source_record_claims = _load_source_record_claims(session, source_record_ids)
    evidence_by_claim = _evidence_links_by_claim(session, claim_ids)
    evidence_groups = _group_evidence_by_dataset(session, claim_ids)
    dataset_badges = _dataset_badges_for_claims(claims)
    procurement_items = _procurement_items(session, claims, evidence_by_claim)
    lobby_items = _lobby_items(source_record_claims, evidence_by_claim, selected_entity_id=entity.id)
    role_items = _role_items(claims, evidence_by_claim)
    registry_items = _registry_items(claims, evidence_by_claim)
    source_records = _source_record_items(session, source_record_ids)
    legislative_vote_items = _legislative_vote_items(claims, evidence_by_claim)
    timeline = build_entity_timeline(session, entity_id)
    graph = build_entity_graph(session, entity_id, depth=1)
    graph_explanation = _graph_explanation_text(graph)

    evidence_count = sum(len(group.links) for group in evidence_groups)
    summary = _summary_text(entity.name, dataset_badges)
    metrics = InvestigationMetrics(
        contracts=len(procurement_items),
        suppliers=len({item.supplier for item in procurement_items if item.supplier}),
        lobby_meetings=len(lobby_items),
        public_roles=len(role_items),
        evidence=evidence_count,
        relationships=len(profile.relationships),
        datasets_involved=len(dataset_badges),
        connected_entities=len(profile.direct_neighbors),
    )

    return InvestigationView(
        profile=profile,
        entity_type_label=entity_type_display_label(entity.entity_type),
        summary=summary,
        dataset_badges=dataset_badges,
        metrics=metrics,
        timeline=timeline,
        graph=graph,
        graph_explanation=graph_explanation,
        procurement_items=procurement_items,
        lobby_items=lobby_items,
        role_items=role_items,
        registry_items=registry_items,
        evidence_groups=evidence_groups,
        explanation=_investigation_explanation_text(),
        source_records=source_records,
        legislative_vote_items=legislative_vote_items,
    )


def investigation_summary_text(view: InvestigationView) -> str:
    return view.summary


def _is_uuid(value: str) -> bool:
    try:
        UUID(str(value))
    except (TypeError, ValueError):
        return False
    return True


def investigation_explanation_text() -> str:
    return _investigation_explanation_text()


def _summary_text(entity_name: str, dataset_badges: tuple[str, ...]) -> str:
    if dataset_badges:
        datasets = ", ".join(dataset_badges)
        return (
            f"Esta vista reúne la información pública guardada para {entity_name} en {datasets}. "
            "No interpreta causalidad ni intención."
        )
    return (
        f"Esta vista reúne la información pública guardada para {entity_name} en las fuentes disponibles. "
        "No interpreta causalidad ni intención."
    )


def _investigation_explanation_text() -> str:
    return "\n".join(
        [
            "Esta página muestra una sola entidad con sus contratos, reuniones, roles, evidencia y cronología.",
            "No afirma causalidad, irregularidad ni intención.",
            "La evidencia importa porque permite revisar el origen de cada registro.",
        ]
    )


def _graph_explanation_text(graph: EntityGraphNodeSummary | None) -> str:
    if graph is None:
        return "No hay grafo disponible para esta entidad."
    return graph_explanation_for_chain(_graph_chain(graph))


def _load_entity_claims(session: Session, entity_id: UUID) -> tuple[Claim, ...]:
    return tuple(
        session.scalars(
            select(Claim)
            .where(or_(Claim.subject_entity_id == entity_id, Claim.object_entity_id == entity_id))
            .options(
                joinedload(Claim.subject_entity),
                joinedload(Claim.object_entity),
                joinedload(Claim.source_record).joinedload(SourceRecord.dataset),
            )
            .order_by(Claim.created_at, Claim.id)
        ).all()
    )


def _load_source_record_claims(session: Session, source_record_ids: tuple[UUID, ...]) -> tuple[Claim, ...]:
    if not source_record_ids:
        return ()
    return tuple(
        session.scalars(
            select(Claim)
            .where(Claim.source_record_id.in_(source_record_ids))
            .options(
                joinedload(Claim.subject_entity),
                joinedload(Claim.object_entity),
                joinedload(Claim.source_record).joinedload(SourceRecord.dataset),
            )
            .order_by(Claim.created_at, Claim.id)
        ).all()
    )


def _dataset_badges_for_claims(claims: tuple[Claim, ...]) -> tuple[str, ...]:
    badges: list[str] = []
    seen: set[str] = set()
    for claim in claims:
        dataset_name = _dataset_group(str(claim.source_record.dataset.name)) if claim.source_record.dataset is not None else None
        if dataset_name is None or dataset_name in seen:
            continue
        seen.add(dataset_name)
        badges.append(dataset_display_name(dataset_name))
    return tuple(badges)


def _source_record_items(session: Session, source_record_ids: tuple[UUID, ...]) -> tuple[InvestigationSourceRecordItem, ...]:
    if not source_record_ids:
        return ()
    rows = session.scalars(
        select(SourceRecord)
        .where(SourceRecord.id.in_(source_record_ids))
        .options(joinedload(SourceRecord.source), joinedload(SourceRecord.dataset))
        .order_by(SourceRecord.retrieved_at.asc(), SourceRecord.external_id.asc(), SourceRecord.id.asc())
    ).all()
    return tuple(
        InvestigationSourceRecordItem(
            id=str(row.id),
            external_id=row.external_id,
            record_type=row.record_type,
            source=row.source.name if row.source is not None else "",
            dataset=dataset_display_name(str(row.dataset.name)) if row.dataset is not None else "",
            official_url=_official_url_from_source_record(row),
            retrieved_at=row.retrieved_at.isoformat() if row.retrieved_at is not None else "",
        )
        for row in rows
    )


def _official_url_from_source_record(row: SourceRecord) -> str:
    payload = row.raw_payload or {}
    if row.record_type == "legislature:vote":
        vote_id = str(payload.get("source_id", "") or row.external_id).removeprefix("camara-votacion-")
        if vote_id:
            return f"https://opendata.camara.cl/services/getVotacion_Detalle?prmVotacionID={vote_id}"
    if isinstance(payload, dict):
        request = payload.get("request", {})
        if isinstance(request, dict) and request.get("url"):
            return str(request["url"])
    return ""


def _evidence_links_by_claim(session: Session, claim_ids: tuple[str, ...]) -> dict[str, tuple[InvestigationEvidenceLink, ...]]:
    if not claim_ids:
        return {}
    uuids = tuple(UUID(claim_id) for claim_id in claim_ids)
    rows = session.execute(
        select(Claim.id, Evidence.title, Evidence.url, Evidence.published_at)
        .select_from(Evidence)
        .join(Claim, Evidence.claim_id == Claim.id)
        .order_by(Evidence.created_at, Evidence.id)
        .where(Claim.id.in_(uuids))
    ).all()
    grouped: dict[str, list[InvestigationEvidenceLink]] = defaultdict(list)
    for claim_id, title, url, published_at in rows:
        grouped[str(claim_id)].append(
            InvestigationEvidenceLink(
                title=str(title),
                url=str(url),
                published_at=published_at,
            )
        )
    return {claim_id: tuple(links) for claim_id, links in grouped.items()}


def _group_evidence_by_dataset(session: Session, claim_ids: tuple[str, ...]) -> tuple[InvestigationEvidenceGroup, ...]:
    if not claim_ids:
        return ()
    uuids = tuple(UUID(claim_id) for claim_id in claim_ids)
    rows = session.execute(
        select(Dataset.name, Evidence.id, Evidence.title, Evidence.url, Evidence.published_at)
        .select_from(Evidence)
        .join(Claim, Evidence.claim_id == Claim.id)
        .join(SourceRecord, Claim.source_record_id == SourceRecord.id)
        .join(Dataset, SourceRecord.dataset_id == Dataset.id)
        .where(Claim.id.in_(uuids))
        .order_by(Dataset.name.asc(), Evidence.created_at.asc(), Evidence.id.asc())
    ).all()
    grouped: dict[str, dict[str, InvestigationEvidenceLink]] = defaultdict(dict)
    for dataset_name, evidence_id, title, url, published_at in rows:
        dataset_group = _dataset_group(str(dataset_name)) or str(dataset_name)
        grouped[dataset_group][str(evidence_id)] = InvestigationEvidenceLink(
            title=str(title),
            url=str(url),
            published_at=published_at,
        )
    return tuple(
        InvestigationEvidenceGroup(
            dataset=dataset_display_name(dataset),
            links=tuple(links.values()),
        )
        for dataset, links in sorted(grouped.items(), key=lambda item: item[0])
    )


def _procurement_items(
    session: Session,
    claims: tuple[Claim, ...],
    evidence_by_claim: dict[str, tuple[InvestigationEvidenceLink, ...]],
) -> tuple[InvestigationProcurementItem, ...]:
    items: list[InvestigationProcurementItem] = []
    for claim in claims:
        if claim.predicate not in PROCUREMENT_PREDICATES:
            continue
        dataset = _dataset_group(str(claim.source_record.dataset.name))
        if dataset is None:
            continue
        supplier = _supplier_for_contract(session, claim)
        contract_name = _contract_name_for_claim(claim)
        items.append(
            InvestigationProcurementItem(
                dataset=dataset_display_name(dataset),
                contract_name=contract_name,
                supplier=supplier,
                evidence_count=len(evidence_by_claim.get(str(claim.id), ())),
                evidence_links=evidence_by_claim.get(str(claim.id), ()),
            )
        )
    return tuple(items)


def _lobby_items(
    claims: tuple[Claim, ...],
    evidence_by_claim: dict[str, tuple[InvestigationEvidenceLink, ...]],
    *,
    selected_entity_id: UUID,
) -> tuple[InvestigationLobbyItem, ...]:
    claims_by_source_record: dict[UUID, list[Claim]] = defaultdict(list)
    for claim in claims:
        claims_by_source_record[claim.source_record_id].append(claim)

    items: list[InvestigationLobbyItem] = []
    for claim in claims:
        if claim.predicate != "ORGANIZATION_HELD_LOBBY_MEETING" and claim.predicate != "COUNTERPARTY_PARTICIPATED_IN_LOBBY":
            continue
        dataset = _dataset_group(str(claim.source_record.dataset.name))
        if dataset is None:
            continue
        sibling_claims = claims_by_source_record.get(claim.source_record_id, [])
        organization_name = ""
        counterparty_name = ""
        subject = ""
        for sibling in sibling_claims:
            if sibling.predicate == "ORGANIZATION_HELD_LOBBY_MEETING" and not organization_name:
                organization_name = sibling.subject_entity.name
            if sibling.predicate == "COUNTERPARTY_PARTICIPATED_IN_LOBBY" and not counterparty_name:
                counterparty_name = sibling.subject_entity.name
            if sibling.predicate == "LOBBY_MEETING_ABOUT_SUBJECT" and not subject:
                subject = _subject_from_object_value(sibling)
        if claim.subject_entity_id != selected_entity_id:
            continue
        if not organization_name:
            organization_name = claim.subject_entity.name
        if not counterparty_name:
            counterparty_name = _counterparty_from_lobby_claim(claim)
        if not subject:
            subject = _subject_from_object_value(claim)
        items.append(
            InvestigationLobbyItem(
                dataset=dataset_display_name(dataset),
                date=claim.valid_from,
                organization=organization_name,
                counterparty=counterparty_name,
                subject=subject,
                evidence_count=len(evidence_by_claim.get(str(claim.id), ())),
                evidence_links=evidence_by_claim.get(str(claim.id), ()),
            )
        )
    return tuple(items)


def _role_items(
    claims: tuple[Claim, ...],
    evidence_by_claim: dict[str, tuple[InvestigationEvidenceLink, ...]],
) -> tuple[InvestigationRoleItem, ...]:
    items: list[InvestigationRoleItem] = []
    for claim in claims:
        if claim.predicate not in TRANSPARENCIA_PREDICATES:
            continue
        dataset = _dataset_group(str(claim.source_record.dataset.name))
        if dataset is None:
            continue
        items.append(
            InvestigationRoleItem(
                dataset=dataset_display_name(dataset),
                holder=claim.subject_entity.name,
                role_title=_role_title_from_object_entity(claim),
                period=_role_period_from_object_value(claim),
                evidence_count=len(evidence_by_claim.get(str(claim.id), ())),
                evidence_links=evidence_by_claim.get(str(claim.id), ()),
            )
        )
    return tuple(items)


def _supplier_for_contract(session: Session, claim: Claim) -> str:
    contract_entity = claim.object_entity
    if contract_entity is None:
        return claim.subject_entity.name
    relationship_rows = session.scalars(
        select(RelationshipPublic)
        .where(RelationshipPublic.target_entity_id == contract_entity.id)
        .options(joinedload(RelationshipPublic.source_entity))
        .order_by(RelationshipPublic.created_at, RelationshipPublic.id)
    ).all()
    for relationship in relationship_rows:
        if relationship.source_entity is not None and relationship.source_entity.entity_type == "COMPANY":
            return relationship.source_entity.name
    return claim.subject_entity.name


def _contract_name_for_claim(claim: Claim) -> str:
    if claim.object_entity is not None and claim.object_entity.name.strip():
        return claim.object_entity.name
    return _object_value_text(claim, "purchase_order_name", default=claim.subject_entity.name)


def _subject_from_object_value(claim: Claim) -> str:
    return _object_value_text(claim, "meeting_subject", default=claim.object_entity.name if claim.object_entity is not None else claim.subject_entity.name)


def _counterparty_from_lobby_claim(claim: Claim) -> str:
    if claim.subject_entity.name.strip():
        return claim.subject_entity.name
    return _object_value_text(claim, "counterparty_name", default="")


def _role_title_from_object_entity(claim: Claim) -> str:
    if claim.object_entity is None:
        return _object_value_text(claim, "role_title", default="Cargo público")
    name = claim.object_entity.name
    if " - " in name:
        return name.split(" - ", 1)[0].strip()
    if "(" in name:
        return name.rsplit("(", 1)[0].strip()
    return name


def _role_period_from_object_value(claim: Claim) -> str:
    return _object_value_text(claim, "period", default=_format_date(claim.valid_from))


def _object_value_text(claim: Claim, key: str, *, default: str) -> str:
    value = claim.object_value or {}
    if isinstance(value, dict) and value.get(key) is not None:
        return str(value[key])
    return default


def _graph_chain(root: EntityGraphNodeSummary) -> tuple[str, ...]:
    chain = [root.entity.entity_type]
    current = root
    seen = {root.entity.id}
    while current.children:
        next_node = current.children[0]
        if next_node.entity.id in seen:
            break
        chain.append(next_node.entity.entity_type)
        seen.add(next_node.entity.id)
        current = next_node
    return tuple(chain)


def _format_date(value: date | None) -> str:
    return value.isoformat() if value is not None else "Sin fecha"


SERVEL_PREDICATES = {"AUTHORITY_ELECTED_TO_OFFICE"}
DIARIO_OFICIAL_PREDICATES = {
    "DECREE_APPLIES_TO_ORGANIZATION",
    "OFFICIAL_PUBLICATION_REFERENCES_ENTITY",
}
ROLE_PREDICATES = TRANSPARENCIA_PREDICATES | SERVEL_PREDICATES | DIARIO_OFICIAL_PREDICATES

_ORIGINAL_SUMMARY_TEXT = _summary_text
_ORIGINAL_ROLE_ITEMS = _role_items
_ORIGINAL_ROLE_PERIOD_FROM_OBJECT_VALUE = _role_period_from_object_value


def _summary_text(entity_name: str, dataset_badges: tuple[str, ...]) -> str:  # type: ignore[override]
    if any(dataset.upper() == "SERVEL" for dataset in dataset_badges):
        return (
            f"Esta vista reune la informacion publica guardada para {entity_name} en {', '.join(dataset_badges)}. "
            "No interpreta causalidad ni intencion."
        )
    return _ORIGINAL_SUMMARY_TEXT(entity_name, dataset_badges)


def _role_period_from_object_value(claim: Claim) -> str:  # type: ignore[override]
    return _object_value_text(
        claim,
        "period_label",
        default=_ORIGINAL_ROLE_PERIOD_FROM_OBJECT_VALUE(claim),
    )


def _role_items(
    claims: tuple[Claim, ...],
    evidence_by_claim: dict[str, tuple[InvestigationEvidenceLink, ...]],
) -> tuple[InvestigationRoleItem, ...]:  # type: ignore[override]
    items: list[InvestigationRoleItem] = []
    for claim in claims:
        if claim.predicate not in ROLE_PREDICATES:
            continue
        dataset = _dataset_group(str(claim.source_record.dataset.name))
        if dataset is None:
            continue
        items.append(
            InvestigationRoleItem(
                dataset=dataset_display_name(dataset),
                holder=claim.subject_entity.name,
                role_title=_role_title_from_object_entity(claim),
                period=_role_period_from_object_value(claim),
                evidence_count=len(evidence_by_claim.get(str(claim.id), ())),
                evidence_links=evidence_by_claim.get(str(claim.id), ()),
            )
        )
    return tuple(items)


def _registry_items(
    claims: tuple[Claim, ...],
    evidence_by_claim: dict[str, tuple[InvestigationEvidenceLink, ...]],
) -> tuple[InvestigationRegistryItem, ...]:
    items: list[InvestigationRegistryItem] = []
    for claim in claims:
        if claim.predicate not in REGISTRY_PREDICATES:
            continue
        dataset = _dataset_group(str(claim.source_record.dataset.name))
        if dataset is None:
            continue
        object_entity = claim.object_entity
        company_name = object_entity.name if object_entity is not None else _object_value_text(claim, "company_name", default=claim.subject_entity.name)
        person_name = claim.subject_entity.name if claim.subject_entity is not None else ""
        relation = {
            "PERSON_REPRESENTS_COMPANY": "Representante",
            "PERSON_OWNS_COMPANY": "Socio",
            "COMPANY_REGISTERED_ON": "Inscripcion",
            "COMPANY_MODIFIED_ON": "Modificacion",
        }.get(claim.predicate, claim.predicate.replace("_", " ").title())
        items.append(
            InvestigationRegistryItem(
                dataset=dataset_display_name(dataset),
                company=company_name,
                person=person_name,
                relation=relation,
                rut=_object_value_text(claim, "company_rut", default=_object_value_text(claim, "rut_empresa", default="")),
                status=_object_value_text(claim, "company_status", default=""),
                ownership_percentage=_object_value_text(claim, "percentage_participation", default=""),
                evidence_count=len(evidence_by_claim.get(str(claim.id), ())),
                evidence_links=evidence_by_claim.get(str(claim.id), ()),
            )
        )
    return tuple(items)


def _legislative_vote_items(
    claims: tuple[Claim, ...],
    evidence_by_claim: dict[str, tuple[InvestigationEvidenceLink, ...]],
) -> tuple[InvestigationLegislativeVoteItem, ...]:
    items: list[InvestigationLegislativeVoteItem] = []
    for claim in claims:
        if claim.predicate != "LEGISLATIVE_BILL_HAS_VOTE":
            continue
        dataset = _dataset_group(str(claim.source_record.dataset.name))
        links = evidence_by_claim.get(str(claim.id), ())
        official_url = links[0].url if links else _official_url_from_source_record(claim.source_record)
        items.append(
            InvestigationLegislativeVoteItem(
                dataset=dataset_display_name(dataset or str(claim.source_record.dataset.name)),
                vote_id=_object_value_text(claim, "vote_id", default=claim.source_record.external_id),
                date=claim.valid_from,
                source="Datos Abiertos Legislativos",
                official_url=official_url,
                evidence_count=len(links),
                evidence_links=links,
            )
        )
    return tuple(items)
