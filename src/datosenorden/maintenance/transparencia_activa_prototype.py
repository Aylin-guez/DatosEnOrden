from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
import json
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

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
from datosenorden.maintenance.entity_matching import match_entity_candidates
from datosenorden.models import Claim, Entity, Evidence, RelationshipPublic, SourceRecord

LOCAL_TEST_DATA = "LOCAL_TEST_DATA"
NOT_OFFICIAL_DATA = "NOT_OFFICIAL_DATA"
TRANSPARENCIA_SAMPLE_DATASET_NAME = "transparencia-activa-sample"
TRANSPARENCIA_SAMPLE_SOURCE_NAME = "DatosEnOrden Transparencia Activa Sample"
TRANSPARENCIA_SAMPLE_SOURCE_URL = "local://sample/transparencia-activa"
TRANSPARENCIA_SAMPLE_RECORD_TYPE = "transparencia:active_transparency_sample"
ORGANIZATION_HAS_PUBLIC_ROLE_PREDICATE = "ORGANIZATION_HAS_PUBLIC_ROLE"
PERSON_HOLDS_PUBLIC_ROLE_PREDICATE = "PERSON_HOLDS_PUBLIC_ROLE"
ROLE_BELONGS_TO_ORGANIZATION_PREDICATE = "ROLE_BELONGS_TO_ORGANIZATION"
TRANSPARENCIA_SAMPLE_PATH = PROJECT_ROOT / "data" / "sample" / "transparencia_activa_sample.json"


@dataclass(frozen=True)
class TransparenciaMatchResult:
    entity: Entity
    match_method: str
    confidence: float


@dataclass(frozen=True)
class TransparenciaImportResult:
    source_records: int
    claims: int
    evidences: int
    entities: int
    relationship_public: int
    organization_entity_id: str
    organization_name: str
    role_entity_id: str
    role_name: str
    person_entity_id: str
    person_name: str
    organization_match_method: str
    organization_match_confidence: float


@dataclass(frozen=True)
class TransparenciaSummaryRow:
    organization_id: str
    organization_name: str
    role_id: str
    role_name: str
    person_id: str
    person_name: str
    period: str
    unit_name: str | None
    claims: tuple[str, ...]
    relationships: tuple[str, ...]
    evidence: int
    organization_match_method: str
    organization_match_confidence: float


@dataclass(frozen=True)
class TransparenciaSummary:
    organizations: int
    people: int
    roles: int
    claims: int
    relationships: int
    evidence: int
    rows: tuple[TransparenciaSummaryRow, ...]


def load_transparencia_sample_payload(input_path: Path | None = None) -> dict[str, Any]:
    path = input_path or TRANSPARENCIA_SAMPLE_PATH
    payload = json.loads(path.read_text(encoding="utf-8"))
    _validate_sample_payload(payload)
    return payload


