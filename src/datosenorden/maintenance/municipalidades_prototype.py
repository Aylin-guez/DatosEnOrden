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
from datosenorden.models import Claim, Entity, Evidence, RelationshipPublic, SourceRecord

LOCAL_TEST_DATA = "LOCAL_TEST_DATA"
NOT_OFFICIAL_DATA = "NOT_OFFICIAL_DATA"
MUNICIPALIDADES_SAMPLE_DATASET_NAME = "municipalidades-project-sample"
MUNICIPALIDADES_SAMPLE_SOURCE_NAME = "DatosEnOrden Municipalidades Sample"
MUNICIPALIDADES_SAMPLE_SOURCE_URL = "local://sample/municipalidades"
MUNICIPALIDADES_SAMPLE_RECORD_TYPE = "municipalidades:project_sample"
MUNICIPALITY_EXECUTES_PROJECT_PREDICATE = "MUNICIPALITY_EXECUTES_PROJECT"
MUNICIPALITY_SPENDS_ON_PREDICATE = "MUNICIPALITY_SPENDS_ON"
MUNICIPALIDADES_SAMPLE_PATH = PROJECT_ROOT / "data" / "sample" / "municipalidad_sample.json"


@dataclass(frozen=True)
class MunicipalidadesImportResult:
    source_records: int
    claims: int
    evidences: int
    entities: int
    relationship_public: int
    municipality_entity_id: str
    municipality_name: str
    project_entity_id: str
    project_name: str
    spending_item_entity_id: str
    spending_item_name: str


@dataclass(frozen=True)
class MunicipalidadesSummaryRow:
    municipality_id: str
    municipality_name: str
    project_id: str
    project_name: str
    spending_item_id: str
    spending_item_name: str
    period: str
    amount: int | None
    currency: str | None
    claims: tuple[str, ...]
    relationships: tuple[str, ...]
    evidence: int


@dataclass(frozen=True)
class MunicipalidadesSummary:
    municipalities: int
    projects: int
    spending_items: int
    claims: int
    relationships: int
    evidence: int
    rows: tuple[MunicipalidadesSummaryRow, ...]


def load_municipalidades_sample_payload(input_path: Path | None = None) -> dict[str, Any]:
    path = input_path or MUNICIPALIDADES_SAMPLE_PATH
    payload = json.loads(path.read_text(encoding="utf-8"))
    _validate_sample_payload(payload)
    return payload


