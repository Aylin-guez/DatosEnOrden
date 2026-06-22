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
CONTRALORIA_SAMPLE_DATASET_NAME = "contraloria-control-report-sample"
CONTRALORIA_SAMPLE_SOURCE_NAME = "DatosEnOrden Contraloria Sample"
CONTRALORIA_SAMPLE_SOURCE_URL = "local://sample/contraloria"
CONTRALORIA_SAMPLE_RECORD_TYPE = "contraloria:control_report_sample"
ORGANIZATION_HAS_CONTROL_REPORT_PREDICATE = "ORGANIZATION_HAS_CONTROL_REPORT"
CONTROL_REPORT_HAS_OBSERVATION_PREDICATE = "CONTROL_REPORT_HAS_OBSERVATION"
CONTRALORIA_SAMPLE_PATH = PROJECT_ROOT / "data" / "sample" / "contraloria_sample.json"


@dataclass(frozen=True)
class ContraloriaMatchResult:
    entity: Entity
    match_method: str
    confidence: float


@dataclass(frozen=True)
class ContraloriaImportResult:
    source_records: int
    claims: int
    evidences: int
    entities: int
    relationship_public: int
    organization_entity_id: str
    organization_name: str
    control_report_entity_id: str
    control_report_name: str
    observation_entity_id: str
    observation_name: str


@dataclass(frozen=True)
class ContraloriaSummaryRow:
    organization_id: str
    organization_name: str
    report_id: str
    report_name: str
    observation_id: str
    observation_name: str
    report_date: date | None
    observation_date: date | None
    claims: tuple[str, ...]
    relationships: tuple[str, ...]
    evidence: int
    organization_match_method: str
    organization_match_confidence: float


@dataclass(frozen=True)
class ContraloriaSummary:
    organizations: int
    reports: int
    observations: int
    claims: int
    relationships: int
    evidence: int
    rows: tuple[ContraloriaSummaryRow, ...]


def load_contraloria_sample_payload(input_path: Path | None = None) -> dict[str, Any]:
    path = input_path or CONTRALORIA_SAMPLE_PATH
    payload = json.loads(path.read_text(encoding="utf-8"))
    _validate_sample_payload(payload)
    return payload