def build_transparencia_sample_batch(session: Session, payload: dict[str, Any] | None = None) -> GraphBatch:
    sample = payload or load_transparencia_sample_payload()
    records = sample.get("records") or []
    if not records:
        raise ValueError("Transparencia Activa sample must include at least one record")

    record = records[0]
    classification = str(sample["classification"])
    official_status = str(sample["official_status"])
    organization_name = str(record["organization_name"])
    person_name = str(record["person_name"])
    role_title = str(record["role_title"])
    period = str(record["period"])
    unit_name = record.get("unit_name")

    organization_match = _match_existing_organization(session, organization_name)
    organization_entity = _build_matched_organization_entity(organization_match)
    role_entity = _build_role_entity(record, classification, official_status)
    person_entity = _build_person_entity(record, classification, official_status)

    source_record_payload = {
        **record,
        "classification": classification,
        "official_status": official_status,
        "sample_markers": [LOCAL_TEST_DATA, NOT_OFFICIAL_DATA],
    }
    source_record = SourceRecordPayload(
        external_id=str(record["external_id"]),
        record_type=TRANSPARENCIA_SAMPLE_RECORD_TYPE,
        payload_hash=stable_json_hash(source_record_payload),
        raw_payload=source_record_payload,
        retrieved_at=datetime.now(timezone.utc),
        status=WorkflowStatus.NORMALIZED,
    )

    role_evidence = _build_evidence(
        source_record,
        external_id=f"{record['external_id']}:organization-role",
        title=f"Transparencia Activa local sample role - {organization_name}",
        url=f"{record['source_url']}/organization-role",
        excerpt=(
            f"{LOCAL_TEST_DATA} / {NOT_OFFICIAL_DATA} administrative role sample for "
            f"{organization_name}: {role_title}."
        ),
    )
    person_evidence = _build_evidence(
        source_record,
        external_id=f"{record['external_id']}:person-role",
        title=f"Transparencia Activa local sample person role - {person_name}",
        url=f"{record['source_url']}/person-role",
        excerpt=(
            f"{LOCAL_TEST_DATA} / {NOT_OFFICIAL_DATA} fictional sample person linked "
            f"to role {role_title}."
        ),
    )
    belongs_evidence = _build_evidence(
        source_record,
        external_id=f"{record['external_id']}:role-organization",
        title="Transparencia Activa local sample role organization",
        url=f"{record['source_url']}/role-organization",
        excerpt=(
            f"{LOCAL_TEST_DATA} / {NOT_OFFICIAL_DATA} role belongs to organization "
            f"sample for {organization_name}."
        ),
    )

    object_value = {
        "period": period,
        "unit_name": unit_name,
        "source_dataset_name": record.get("source_dataset_name"),
        "dataset": TRANSPARENCIA_SAMPLE_DATASET_NAME,
        "classification": classification,
        "official_status": official_status,
    }
    organization_claim = ClaimRecord(
        subject_entity=organization_entity,
        predicate=ORGANIZATION_HAS_PUBLIC_ROLE_PREDICATE,
        object_entity=role_entity,
        source_record=source_record,
        evidence=role_evidence,
        object_value=object_value,
        valid_from=_period_start(period),
        confidence=organization_match.confidence,
        status=WorkflowStatus.VALIDATED,
        metadata={"dataset": TRANSPARENCIA_SAMPLE_DATASET_NAME},
    )
    person_claim = ClaimRecord(
        subject_entity=person_entity,
        predicate=PERSON_HOLDS_PUBLIC_ROLE_PREDICATE,
        object_entity=role_entity,
        source_record=source_record,
        evidence=person_evidence,
        object_value=object_value,
        valid_from=_period_start(period),
        confidence=1.0,
        status=WorkflowStatus.VALIDATED,
        metadata={"dataset": TRANSPARENCIA_SAMPLE_DATASET_NAME},
    )
    belongs_claim = ClaimRecord(
        subject_entity=role_entity,
        predicate=ROLE_BELONGS_TO_ORGANIZATION_PREDICATE,
        object_entity=organization_entity,
        source_record=source_record,
        evidence=belongs_evidence,
        object_value=object_value,
        valid_from=_period_start(period),
        confidence=organization_match.confidence,
        status=WorkflowStatus.VALIDATED,
        metadata={"dataset": TRANSPARENCIA_SAMPLE_DATASET_NAME},
    )

    organization_role_relationship = PublicRelationshipRecord(
        source_entity=organization_entity,
        target_entity=role_entity,
        relationship_type=RelationshipType.ORGANIZATION_HAS_PUBLIC_ROLE,
        claim=organization_claim,
        published_at=datetime.now(timezone.utc),
        status=WorkflowStatus.PUBLISHED,
        metadata=_relationship_metadata(classification, official_status, organization_match),
    )
    role_person_relationship = PublicRelationshipRecord(
        source_entity=role_entity,
        target_entity=person_entity,
        relationship_type=RelationshipType.PERSON_HOLDS_PUBLIC_ROLE,
        claim=person_claim,
        published_at=datetime.now(timezone.utc),
        status=WorkflowStatus.PUBLISHED,
        metadata=_relationship_metadata(classification, official_status, organization_match),
    )
    role_organization_relationship = PublicRelationshipRecord(
        source_entity=role_entity,
        target_entity=organization_entity,
        relationship_type=RelationshipType.ROLE_BELONGS_TO_ORGANIZATION,
        claim=belongs_claim,
        published_at=datetime.now(timezone.utc),
        status=WorkflowStatus.PUBLISHED,
        metadata=_relationship_metadata(classification, official_status, organization_match),
    )

    source = SourceInfo(
        name=TRANSPARENCIA_SAMPLE_SOURCE_NAME,
        publisher="DatosEnOrden",
        url=TRANSPARENCIA_SAMPLE_SOURCE_URL,
        license=f"{LOCAL_TEST_DATA} / {NOT_OFFICIAL_DATA}",
        retrieved_at=datetime.now(timezone.utc),
        metadata={
            "classification": classification,
            "official_status": official_status,
            "dataset": TRANSPARENCIA_SAMPLE_DATASET_NAME,
        },
    )
    dataset = DatasetRecord(
        source_name=TRANSPARENCIA_SAMPLE_SOURCE_NAME,
        name=TRANSPARENCIA_SAMPLE_DATASET_NAME,
        description=(
            "LOCAL_TEST_DATA / NOT_OFFICIAL_DATA sample used to validate "
            "Transparencia Activa role connections"
        ),
        version="local-sample-1",
        dataset_url=f"{TRANSPARENCIA_SAMPLE_SOURCE_URL}/dataset",
        content_hash=stable_json_hash(sample),
        loaded_at=datetime.now(timezone.utc),
        metadata={
            "classification": classification,
            "official_status": official_status,
            "dataset": TRANSPARENCIA_SAMPLE_DATASET_NAME,
        },
    )
    return GraphBatch(
        source=source,
        dataset=dataset,
        source_records=(source_record,),
        entities=(organization_entity, role_entity, person_entity),
        evidence=(role_evidence, person_evidence, belongs_evidence),
        claims=(organization_claim, person_claim, belongs_claim),
        public_relationships=(
            organization_role_relationship,
            role_person_relationship,
            role_organization_relationship,
        ),
        raw_count=len(records),
        rejected_count=0,
        errors=(),
    )


