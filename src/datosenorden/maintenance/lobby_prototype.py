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
LOBBY_SAMPLE_DATASET_NAME = "lobby-meeting-sample"
LOBBY_SAMPLE_SOURCE_NAME = "DatosEnOrden Lobby Sample"
LOBBY_SAMPLE_SOURCE_URL = "local://sample/lobby-meeting"
LOBBY_SAMPLE_RECORD_TYPE = "lobby:meeting_sample"
ORGANIZATION_HELD_LOBBY_MEETING_PREDICATE = "ORGANIZATION_HELD_LOBBY_MEETING"
COUNTERPARTY_PARTICIPATED_IN_LOBBY_PREDICATE = "COUNTERPARTY_PARTICIPATED_IN_LOBBY"
LOBBY_MEETING_ABOUT_SUBJECT_PREDICATE = "LOBBY_MEETING_ABOUT_SUBJECT"
LOBBY_SAMPLE_PATH = PROJECT_ROOT / "data" / "sample" / "lobby_meeting_sample.json"


@dataclass(frozen=True)
class LobbyMatchResult:
    entity: Entity
    match_method: str
    confidence: float


@dataclass(frozen=True)
class LobbyImportResult:
    source_records: int
    claims: int
    evidences: int
    entities: int
    relationship_public: int
    organization_entity_id: str
    organization_name: str
    counterparty_entity_id: str
    counterparty_name: str
    lobby_meeting_entity_id: str
    lobby_meeting_name: str


@dataclass(frozen=True)
class LobbySummaryRow:
    lobby_meeting_id: str
    lobby_meeting_name: str
    organization_id: str
    organization_name: str
    counterparty_id: str
    counterparty_name: str
    counterparty_type: str
    meeting_subject: str
    meeting_date: date | None
    claims: tuple[str, ...]
    relationships: tuple[str, ...]
    organization_match_method: str
    organization_match_confidence: float
    counterparty_match_method: str
    counterparty_match_confidence: float


def load_lobby_sample_payload(input_path: Path | None = None) -> dict[str, Any]:
    path = input_path or LOBBY_SAMPLE_PATH
    payload = json.loads(path.read_text(encoding="utf-8"))
    _validate_sample_payload(payload)
    return payload


