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
SANCIONES_PROCEDIMIENTOS_SAMPLE_DATASET_NAME = "sanciones-procedimientos-sample"
SANCIONES_PROCEDIMIENTOS_SAMPLE_SOURCE_NAME = "DatosEnOrden Sanciones Procedimientos Sample"
SANCIONES_PROCEDIMIENTOS_SAMPLE_SOURCE_URL = "local://sample/sanciones-procedimientos"
SANCIONES_PROCEDIMIENTOS_SAMPLE_RECORD_TYPE = "sanciones_procedimientos:local_sample"
SANCIONES_PROCEDIMIENTOS_SAMPLE_PATH = PROJECT_ROOT / "data" / "sample" / "sanciones_procedimientos_sample.json"

PROCEDURE_INVOLVES_ORGANIZATION = "PROCEDURE_INVOLVES_ORGANIZATION"
PROCEDURE_INVOLVES_COMPANY = "PROCEDURE_INVOLVES_COMPANY"
PROCEDURE_INVOLVES_PERSON = "PROCEDURE_INVOLVES_PERSON"
PROCEDURE_HAS_RESOLUTION = "PROCEDURE_HAS_RESOLUTION"


@dataclass(frozen=True)
class SancionesProcedimientosImportResult:
    source_records: int
    claims: int
    evidences: int
    entities: int
    relationship_public: int
    procedure_entity_id: str
    procedure_name: str
    resolution_entity_id: str
    resolution_name: str


@dataclass(frozen=True)
class SancionesProcedimientosSummaryRow:
    procedure_id: str
    procedure_name: str
    resolution_id: str
    resolution_name: str
    organization_name: str
    company_name: str
    person_name: str
    procedure_date: date | None
    resolution_date: date | None
    relationships: tuple[str, ...]
    evidence: int


@dataclass(frozen=True)
class SancionesProcedimientosSummary:
    procedures: int
    resolutions: int
    claims: int
    relationships: int
    evidence: int
    rows: tuple[SancionesProcedimientosSummaryRow, ...]


def load_sanciones_procedimientos_sample_payload(input_path: Path | None = None) -> dict[str, Any]:
    path = input_path or SANCIONES_PROCEDIMIENTOS_SAMPLE_PATH
    payload = json.loads(path.read_text(encoding="utf-8"))
    _validate_sample_payload(payload)
    return payload


