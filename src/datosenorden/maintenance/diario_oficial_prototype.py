from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
import json
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from datosenorden.core.config import PROJECT_ROOT
from datosenorden.etl.core.contracts import (
    ClaimRecord,
    DatasetRecord,
    EntityRecord,
    EntityType,
    EvidenceRecord,
    GraphBatch,
    PublicRelationshipRecord,
    RelationshipType,
    SourceInfo,
    SourceRecordPayload,
    WorkflowStatus,
)
from datosenorden.etl.core.hash import stable_json_hash
from datosenorden.etl.core.text import normalized_key
from datosenorden.etl.loaders.graph_loader import GraphLoader
from datosenorden.models import Claim, Entity, Evidence, RelationshipPublic, SourceRecord

LOCAL_TEST_DATA = "LOCAL_TEST_DATA"
NOT_OFFICIAL_DATA = "NOT_OFFICIAL_DATA"
DIARIO_SAMPLE_DATASET_NAME = "diario-oficial-sample"
DIARIO_SAMPLE_SOURCE_NAME = "DatosEnOrden Diario Oficial Sample"
DIARIO_SAMPLE_SOURCE_URL = "local://sample/diario-oficial"
DIARIO_SAMPLE_RECORD_TYPE = "diario_oficial:publication_sample"
DIARIO_SAMPLE_PATH = PROJECT_ROOT / "data" / "sample" / "diario_oficial_sample.json"

PERSON_APPOINTED_TO_PUBLIC_OFFICE_PREDICATE = "PERSON_APPOINTED_TO_PUBLIC_OFFICE"
PERSON_RESIGNED_FROM_PUBLIC_OFFICE_PREDICATE = "PERSON_RESIGNED_FROM_PUBLIC_OFFICE"
DECREE_APPLIES_TO_ORGANIZATION_PREDICATE = "DECREE_APPLIES_TO_ORGANIZATION"
OFFICIAL_PUBLICATION_REFERENCES_ENTITY_PREDICATE = "OFFICIAL_PUBLICATION_REFERENCES_ENTITY"
PUBLIC_OFFICE_BELONGS_TO_ORGANIZATION_PREDICATE = "PUBLIC_OFFICE_BELONGS_TO_ORGANIZATION"


@dataclass(frozen=True)
class DiarioOficialImportResult:
    source_records: int
    claims: int
    evidences: int
    entities: int
    relationship_public: int
    publications: int
    people: int
    offices: int
    organizations: int


@dataclass(frozen=True)
class DiarioOficialSummaryRow:
    publication_id: str
    publication_date: date | None
    publication_number: str
    publication_title: str
    event_kind: str
    person_name: str
    office_name: str
    organization_name: str
    claims: tuple[str, ...]
    relationships: tuple[str, ...]
    evidence: int


@dataclass(frozen=True)
class DiarioOficialSummary:
    publications: int
    people: int
    offices: int
    organizations: int
    relationships: int
    evidence: int
    rows: tuple[DiarioOficialSummaryRow, ...]


def load_diario_oficial_sample_payload(input_path: Path | None = None) -> dict[str, Any]:
    path = input_path or DIARIO_SAMPLE_PATH
    payload = json.loads(path.read_text(encoding="utf-8"))
    _validate_sample_payload(payload)
    return payload