def build_lobby_sample_batch(session: Session, payload: dict[str, Any] | None = None) -> GraphBatch:
    sample = payload or load_lobby_sample_payload()
    records = sample.get("records") or []
    if not records:
        raise ValueError("Lobby sample must include at least one record")

    record = records[0]
    classification = str(sample["classification"])
    official_status = str(sample["official_status"])
    organization_name = str(record["organization_name"])
    counterparty_name = str(record["counterparty_name"])
    counterparty_type = str(record.get("counterparty_type", EntityType.COMPANY.value)).upper()
    meeting_date = _parse_date(record.get("meeting_date"))
    meeting_subject = str(record["meeting_subject"])

    organization_match = _match_existing_entity(
        session,
        entity_type=EntityType.PUBLIC_ORGANIZATION.value,
        name=organization_name,
    )
    counterparty_match = _match_existing_entity(
        session,
        entity_type=counterparty_type,
        name=counterparty_name,
    )

    meeting_entity = _build_lobby_meeting_entity(record, classification, official_status)
    organization_entity = _build_matched_entity_record(organization_match, EntityType.PUBLIC_ORGANIZATION)
    counterparty_entity = _build_matched_entity_record(counterparty_match, EntityType(counterparty_type))

    source_record_payload = {
        **record,
        "classification": classification,
        "official_status": official_status,
        "sample_markers": [LOCAL_TEST_DATA, NOT_OFFICIAL_DATA],
    }
    source_record = SourceRecordPayload(
        external_id=str(record["external_id"]),
        record_type=LOBBY_SAMPLE_RECORD_TYPE,
        payload_hash=stable_json_hash(source_record_payload),
        raw_payload=source_record_payload,
        retrieved_at=datetime.now(timezone.utc),
        status=WorkflowStatus.NORMALIZED,
    )

    organization_evidence = _build_evidence(
        source_record,
        external_id=f"{record['external_id']}:organization",
        title=f"Lobby sample organization meeting - {organization_name}",
        url=f"{record['source_url']}/organization",
        excerpt=(
            f"{LOCAL_TEST_DATA} / {NOT_OFFICIAL_DATA} meeting sample connects "
            f"{organization_name} with {counterparty_name}."
        ),
        published_at=meeting_date,
    )
    counterparty_evidence = _build_evidence(
        source_record,
        external_id=f"{record['external_id']}:counterparty",
        title=f"Lobby sample counterparty meeting - {counterparty_name}",
        url=f"{record['source_url']}/counterparty",
        excerpt=(
            f"{LOCAL_TEST_DATA} / {NOT_OFFICIAL_DATA} counterparty participation sample "
            f"for {counterparty_name}."
        ),
        published_at=meeting_date,
    )
    subject_evidence = _build_evidence(
        source_record,
        external_id=f"{record['external_id']}:subject",
        title="Lobby sample meeting subject",
        url=f"{record['source_url']}/subject",
        excerpt=f"{LOCAL_TEST_DATA} / {NOT_OFFICIAL_DATA} meeting subject: {meeting_subject}",
        published_at=meeting_date,
    )

    organization_claim = ClaimRecord(
        subject_entity=organization_entity,
        predicate=ORGANIZATION_HELD_LOBBY_MEETING_PREDICATE,
        object_entity=meeting_entity,
        source_record=source_record,
        evidence=organization_evidence,
        valid_from=meeting_date,
        confidence=organization_match.confidence,
        status=WorkflowStatus.VALIDATED,
        metadata={"dataset": LOBBY_SAMPLE_DATASET_NAME},
    )
    counterparty_claim = ClaimRecord(
        subject_entity=counterparty_entity,
        predicate=COUNTERPARTY_PARTICIPATED_IN_LOBBY_PREDICATE,
        object_entity=meeting_entity,
        source_record=source_record,
        evidence=counterparty_evidence,
        valid_from=meeting_date,
        confidence=counterparty_match.confidence,
        status=WorkflowStatus.VALIDATED,
        metadata={"dataset": LOBBY_SAMPLE_DATASET_NAME},
    )
    subject_claim = ClaimRecord(
        subject_entity=meeting_entity,
        predicate=LOBBY_MEETING_ABOUT_SUBJECT_PREDICATE,
        source_record=source_record,
        evidence=subject_evidence,
        object_value={
            "meeting_subject": meeting_subject,
            "meeting_location": record.get("meeting_location"),
            "source_dataset_name": record.get("source_dataset_name"),
            "dataset": LOBBY_SAMPLE_DATASET_NAME,
        },
        valid_from=meeting_date,
        confidence=1.0,
        status=WorkflowStatus.VALIDATED,
        metadata={"dataset": LOBBY_SAMPLE_DATASET_NAME},
    )

    organization_relationship = PublicRelationshipRecord(
        source_entity=organization_entity,
        target_entity=meeting_entity,
        relationship_type=RelationshipType.ORGANIZATION_HELD_LOBBY_MEETING,
        claim=organization_claim,
        published_at=datetime.now(timezone.utc),
        status=WorkflowStatus.PUBLISHED,
        metadata={
            "classification": classification,
            "official_status": official_status,
            "dataset": LOBBY_SAMPLE_DATASET_NAME,
            "match_method": organization_match.match_method,
            "match_confidence": organization_match.confidence,
        },
    )
    counterparty_relationship = PublicRelationshipRecord(
        source_entity=counterparty_entity,
        target_entity=meeting_entity,
        relationship_type=RelationshipType.COUNTERPARTY_PARTICIPATED_IN_LOBBY,
        claim=counterparty_claim,
        published_at=datetime.now(timezone.utc),
        status=WorkflowStatus.PUBLISHED,
        metadata={
            "classification": classification,
            "official_status": official_status,
            "dataset": LOBBY_SAMPLE_DATASET_NAME,
            "match_method": counterparty_match.match_method,
            "match_confidence": counterparty_match.confidence,
        },
    )

    source = SourceInfo(
        name=LOBBY_SAMPLE_SOURCE_NAME,
        publisher="DatosEnOrden",
        url=LOBBY_SAMPLE_SOURCE_URL,
        license=f"{LOCAL_TEST_DATA} / {NOT_OFFICIAL_DATA}",
        retrieved_at=datetime.now(timezone.utc),
        metadata={
            "classification": classification,
            "official_status": official_status,
            "dataset": LOBBY_SAMPLE_DATASET_NAME,
        },
    )
    dataset = DatasetRecord(
        source_name=LOBBY_SAMPLE_SOURCE_NAME,
        name=LOBBY_SAMPLE_DATASET_NAME,
        description=(
            "LOCAL_TEST_DATA / NOT_OFFICIAL_DATA sample used to validate neutral "
            "lobby-meeting graph links"
        ),
        version="local-sample-1",
        dataset_url=f"{LOBBY_SAMPLE_SOURCE_URL}/dataset",
        content_hash=stable_json_hash(sample),
        loaded_at=datetime.now(timezone.utc),
        metadata={
            "classification": classification,
            "official_status": official_status,
            "dataset": LOBBY_SAMPLE_DATASET_NAME,
        },
    )
    return GraphBatch(
        source=source,
        dataset=dataset,
        source_records=(source_record,),
        entities=(meeting_entity, organization_entity, counterparty_entity),
        evidence=(organization_evidence, counterparty_evidence, subject_evidence),
        claims=(organization_claim, counterparty_claim, subject_claim),
        public_relationships=(organization_relationship, counterparty_relationship),
        raw_count=len(records),
        rejected_count=0,
        errors=(),
    )


