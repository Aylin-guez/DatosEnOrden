from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any


class StrEnum(str, Enum):
    """Compatibility fallback for Python versions without enum.StrEnum."""


class WorkflowStatus(StrEnum):
    INGESTED = "ingested"
    NORMALIZED = "normalized"
    VALIDATED = "validated"
    PUBLISHED = "published"
    REJECTED = "rejected"
    DISPUTED = "disputed"
    WITHDRAWN = "withdrawn"


class EntityType(StrEnum):
    PERSON = "PERSON"
    ROLE = "ROLE"
    COMPANY = "COMPANY"
    CONTRACT = "CONTRACT"
    BUDGET = "BUDGET"
    LOBBY_MEETING = "LOBBY_MEETING"
    PUBLIC_ORGANIZATION = "PUBLIC_ORGANIZATION"
    TENDER = "TENDER"
    CONTROL_REPORT = "CONTROL_REPORT"
    PUBLIC_OBSERVATION = "PUBLIC_OBSERVATION"
    MUNICIPALITY = "MUNICIPALITY"
    PUBLIC_PROJECT = "PUBLIC_PROJECT"
    SPENDING_ITEM = "SPENDING_ITEM"
    ELECTORAL_PERIOD = "ELECTORAL_PERIOD"
    ADMINISTRATIVE_PROCEDURE = "ADMINISTRATIVE_PROCEDURE"
    ADMINISTRATIVE_RESOLUTION = "ADMINISTRATIVE_RESOLUTION"


class RelationshipType(StrEnum):
    ORGANIZATION_HAS_PUBLIC_ROLE = "ORGANIZATION_HAS_PUBLIC_ROLE"
    PERSON_HOLDS_PUBLIC_ROLE = "PERSON_HOLDS_PUBLIC_ROLE"
    ROLE_BELONGS_TO_ORGANIZATION = "ROLE_BELONGS_TO_ORGANIZATION"
    AUTHORITY_ELECTED_TO_OFFICE = "AUTHORITY_ELECTED_TO_OFFICE"
    AUTHORITY_REPRESENTS_TERRITORY = "AUTHORITY_REPRESENTS_TERRITORY"
    OFFICE_BELONGS_TO_MUNICIPALITY = "OFFICE_BELONGS_TO_MUNICIPALITY"
    AUTHORITY_HAS_ELECTORAL_PERIOD = "AUTHORITY_HAS_ELECTORAL_PERIOD"
    PERSON_APPOINTED_TO_PUBLIC_OFFICE = "PERSON_APPOINTED_TO_PUBLIC_OFFICE"
    PERSON_RESIGNED_FROM_PUBLIC_OFFICE = "PERSON_RESIGNED_FROM_PUBLIC_OFFICE"
    DECREE_APPLIES_TO_ORGANIZATION = "DECREE_APPLIES_TO_ORGANIZATION"
    OFFICIAL_PUBLICATION_REFERENCES_ENTITY = "OFFICIAL_PUBLICATION_REFERENCES_ENTITY"
    PUBLIC_OFFICE_BELONGS_TO_ORGANIZATION = "PUBLIC_OFFICE_BELONGS_TO_ORGANIZATION"
    PERSON_REPRESENTS_COMPANY = "PERSON_REPRESENTS_COMPANY"
    PERSON_OWNS_COMPANY = "PERSON_OWNS_COMPANY"
    COMPANY_REGISTERED_ON = "COMPANY_REGISTERED_ON"
    COMPANY_MODIFIED_ON = "COMPANY_MODIFIED_ON"
    BUDGET_ALLOCATED_TO = "BUDGET_ALLOCATED_TO"
    AWARDS_CONTRACT = "AWARDS_CONTRACT"
    COUNTERPARTY_PARTICIPATED_IN_LOBBY = "COUNTERPARTY_PARTICIPATED_IN_LOBBY"
    ISSUES_PURCHASE_ORDER = "ISSUES_PURCHASE_ORDER"
    ORGANIZATION_HELD_LOBBY_MEETING = "ORGANIZATION_HELD_LOBBY_MEETING"
    PUBLISHED_TENDER = "PUBLISHED_TENDER"
    RECEIVES_CONTRACT = "RECEIVES_CONTRACT"
    ORGANIZATION_HAS_CONTROL_REPORT = "ORGANIZATION_HAS_CONTROL_REPORT"
    CONTROL_REPORT_HAS_OBSERVATION = "CONTROL_REPORT_HAS_OBSERVATION"
    MUNICIPALITY_EXECUTES_PROJECT = "MUNICIPALITY_EXECUTES_PROJECT"
    MUNICIPALITY_SPENDS_ON = "MUNICIPALITY_SPENDS_ON"
    PROCEDURE_INVOLVES_ORGANIZATION = "PROCEDURE_INVOLVES_ORGANIZATION"
    PROCEDURE_INVOLVES_COMPANY = "PROCEDURE_INVOLVES_COMPANY"
    PROCEDURE_INVOLVES_PERSON = "PROCEDURE_INVOLVES_PERSON"
    PROCEDURE_HAS_RESOLUTION = "PROCEDURE_HAS_RESOLUTION"


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