def build_municipalidades_sample_batch(session: Session, payload: dict[str, Any] | None = None) -> GraphBatch:
    sample = payload or load_municipalidades_sample_payload()
    records = sample.get("records") or []
    if not records:
        raise ValueError("Municipalidades sample must include at least one record")

    record = records[0]
    classification = str(sample["classification"])
    official_status = str(sample["official_status"])
    municipality_name = str(record["municipality_name"])
    project_name = str(record["project_name"])
    spending_item_name = str(record["spending_item_name"])
    period = str(record["period"])
    amount = int(record["amount"])
    currency = str(record["currency"])
    period_date = _parse_date(record.get("period_date"))

    municipality_entity = _build_municipality_entity(record, classification, official_status)
    project_entity = _build_project_entity(record, classification, official_status)
    spending_item_entity = _build_spending_item_entity(record, classification, official_status)

    source_record_payload = {
        **record,
        "classification": classification,
        "official_status": official_status,
        "sample_markers": [LOCAL_TEST_DATA, NOT_OFFICIAL_DATA],
    }
    source_record = SourceRecordPayload(
        external_id=str(record["external_id"]),
        record_type=MUNICIPALIDADES_SAMPLE_RECORD_TYPE,
        payload_hash=stable_json_hash(source_record_payload),
        raw_payload=source_record_payload,
        retrieved_at=datetime.now(timezone.utc),
        status=WorkflowStatus.NORMALIZED,
    )

    project_evidence = _build_evidence(
        source_record,
        external_id=f"{record['external_id']}:project",
        title=f"Municipalidades local sample project - {project_name}",
        url=f"{record['source_url']}/project",
        excerpt=f"{LOCAL_TEST_DATA} / {NOT_OFFICIAL_DATA} project sample for {municipality_name}.",
        published_at=period_date,
    )
    spending_evidence = _build_evidence(
        source_record,
        external_id=f"{record['external_id']}:spending",
        title=f"Municipalidades local sample spending - {spending_item_name}",
        url=f"{record['source_url']}/spending",
        excerpt=f"{LOCAL_TEST_DATA} / {NOT_OFFICIAL_DATA} spending item sample for {municipality_name}.",
        published_at=period_date,
    )

    project_claim = ClaimRecord(
        subject_entity=municipality_entity,
        predicate=MUNICIPALITY_EXECUTES_PROJECT_PREDICATE,
        object_entity=project_entity,
        source_record=source_record,
        evidence=project_evidence,
        object_value={
            "project_name": project_name,
            "period": period,
            "amount": amount,
            "currency": currency,
            "classification": classification,
            "official_status": official_status,
        },
        valid_from=period_date,
        confidence=1.0,
        status=WorkflowStatus.VALIDATED,
        metadata={"dataset": MUNICIPALIDADES_SAMPLE_DATASET_NAME},
    )
    spending_claim = ClaimRecord(
        subject_entity=municipality_entity,
        predicate=MUNICIPALITY_SPENDS_ON_PREDICATE,
        object_entity=spending_item_entity,
        source_record=source_record,
        evidence=spending_evidence,
        object_value={
            "spending_item_name": spending_item_name,
            "period": period,
            "amount": amount,
            "currency": currency,
            "classification": classification,
            "official_status": official_status,
        },
        valid_from=period_date,
        confidence=1.0,
        status=WorkflowStatus.VALIDATED,
        metadata={"dataset": MUNICIPALIDADES_SAMPLE_DATASET_NAME},
    )

    project_relationship = PublicRelationshipRecord(
        source_entity=municipality_entity,
        target_entity=project_entity,
        relationship_type=RelationshipType.MUNICIPALITY_EXECUTES_PROJECT,
        claim=project_claim,
        published_at=datetime.now(timezone.utc),
        status=WorkflowStatus.PUBLISHED,
        metadata={
            "classification": classification,
            "official_status": official_status,
            "dataset": MUNICIPALIDADES_SAMPLE_DATASET_NAME,
        },
    )
    spending_relationship = PublicRelationshipRecord(
        source_entity=municipality_entity,
        target_entity=spending_item_entity,
        relationship_type=RelationshipType.MUNICIPALITY_SPENDS_ON,
        claim=spending_claim,
        published_at=datetime.now(timezone.utc),
        status=WorkflowStatus.PUBLISHED,
        metadata={
            "classification": classification,
            "official_status": official_status,
            "dataset": MUNICIPALIDADES_SAMPLE_DATASET_NAME,
        },
    )

    source = SourceInfo(
        name=MUNICIPALIDADES_SAMPLE_SOURCE_NAME,
        publisher="DatosEnOrden",
        url=MUNICIPALIDADES_SAMPLE_SOURCE_URL,
        license=f"{LOCAL_TEST_DATA} / {NOT_OFFICIAL_DATA}",
        retrieved_at=datetime.now(timezone.utc),
        metadata={
            "classification": classification,
            "official_status": official_status,
            "dataset": MUNICIPALIDADES_SAMPLE_DATASET_NAME,
        },
    )
    dataset = DatasetRecord(
        source_name=MUNICIPALIDADES_SAMPLE_SOURCE_NAME,
        name=MUNICIPALIDADES_SAMPLE_DATASET_NAME,
        description=(
            "LOCAL_TEST_DATA / NOT_OFFICIAL_DATA sample used to validate municipal "
            "project and spending links"
        ),
        version="local-sample-1",
        dataset_url=f"{MUNICIPALIDADES_SAMPLE_SOURCE_URL}/dataset",
        content_hash=stable_json_hash(sample),
        loaded_at=datetime.now(timezone.utc),
        metadata={
            "classification": classification,
            "official_status": official_status,
            "dataset": MUNICIPALIDADES_SAMPLE_DATASET_NAME,
        },
    )
    return GraphBatch(
        source=source,
        dataset=dataset,
        source_records=(source_record,),
        entities=(municipality_entity, project_entity, spending_item_entity),
        evidence=(project_evidence, spending_evidence),
        claims=(project_claim, spending_claim),
        public_relationships=(project_relationship, spending_relationship),
        raw_count=len(records),
        rejected_count=0,
        errors=(),
    )


def persist_municipalidades_sample(session: Session, input_path: Path | None = None) -> MunicipalidadesImportResult:
    payload = load_municipalidades_sample_payload(input_path)
    batch = build_municipalidades_sample_batch(session, payload)
    GraphLoader(session).load(batch, dry_run=False)

    record = payload["records"][0]
    municipality = session.scalar(
        select(Entity).where(
            Entity.entity_type == EntityType.MUNICIPALITY.value,
            Entity.external_id == f"municipalidades:municipality:{record['external_id']}",
        )
    )
    project = session.scalar(
        select(Entity).where(
            Entity.entity_type == EntityType.PUBLIC_PROJECT.value,
            Entity.external_id == f"municipalidades:project:{record['external_id']}",
        )
    )
    spending_item = session.scalar(
        select(Entity).where(
            Entity.entity_type == EntityType.SPENDING_ITEM.value,
            Entity.external_id == f"municipalidades:spending:{record['external_id']}",
        )
    )
    if municipality is None or project is None or spending_item is None:
        raise LookupError("Municipalidades sample entities not found after load")
    return MunicipalidadesImportResult(
        source_records=_count_rows(session, SourceRecord),
        claims=_count_rows(session, Claim),
        evidences=_count_rows(session, Evidence),
        entities=_count_rows(session, Entity),
        relationship_public=_count_rows(session, RelationshipPublic),
        municipality_entity_id=str(municipality.id),
        municipality_name=municipality.name,
        project_entity_id=str(project.id),
        project_name=project.name,
        spending_item_entity_id=str(spending_item.id),
        spending_item_name=spending_item.name,
    )