def build_sanciones_procedimientos_sample_batch(session: Session, payload: dict[str, Any] | None = None) -> GraphBatch:
    sample = payload or load_sanciones_procedimientos_sample_payload()
    records = sample.get("records") or []
    if not records:
        raise ValueError("Sanciones y procedimientos sample must include at least one record")

    record = records[0]
    classification = str(sample["classification"])
    official_status = str(sample["official_status"])
    procedure_date = _parse_date(record.get("procedure_date"))
    resolution_date = _parse_date(record.get("resolution_date"))

    organization = _entity_record_for_name(session, EntityType.PUBLIC_ORGANIZATION, str(record["organization_name"]), "organization")
    company = _entity_record_for_name(session, EntityType.COMPANY, str(record["company_name"]), "company")
    person = _entity_record_for_name(session, EntityType.PERSON, str(record["person_name"]), "person")
    procedure = _procedure_entity(record, classification, official_status)
    resolution = _resolution_entity(record, classification, official_status)

    source_record_payload = {
        **record,
        "classification": classification,
        "official_status": official_status,
        "sample_markers": [LOCAL_TEST_DATA, NOT_OFFICIAL_DATA],
    }
    source_record = SourceRecordPayload(
        external_id=str(record["external_id"]),
        record_type=SANCIONES_PROCEDIMIENTOS_SAMPLE_RECORD_TYPE,
        payload_hash=stable_json_hash(source_record_payload),
        raw_payload=source_record_payload,
        retrieved_at=datetime.now(timezone.utc),
        status=WorkflowStatus.NORMALIZED,
    )
    procedure_evidence = _evidence(
        source_record,
        external_id=f"{record['external_id']}:procedure",
        title=f"Procedimiento administrativo local - {record['procedure_number']}",
        url=f"{record['source_url']}/procedure",
        excerpt=f"{LOCAL_TEST_DATA} / {NOT_OFFICIAL_DATA} procedure record sample.",
        published_at=procedure_date,
    )
    resolution_evidence = _evidence(
        source_record,
        external_id=f"{record['external_id']}:resolution",
        title=f"Resolucion administrativa local - {record['resolution_number']}",
        url=f"{record['source_url']}/resolution",
        excerpt=f"{LOCAL_TEST_DATA} / {NOT_OFFICIAL_DATA} resolution record sample.",
        published_at=resolution_date,
    )

    claims = (
        _claim(procedure, PROCEDURE_INVOLVES_ORGANIZATION, organization, source_record, procedure_evidence, record, procedure_date),
        _claim(procedure, PROCEDURE_INVOLVES_COMPANY, company, source_record, procedure_evidence, record, procedure_date),
        _claim(procedure, PROCEDURE_INVOLVES_PERSON, person, source_record, procedure_evidence, record, procedure_date),
        _claim(procedure, PROCEDURE_HAS_RESOLUTION, resolution, source_record, resolution_evidence, record, resolution_date),
    )
    relationships = (
        _relationship(procedure, organization, RelationshipType.PROCEDURE_INVOLVES_ORGANIZATION, claims[0], procedure_date),
        _relationship(procedure, company, RelationshipType.PROCEDURE_INVOLVES_COMPANY, claims[1], procedure_date),
        _relationship(procedure, person, RelationshipType.PROCEDURE_INVOLVES_PERSON, claims[2], procedure_date),
        _relationship(procedure, resolution, RelationshipType.PROCEDURE_HAS_RESOLUTION, claims[3], resolution_date),
    )

    source = SourceInfo(
        name=SANCIONES_PROCEDIMIENTOS_SAMPLE_SOURCE_NAME,
        publisher="DatosEnOrden",
        url=SANCIONES_PROCEDIMIENTOS_SAMPLE_SOURCE_URL,
        license=f"{LOCAL_TEST_DATA} / {NOT_OFFICIAL_DATA}",
        retrieved_at=datetime.now(timezone.utc),
        metadata={"classification": classification, "official_status": official_status},
    )
    dataset = DatasetRecord(
        source_name=SANCIONES_PROCEDIMIENTOS_SAMPLE_SOURCE_NAME,
        name=SANCIONES_PROCEDIMIENTOS_SAMPLE_DATASET_NAME,
        description="LOCAL_TEST_DATA / NOT_OFFICIAL_DATA sample for administrative procedures and resolutions.",
        version="local-sample-1",
        dataset_url=f"{SANCIONES_PROCEDIMIENTOS_SAMPLE_SOURCE_URL}/dataset",
        content_hash=stable_json_hash(sample),
        loaded_at=datetime.now(timezone.utc),
        metadata={"classification": classification, "official_status": official_status},
    )
    return GraphBatch(
        source=source,
        dataset=dataset,
        source_records=(source_record,),
        entities=(organization, company, person, procedure, resolution),
        evidence=(procedure_evidence, resolution_evidence),
        claims=claims,
        public_relationships=relationships,
        raw_count=len(records),
        rejected_count=0,
        errors=(),
    )


def persist_sanciones_procedimientos_sample(session: Session, input_path: Path | None = None) -> SancionesProcedimientosImportResult:
    payload = load_sanciones_procedimientos_sample_payload(input_path)
    batch = build_sanciones_procedimientos_sample_batch(session, payload)
    GraphLoader(session).load(batch, dry_run=False)

    record = payload["records"][0]
    procedure = session.scalar(select(Entity).where(Entity.external_id == f"sanciones:procedure:{record['external_id']}"))
    resolution = session.scalar(select(Entity).where(Entity.external_id == f"sanciones:resolution:{record['external_id']}"))
    if procedure is None or resolution is None:
        raise LookupError("Sanciones y procedimientos sample entities not found after load")
    return SancionesProcedimientosImportResult(
        source_records=_count_rows(session, SourceRecord),
        claims=_count_rows(session, Claim),
        evidences=_count_rows(session, Evidence),
        entities=_count_rows(session, Entity),
        relationship_public=_count_rows(session, RelationshipPublic),
        procedure_entity_id=str(procedure.id),
        procedure_name=procedure.name,
        resolution_entity_id=str(resolution.id),
        resolution_name=resolution.name,
    )