def persist_transparencia_sample(session: Session, input_path: Path | None = None) -> TransparenciaImportResult:
    payload = load_transparencia_sample_payload(input_path)
    batch = build_transparencia_sample_batch(session, payload)
    GraphLoader(session).load(batch, dry_run=False)

    record = payload["records"][0]
    organization_match = _match_existing_organization(session, str(record["organization_name"]))
    role_external_id = _role_external_id(record)
    person_external_id = _person_external_id(record)
    role = _load_entity(session, EntityType.ROLE.value, role_external_id)
    person = _load_entity(session, EntityType.PERSON.value, person_external_id)
    return TransparenciaImportResult(
        source_records=_count_rows(session, SourceRecord),
        claims=_count_rows(session, Claim),
        evidences=_count_rows(session, Evidence),
        entities=_count_rows(session, Entity),
        relationship_public=_count_rows(session, RelationshipPublic),
        organization_entity_id=str(organization_match.entity.id),
        organization_name=organization_match.entity.name,
        role_entity_id=str(role.id),
        role_name=role.name,
        person_entity_id=str(person.id),
        person_name=person.name,
        organization_match_method=organization_match.match_method,
        organization_match_confidence=organization_match.confidence,
    )


def read_transparencia_summary(session: Session) -> TransparenciaSummary:
    role_claims = _load_organization_role_claims(session)
    rows: list[TransparenciaSummaryRow] = []
    for role_claim in role_claims:
        organization = role_claim.subject_entity
        role = role_claim.object_entity
        source_record = role_claim.source_record
        if organization is None or role is None or source_record is None:
            continue
        person_claim = _load_role_person_claim(session, source_record.id)
        belongs_claim = _load_role_organization_claim(session, source_record.id)
        if person_claim is None or person_claim.subject_entity is None:
            continue
        relationships = _load_transparencia_relationships(session, source_record.id)
        claim_ids = tuple(
            str(claim.id)
            for claim in (role_claim, person_claim, belongs_claim)
            if claim is not None and getattr(claim, "id", None) is not None
        )
        data = role_claim.object_value or {}
        rows.append(
            TransparenciaSummaryRow(
                organization_id=str(organization.id),
                organization_name=organization.name,
                role_id=str(role.id),
                role_name=role.name,
                person_id=str(person_claim.subject_entity.id),
                person_name=person_claim.subject_entity.name,
                period=str(data.get("period", "")),
                unit_name=data.get("unit_name"),
                claims=(
                    role_claim.predicate,
                    person_claim.predicate,
                    belongs_claim.predicate if belongs_claim is not None else ROLE_BELONGS_TO_ORGANIZATION_PREDICATE,
                ),
                relationships=tuple(relationship.relationship_type for relationship in relationships),
                evidence=_count_evidence_for_claim_ids(session, claim_ids),
                organization_match_method=_metadata_value(relationships, "match_method"),
                organization_match_confidence=_metadata_float(
                    relationships,
                    "match_confidence",
                    float(role_claim.confidence),
                ),
            )
        )

    unique_orgs = {row.organization_id for row in rows}
    unique_people = {row.person_id for row in rows}
    unique_roles = {row.role_id for row in rows}
    unique_claims = {(row.organization_id, claim) for row in rows for claim in row.claims}
    unique_relationships = {(row.organization_id, relationship) for row in rows for relationship in row.relationships}
    return TransparenciaSummary(
        organizations=len(unique_orgs),
        people=len(unique_people),
        roles=len(unique_roles),
        claims=len(unique_claims),
        relationships=len(unique_relationships),
        evidence=sum(row.evidence for row in rows),
        rows=tuple(sorted(rows, key=lambda item: (item.organization_name.lower(), item.role_name.lower()))),
    )