def build_contraloria_sample_batch(session: Session, payload: dict[str, Any] | None = None) -> GraphBatch:
    sample = payload or load_contraloria_sample_payload()
    records = sample.get("records") or []
    if not records:
        raise ValueError("Contraloria sample must include at least one record")

    record = records[0]
    classification = str(sample["classification"])
    official_status = str(sample["official_status"])
    organization_name = str(record["organization_name"])
    report_title = str(record["report_title"])
    observation_text = str(record["observation_text"])
    report_number = str(record.get("report_number", ""))
    report_date = _parse_date(record.get("report_date"))
    observation_date = _parse_date(record.get("observation_date"))

    organization_match = _match_existing_organization(session, organization_name)
    organization_entity = _build_matched_organization_entity(organization_match)
    report_entity = _build_report_entity(record, classification, official_status)
    observation_entity = _build_observation_entity(record, classification, official_status)

    source_record_payload = {
        **record,
        "classification": classification,
        "official_status": official_status,
        "sample_markers": [LOCAL_TEST_DATA, NOT_OFFICIAL_DATA],
    }
    source_record = SourceRecordPayload(
        external_id=str(record["external_id"]),
        record_type=CONTRALORIA_SAMPLE_RECORD_TYPE,
        payload_hash=stable_json_hash(source_record_payload),
        raw_payload=source_record_payload,
        retrieved_at=datetime.now(timezone.utc),
        status=WorkflowStatus.NORMALIZED,
    )

    report_evidence = _build_evidence(
        source_record,
        external_id=f"{record['external_id']}:report",
        title=f"Contraloria local sample report - {report_number or organization_name}",
        url=f"{record['source_url']}/report",
        excerpt=(
            f"{LOCAL_TEST_DATA} / {NOT_OFFICIAL_DATA} control report sample for {organization_name}."
        ),
        published_at=report_date,
    )
    observation_evidence = _build_evidence(
        source_record,
        external_id=f"{record['external_id']}:observation",
        title=f"Contraloria local sample observation - {organization_name}",
        url=f"{record['source_url']}/observation",
        excerpt=(
            f"{LOCAL_TEST_DATA} / {NOT_OFFICIAL_DATA} neutral observation sample for {organization_name}."
        ),
        published_at=observation_date,
    )

    organization_claim = ClaimRecord(
        subject_entity=organization_entity,
        predicate=ORGANIZATION_HAS_CONTROL_REPORT_PREDICATE,
        object_entity=report_entity,
        source_record=source_record,
        evidence=report_evidence,
        object_value={
            "report_number": report_number,
            "report_title": report_title,
            "report_date": report_date.isoformat() if report_date else None,
            "classification": classification,
            "official_status": official_status,
        },
        valid_from=report_date,
        confidence=organization_match.confidence,
        status=WorkflowStatus.VALIDATED,
        metadata={"dataset": CONTRALORIA_SAMPLE_DATASET_NAME},
    )
    report_claim = ClaimRecord(
        subject_entity=report_entity,
        predicate=CONTROL_REPORT_HAS_OBSERVATION_PREDICATE,
        object_entity=observation_entity,
        source_record=source_record,
        evidence=observation_evidence,
        object_value={
            "observation_text": observation_text,
            "observation_date": observation_date.isoformat() if observation_date else None,
            "classification": classification,
            "official_status": official_status,
        },
        valid_from=observation_date,
        confidence=1.0,
        status=WorkflowStatus.VALIDATED,
        metadata={"dataset": CONTRALORIA_SAMPLE_DATASET_NAME},
    )

    organization_relationship = PublicRelationshipRecord(
        source_entity=organization_entity,
        target_entity=report_entity,
        relationship_type=RelationshipType.ORGANIZATION_HAS_CONTROL_REPORT,
        claim=organization_claim,
        published_at=datetime.now(timezone.utc),
        status=WorkflowStatus.PUBLISHED,
        metadata={
            "classification": classification,
            "official_status": official_status,
            "dataset": CONTRALORIA_SAMPLE_DATASET_NAME,
            "match_method": organization_match.match_method,
            "match_confidence": organization_match.confidence,
        },
    )
    report_relationship = PublicRelationshipRecord(
        source_entity=report_entity,
        target_entity=observation_entity,
        relationship_type=RelationshipType.CONTROL_REPORT_HAS_OBSERVATION,
        claim=report_claim,
        published_at=datetime.now(timezone.utc),
        status=WorkflowStatus.PUBLISHED,
        metadata={
            "classification": classification,
            "official_status": official_status,
            "dataset": CONTRALORIA_SAMPLE_DATASET_NAME,
        },
    )

    source = SourceInfo(
        name=CONTRALORIA_SAMPLE_SOURCE_NAME,
        publisher="DatosEnOrden",
        url=CONTRALORIA_SAMPLE_SOURCE_URL,
        license=f"{LOCAL_TEST_DATA} / {NOT_OFFICIAL_DATA}",
        retrieved_at=datetime.now(timezone.utc),
        metadata={
            "classification": classification,
            "official_status": official_status,
            "dataset": CONTRALORIA_SAMPLE_DATASET_NAME,
        },
    )
    dataset = DatasetRecord(
        source_name=CONTRALORIA_SAMPLE_SOURCE_NAME,
        name=CONTRALORIA_SAMPLE_DATASET_NAME,
        description=(
            "LOCAL_TEST_DATA / NOT_OFFICIAL_DATA sample used to validate control "
            "report and observation links"
        ),
        version="local-sample-1",
        dataset_url=f"{CONTRALORIA_SAMPLE_SOURCE_URL}/dataset",
        content_hash=stable_json_hash(sample),
        loaded_at=datetime.now(timezone.utc),
        metadata={
            "classification": classification,
            "official_status": official_status,
            "dataset": CONTRALORIA_SAMPLE_DATASET_NAME,
        },
    )
    return GraphBatch(
        source=source,
        dataset=dataset,
        source_records=(source_record,),
        entities=(organization_entity, report_entity, observation_entity),
        evidence=(report_evidence, observation_evidence),
        claims=(organization_claim, report_claim),
        public_relationships=(organization_relationship, report_relationship),
        raw_count=len(records),
        rejected_count=0,
        errors=(),
    )