def persist_lobby_sample(session: Session, input_path: Path | None = None) -> LobbyImportResult:
    payload = load_lobby_sample_payload(input_path)
    batch = build_lobby_sample_batch(session, payload)
    GraphLoader(session).load(batch, dry_run=False)
    _deduplicate_lobby_sample(session)

    record = payload["records"][0]
    organization_match = _match_existing_entity(
        session,
        entity_type=EntityType.PUBLIC_ORGANIZATION.value,
        name=str(record["organization_name"]),
    )
    counterparty_type = str(record.get("counterparty_type", EntityType.COMPANY.value)).upper()
    counterparty_match = _match_existing_entity(
        session,
        entity_type=counterparty_type,
        name=str(record["counterparty_name"]),
    )
    meeting = session.scalar(
        select(Entity).where(
            Entity.entity_type == EntityType.LOBBY_MEETING.value,
            Entity.external_id == f"lobby:meeting:{record['external_id']}",
        )
    )
    if meeting is None:
        raise LookupError(f"Lobby meeting entity not found after load: {record['external_id']}")
    return LobbyImportResult(
        source_records=_count_rows(session, SourceRecord),
        claims=_count_rows(session, Claim),
        evidences=_count_rows(session, Evidence),
        entities=_count_rows(session, Entity),
        relationship_public=_count_rows(session, RelationshipPublic),
        organization_entity_id=str(organization_match.entity.id),
        organization_name=organization_match.entity.name,
        counterparty_entity_id=str(counterparty_match.entity.id),
        counterparty_name=counterparty_match.entity.name,
        lobby_meeting_entity_id=str(meeting.id),
        lobby_meeting_name=meeting.name,
    )