def build_diario_oficial_sample_batch(session: Session, payload: dict[str, Any] | None = None) -> GraphBatch:
    _ = session
    sample = payload or load_diario_oficial_sample_payload()
    records = sample.get("records") or []
    if not records:
        raise ValueError("Diario Oficial sample must include at least one record")

    source_records: list[SourceRecordPayload] = []
    entities: list[EntityRecord] = []
    evidence: list[EvidenceRecord] = []
    claims: list[ClaimRecord] = []
    public_relationships: list[PublicRelationshipRecord] = []

    for record in records:
        parsed = _build_record_components(record)
        source_records.append(parsed["source_record"])
        entities.extend(parsed["entities"])
        evidence.extend(parsed["evidence"])
        claims.extend(parsed["claims"])
        public_relationships.extend(parsed["public_relationships"])

    source = SourceInfo(
        name=DIARIO_SAMPLE_SOURCE_NAME,
        publisher="DatosEnOrden",
        url=DIARIO_SAMPLE_SOURCE_URL,
        license=f"{LOCAL_TEST_DATA} / {NOT_OFFICIAL_DATA}",
        retrieved_at=datetime.now(timezone.utc),
        metadata={
            "dataset": DIARIO_SAMPLE_DATASET_NAME,
            "classification": sample["classification"],
            "official_status": sample["official_status"],
        },
    )
    dataset = DatasetRecord(
        source_name=DIARIO_SAMPLE_SOURCE_NAME,
        name=DIARIO_SAMPLE_DATASET_NAME,
        description=(
            "LOCAL_TEST_DATA / NOT_OFFICIAL_DATA sample used to validate neutral "
            "official publication links"
        ),
        version="local-sample-1",
        dataset_url=f"{DIARIO_SAMPLE_SOURCE_URL}/dataset",
        content_hash=stable_json_hash(sample),
        loaded_at=datetime.now(timezone.utc),
        metadata={
            "dataset": DIARIO_SAMPLE_DATASET_NAME,
            "classification": sample["classification"],
            "official_status": sample["official_status"],
        },
    )
    return GraphBatch(
        source=source,
        dataset=dataset,
        source_records=tuple(source_records),
        entities=tuple(_unique_records(entities, key=lambda item: (item.entity_type.value, item.external_id))),
        evidence=tuple(_unique_records(evidence, key=lambda item: (item.source_record.external_id, item.url))),
        claims=tuple(
            _unique_records(
                claims,
                key=lambda item: (
                    item.subject_entity.entity_type.value,
                    item.subject_entity.external_id,
                    item.predicate,
                    item.object_entity.entity_type.value if item.object_entity is not None else "",
                    item.object_entity.external_id if item.object_entity is not None else "",
                    json.dumps(item.object_value, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                    item.source_record.external_id,
                ),
            )
        ),
        public_relationships=tuple(
            _unique_records(
                public_relationships,
                key=lambda item: (
                    item.source_entity.entity_type.value,
                    item.source_entity.external_id,
                    item.target_entity.entity_type.value,
                    item.target_entity.external_id,
                    item.relationship_type.value,
                    item.claim.source_record.external_id,
                ),
            )
        ),
        raw_count=len(records),
        rejected_count=0,
        errors=(),
    )


def load_diario_oficial_sample(session: Session, input_path: Path | None = None) -> DiarioOficialImportResult:
    payload = load_diario_oficial_sample_payload(input_path)
    batch = build_diario_oficial_sample_batch(session, payload)
    GraphLoader(session).load(batch, dry_run=False)

    return DiarioOficialImportResult(
        source_records=_count_rows(session, SourceRecord),
        claims=_count_rows(session, Claim),
        evidences=_count_rows(session, Evidence),
        entities=_count_rows(session, Entity),
        relationship_public=_count_rows(session, RelationshipPublic),
        publications=_count_source_records(session),
        people=_count_entities(session, EntityType.PERSON.value),
        offices=_count_entities(session, EntityType.ROLE.value),
        organizations=_count_entities(session, EntityType.PUBLIC_ORGANIZATION.value),
    )


def read_diario_oficial_summary(session: Session) -> DiarioOficialSummary:
    rows = _load_diario_oficial_rows(session)
    publications = {row.publication_id for row in rows}
    people = {row.person_name for row in rows if row.person_name}
    offices = {row.office_name for row in rows if row.office_name}
    organizations = {row.organization_name for row in rows if row.organization_name}
    relationships = {relationship for row in rows for relationship in row.relationships}
    return DiarioOficialSummary(
        publications=len(publications),
        people=len(people),
        offices=len(offices),
        organizations=len(organizations),
        relationships=len(relationships),
        evidence=sum(row.evidence for row in rows),
        rows=tuple(sorted(rows, key=lambda item: (item.publication_date or date.min, item.person_name.lower(), item.publication_id))),
    )


def render_diario_oficial_summary_text(summary: DiarioOficialSummary) -> str:
    lines = [
        "diario_oficial_summary:",
        f"  publications={summary.publications}",
        f"  people={summary.people}",
        f"  offices={summary.offices}",
        f"  organizations={summary.organizations}",
        f"  relationships={summary.relationships}",
        f"  evidence={summary.evidence}",
    ]
    if not summary.rows:
        lines.append("  (no diario oficial sample publications found)")
        return "\n".join(lines)
    for row in summary.rows:
        lines.extend(
            [
                "  publication:",
                f"    id={row.publication_id}",
                f"    date={row.publication_date.isoformat() if row.publication_date else 'None'}",
                f"    number={row.publication_number}",
                f"    title={row.publication_title}",
                f"    event_kind={row.event_kind}",
                f"    person={row.person_name}",
                f"    office={row.office_name}",
                f"    organization={row.organization_name}",
            ]
        )
    return "\n".join(lines).rstrip()


def render_diario_oficial_import_result_text(result: DiarioOficialImportResult) -> str:
    return "\n".join(
        [
            "diario_oficial_sample_loaded:",
            f"  source_records={result.source_records}",
            f"  claims={result.claims}",
            f"  evidences={result.evidences}",
            f"  entities={result.entities}",
            f"  relationship_public={result.relationship_public}",
            f"  publications={result.publications}",
            f"  people={result.people}",
            f"  offices={result.offices}",
            f"  organizations={result.organizations}",
        ]
    )


def _build_record_components(record: dict[str, Any]) -> dict[str, Any]:
    external_id = str(record["external_id"])
    publication_date = _parse_date(record.get("publication_date"))
    publication_number = str(record["publication_number"])
    publication_title = str(record["publication_title"])
    document_kind = str(record["document_kind"])
    event_kind = str(record["event_kind"])
    person_name = str(record["person_name"])
    office_name = str(record["office_name"])
    organization_name = str(record["organization_name"])
    decree_number = str(record["decree_number"])
    publication_section = str(record.get("publication_section", ""))
    source_url = str(record["source_url"])

    publisher_entity = EntityRecord(
        entity_type=EntityType.PUBLIC_ORGANIZATION,
        external_id="diario-oficial:publisher",
        name="Diario Oficial",
        description=f"{LOCAL_TEST_DATA} / {NOT_OFFICIAL_DATA} official publication sample publisher.",
        normalized_key=normalized_key("Diario Oficial"),
        metadata={
            "dataset": DIARIO_SAMPLE_DATASET_NAME,
            "document_kind": document_kind,
        },
    )
    person_entity = EntityRecord(
        entity_type=EntityType.PERSON,
        external_id=f"diario-oficial:person:{external_id}",
        name=person_name,
        description=(
            f"{LOCAL_TEST_DATA} / {NOT_OFFICIAL_DATA} official publication sample person record."
        ),
        normalized_key=normalized_key(person_name),
        metadata={
            "dataset": DIARIO_SAMPLE_DATASET_NAME,
            "document_kind": document_kind,
            "event_kind": event_kind,
        },
    )
    office_entity = EntityRecord(
        entity_type=EntityType.ROLE,
        external_id=f"diario-oficial:office:{external_id}",
        name=office_name,
        description=(
            f"{LOCAL_TEST_DATA} / {NOT_OFFICIAL_DATA} public office sample related to {organization_name}."
        ),
        normalized_key=normalized_key(f"{office_name} {organization_name}"),
        metadata={
            "dataset": DIARIO_SAMPLE_DATASET_NAME,
            "organization_name": organization_name,
            "document_kind": document_kind,
        },
    )
    organization_entity = EntityRecord(
        entity_type=EntityType.PUBLIC_ORGANIZATION,
        external_id=f"diario-oficial:organization:{external_id}",
        name=organization_name,
        description=(
            f"{LOCAL_TEST_DATA} / {NOT_OFFICIAL_DATA} organization referenced by an official publication."
        ),
        normalized_key=normalized_key(organization_name),
        metadata={
            "dataset": DIARIO_SAMPLE_DATASET_NAME,
            "document_kind": document_kind,
            "publication_section": publication_section,
        },
    )

    source_record_payload = {
        **record,
        "sample_markers": [LOCAL_TEST_DATA, NOT_OFFICIAL_DATA],
    }
    source_record = SourceRecordPayload(
        external_id=external_id,
        record_type=DIARIO_SAMPLE_RECORD_TYPE,
        payload_hash=stable_json_hash(source_record_payload),
        raw_payload=source_record_payload,
        retrieved_at=datetime.now(timezone.utc),
        status=WorkflowStatus.NORMALIZED,
    )

    appointment_evidence = _build_evidence(
        source_record,
        external_id=f"{external_id}:appointment",
        title=f"Diario Oficial local sample - {publication_title}",
        url=f"{source_url}/appointment",
        excerpt=(
            f"{LOCAL_TEST_DATA} / {NOT_OFFICIAL_DATA} appointment or resignation sample for "
            f"{person_name}."
        ),
        published_at=publication_date,
    )
    office_evidence = _build_evidence(
        source_record,
        external_id=f"{external_id}:office",
        title=f"Diario Oficial local sample - {office_name}",
        url=f"{source_url}/office",
        excerpt=(
            f"{LOCAL_TEST_DATA} / {NOT_OFFICIAL_DATA} public office sample for {office_name}."
        ),
        published_at=publication_date,
    )
    organization_evidence = _build_evidence(
        source_record,
        external_id=f"{external_id}:organization",
        title=f"Diario Oficial local sample - {organization_name}",
        url=f"{source_url}/organization",
        excerpt=(
            f"{LOCAL_TEST_DATA} / {NOT_OFFICIAL_DATA} official publication reference for {organization_name}."
        ),
        published_at=publication_date,
    )
    publication_evidence = _build_evidence(
        source_record,
        external_id=f"{external_id}:publication",
        title=f"Diario Oficial local sample - {publication_number}",
        url=f"{source_url}/publication",
        excerpt=(
            f"{LOCAL_TEST_DATA} / {NOT_OFFICIAL_DATA} official publication sample for {publication_number}."
        ),
        published_at=publication_date,
    )

    appointment_predicate = (
        PERSON_APPOINTED_TO_PUBLIC_OFFICE_PREDICATE if event_kind == "appointment" else PERSON_RESIGNED_FROM_PUBLIC_OFFICE_PREDICATE
    )
    appointment_claim = ClaimRecord(
        subject_entity=person_entity,
        predicate=appointment_predicate,
        object_entity=office_entity,
        source_record=source_record,
        evidence=appointment_evidence,
        object_value={
            "event_kind": event_kind,
            "person_name": person_name,
            "office_name": office_name,
            "organization_name": organization_name,
            "publication_date": publication_date.isoformat() if publication_date else None,
            "publication_number": publication_number,
            "publication_title": publication_title,
            "document_kind": document_kind,
            "decree_number": decree_number,
            "publication_section": publication_section,
            "dataset": DIARIO_SAMPLE_DATASET_NAME,
            "period_label": f"{publication_number} ({publication_date.isoformat() if publication_date else 'sin fecha'})",
        },
        valid_from=publication_date,
        valid_to=publication_date,
        confidence=1.0,
        status=WorkflowStatus.VALIDATED,
        metadata={"dataset": DIARIO_SAMPLE_DATASET_NAME},
    )
    office_claim = ClaimRecord(
        subject_entity=office_entity,
        predicate=PUBLIC_OFFICE_BELONGS_TO_ORGANIZATION_PREDICATE,
        object_entity=organization_entity,
        source_record=source_record,
        evidence=office_evidence,
        object_value={
            "office_name": office_name,
            "organization_name": organization_name,
            "publication_number": publication_number,
            "document_kind": document_kind,
            "dataset": DIARIO_SAMPLE_DATASET_NAME,
        },
        valid_from=publication_date,
        valid_to=publication_date,
        confidence=1.0,
        status=WorkflowStatus.VALIDATED,
        metadata={"dataset": DIARIO_SAMPLE_DATASET_NAME},
    )
    publication_organization_claim = ClaimRecord(
        subject_entity=publisher_entity,
        predicate=DECREE_APPLIES_TO_ORGANIZATION_PREDICATE,
        object_entity=organization_entity,
        source_record=source_record,
        evidence=organization_evidence,
        object_value={
            "publication_number": publication_number,
            "document_kind": document_kind,
            "decree_number": decree_number,
            "organization_name": organization_name,
            "publication_title": publication_title,
            "publication_section": publication_section,
            "publication_date": publication_date.isoformat() if publication_date else None,
            "dataset": DIARIO_SAMPLE_DATASET_NAME,
        },
        valid_from=publication_date,
        valid_to=publication_date,
        confidence=1.0,
        status=WorkflowStatus.VALIDATED,
        metadata={"dataset": DIARIO_SAMPLE_DATASET_NAME},
    )
    publication_reference_claim = ClaimRecord(
        subject_entity=publisher_entity,
        predicate=OFFICIAL_PUBLICATION_REFERENCES_ENTITY_PREDICATE,
        object_entity=person_entity,
        source_record=source_record,
        evidence=publication_evidence,
        object_value={
            "publication_number": publication_number,
            "document_kind": document_kind,
            "person_name": person_name,
            "organization_name": organization_name,
            "publication_title": publication_title,
            "publication_section": publication_section,
            "event_kind": event_kind,
            "dataset": DIARIO_SAMPLE_DATASET_NAME,
        },
        valid_from=publication_date,
        valid_to=publication_date,
        confidence=1.0,
        status=WorkflowStatus.VALIDATED,
        metadata={"dataset": DIARIO_SAMPLE_DATASET_NAME},
    )

    appointment_relationship = PublicRelationshipRecord(
        source_entity=person_entity,
        target_entity=office_entity,
        relationship_type=(
            RelationshipType.PERSON_APPOINTED_TO_PUBLIC_OFFICE
            if event_kind == "appointment"
            else RelationshipType.PERSON_RESIGNED_FROM_PUBLIC_OFFICE
        ),
        claim=appointment_claim,
        published_at=datetime.now(timezone.utc),
        status=WorkflowStatus.PUBLISHED,
        metadata={
            "dataset": DIARIO_SAMPLE_DATASET_NAME,
            "document_kind": document_kind,
            "event_kind": event_kind,
        },
    )
    office_relationship = PublicRelationshipRecord(
        source_entity=office_entity,
        target_entity=organization_entity,
        relationship_type=RelationshipType.PUBLIC_OFFICE_BELONGS_TO_ORGANIZATION,
        claim=office_claim,
        published_at=datetime.now(timezone.utc),
        status=WorkflowStatus.PUBLISHED,
        metadata={
            "dataset": DIARIO_SAMPLE_DATASET_NAME,
            "document_kind": document_kind,
            "event_kind": event_kind,
        },
    )
    publication_relationship = PublicRelationshipRecord(
        source_entity=publisher_entity,
        target_entity=organization_entity,
        relationship_type=RelationshipType.DECREE_APPLIES_TO_ORGANIZATION,
        claim=publication_organization_claim,
        published_at=datetime.now(timezone.utc),
        status=WorkflowStatus.PUBLISHED,
        metadata={
            "dataset": DIARIO_SAMPLE_DATASET_NAME,
            "document_kind": document_kind,
            "event_kind": event_kind,
        },
    )
    publication_reference_relationship = PublicRelationshipRecord(
        source_entity=publisher_entity,
        target_entity=person_entity,
        relationship_type=RelationshipType.OFFICIAL_PUBLICATION_REFERENCES_ENTITY,
        claim=publication_reference_claim,
        published_at=datetime.now(timezone.utc),
        status=WorkflowStatus.PUBLISHED,
        metadata={
            "dataset": DIARIO_SAMPLE_DATASET_NAME,
            "document_kind": document_kind,
            "event_kind": event_kind,
        },
    )

    return {
        "source_record": source_record,
        "entities": (publisher_entity, person_entity, office_entity, organization_entity),
        "evidence": (appointment_evidence, office_evidence, organization_evidence, publication_evidence),
        "claims": (
            appointment_claim,
            office_claim,
            publication_organization_claim,
            publication_reference_claim,
        ),
        "public_relationships": (
            appointment_relationship,
            office_relationship,
            publication_relationship,
            publication_reference_relationship,
        ),
    }


def _build_evidence(
    source_record: SourceRecordPayload,
    *,
    external_id: str,
    title: str,
    url: str,
    excerpt: str,
    published_at: date | None,
) -> EvidenceRecord:
    return EvidenceRecord(
        source_record=source_record,
        source_name=DIARIO_SAMPLE_SOURCE_NAME,
        title=title,
        url=url,
        published_at=published_at,
        excerpt=excerpt,
        metadata={
            "classification": LOCAL_TEST_DATA,
            "official_status": NOT_OFFICIAL_DATA,
            "dataset": DIARIO_SAMPLE_DATASET_NAME,
            "external_id": external_id,
        },
    )


def _load_diario_oficial_rows(session: Session) -> tuple[DiarioOficialSummaryRow, ...]:
    claims = list(
        session.scalars(
            select(Claim)
            .join(SourceRecord, Claim.source_record_id == SourceRecord.id)
            .options(joinedload(Claim.subject_entity), joinedload(Claim.object_entity), joinedload(Claim.source_record))
            .where(SourceRecord.record_type == DIARIO_SAMPLE_RECORD_TYPE)
            .order_by(Claim.created_at, Claim.id)
        ).all()
    )
    if not claims:
        return ()

    rows: list[DiarioOficialSummaryRow] = []
    claims_by_source_record: dict[str, list[Claim]] = {}
    for claim in claims:
        claims_by_source_record.setdefault(str(claim.source_record_id), []).append(claim)

    for source_record_id, record_claims in claims_by_source_record.items():
        source_record = record_claims[0].source_record
        if source_record is None:
            continue
        publication = _load_claim(record_claims, PERSON_APPOINTED_TO_PUBLIC_OFFICE_PREDICATE) or _load_claim(
            record_claims, PERSON_RESIGNED_FROM_PUBLIC_OFFICE_PREDICATE
        )
        if publication is None:
            continue
        person = publication.subject_entity
        office = publication.object_entity
        organization_claim = _load_claim(record_claims, DECREE_APPLIES_TO_ORGANIZATION_PREDICATE)
        organization = organization_claim.object_entity if organization_claim is not None else None
        payload = source_record.raw_payload if isinstance(source_record.raw_payload, dict) else {}
        rows.append(
            DiarioOficialSummaryRow(
                publication_id=str(source_record_id),
                publication_date=_parse_date(payload.get("publication_date")),
                publication_number=str(payload.get("publication_number", "")),
                publication_title=str(payload.get("publication_title", "")),
                event_kind=str(payload.get("event_kind", "")),
                person_name=person.name if person is not None else "",
                office_name=office.name if office is not None else "",
                organization_name=organization.name if organization is not None else "",
                claims=tuple(claim.predicate for claim in record_claims),
                relationships=tuple(
                    relationship.relationship_type
                    for relationship in _load_relationships_for_source_record(session, source_record.id)
                ),
                evidence=_count_evidence_for_source_record(session, source_record.id),
            )
        )
    return tuple(rows)


def _load_claim(claims: list[Claim], predicate: str) -> Claim | None:
    for claim in claims:
        if claim.predicate == predicate:
            return claim
    return None


def _load_relationships_for_source_record(session: Session, source_record_id) -> tuple[RelationshipPublic, ...]:  # type: ignore[no-untyped-def]
    return tuple(
        session.scalars(
            select(RelationshipPublic)
            .join(Claim, RelationshipPublic.claim_id == Claim.id)
            .where(Claim.source_record_id == source_record_id)
            .order_by(RelationshipPublic.relationship_type.asc(), RelationshipPublic.id.asc())
        ).all()
    )


def _count_evidence_for_source_record(session: Session, source_record_id) -> int:  # type: ignore[no-untyped-def]
    return int(
        session.scalar(select(func.count()).select_from(Evidence).where(Evidence.source_record_id == source_record_id))
        or 0
    )


def _validate_sample_payload(payload: dict[str, Any]) -> None:
    if payload.get("classification") != LOCAL_TEST_DATA:
        raise ValueError("Diario Oficial sample must be marked LOCAL_TEST_DATA")
    if payload.get("official_status") != NOT_OFFICIAL_DATA:
        raise ValueError("Diario Oficial sample must be marked NOT_OFFICIAL_DATA")
    if "records" not in payload or not isinstance(payload["records"], list):
        raise ValueError("Diario Oficial sample must include a records array")
    for record in payload["records"]:
        for key in (
            "external_id",
            "publication_date",
            "publication_number",
            "publication_title",
            "document_kind",
            "event_kind",
            "person_name",
            "office_name",
            "organization_name",
            "decree_number",
            "source_url",
        ):
            if not record.get(key):
                raise ValueError(f"Diario Oficial sample record must include {key}")


def _count_rows(session: Session, model) -> int:  # type: ignore[no-untyped-def]
    return int(session.scalar(select(func.count()).select_from(model)) or 0)


def _count_source_records(session: Session) -> int:
    return int(
        session.scalar(
            select(func.count())
            .select_from(SourceRecord)
            .where(SourceRecord.record_type == DIARIO_SAMPLE_RECORD_TYPE)
        )
        or 0
    )


def _count_entities(session: Session, entity_type: str) -> int:
    return int(session.scalar(select(func.count()).select_from(Entity).where(Entity.entity_type == entity_type)) or 0)


def _parse_date(value: object | None) -> date | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return date.fromisoformat(text[:10])


def _unique_records(items: list[Any], *, key):  # noqa: ANN001
    seen: set[Any] = set()
    ordered: list[Any] = []
    for item in items:
        identity = key(item)
        if identity in seen:
            continue
        seen.add(identity)
        ordered.append(item)
    return ordered