def persist_contraloria_sample(session: Session, input_path: Path | None = None) -> ContraloriaImportResult:
    payload = load_contraloria_sample_payload(input_path)
    batch = build_contraloria_sample_batch(session, payload)
    GraphLoader(session).load(batch, dry_run=False)

    record = payload["records"][0]
    organization_match = _match_existing_organization(session, str(record["organization_name"]))
    report = session.scalar(
        select(Entity).where(
            Entity.entity_type == EntityType.CONTROL_REPORT.value,
            Entity.external_id == f"contraloria:report:{record['external_id']}",
        )
    )
    observation = session.scalar(
        select(Entity).where(
            Entity.entity_type == EntityType.PUBLIC_OBSERVATION.value,
            Entity.external_id == f"contraloria:observation:{record['external_id']}",
        )
    )
    if report is None or observation is None:
        raise LookupError("Contraloria sample entities not found after load")
    return ContraloriaImportResult(
        source_records=_count_rows(session, SourceRecord),
        claims=_count_rows(session, Claim),
        evidences=_count_rows(session, Evidence),
        entities=_count_rows(session, Entity),
        relationship_public=_count_rows(session, RelationshipPublic),
        organization_entity_id=str(organization_match.entity.id),
        organization_name=organization_match.entity.name,
        control_report_entity_id=str(report.id),
        control_report_name=report.name,
        observation_entity_id=str(observation.id),
        observation_name=observation.name,
    )


def read_contraloria_summary(session: Session) -> ContraloriaSummary:
    report_claims = _load_report_claims(session)
    rows: list[ContraloriaSummaryRow] = []
    for report_claim in report_claims:
        organization = report_claim.subject_entity
        report = report_claim.object_entity
        source_record = report_claim.source_record
        if organization is None or report is None or source_record is None:
            continue
        observation_claim = _load_observation_claim(session, source_record.id)
        if observation_claim is None or observation_claim.subject_entity is None:
            continue
        relationships = _load_contraloria_relationships(session, source_record.id)
        rows.append(
            ContraloriaSummaryRow(
                organization_id=str(organization.id),
                organization_name=organization.name,
                report_id=str(report.id),
                report_name=report.name,
                observation_id=str(observation_claim.subject_entity.id),
                observation_name=observation_claim.subject_entity.name,
                report_date=report_claim.valid_from,
                observation_date=observation_claim.valid_from,
                claims=(report_claim.predicate, observation_claim.predicate),
                relationships=tuple(relationship.relationship_type for relationship in relationships),
                evidence=_count_evidence_for_source_record(session, source_record.id),
                organization_match_method=_metadata_value(relationships, ORGANIZATION_HAS_CONTROL_REPORT_PREDICATE, "match_method"),
                organization_match_confidence=_metadata_float(
                    relationships,
                    ORGANIZATION_HAS_CONTROL_REPORT_PREDICATE,
                    "match_confidence",
                    float(getattr(report_claim, "confidence", 1.0)),
                ),
            )
        )

    unique_orgs = {row.organization_id for row in rows}
    unique_reports = {row.report_id for row in rows}
    unique_observations = {row.observation_id for row in rows}
    unique_claims = {(row.report_id, claim) for row in rows for claim in row.claims}
    unique_relationships = {(row.report_id, relationship) for row in rows for relationship in row.relationships}
    return ContraloriaSummary(
        organizations=len(unique_orgs),
        reports=len(unique_reports),
        observations=len(unique_observations),
        claims=len(unique_claims),
        relationships=len(unique_relationships),
        evidence=sum(row.evidence for row in rows),
        rows=tuple(sorted(rows, key=lambda item: (item.organization_name.lower(), item.report_name.lower()))),
    )