def read_lobby_summary(session: Session) -> tuple[LobbySummaryRow, ...]:
    meeting_claims = _load_lobby_subject_claims(session)
    rows: list[LobbySummaryRow] = []
    seen_meetings: set[tuple[str, str]] = set()
    for subject_claim in meeting_claims:
        meeting = subject_claim.subject_entity
        source_record = subject_claim.source_record
        if meeting is None or source_record is None:
            continue
        meeting_key = (str(source_record.id), str(meeting.id))
        if meeting_key in seen_meetings:
            continue
        seen_meetings.add(meeting_key)
        organization_claim = _load_lobby_link_claim(
            session,
            source_record.id,
            ORGANIZATION_HELD_LOBBY_MEETING_PREDICATE,
        )
        counterparty_claim = _load_lobby_link_claim(
            session,
            source_record.id,
            COUNTERPARTY_PARTICIPATED_IN_LOBBY_PREDICATE,
        )
        if organization_claim is None or counterparty_claim is None:
            continue
        relationships = _unique_lobby_relationships(_load_lobby_relationships(session, source_record.id))
        subject_data = subject_claim.object_value or {}
        rows.append(
            LobbySummaryRow(
                lobby_meeting_id=str(meeting.id),
                lobby_meeting_name=meeting.name,
                organization_id=str(organization_claim.subject_entity.id),
                organization_name=organization_claim.subject_entity.name,
                counterparty_id=str(counterparty_claim.subject_entity.id),
                counterparty_name=counterparty_claim.subject_entity.name,
                counterparty_type=counterparty_claim.subject_entity.entity_type,
                meeting_subject=str(subject_data.get("meeting_subject", "")),
                meeting_date=subject_claim.valid_from,
                claims=(
                    organization_claim.predicate,
                    counterparty_claim.predicate,
                    subject_claim.predicate,
                ),
                relationships=tuple(relationship.relationship_type for relationship in relationships),
                organization_match_method=_metadata_value(relationships, ORGANIZATION_HELD_LOBBY_MEETING_PREDICATE, "match_method"),
                organization_match_confidence=_metadata_float(
                    relationships,
                    ORGANIZATION_HELD_LOBBY_MEETING_PREDICATE,
                    "match_confidence",
                    float(organization_claim.confidence),
                ),
                counterparty_match_method=_metadata_value(
                    relationships,
                    COUNTERPARTY_PARTICIPATED_IN_LOBBY_PREDICATE,
                    "match_method",
                ),
                counterparty_match_confidence=_metadata_float(
                    relationships,
                    COUNTERPARTY_PARTICIPATED_IN_LOBBY_PREDICATE,
                    "match_confidence",
                    float(counterparty_claim.confidence),
                ),
            )
        )
    return tuple(sorted(rows, key=lambda row: (row.meeting_date or date.min, row.lobby_meeting_name)))


def render_lobby_summary_text(rows: tuple[LobbySummaryRow, ...]) -> str:
    lines = ["lobby_summary:"]
    if not rows:
        lines.append("  (no lobby meetings found)")
        return "\n".join(lines)
    for row in rows:
        lines.extend(
            [
                "  lobby_meeting:",
                f"    id={row.lobby_meeting_id}",
                f"    name={row.lobby_meeting_name}",
                f"    meeting_date={row.meeting_date.isoformat() if row.meeting_date else 'None'}",
                f"    meeting_subject={row.meeting_subject}",
                "    organization:",
                f"      id={row.organization_id}",
                f"      name={row.organization_name}",
                "    counterparty:",
                f"      id={row.counterparty_id}",
                f"      type={row.counterparty_type}",
                f"      name={row.counterparty_name}",
                "    claims:",
                *[f"      {claim}" for claim in row.claims],
                "    relationships:",
                *[f"      {relationship}" for relationship in row.relationships],
                "    matched_entities:",
                f"      organization_match_method={row.organization_match_method}",
                f"      organization_match_confidence={row.organization_match_confidence}",
                f"      counterparty_match_method={row.counterparty_match_method}",
                f"      counterparty_match_confidence={row.counterparty_match_confidence}",
                "",
            ]
        )
    return "\n".join(lines).rstrip()


def render_lobby_import_result_text(result: LobbyImportResult) -> str:
    return "\n".join(
        [
            "lobby_sample_loaded:",
            f"  source_records={result.source_records}",
            f"  claims={result.claims}",
            f"  evidences={result.evidences}",
            f"  entities={result.entities}",
            f"  relationship_public={result.relationship_public}",
            f"  organization_entity_id={result.organization_entity_id}",
            f"  organization_name={result.organization_name}",
            f"  counterparty_entity_id={result.counterparty_entity_id}",
            f"  counterparty_name={result.counterparty_name}",
            f"  lobby_meeting_entity_id={result.lobby_meeting_entity_id}",
            f"  lobby_meeting_name={result.lobby_meeting_name}",
        ]
    )