def render_transparencia_summary_text(summary: TransparenciaSummary) -> str:
    lines = [
        "transparencia_summary:",
        f"  organizations={summary.organizations}",
        f"  people={summary.people}",
        f"  roles={summary.roles}",
        f"  claims={summary.claims}",
        f"  relationships={summary.relationships}",
        f"  evidence={summary.evidence}",
        "  matched_entities:",
    ]
    if not summary.rows:
        lines.append("    (no transparencia sample roles found)")
        return "\n".join(lines)
    first = summary.rows[0]
    lines.extend(
        [
            f"    organization_match_method={first.organization_match_method}",
            f"    organization_match_confidence={first.organization_match_confidence}",
        ]
    )
    for row in summary.rows:
        lines.extend(
            [
                "  role_connection:",
                f"    organization={row.organization_name}",
                f"    role={row.role_name}",
                f"    person={row.person_name}",
                f"    period={row.period}",
                f"    unit={row.unit_name or 'None'}",
            ]
        )
    return "\n".join(lines)


def render_transparencia_import_result_text(result: TransparenciaImportResult) -> str:
    return "\n".join(
        [
            "transparencia_sample_loaded:",
            f"  source_records={result.source_records}",
            f"  claims={result.claims}",
            f"  evidences={result.evidences}",
            f"  entities={result.entities}",
            f"  relationship_public={result.relationship_public}",
            f"  organization_entity_id={result.organization_entity_id}",
            f"  organization_name={result.organization_name}",
            f"  role_entity_id={result.role_entity_id}",
            f"  role_name={result.role_name}",
            f"  person_entity_id={result.person_entity_id}",
            f"  person_name={result.person_name}",
            f"  organization_match_method={result.organization_match_method}",
            f"  organization_match_confidence={result.organization_match_confidence}",
        ]
    )


def transparencia_human_explanation() -> str:
    return "\n".join(
        [
            "Transparencia Activa muestra informacion administrativa publicada por organismos.",
            "Este prototipo usa datos de muestra, no datos oficiales.",
            "No implica irregularidad; solo representa informacion publica o de muestra.",
        ]
    )


def _validate_sample_payload(payload: dict[str, Any]) -> None:
    if payload.get("classification") != LOCAL_TEST_DATA:
        raise ValueError("Transparencia Activa sample must be marked LOCAL_TEST_DATA")
    if payload.get("official_status") != NOT_OFFICIAL_DATA:
        raise ValueError("Transparencia Activa sample must be marked NOT_OFFICIAL_DATA")
    if "records" not in payload or not isinstance(payload["records"], list):
        raise ValueError("Transparencia Activa sample must include a records array")
    for record in payload["records"]:
        for key in (
            "organization_name",
            "person_name",
            "role_title",
            "period",
            "source_url",
            "source_dataset_name",
        ):
            if not record.get(key):
                raise ValueError(f"Transparencia Activa sample record must include {key}")
        if "MUESTRA" not in str(record["person_name"]).upper():
            raise ValueError("Transparencia Activa sample person must be clearly marked as sample data")