def render_contraloria_summary_text(summary: ContraloriaSummary) -> str:
    lines = [
        "contraloria_summary:",
        f"  organizations={summary.organizations}",
        f"  reports={summary.reports}",
        f"  observations={summary.observations}",
        f"  claims={summary.claims}",
        f"  relationships={summary.relationships}",
        f"  evidence={summary.evidence}",
        "  matched_entities:",
    ]
    if not summary.rows:
        lines.append("    (no contraloria sample reports found)")
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
                "  report_connection:",
                f"    organization={row.organization_name}",
                f"    report={row.report_name}",
                f"    observation={row.observation_name}",
                f"    report_date={row.report_date.isoformat() if row.report_date else 'None'}",
                f"    observation_date={row.observation_date.isoformat() if row.observation_date else 'None'}",
            ]
        )
    return "\n".join(lines)


def render_contraloria_import_result_text(result: ContraloriaImportResult) -> str:
    return "\n".join(
        [
            "contraloria_sample_loaded:",
            f"  source_records={result.source_records}",
            f"  claims={result.claims}",
            f"  evidences={result.evidences}",
            f"  entities={result.entities}",
            f"  relationship_public={result.relationship_public}",
            f"  organization_entity_id={result.organization_entity_id}",
            f"  organization_name={result.organization_name}",
            f"  control_report_entity_id={result.control_report_entity_id}",
            f"  control_report_name={result.control_report_name}",
            f"  observation_entity_id={result.observation_entity_id}",
            f"  observation_name={result.observation_name}",
        ]
    )


def contraloria_human_explanation() -> str:
    return "\n".join(
        [
            "Contraloria muestra informes de control de muestra.",
            "Este prototipo usa datos de muestra, no datos oficiales.",
            "No implica irregularidad; solo representa informacion publica o de muestra.",
        ]
    )


def _validate_sample_payload(payload: dict[str, Any]) -> None:
    if payload.get("classification") != LOCAL_TEST_DATA:
        raise ValueError("Contraloria sample must be marked LOCAL_TEST_DATA")
    if payload.get("official_status") != NOT_OFFICIAL_DATA:
        raise ValueError("Contraloria sample must be marked NOT_OFFICIAL_DATA")
    if "records" not in payload or not isinstance(payload["records"], list):
        raise ValueError("Contraloria sample must include a records array")
    for record in payload["records"]:
        for key in (
            "organization_name",
            "report_title",
            "observation_text",
            "report_date",
            "observation_date",
            "source_url",
            "source_dataset_name",
        ):
            if not record.get(key):
                raise ValueError(f"Contraloria sample record must include {key}")


def _match_existing_organization(session: Session, organization_name: str) -> ContraloriaMatchResult:
    candidates = match_entity_candidates(
        session,
        entity_type=EntityType.PUBLIC_ORGANIZATION.value,
        name=organization_name,
        limit=1,
    )
    if not candidates:
        external_id = f"contraloria:local:public_organization:{normalized_key(organization_name) or organization_name.lower()}"
        return ContraloriaMatchResult(
            entity=Entity(
                id=uuid5(NAMESPACE_URL, external_id),
                entity_type=EntityType.PUBLIC_ORGANIZATION.value,
                name=organization_name,
                external_id=external_id,
                normalized_key=normalized_key(organization_name),
                status="active",
                entity_metadata={
                    "classification": LOCAL_TEST_DATA,
                    "official_status": NOT_OFFICIAL_DATA,
                    "dataset": CONTRALORIA_SAMPLE_DATASET_NAME,
                    "match_note": "No existing entity was available; local sample entity created.",
                },
            ),
            match_method="local_sample_no_existing_match",
            confidence=0.5,
        )

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
    return ContraloriaMatchResult(entity=entity, match_method=candidate.match_method, confidence=candidate.score)


def _build_matched_organization_entity(match: ContraloriaMatchResult) -> EntityRecord:
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


def _build_report_entity(record: dict[str, Any], classification: str, official_status: str) -> EntityRecord:
    report_title = str(record["report_title"])
    report_number = str(record.get("report_number", ""))
    organization_name = str(record["organization_name"])
    report_date = str(record["report_date"])
    return EntityRecord(
        entity_type=EntityType.CONTROL_REPORT,
        external_id=f"contraloria:report:{record['external_id']}",
        name=f"{report_title} - {organization_name}",
        description=(
            f"{LOCAL_TEST_DATA} / {NOT_OFFICIAL_DATA} Contraloria control report sample."
        ),
        normalized_key=normalized_key(f"{organization_name} {report_number} {report_date}"),
        metadata={
            "classification": classification,
            "official_status": official_status,
            "dataset": CONTRALORIA_SAMPLE_DATASET_NAME,
            "organization_name": organization_name,
            "report_number": report_number,
            "report_title": report_title,
            "report_date": report_date,
        },
    )


