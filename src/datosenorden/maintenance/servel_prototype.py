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
SERVEL_SAMPLE_DATASET_NAME = "servel-authorities-sample"
SERVEL_SAMPLE_SOURCE_NAME = "DatosEnOrden Servel Sample"
SERVEL_SAMPLE_SOURCE_URL = "local://sample/servel"
SERVEL_SAMPLE_RECORD_TYPE = "servel:authority_sample"
AUTHORITY_ELECTED_TO_OFFICE_PREDICATE = "AUTHORITY_ELECTED_TO_OFFICE"
AUTHORITY_REPRESENTS_TERRITORY_PREDICATE = "AUTHORITY_REPRESENTS_TERRITORY"
OFFICE_BELONGS_TO_MUNICIPALITY_PREDICATE = "OFFICE_BELONGS_TO_MUNICIPALITY"
AUTHORITY_HAS_ELECTORAL_PERIOD_PREDICATE = "AUTHORITY_HAS_ELECTORAL_PERIOD"
SERVEL_SAMPLE_PATH = PROJECT_ROOT / "data" / "sample" / "servel_authorities_sample.json"


@dataclass(frozen=True)
class ServelImportResult:
    source_records: int
    claims: int
    evidences: int
    entities: int
    relationship_public: int
    authorities: int
    offices: int
    territories: int
    periods: int


@dataclass(frozen=True)
class ServelSummaryRow:
    authority_id: str
    authority_name: str
    office_id: str
    office_name: str
    territory_id: str
    territory_name: str
    period_id: str
    period_name: str
    period_start: date | None
    period_end: date | None
    claims: tuple[str, ...]
    relationships: tuple[str, ...]
    evidence: int


@dataclass(frozen=True)
class ServelSummary:
    authorities: int
    offices: int
    territories: int
    periods: int
    relationships: int
    evidence: int
    rows: tuple[ServelSummaryRow, ...]


def load_servel_sample_payload(input_path: Path | None = None) -> dict[str, Any]:
    path = input_path or SERVEL_SAMPLE_PATH
    payload = json.loads(path.read_text(encoding="utf-8"))
    _validate_sample_payload(payload)
    return payload