def read_sanciones_procedimientos_summary(session: Session) -> SancionesProcedimientosSummary:
    claims = _load_procedure_claims(session)
    by_source_record: dict[object, list[Claim]] = {}
    for claim in claims:
        by_source_record.setdefault(claim.source_record_id, []).append(claim)

    rows: list[SancionesProcedimientosSummaryRow] = []
    for source_record_id, record_claims in by_source_record.items():
        procedure_claim = next((claim for claim in record_claims if claim.predicate == PROCEDURE_HAS_RESOLUTION), None)
        if procedure_claim is None or procedure_claim.subject_entity is None or procedure_claim.object_entity is None:
            continue
        relationships = _load_relationships(session, source_record_id)
        rows.append(
            SancionesProcedimientosSummaryRow(
                procedure_id=str(procedure_claim.subject_entity.id),
                procedure_name=procedure_claim.subject_entity.name,
                resolution_id=str(procedure_claim.object_entity.id),
                resolution_name=procedure_claim.object_entity.name,
                organization_name=_object_name(record_claims, PROCEDURE_INVOLVES_ORGANIZATION),
                company_name=_object_name(record_claims, PROCEDURE_INVOLVES_COMPANY),
                person_name=_object_name(record_claims, PROCEDURE_INVOLVES_PERSON),
                procedure_date=_valid_from(record_claims, PROCEDURE_INVOLVES_ORGANIZATION),
                resolution_date=procedure_claim.valid_from,
                relationships=tuple(relationship.relationship_type for relationship in relationships),
                evidence=_count_evidence_for_source_record(session, source_record_id),
            )
        )

    unique_claims = {(row.procedure_id, relationship) for row in rows for relationship in row.relationships}
    return SancionesProcedimientosSummary(
        procedures=len({row.procedure_id for row in rows}),
        resolutions=len({row.resolution_id for row in rows}),
        claims=len(unique_claims),
        relationships=len(unique_claims),
        evidence=sum(row.evidence for row in rows),
        rows=tuple(sorted(rows, key=lambda item: item.procedure_name.lower())),
    )


def render_sanciones_procedimientos_summary_text(summary: SancionesProcedimientosSummary) -> str:
    lines = [
        "sanciones_procedimientos_summary:",
        f"  procedures={summary.procedures}",
        f"  resolutions={summary.resolutions}",
        f"  claims={summary.claims}",
        f"  relationships={summary.relationships}",
        f"  evidence={summary.evidence}",
    ]
    if not summary.rows:
        lines.append("  (no local sample records found)")
        return "\n".join(lines)
    for row in summary.rows:
        lines.extend(
            [
                "  procedure_connection:",
                f"    procedure={row.procedure_name}",
                f"    resolution={row.resolution_name}",
                f"    organization={row.organization_name}",
                f"    company={row.company_name}",
                f"    person={row.person_name}",
                f"    procedure_date={row.procedure_date.isoformat() if row.procedure_date else 'None'}",
                f"    resolution_date={row.resolution_date.isoformat() if row.resolution_date else 'None'}",
            ]
        )
    return "\n".join(lines)


def render_sanciones_procedimientos_import_result_text(result: SancionesProcedimientosImportResult) -> str:
    return "\n".join(
        [
            "sanciones_procedimientos_sample_loaded:",
            f"  source_records={result.source_records}",
            f"  claims={result.claims}",
            f"  evidences={result.evidences}",
            f"  entities={result.entities}",
            f"  relationship_public={result.relationship_public}",
            f"  procedure_entity_id={result.procedure_entity_id}",
            f"  procedure_name={result.procedure_name}",
            f"  resolution_entity_id={result.resolution_entity_id}",
            f"  resolution_name={result.resolution_name}",
        ]
    )