def _build_observation_entity(record: dict[str, Any], classification: str, official_status: str) -> EntityRecord:
    observation_text = str(record["observation_text"])
    report_number = str(record.get("report_number", ""))
    organization_name = str(record["organization_name"])
    observation_date = str(record["observation_date"])
    return EntityRecord(
        entity_type=EntityType.PUBLIC_OBSERVATION,
        external_id=f"contraloria:observation:{record['external_id']}",
        name=f"Observation {report_number or observation_date} - {organization_name}",
        description=(
            f"{LOCAL_TEST_DATA} / {NOT_OFFICIAL_DATA} neutral observation sample. "
            f"{observation_text}"
        ),
        normalized_key=normalized_key(f"{organization_name} {report_number} {observation_date}"),
        metadata={
            "classification": classification,
            "official_status": official_status,
            "dataset": CONTRALORIA_SAMPLE_DATASET_NAME,
            "organization_name": organization_name,
            "report_number": report_number,
            "observation_text": observation_text,
            "observation_date": observation_date,
        },
    )


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
        source_name=CONTRALORIA_SAMPLE_SOURCE_NAME,
        title=title,
        url=url,
        published_at=published_at,
        excerpt=excerpt,
        metadata={
            "classification": LOCAL_TEST_DATA,
            "official_status": NOT_OFFICIAL_DATA,
            "dataset": CONTRALORIA_SAMPLE_DATASET_NAME,
            "external_id": external_id,
        },
    )


def _load_report_claims(session: Session) -> list[Claim]:
    return list(
        session.scalars(
            select(Claim)
            .join(SourceRecord, Claim.source_record_id == SourceRecord.id)
            .options(joinedload(Claim.subject_entity), joinedload(Claim.object_entity), joinedload(Claim.source_record))
            .where(
                SourceRecord.record_type == CONTRALORIA_SAMPLE_RECORD_TYPE,
                Claim.predicate == ORGANIZATION_HAS_CONTROL_REPORT_PREDICATE,
            )
            .order_by(Claim.created_at, Claim.id)
        ).all()
    )


def _load_observation_claim(session: Session, source_record_id) -> Claim | None:  # type: ignore[no-untyped-def]
    return session.scalar(
        select(Claim)
        .options(joinedload(Claim.subject_entity), joinedload(Claim.object_entity))
        .where(
            Claim.source_record_id == source_record_id,
            Claim.predicate == CONTROL_REPORT_HAS_OBSERVATION_PREDICATE,
        )
        .order_by(Claim.created_at, Claim.id)
    )


def _load_contraloria_relationships(session: Session, source_record_id) -> tuple[RelationshipPublic, ...]:  # type: ignore[no-untyped-def]
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
        session.scalar(
            select(func.count()).select_from(Evidence).where(Evidence.source_record_id == source_record_id)
        )
        or 0
    )


def _metadata_value(relationships: tuple[RelationshipPublic, ...], relationship_type: str, key: str) -> str:
    for relationship in relationships:
        if relationship.relationship_type != relationship_type:
            continue
        metadata = relationship.relationship_metadata or {}
        if metadata.get(key) is not None:
            return str(metadata[key])
    return "unknown"


def _metadata_float(
    relationships: tuple[RelationshipPublic, ...],
    relationship_type: str,
    key: str,
    default: float,
) -> float:
    for relationship in relationships:
        if relationship.relationship_type != relationship_type:
            continue
        metadata = relationship.relationship_metadata or {}
        if metadata.get(key) is not None:
            return float(metadata[key])
    return default


def _parse_date(value: object | None) -> date | None:
    if value is None:
        return None
    return date.fromisoformat(str(value))


def _count_rows(session: Session, model) -> int:  # type: ignore[no-untyped-def]
    return int(session.scalar(select(func.count()).select_from(model)) or 0)
