from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum
from typing import Any


class WorkflowStatus(StrEnum):
    INGESTED = "ingested"
    NORMALIZED = "normalized"
    VALIDATED = "validated"
    PUBLISHED = "published"
    REJECTED = "rejected"
    DISPUTED = "disputed"
    WITHDRAWN = "withdrawn"


class EntityType(StrEnum):
    COMPANY = "COMPANY"
    CONTRACT = "CONTRACT"
    PUBLIC_ORGANIZATION = "PUBLIC_ORGANIZATION"
    TENDER = "TENDER"


class RelationshipType(StrEnum):
    AWARDS_CONTRACT = "AWARDS_CONTRACT"
    ISSUES_PURCHASE_ORDER = "ISSUES_PURCHASE_ORDER"
    PUBLISHED_TENDER = "PUBLISHED_TENDER"
    RECEIVES_CONTRACT = "RECEIVES_CONTRACT"


class ChileCompraResource(StrEnum):
    BUYERS = "buyers"
    PURCHASE_ORDERS = "purchase_orders"
    SUPPLIERS = "suppliers"
    TENDERS = "tenders"


@dataclass(frozen=True)
class SourceInfo:
    name: str
    publisher: str
    url: str
    license: str | None = None
    retrieved_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SourceRecordPayload:
    external_id: str
    record_type: str
    payload_hash: str
    raw_payload: dict[str, Any]
    retrieved_at: datetime
    processed_at: datetime | None = None
    status: WorkflowStatus = WorkflowStatus.INGESTED
    error_log: str | None = None


@dataclass(frozen=True)
class DatasetRecord:
    source_name: str
    name: str
    description: str
    version: str
    dataset_url: str
    content_hash: str | None = None
    loaded_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EntityRecord:
    entity_type: EntityType
    name: str
    external_id: str
    description: str | None = None
    normalized_key: str | None = None
    status: str = "active"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RelationshipRecord:
    source_entity: EntityRecord
    target_entity: EntityRecord
    relationship_type: RelationshipType
    start_date: date | None = None
    end_date: date | None = None
    notes: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EvidenceRecord:
    source_record: SourceRecordPayload
    source_name: str
    title: str
    url: str
    published_at: date | None = None
    excerpt: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ClaimRecord:
    subject_entity: EntityRecord
    predicate: str
    source_record: SourceRecordPayload
    evidence: EvidenceRecord
    object_entity: EntityRecord | None = None
    object_value: dict[str, Any] | str | int | float | bool | None = None
    valid_from: date | None = None
    valid_to: date | None = None
    confidence: float = 1.0
    status: WorkflowStatus = WorkflowStatus.VALIDATED
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PublicRelationshipRecord:
    source_entity: EntityRecord
    target_entity: EntityRecord
    relationship_type: RelationshipType
    claim: ClaimRecord
    published_at: datetime | None = None
    status: WorkflowStatus = WorkflowStatus.PUBLISHED
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GraphBatch:
    source: SourceInfo
    dataset: DatasetRecord
    source_records: tuple[SourceRecordPayload, ...]
    entities: tuple[EntityRecord, ...]
    evidence: tuple[EvidenceRecord, ...]
    claims: tuple[ClaimRecord, ...]
    public_relationships: tuple[PublicRelationshipRecord, ...]
    raw_count: int
    rejected_count: int = 0
    errors: tuple[str, ...] = ()