def _validate_sample_payload(payload: dict[str, Any]) -> None:
    if payload.get("classification") != LOCAL_TEST_DATA:
        raise ValueError("Sanciones y procedimientos sample must be marked LOCAL_TEST_DATA")
    if payload.get("official_status") != NOT_OFFICIAL_DATA:
        raise ValueError("Sanciones y procedimientos sample must be marked NOT_OFFICIAL_DATA")
    if "records" not in payload or not isinstance(payload["records"], list):
        raise ValueError("Sanciones y procedimientos sample must include a records array")
    for record in payload["records"]:
        for key in (
            "organization_name",
            "company_name",
            "person_name",
            "procedure_title",
            "procedure_date",
            "resolution_title",
            "resolution_date",
            "source_url",
        ):
            if not record.get(key):
                raise ValueError(f"Sanciones y procedimientos sample record must include {key}")


def _entity_record_for_name(session: Session, entity_type: EntityType, name: str, label: str) -> EntityRecord:
    candidates = match_entity_candidates(session, entity_type=entity_type.value, name=name, limit=1)
    if candidates:
        candidate = candidates[0]
        entity = session.get(Entity, UUID(candidate.candidate_entity_id)) if hasattr(session, "get") else None
        if entity is not None:
            return EntityRecord(
                entity_type=entity_type,
                external_id=str(entity.external_id),
                name=entity.name,
                description=entity.description,
                normalized_key=entity.normalized_key,
                status=entity.status,
                metadata=entity.entity_metadata or {},
            )
    external_id = f"sanciones:{label}:{normalized_key(name) or name.lower()}"
    return EntityRecord(
        entity_type=entity_type,
        external_id=external_id,
        name=name,
        normalized_key=normalized_key(name),
        metadata={
            "classification": LOCAL_TEST_DATA,
            "official_status": NOT_OFFICIAL_DATA,
            "dataset": SANCIONES_PROCEDIMIENTOS_SAMPLE_DATASET_NAME,
        },
    )


def _procedure_entity(record: dict[str, Any], classification: str, official_status: str) -> EntityRecord:
    return EntityRecord(
        entity_type=EntityType.ADMINISTRATIVE_PROCEDURE,
        external_id=f"sanciones:procedure:{record['external_id']}",
        name=str(record["procedure_title"]),
        description=f"{LOCAL_TEST_DATA} / {NOT_OFFICIAL_DATA} administrative procedure sample.",
        normalized_key=normalized_key(f"{record['procedure_number']} {record['organization_name']}"),
        metadata={
            "classification": classification,
            "official_status": official_status,
            "dataset": SANCIONES_PROCEDIMIENTOS_SAMPLE_DATASET_NAME,
            "procedure_number": record.get("procedure_number"),
            "procedure_status": record.get("procedure_status"),
        },
    )


def _resolution_entity(record: dict[str, Any], classification: str, official_status: str) -> EntityRecord:
    return EntityRecord(
        entity_type=EntityType.ADMINISTRATIVE_RESOLUTION,
        external_id=f"sanciones:resolution:{record['external_id']}",
        name=str(record["resolution_title"]),
        description=f"{LOCAL_TEST_DATA} / {NOT_OFFICIAL_DATA} administrative resolution sample.",
        normalized_key=normalized_key(f"{record['resolution_number']} {record['organization_name']}"),
        metadata={
            "classification": classification,
            "official_status": official_status,
            "dataset": SANCIONES_PROCEDIMIENTOS_SAMPLE_DATASET_NAME,
            "resolution_number": record.get("resolution_number"),
            "administrative_measure": record.get("administrative_measure"),
        },
    )