def read_municipalidades_summary(session: Session) -> MunicipalidadesSummary:
    project_claims = _load_project_claims(session)
    rows: list[MunicipalidadesSummaryRow] = []
    for project_claim in project_claims:
        municipality = project_claim.subject_entity
        project = project_claim.object_entity
        source_record = project_claim.source_record
        if municipality is None or project is None or source_record is None:
            continue
        spending_claim = _load_spending_claim(session, source_record.id)
        if spending_claim is None or spending_claim.object_entity is None:
            continue
        relationships = _load_municipalidades_relationships(session, source_record.id)
        data = getattr(project_claim, "object_value", None) or {}
        rows.append(
            MunicipalidadesSummaryRow(
                municipality_id=str(municipality.id),
                municipality_name=municipality.name,
                project_id=str(project.id),
                project_name=project.name,
                spending_item_id=str(spending_claim.object_entity.id),
                spending_item_name=spending_claim.object_entity.name,
                period=str(data.get("period", "")),
                amount=int(data.get("amount")) if data.get("amount") is not None else None,
                currency=str(data.get("currency")) if data.get("currency") is not None else None,
                claims=(project_claim.predicate, spending_claim.predicate),
                relationships=tuple(relationship.relationship_type for relationship in relationships),
                evidence=_count_evidence_for_source_record(session, source_record.id),
            )
        )

    unique_municipalities = {row.municipality_id for row in rows}
    unique_projects = {row.project_id for row in rows}
    unique_spending_items = {row.spending_item_id for row in rows}
    unique_claims = {(row.project_id, claim) for row in rows for claim in row.claims}
    unique_relationships = {(row.project_id, relationship) for row in rows for relationship in row.relationships}
    return MunicipalidadesSummary(
        municipalities=len(unique_municipalities),
        projects=len(unique_projects),
        spending_items=len(unique_spending_items),
        claims=len(unique_claims),
        relationships=len(unique_relationships),
        evidence=sum(row.evidence for row in rows),
        rows=tuple(sorted(rows, key=lambda item: (item.municipality_name.lower(), item.project_name.lower()))),
    )


def render_municipalidades_summary_text(summary: MunicipalidadesSummary) -> str:
    lines = [
        "municipalidades_summary:",
        f"  municipalities={summary.municipalities}",
        f"  projects={summary.projects}",
        f"  spending_items={summary.spending_items}",
        f"  claims={summary.claims}",
        f"  relationships={summary.relationships}",
        f"  evidence={summary.evidence}",
    ]
    for row in summary.rows:
        lines.extend(
            [
                "  project_connection:",
                f"    municipality={row.municipality_name}",
                f"    project={row.project_name}",
                f"    spending_item={row.spending_item_name}",
                f"    period={row.period}",
                f"    amount={row.amount if row.amount is not None else 'None'}",
                f"    currency={row.currency or 'None'}",
            ]
        )
    return "\n".join(lines)


def render_municipalidades_import_result_text(result: MunicipalidadesImportResult) -> str:
    return "\n".join(
        [
            "municipalidades_sample_loaded:",
            f"  source_records={result.source_records}",
            f"  claims={result.claims}",
            f"  evidences={result.evidences}",
            f"  entities={result.entities}",
            f"  relationship_public={result.relationship_public}",
            f"  municipality_entity_id={result.municipality_entity_id}",
            f"  municipality_name={result.municipality_name}",
            f"  project_entity_id={result.project_entity_id}",
            f"  project_name={result.project_name}",
            f"  spending_item_entity_id={result.spending_item_entity_id}",
            f"  spending_item_name={result.spending_item_name}",
        ]
    )


def municipalidades_human_explanation() -> str:
    return "\n".join(
        [
            "Municipalidades muestra proyectos y gastos de muestra.",
            "Este prototipo usa datos de muestra, no datos oficiales.",
            "No implica irregularidad; solo representa informacion publica o de muestra.",
        ]
    )