def _match_existing_organization(session: Session, organization_name: str) -> TransparenciaMatchResult:
    candidates = match_entity_candidates(
        session,
        entity_type=EntityType.PUBLIC_ORGANIZATION.value,
        name=organization_name,
        limit=1,
    )
    if not candidates:
        raise LookupError(f"No PUBLIC_ORGANIZATION match found for {organization_name}")
    candidate = candidates[0]
    entity = session.get(Entity, UUID(candidate.candidate_entity_id)) if hasattr(session, "get") else None
    if entity is None:
        entity = Entity(
            id=UUID(candidate.candidate_entity_id),
            entity_type=candidate.entity_type,
            name=candidate.candidate_name,
            external_id=candidate.candidate_entity_id,
            status="active",
        )
    return TransparenciaMatchResult(entity=entity, match_method=candidate.match_method, confidence=candidate.score)


def _build_matched_organization_entity(match: TransparenciaMatchResult) -> EntityRecord:
    entity = match.entity
    return EntityRecord(
        entity_type=EntityType.PUBLIC_ORGANIZATION,
        external_id=str(entity.external_id),
        name=entity.name,
        description=entity.description,
        normalized_key=entity.normalized_key,
        status=entity.status,
        metadata=entity.entity_metadata or {},
    )


def _build_role_entity(record: dict[str, Any], classification: str, official_status: str) -> EntityRecord:
    role_title = str(record["role_title"])
    organization_name = str(record["organization_name"])
    period = str(record["period"])
    return EntityRecord(
        entity_type=EntityType.ROLE,
        external_id=_role_external_id(record),
        name=f"{role_title} - {organization_name} ({period})",
        description=(
            f"{LOCAL_TEST_DATA} / {NOT_OFFICIAL_DATA} Transparencia Activa role sample. "
            "Neutral local sample record."
        ),
        normalized_key=normalized_key(f"{organization_name} {role_title} {period}"),
        metadata={
            "classification": classification,
            "official_status": official_status,
            "dataset": TRANSPARENCIA_SAMPLE_DATASET_NAME,
            "organization_name": organization_name,
            "role_title": role_title,
            "unit_name": record.get("unit_name"),
            "period": period,
        },
    )


def _build_person_entity(record: dict[str, Any], classification: str, official_status: str) -> EntityRecord:
    person_name = str(record["person_name"])
    return EntityRecord(
        entity_type=EntityType.PERSON,
        external_id=_person_external_id(record),
        name=person_name,
        description=(
            f"{LOCAL_TEST_DATA} / {NOT_OFFICIAL_DATA} fictional person for local "
            "Transparencia Activa prototype validation."
        ),
        normalized_key=normalized_key(person_name),
        metadata={
            "classification": classification,
            "official_status": official_status,
            "dataset": TRANSPARENCIA_SAMPLE_DATASET_NAME,
            "sample_person": True,
        },
    )


def _build_evidence(
    source_record: SourceRecordPayload,
    *,
    external_id: str,
    title: str,
    url: str,
    excerpt: str,
) -> EvidenceRecord:
    return EvidenceRecord(
        source_record=source_record,
        source_name=TRANSPARENCIA_SAMPLE_SOURCE_NAME,
        title=title,
        url=url,
        published_at=None,
        excerpt=excerpt,
        metadata={
            "classification": LOCAL_TEST_DATA,
            "official_status": NOT_OFFICIAL_DATA,
            "dataset": TRANSPARENCIA_SAMPLE_DATASET_NAME,
            "external_id": external_id,
        },
    )


def _relationship_metadata(
    classification: str,
    official_status: str,
    organization_match: TransparenciaMatchResult,
) -> dict[str, object]:
    return {
        "classification": classification,
        "official_status": official_status,
        "dataset": TRANSPARENCIA_SAMPLE_DATASET_NAME,
        "match_method": organization_match.match_method,
        "match_confidence": organization_match.confidence,
    }