def _evidence(
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
        source_name=SANCIONES_PROCEDIMIENTOS_SAMPLE_SOURCE_NAME,
        title=title,
        url=url,
        published_at=published_at,
        excerpt=excerpt,
        metadata={
            "classification": LOCAL_TEST_DATA,
            "official_status": NOT_OFFICIAL_DATA,
            "dataset": SANCIONES_PROCEDIMIENTOS_SAMPLE_DATASET_NAME,
            "external_id": external_id,
        },
    )


def _claim(
    subject: EntityRecord,
    predicate: str,
    object_entity: EntityRecord,
    source_record: SourceRecordPayload,
    evidence: EvidenceRecord,
    record: dict[str, Any],
    valid_from: date | None,
) -> ClaimRecord:
    return ClaimRecord(
        subject_entity=subject,
        predicate=predicate,
        object_entity=object_entity,
        source_record=source_record,
        evidence=evidence,
        object_value={
            "procedure_number": record.get("procedure_number"),
            "resolution_number": record.get("resolution_number"),
            "classification": LOCAL_TEST_DATA,
            "official_status": NOT_OFFICIAL_DATA,
        },
        valid_from=valid_from,
        confidence=1.0,
        status=WorkflowStatus.VALIDATED,
        metadata={"dataset": SANCIONES_PROCEDIMIENTOS_SAMPLE_DATASET_NAME},
    )


def _relationship(
    source: EntityRecord,
    target: EntityRecord,
    relationship_type: RelationshipType,
    claim: ClaimRecord,
    published_at: date | None,
) -> PublicRelationshipRecord:
    published_datetime = datetime.combine(published_at, datetime.min.time(), tzinfo=timezone.utc) if published_at else datetime.now(timezone.utc)
    return PublicRelationshipRecord(
        source_entity=source,
        target_entity=target,
        relationship_type=relationship_type,
        claim=claim,
        published_at=published_datetime,
        status=WorkflowStatus.PUBLISHED,
        metadata={
            "classification": LOCAL_TEST_DATA,
            "official_status": NOT_OFFICIAL_DATA,
            "dataset": SANCIONES_PROCEDIMIENTOS_SAMPLE_DATASET_NAME,
        },
    )


def _load_procedure_claims(session: Session) -> list[Claim]:
    return list(
        session.scalars(
            select(Claim)
            .join(SourceRecord, Claim.source_record_id == SourceRecord.id)
            .options(joinedload(Claim.subject_entity), joinedload(Claim.object_entity))
            .where(SourceRecord.record_type == SANCIONES_PROCEDIMIENTOS_SAMPLE_RECORD_TYPE)
            .order_by(Claim.created_at, Claim.id)
        ).all()
    )


def _load_relationships(session: Session, source_record_id) -> tuple[RelationshipPublic, ...]:  # type: ignore[no-untyped-def]
    return tuple(
        session.scalars(
            select(RelationshipPublic)
            .join(Claim, RelationshipPublic.claim_id == Claim.id)
            .where(Claim.source_record_id == source_record_id)
            .order_by(RelationshipPublic.relationship_type.asc(), RelationshipPublic.id.asc())
        ).all()
    )


def _object_name(claims: list[Claim], predicate: str) -> str:
    match = next((claim for claim in claims if claim.predicate == predicate and claim.object_entity is not None), None)
    return match.object_entity.name if match is not None and match.object_entity is not None else ""


def _valid_from(claims: list[Claim], predicate: str) -> date | None:
    match = next((claim for claim in claims if claim.predicate == predicate), None)
    return match.valid_from if match is not None else None


def _count_evidence_for_source_record(session: Session, source_record_id) -> int:  # type: ignore[no-untyped-def]
    return int(session.scalar(select(func.count()).select_from(Evidence).where(Evidence.source_record_id == source_record_id)) or 0)


def _parse_date(value: object | None) -> date | None:
    if value is None:
        return None
    return date.fromisoformat(str(value))


def _count_rows(session: Session, model) -> int:  # type: ignore[no-untyped-def]
    return int(session.scalar(select(func.count()).select_from(model)) or 0)