def _validate_sample_payload(payload: dict[str, Any]) -> None:
    if payload.get("classification") != LOCAL_TEST_DATA:
        raise ValueError("Lobby sample must be marked LOCAL_TEST_DATA")
    if payload.get("official_status") != NOT_OFFICIAL_DATA:
        raise ValueError("Lobby sample must be marked NOT_OFFICIAL_DATA")
    if "records" not in payload or not isinstance(payload["records"], list):
        raise ValueError("Lobby sample must include a records array")
    for record in payload["records"]:
        for key in (
            "organization_name",
            "counterparty_name",
            "meeting_subject",
            "meeting_date",
            "source_url",
            "source_dataset_name",
        ):
            if not record.get(key):
                raise ValueError(f"Lobby sample record must include {key}")


def _match_existing_entity(session: Session, *, entity_type: str, name: str) -> LobbyMatchResult:
    candidates = match_entity_candidates(session, entity_type=entity_type, name=name, limit=1)
    if not candidates:
        external_id = f"lobby:local:{entity_type.lower()}:{normalized_key(name) or name.lower()}"
        return LobbyMatchResult(
            entity=Entity(
                id=uuid5(NAMESPACE_URL, external_id),
                entity_type=entity_type,
                name=name,
                external_id=external_id,
                normalized_key=normalized_key(name),
                status="active",
                entity_metadata={
                    "classification": LOCAL_TEST_DATA,
                    "official_status": NOT_OFFICIAL_DATA,
                    "dataset": LOBBY_SAMPLE_DATASET_NAME,
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
    return LobbyMatchResult(entity=entity, match_method=candidate.match_method, confidence=candidate.score)


def _build_lobby_meeting_entity(record: dict[str, Any], classification: str, official_status: str) -> EntityRecord:
    meeting_date = str(record["meeting_date"])
    organization_name = str(record["organization_name"])
    counterparty_name = str(record["counterparty_name"])
    external_id = str(record["external_id"])
    return EntityRecord(
        entity_type=EntityType.LOBBY_MEETING,
        external_id=f"lobby:meeting:{external_id}",
        name=f"Lobby meeting {meeting_date} - {organization_name} / {counterparty_name}",
        description=(
            f"{LOCAL_TEST_DATA} / {NOT_OFFICIAL_DATA} lobby meeting sample. "
            "Neutral sample record; it does not imply irregularity or wrongdoing."
        ),
        normalized_key=normalized_key(f"{organization_name} {counterparty_name} {meeting_date}"),
        metadata={
            "classification": classification,
            "official_status": official_status,
            "dataset": LOBBY_SAMPLE_DATASET_NAME,
            "meeting_date": meeting_date,
            "meeting_location": record.get("meeting_location"),
            "meeting_subject": record["meeting_subject"],
        },
    )


def _build_matched_entity_record(match: LobbyMatchResult, entity_type: EntityType) -> EntityRecord:
    entity = match.entity
    return EntityRecord(
        entity_type=entity_type,
        external_id=str(entity.external_id),
        name=entity.name,
        description=entity.description,
        normalized_key=entity.normalized_key,
        status=entity.status,
        metadata=entity.entity_metadata or {},
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
        source_name=LOBBY_SAMPLE_SOURCE_NAME,
        title=title,
        url=url,
        published_at=published_at,
        excerpt=excerpt,
        metadata={
            "classification": LOCAL_TEST_DATA,
            "official_status": NOT_OFFICIAL_DATA,
            "dataset": LOBBY_SAMPLE_DATASET_NAME,
            "external_id": external_id,
        },
    )


def _load_lobby_subject_claims(session: Session) -> list[Claim]:
    return list(
        session.scalars(
            select(Claim)
            .join(SourceRecord, Claim.source_record_id == SourceRecord.id)
            .options(joinedload(Claim.subject_entity), joinedload(Claim.source_record))
            .where(
                SourceRecord.record_type == LOBBY_SAMPLE_RECORD_TYPE,
                Claim.predicate == LOBBY_MEETING_ABOUT_SUBJECT_PREDICATE,
            )
            .order_by(Claim.created_at, Claim.id)
        ).all()
    )


def _load_lobby_link_claim(session: Session, source_record_id, predicate: str) -> Claim | None:  # type: ignore[no-untyped-def]
    return session.scalar(
        select(Claim)
        .options(joinedload(Claim.subject_entity), joinedload(Claim.object_entity))
        .where(
            Claim.source_record_id == source_record_id,
            Claim.predicate == predicate,
        )
        .order_by(Claim.created_at, Claim.id)
    )


def _load_lobby_relationships(session: Session, source_record_id) -> tuple[RelationshipPublic, ...]:  # type: ignore[no-untyped-def]
    return tuple(
        session.scalars(
            select(RelationshipPublic)
            .join(Claim, RelationshipPublic.claim_id == Claim.id)
            .where(Claim.source_record_id == source_record_id)
            .order_by(RelationshipPublic.relationship_type.asc(), RelationshipPublic.id.asc())
        ).all()
    )


def _unique_lobby_relationships(
    relationships: tuple[RelationshipPublic, ...],
) -> tuple[RelationshipPublic, ...]:
    unique: dict[tuple[str, str, str], RelationshipPublic] = {}
    for relationship in relationships:
        key = (
            str(getattr(relationship, "source_entity_id", "")),
            str(getattr(relationship, "target_entity_id", "")),
            relationship.relationship_type,
        )
        unique.setdefault(key, relationship)
    return tuple(unique[key] for key in sorted(unique, key=lambda item: (item[2], item[0], item[1])))


def _deduplicate_lobby_sample(session: Session) -> None:
    source_record_ids = tuple(
        session.scalars(
            select(SourceRecord.id).where(SourceRecord.record_type == LOBBY_SAMPLE_RECORD_TYPE)
        ).all()
    )
    if not source_record_ids:
        return
    _deduplicate_lobby_relationships(session, source_record_ids)
    _deduplicate_lobby_claims(session, source_record_ids)
    _deduplicate_lobby_relationships(session, source_record_ids)
    session.commit()


def _deduplicate_lobby_relationships(session: Session, source_record_ids: tuple[UUID, ...]) -> None:
    relationships = list(
        session.scalars(
            select(RelationshipPublic)
            .join(Claim, RelationshipPublic.claim_id == Claim.id)
            .where(Claim.source_record_id.in_(source_record_ids))
            .order_by(
                RelationshipPublic.source_entity_id.asc(),
                RelationshipPublic.target_entity_id.asc(),
                RelationshipPublic.relationship_type.asc(),
                RelationshipPublic.claim_id.asc(),
                RelationshipPublic.created_at.asc(),
                RelationshipPublic.id.asc(),
            )
        ).all()
    )
    seen: set[tuple[str, str, str, str]] = set()
    for relationship in relationships:
        key = (
            str(relationship.source_entity_id),
            str(relationship.target_entity_id),
            relationship.relationship_type,
            str(relationship.claim_id),
        )
        if key in seen:
            session.delete(relationship)
            continue
        seen.add(key)
    session.flush()


def _deduplicate_lobby_claims(session: Session, source_record_ids: tuple[UUID, ...]) -> None:
    claims = list(
        session.scalars(
            select(Claim)
            .where(Claim.source_record_id.in_(source_record_ids))
            .order_by(
                Claim.source_record_id.asc(),
                Claim.subject_entity_id.asc(),
                Claim.predicate.asc(),
                Claim.object_entity_id.asc(),
                Claim.created_at.asc(),
                Claim.id.asc(),
            )
        ).all()
    )
    seen: set[tuple[str, str, str, str, str]] = set()
    duplicate_claim_ids: set[UUID] = set()
    for claim in claims:
        key = _stable_claim_identity(claim)
        if key in seen:
            duplicate_claim_ids.add(claim.id)
            continue
        seen.add(key)
    if not duplicate_claim_ids:
        return

    duplicate_relationships = list(
        session.scalars(
            select(RelationshipPublic).where(RelationshipPublic.claim_id.in_(duplicate_claim_ids))
        ).all()
    )
    for relationship in duplicate_relationships:
        session.delete(relationship)
    session.flush()

    for claim in claims:
        if claim.id in duplicate_claim_ids:
            session.delete(claim)
    session.flush()


def _stable_claim_identity(claim: Claim) -> tuple[str, str, str, str, str]:
    return (
        str(claim.source_record_id),
        str(claim.subject_entity_id),
        claim.predicate,
        str(claim.object_entity_id) if claim.object_entity_id is not None else "",
        _stable_json_identity(claim.object_value),
    )


def _stable_json_identity(value: object | None) -> str:
    if value is None:
        return ""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


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