def _role_external_id(record: dict[str, Any]) -> str:
    return f"transparencia:role:{record['external_id']}"


def _person_external_id(record: dict[str, Any]) -> str:
    key = normalized_key(str(record["person_name"])) or str(record["person_name"]).lower()
    return f"transparencia:person:{key}:{record['external_id']}"


def _load_entity(session: Session, entity_type: str, external_id: str) -> Entity:
    entity = session.scalar(
        select(Entity).where(
            Entity.entity_type == entity_type,
            Entity.external_id == external_id,
        )
    )
    if entity is None:
        raise LookupError(f"{entity_type} entity not found after load: {external_id}")
    return entity


def _load_organization_role_claims(session: Session) -> list[Claim]:
    return list(
        session.scalars(
            select(Claim)
            .join(SourceRecord, Claim.source_record_id == SourceRecord.id)
            .options(
                joinedload(Claim.subject_entity),
                joinedload(Claim.object_entity),
                joinedload(Claim.source_record),
            )
            .where(
                SourceRecord.record_type == TRANSPARENCIA_SAMPLE_RECORD_TYPE,
                Claim.predicate == ORGANIZATION_HAS_PUBLIC_ROLE_PREDICATE,
            )
            .order_by(Claim.created_at, Claim.id)
        ).all()
    )


def _load_role_person_claim(session: Session, source_record_id) -> Claim | None:  # type: ignore[no-untyped-def]
    return session.scalar(
        select(Claim)
        .options(joinedload(Claim.subject_entity), joinedload(Claim.object_entity))
        .where(
            Claim.source_record_id == source_record_id,
            Claim.predicate == PERSON_HOLDS_PUBLIC_ROLE_PREDICATE,
        )
        .order_by(Claim.created_at, Claim.id)
    )


def _load_role_organization_claim(session: Session, source_record_id) -> Claim | None:  # type: ignore[no-untyped-def]
    return session.scalar(
        select(Claim)
        .options(joinedload(Claim.subject_entity), joinedload(Claim.object_entity))
        .where(
            Claim.source_record_id == source_record_id,
            Claim.predicate == ROLE_BELONGS_TO_ORGANIZATION_PREDICATE,
        )
        .order_by(Claim.created_at, Claim.id)
    )


def _load_transparencia_relationships(session: Session, source_record_id) -> tuple[RelationshipPublic, ...]:  # type: ignore[no-untyped-def]
    return tuple(
        session.scalars(
            select(RelationshipPublic)
            .join(Claim, RelationshipPublic.claim_id == Claim.id)
            .where(Claim.source_record_id == source_record_id)
            .order_by(RelationshipPublic.relationship_type.asc(), RelationshipPublic.id.asc())
        ).all()
    )


def _count_evidence_for_claim_ids(session: Session, claim_ids: tuple[str, ...]) -> int:
    if not claim_ids:
        return 0
    uuids = tuple(UUID(claim_id) for claim_id in claim_ids)
    return int(
        session.scalar(
            select(func.count()).select_from(Evidence).where(Evidence.claim_id.in_(uuids))
        )
        or 0
    )


def _metadata_value(relationships: tuple[RelationshipPublic, ...], key: str) -> str:
    for relationship in relationships:
        metadata = relationship.relationship_metadata or {}
        if metadata.get(key) is not None:
            return str(metadata[key])
    return "unknown"


def _metadata_float(relationships: tuple[RelationshipPublic, ...], key: str, default: float) -> float:
    for relationship in relationships:
        metadata = relationship.relationship_metadata or {}
        if metadata.get(key) is not None:
            return float(metadata[key])
    return default


def _period_start(period: str) -> date | None:
    parts = period.split("-")
    if len(parts) < 2:
        return None
    return date(int(parts[0]), int(parts[1]), 1)


def _count_rows(session: Session, model) -> int:  # type: ignore[no-untyped-def]
    return int(session.scalar(select(func.count()).select_from(model)) or 0)


def deterministic_sample_uuid(value: str) -> UUID:
    return uuid5(NAMESPACE_URL, value)