def build_servel_sample_batch(session: Session, payload: dict[str, Any] | None = None) -> GraphBatch:
    _ = session
    sample = payload or load_servel_sample_payload()
    records = sample.get("records") or []
    if not records:
        raise ValueError("SERVEL sample must include at least one record")

    classification = str(sample["classification"])
    official_status = str(sample["official_status"])

    source_records: list[SourceRecordPayload] = []
    entities: list[EntityRecord] = []
    evidence: list[EvidenceRecord] = []
    claims: list[ClaimRecord] = []
    public_relationships: list[PublicRelationshipRecord] = []

    for record in records:
        parsed = _build_record_components(record, classification, official_status)
        source_records.append(parsed["source_record"])
        entities.extend(parsed["entities"])
        evidence.extend(parsed["evidence"])
        claims.extend(parsed["claims"])
        public_relationships.extend(parsed["public_relationships"])

    source = SourceInfo(
        name=SERVEL_SAMPLE_SOURCE_NAME,
        publisher="DatosEnOrden",
        url=SERVEL_SAMPLE_SOURCE_URL,
        license=f"{LOCAL_TEST_DATA} / {NOT_OFFICIAL_DATA}",
        retrieved_at=datetime.now(timezone.utc),
        metadata={
            "classification": classification,
            "official_status": official_status,
            "dataset": SERVEL_SAMPLE_DATASET_NAME,
        },
    )
    dataset = DatasetRecord(
        source_name=SERVEL_SAMPLE_SOURCE_NAME,
        name=SERVEL_SAMPLE_DATASET_NAME,
        description=(
            "LOCAL_TEST_DATA / NOT_OFFICIAL_DATA sample used to validate neutral "
            "elected authority graph links"
        ),
        version="local-sample-1",
        dataset_url=f"{SERVEL_SAMPLE_SOURCE_URL}/dataset",
        content_hash=stable_json_hash(sample),
        loaded_at=datetime.now(timezone.utc),
        metadata={
            "classification": classification,
            "official_status": official_status,
            "dataset": SERVEL_SAMPLE_DATASET_NAME,
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


def load_servel_sample(session: Session, input_path: Path | None = None) -> ServelImportResult:
    payload = load_servel_sample_payload(input_path)
    batch = build_servel_sample_batch(session, payload)
    GraphLoader(session).load(batch, dry_run=False)

    return ServelImportResult(
        source_records=_count_rows(session, SourceRecord),
        claims=_count_rows(session, Claim),
        evidences=_count_rows(session, Evidence),
        entities=_count_rows(session, Entity),
        relationship_public=_count_rows(session, RelationshipPublic),
        authorities=_count_entities(session, EntityType.PERSON.value),
        offices=_count_entities(session, EntityType.ROLE.value),
        territories=_count_entities(session, EntityType.MUNICIPALITY.value),
        periods=_count_entities(session, EntityType.ELECTORAL_PERIOD.value),
    )


def read_servel_summary(session: Session) -> ServelSummary:
    claims = _load_servel_authority_claims(session)
    rows: list[ServelSummaryRow] = []
    for authority_claim in claims:
        authority = authority_claim.subject_entity
        office = authority_claim.object_entity
        source_record = authority_claim.source_record
        if authority is None or office is None or source_record is None:
            continue
        territory_claim = _load_claim(session, source_record.id, AUTHORITY_REPRESENTS_TERRITORY_PREDICATE)
        period_claim = _load_claim(session, source_record.id, AUTHORITY_HAS_ELECTORAL_PERIOD_PREDICATE)
        if territory_claim is None or period_claim is None or territory_claim.object_entity is None or period_claim.object_entity is None:
            continue
        rows.append(
            ServelSummaryRow(
                authority_id=str(authority.id),
                authority_name=authority.name,
                office_id=str(office.id),
                office_name=office.name,
                territory_id=str(territory_claim.object_entity.id),
                territory_name=territory_claim.object_entity.name,
                period_id=str(period_claim.object_entity.id),
                period_name=period_claim.object_entity.name,
                period_start=_parse_date(_object_value_text(period_claim, "period_start")),
                period_end=_parse_date(_object_value_text(period_claim, "period_end")),
                claims=(
                    authority_claim.predicate,
                    territory_claim.predicate,
                    period_claim.predicate,
                    OFFICE_BELONGS_TO_MUNICIPALITY_PREDICATE,
                ),
                relationships=tuple(
                    relationship.relationship_type
                    for relationship in _load_servel_relationships(session, source_record.id)
                ),
                evidence=_count_evidence_for_source_record(session, source_record.id),
            )
        )

    unique_authorities = {row.authority_id for row in rows}
    unique_offices = {row.office_id for row in rows}
    unique_territories = {row.territory_id for row in rows}
    unique_periods = {row.period_id for row in rows}
    unique_relationships = {(row.authority_id, relationship) for row in rows for relationship in row.relationships}
    return ServelSummary(
        authorities=len(unique_authorities),
        offices=len(unique_offices),
        territories=len(unique_territories),
        periods=len(unique_periods),
        relationships=len(unique_relationships),
        evidence=sum(row.evidence for row in rows),
        rows=tuple(sorted(rows, key=lambda item: (item.authority_name.lower(), item.office_name.lower()))),
    )


def render_servel_summary_text(summary: ServelSummary) -> str:
    lines = [
        "servel_summary:",
        f"  authorities={summary.authorities}",
        f"  offices={summary.offices}",
        f"  territories={summary.territories}",
        f"  periods={summary.periods}",
        f"  relationships={summary.relationships}",
        f"  evidence={summary.evidence}",
    ]
    if not summary.rows:
        lines.append("  (no servel sample authorities found)")
        return "\n".join(lines)
    for row in summary.rows:
        lines.extend(
            [
                "  authority_connection:",
                f"    authority={row.authority_name}",
                f"    office={row.office_name}",
                f"    territory={row.territory_name}",
                f"    period={row.period_name}",
                f"    period_start={row.period_start.isoformat() if row.period_start else 'None'}",
                f"    period_end={row.period_end.isoformat() if row.period_end else 'None'}",
            ]
        )
    return "\n".join(lines)


def render_servel_import_result_text(result: ServelImportResult) -> str:
    return "\n".join(
        [
            "servel_sample_loaded:",
            f"  source_records={result.source_records}",
            f"  claims={result.claims}",
            f"  evidences={result.evidences}",
            f"  entities={result.entities}",
            f"  relationship_public={result.relationship_public}",
            f"  authorities={result.authorities}",
            f"  offices={result.offices}",
            f"  territories={result.territories}",
            f"  periods={result.periods}",
        ]
    )


def _build_record_components(
    record: dict[str, Any],
    classification: str,
    official_status: str,
) -> dict[str, Any]:
    authority_name = str(record["authority_name"])
    office_name = str(record["office_name"])
    municipality_name = str(record["municipality_name"])
    territory_name = str(record.get("territory_name", municipality_name))
    period_name = str(record["period_name"])
    period_start = _parse_date(record.get("period_start"))
    period_end = _parse_date(record.get("period_end"))
    election_cycle = str(record.get("election_cycle", ""))
    source_dataset_name = str(record["source_dataset_name"])
    external_id = str(record["external_id"])

    authority_entity = EntityRecord(
        entity_type=EntityType.PERSON,
        external_id=f"servel:authority:{external_id}",
        name=authority_name,
        description=(
            f"{LOCAL_TEST_DATA} / {NOT_OFFICIAL_DATA} elected authority sample. "
            "Neutral civic transparency metadata only."
        ),
        normalized_key=normalized_key(authority_name),
        metadata={
            "classification": classification,
            "official_status": official_status,
            "dataset": SERVEL_SAMPLE_DATASET_NAME,
            "authority_name": authority_name,
            "office_name": office_name,
            "municipality_name": municipality_name,
            "period_name": period_name,
        },
    )
    office_entity = EntityRecord(
        entity_type=EntityType.ROLE,
        external_id=f"servel:office:{external_id}",
        name=office_name,
        description=(
            f"{LOCAL_TEST_DATA} / {NOT_OFFICIAL_DATA} public office sample for {municipality_name}."
        ),
        normalized_key=normalized_key(f"{office_name} {municipality_name}"),
        metadata={
            "classification": classification,
            "official_status": official_status,
            "dataset": SERVEL_SAMPLE_DATASET_NAME,
            "authority_name": authority_name,
            "municipality_name": municipality_name,
            "period_name": period_name,
        },
    )
    municipality_entity = EntityRecord(
        entity_type=EntityType.MUNICIPALITY,
        external_id=f"servel:municipality:{normalized_key(municipality_name) or external_id}",
        name=municipality_name,
        description=f"{LOCAL_TEST_DATA} / {NOT_OFFICIAL_DATA} municipal territory sample.",
        normalized_key=normalized_key(municipality_name),
        metadata={
            "classification": classification,
            "official_status": official_status,
            "dataset": SERVEL_SAMPLE_DATASET_NAME,
            "territory_name": territory_name,
        },
    )
    period_entity = EntityRecord(
        entity_type=EntityType.ELECTORAL_PERIOD,
        external_id=f"servel:period:{normalized_key(period_name) or external_id}",
        name=period_name,
        description=(
            f"{LOCAL_TEST_DATA} / {NOT_OFFICIAL_DATA} electoral period sample for {authority_name}."
        ),
        normalized_key=normalized_key(period_name),
        metadata={
            "classification": classification,
            "official_status": official_status,
            "dataset": SERVEL_SAMPLE_DATASET_NAME,
            "election_cycle": election_cycle,
            "period_start": period_start.isoformat() if period_start else None,
            "period_end": period_end.isoformat() if period_end else None,
        },
    )

    source_record_payload = {
        **record,
        "classification": classification,
        "official_status": official_status,
        "sample_markers": [LOCAL_TEST_DATA, NOT_OFFICIAL_DATA],
    }
    source_record = SourceRecordPayload(
        external_id=external_id,
        record_type=SERVEL_SAMPLE_RECORD_TYPE,
        payload_hash=stable_json_hash(source_record_payload),
        raw_payload=source_record_payload,
        retrieved_at=datetime.now(timezone.utc),
        status=WorkflowStatus.NORMALIZED,
    )

    authority_evidence = _build_evidence(
        source_record,
        external_id=f"{external_id}:authority",
        title=f"SERVEL local sample authority - {authority_name}",
        url=f"{record['source_url']}/authority",
        excerpt=(
            f"{LOCAL_TEST_DATA} / {NOT_OFFICIAL_DATA} elected authority sample for "
            f"{authority_name} in {municipality_name}."
        ),
        published_at=period_start,
    )
    office_evidence = _build_evidence(
        source_record,
        external_id=f"{external_id}:office",
        title=f"SERVEL local sample office - {office_name}",
        url=f"{record['source_url']}/office",
        excerpt=(
            f"{LOCAL_TEST_DATA} / {NOT_OFFICIAL_DATA} public office sample for "
            f"{municipality_name}."
        ),
        published_at=period_start,
    )
    territory_evidence = _build_evidence(
        source_record,
        external_id=f"{external_id}:territory",
        title=f"SERVEL local sample territory - {municipality_name}",
        url=f"{record['source_url']}/territory",
        excerpt=(
            f"{LOCAL_TEST_DATA} / {NOT_OFFICIAL_DATA} territory sample for "
            f"{authority_name}."
        ),
        published_at=period_start,
    )
    period_evidence = _build_evidence(
        source_record,
        external_id=f"{external_id}:period",
        title=f"SERVEL local sample period - {period_name}",
        url=f"{record['source_url']}/period",
        excerpt=(
            f"{LOCAL_TEST_DATA} / {NOT_OFFICIAL_DATA} electoral period sample for "
            f"{authority_name}."
        ),
        published_at=period_start,
    )

    authority_claim = ClaimRecord(
        subject_entity=authority_entity,
        predicate=AUTHORITY_ELECTED_TO_OFFICE_PREDICATE,
        object_entity=office_entity,
        source_record=source_record,
        evidence=authority_evidence,
        object_value={
            "authority_name": authority_name,
            "office_name": office_name,
            "municipality_name": municipality_name,
            "territory_name": territory_name,
            "period_label": period_name,
            "period_start": period_start.isoformat() if period_start else None,
            "period_end": period_end.isoformat() if period_end else None,
            "election_cycle": election_cycle,
            "source_dataset_name": source_dataset_name,
            "dataset": SERVEL_SAMPLE_DATASET_NAME,
        },
        valid_from=period_start,
        valid_to=period_end,
        confidence=1.0,
        status=WorkflowStatus.VALIDATED,
        metadata={"dataset": SERVEL_SAMPLE_DATASET_NAME},
    )
    territory_claim = ClaimRecord(
        subject_entity=authority_entity,
        predicate=AUTHORITY_REPRESENTS_TERRITORY_PREDICATE,
        object_entity=municipality_entity,
        source_record=source_record,
        evidence=territory_evidence,
        object_value={
            "authority_name": authority_name,
            "territory_name": territory_name,
            "municipality_name": municipality_name,
            "dataset": SERVEL_SAMPLE_DATASET_NAME,
        },
        valid_from=period_start,
        valid_to=period_end,
        confidence=1.0,
        status=WorkflowStatus.VALIDATED,
        metadata={"dataset": SERVEL_SAMPLE_DATASET_NAME},
    )
    office_claim = ClaimRecord(
        subject_entity=office_entity,
        predicate=OFFICE_BELONGS_TO_MUNICIPALITY_PREDICATE,
        object_entity=municipality_entity,
        source_record=source_record,
        evidence=office_evidence,
        object_value={
            "office_name": office_name,
            "municipality_name": municipality_name,
            "dataset": SERVEL_SAMPLE_DATASET_NAME,
        },
        valid_from=period_start,
        valid_to=period_end,
        confidence=1.0,
        status=WorkflowStatus.VALIDATED,
        metadata={"dataset": SERVEL_SAMPLE_DATASET_NAME},
    )
    period_claim = ClaimRecord(
        subject_entity=authority_entity,
        predicate=AUTHORITY_HAS_ELECTORAL_PERIOD_PREDICATE,
        object_entity=period_entity,
        source_record=source_record,
        evidence=period_evidence,
        object_value={
            "period_label": period_name,
            "period_start": period_start.isoformat() if period_start else None,
            "period_end": period_end.isoformat() if period_end else None,
            "election_cycle": election_cycle,
            "dataset": SERVEL_SAMPLE_DATASET_NAME,
        },
        valid_from=period_start,
        valid_to=period_end,
        confidence=1.0,
        status=WorkflowStatus.VALIDATED,
        metadata={"dataset": SERVEL_SAMPLE_DATASET_NAME},
    )

    authority_relationship = PublicRelationshipRecord(
        source_entity=authority_entity,
        target_entity=office_entity,
        relationship_type=RelationshipType.AUTHORITY_ELECTED_TO_OFFICE,
        claim=authority_claim,
        published_at=datetime.now(timezone.utc),
        status=WorkflowStatus.PUBLISHED,
        metadata={
            "classification": classification,
            "official_status": official_status,
            "dataset": SERVEL_SAMPLE_DATASET_NAME,
        },
    )
    territory_relationship = PublicRelationshipRecord(
        source_entity=authority_entity,
        target_entity=municipality_entity,
        relationship_type=RelationshipType.AUTHORITY_REPRESENTS_TERRITORY,
        claim=territory_claim,
        published_at=datetime.now(timezone.utc),
        status=WorkflowStatus.PUBLISHED,
        metadata={
            "classification": classification,
            "official_status": official_status,
            "dataset": SERVEL_SAMPLE_DATASET_NAME,
        },
    )
    office_relationship = PublicRelationshipRecord(
        source_entity=office_entity,
        target_entity=municipality_entity,
        relationship_type=RelationshipType.OFFICE_BELONGS_TO_MUNICIPALITY,
        claim=office_claim,
        published_at=datetime.now(timezone.utc),
        status=WorkflowStatus.PUBLISHED,
        metadata={
            "classification": classification,
            "official_status": official_status,
            "dataset": SERVEL_SAMPLE_DATASET_NAME,
        },
    )
    period_relationship = PublicRelationshipRecord(
        source_entity=authority_entity,
        target_entity=period_entity,
        relationship_type=RelationshipType.AUTHORITY_HAS_ELECTORAL_PERIOD,
        claim=period_claim,
        published_at=datetime.now(timezone.utc),
        status=WorkflowStatus.PUBLISHED,
        metadata={
            "classification": classification,
            "official_status": official_status,
            "dataset": SERVEL_SAMPLE_DATASET_NAME,
        },
    )

    return {
        "source_record": source_record,
        "entities": (authority_entity, office_entity, municipality_entity, period_entity),
        "evidence": (authority_evidence, office_evidence, territory_evidence, period_evidence),
        "claims": (authority_claim, territory_claim, office_claim, period_claim),
        "public_relationships": (
            authority_relationship,
            territory_relationship,
            office_relationship,
            period_relationship,
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
        source_name=SERVEL_SAMPLE_SOURCE_NAME,
        title=title,
        url=url,
        published_at=published_at,
        excerpt=excerpt,
        metadata={
            "classification": LOCAL_TEST_DATA,
            "official_status": NOT_OFFICIAL_DATA,
            "dataset": SERVEL_SAMPLE_DATASET_NAME,
            "external_id": external_id,
        },
    )


def _load_servel_authority_claims(session: Session) -> list[Claim]:
    return list(
        session.scalars(
            select(Claim)
            .join(SourceRecord, Claim.source_record_id == SourceRecord.id)
            .options(joinedload(Claim.subject_entity), joinedload(Claim.object_entity), joinedload(Claim.source_record))
            .where(
                SourceRecord.record_type == SERVEL_SAMPLE_RECORD_TYPE,
                Claim.predicate == AUTHORITY_ELECTED_TO_OFFICE_PREDICATE,
            )
            .order_by(Claim.created_at, Claim.id)
        ).all()
    )


def _load_claim(session: Session, source_record_id, predicate: str) -> Claim | None:  # type: ignore[no-untyped-def]
    return session.scalar(
        select(Claim)
        .options(joinedload(Claim.subject_entity), joinedload(Claim.object_entity))
        .where(
            Claim.source_record_id == source_record_id,
            Claim.predicate == predicate,
        )
        .order_by(Claim.created_at, Claim.id)
    )


def _load_servel_relationships(session: Session, source_record_id) -> tuple[RelationshipPublic, ...]:  # type: ignore[no-untyped-def]
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
        raise ValueError("SERVEL sample must be marked LOCAL_TEST_DATA")
    if payload.get("official_status") != NOT_OFFICIAL_DATA:
        raise ValueError("SERVEL sample must be marked NOT_OFFICIAL_DATA")
    if "records" not in payload or not isinstance(payload["records"], list):
        raise ValueError("SERVEL sample must include a records array")
    for record in payload["records"]:
        for key in (
            "authority_name",
            "office_name",
            "municipality_name",
            "period_name",
            "period_start",
            "period_end",
            "source_url",
            "source_dataset_name",
        ):
            if not record.get(key):
                raise ValueError(f"SERVEL sample record must include {key}")


def _object_value_text(claim: Claim, key: str) -> str | None:
    value = claim.object_value or {}
    if isinstance(value, dict):
        raw = value.get(key)
        if raw is not None:
            return str(raw)
    return None


def _parse_date(value: object | None) -> date | None:
    if value is None:
        return None
    return date.fromisoformat(str(value))


def _count_rows(session: Session, model) -> int:  # type: ignore[no-untyped-def]
    return int(session.scalar(select(func.count()).select_from(model)) or 0)


def _count_entities(session: Session, entity_type: str) -> int:
    return int(session.scalar(select(func.count()).select_from(Entity).where(Entity.entity_type == entity_type)) or 0)


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