def _validate_sample_payload(payload: dict[str, Any]) -> None:
    if payload.get("classification") != LOCAL_TEST_DATA:
        raise ValueError("Municipalidades sample must be marked LOCAL_TEST_DATA")
    if payload.get("official_status") != NOT_OFFICIAL_DATA:
        raise ValueError("Municipalidades sample must be marked NOT_OFFICIAL_DATA")
    if "records" not in payload or not isinstance(payload["records"], list):
        raise ValueError("Municipalidades sample must include a records array")
    for record in payload["records"]:
        for key in (
            "municipality_name",
            "project_name",
            "spending_item_name",
            "period",
            "period_date",
            "amount",
            "currency",
            "source_url",
            "source_dataset_name",
        ):
            if key not in record or record[key] in (None, ""):
                raise ValueError(f"Municipalidades sample record must include {key}")


def _build_municipality_entity(record: dict[str, Any], classification: str, official_status: str) -> EntityRecord:
    municipality_name = str(record["municipality_name"])
    return EntityRecord(
        entity_type=EntityType.MUNICIPALITY,
        external_id=f"municipalidades:municipality:{record['external_id']}",
        name=municipality_name,
        description=(
            f"{LOCAL_TEST_DATA} / {NOT_OFFICIAL_DATA} municipal sample entity."
        ),
        normalized_key=normalized_key(municipality_name),
        metadata={
            "classification": classification,
            "official_status": official_status,
            "dataset": MUNICIPALIDADES_SAMPLE_DATASET_NAME,
            "municipality_name": municipality_name,
        },
    )


def _build_project_entity(record: dict[str, Any], classification: str, official_status: str) -> EntityRecord:
    municipality_name = str(record["municipality_name"])
    project_name = str(record["project_name"])
    return EntityRecord(
        entity_type=EntityType.PUBLIC_PROJECT,
        external_id=f"municipalidades:project:{record['external_id']}",
        name=project_name,
        description=(
            f"{LOCAL_TEST_DATA} / {NOT_OFFICIAL_DATA} public project sample for {municipality_name}."
        ),
        normalized_key=normalized_key(f"{municipality_name} {project_name}"),
        metadata={
            "classification": classification,
            "official_status": official_status,
            "dataset": MUNICIPALIDADES_SAMPLE_DATASET_NAME,
            "municipality_name": municipality_name,
            "project_name": project_name,
        },
    )


def _build_spending_item_entity(record: dict[str, Any], classification: str, official_status: str) -> EntityRecord:
    municipality_name = str(record["municipality_name"])
    spending_item_name = str(record["spending_item_name"])
    return EntityRecord(
        entity_type=EntityType.SPENDING_ITEM,
        external_id=f"municipalidades:spending:{record['external_id']}",
        name=spending_item_name,
        description=(
            f"{LOCAL_TEST_DATA} / {NOT_OFFICIAL_DATA} spending item sample for {municipality_name}."
        ),
        normalized_key=normalized_key(f"{municipality_name} {spending_item_name}"),
        metadata={
            "classification": classification,
            "official_status": official_status,
            "dataset": MUNICIPALIDADES_SAMPLE_DATASET_NAME,
            "municipality_name": municipality_name,
            "spending_item_name": spending_item_name,
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
        source_name=MUNICIPALIDADES_SAMPLE_SOURCE_NAME,
        title=title,
        url=url,
        published_at=published_at,
        excerpt=excerpt,
        metadata={
            "classification": LOCAL_TEST_DATA,
            "official_status": NOT_OFFICIAL_DATA,
            "dataset": MUNICIPALIDADES_SAMPLE_DATASET_NAME,
            "external_id": external_id,
        },
    )


def _load_project_claims(session: Session) -> list[Claim]:
    return list(
        session.scalars(
            select(Claim)
            .join(SourceRecord, Claim.source_record_id == SourceRecord.id)
            .options(joinedload(Claim.subject_entity), joinedload(Claim.object_entity), joinedload(Claim.source_record))
            .where(
                SourceRecord.record_type == MUNICIPALIDADES_SAMPLE_RECORD_TYPE,
                Claim.predicate == MUNICIPALITY_EXECUTES_PROJECT_PREDICATE,
            )
            .order_by(Claim.created_at, Claim.id)
        ).all()
    )


def _load_spending_claim(session: Session, source_record_id) -> Claim | None:  # type: ignore[no-untyped-def]
    return session.scalar(
        select(Claim)
        .options(joinedload(Claim.subject_entity), joinedload(Claim.object_entity))
        .where(
            Claim.source_record_id == source_record_id,
            Claim.predicate == MUNICIPALITY_SPENDS_ON_PREDICATE,
        )
        .order_by(Claim.created_at, Claim.id)
    )


def _load_municipalidades_relationships(session: Session, source_record_id) -> tuple[RelationshipPublic, ...]:  # type: ignore[no-untyped-def]
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


def _parse_date(value: object | None) -> date | None:
    if value is None:
        return None
    return date.fromisoformat(str(value))


def _count_rows(session: Session, model) -> int:  # type: ignore[no-untyped-def]
    return int(session.scalar(select(func.count()).select_from(model)) or 0)
