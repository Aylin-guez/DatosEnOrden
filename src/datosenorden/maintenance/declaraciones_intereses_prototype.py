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
DECLARACIONES_SAMPLE_DATASET_NAME = "declaraciones-intereses-sample"
DECLARACIONES_SAMPLE_SOURCE_NAME = "DatosEnOrden Declaraciones Intereses Sample"
DECLARACIONES_SAMPLE_SOURCE_URL = "local://sample/declaraciones-intereses"
DECLARACIONES_SAMPLE_RECORD_TYPE = "declaraciones_intereses:local_sample"
PERSON_HAS_DECLARATION_PREDICATE = "PERSON_HAS_DECLARATION"
DECLARATION_REFERENCES_COMPANY_PREDICATE = "DECLARATION_REFERENCES_COMPANY"
DECLARATION_REFERENCES_ORGANIZATION_PREDICATE = "DECLARATION_REFERENCES_ORGANIZATION"
PERSON_HOLDS_PUBLIC_ROLE_PREDICATE = "PERSON_HOLDS_PUBLIC_ROLE"
DECLARACIONES_SAMPLE_PATH = PROJECT_ROOT / "data" / "sample" / "declaraciones_intereses_sample.json"


@dataclass(frozen=True)
class DeclaracionesInteresesImportResult:
    source_records: int
    claims: int
    evidences: int
    entities: int
    relationship_public: int
    declarations: int
    people: int
    roles: int
    companies: int
    organizations: int


@dataclass(frozen=True)
class DeclaracionesInteresesSummaryRow:
    person_id: str
    person_name: str
    declaration_period: str
    declaration_date: date | None
    role_name: str
    organization_name: str
    referenced_companies: tuple[str, ...]
    referenced_organizations: tuple[str, ...]
    claims: tuple[str, ...]
    relationships: tuple[str, ...]
    evidence: int


@dataclass(frozen=True)
class DeclaracionesInteresesSummary:
    declarations: int
    people: int
    roles: int
    companies: int
    organizations: int
    relationships: int
    evidence: int
    rows: tuple[DeclaracionesInteresesSummaryRow, ...]


def load_declaraciones_intereses_sample_payload(input_path: Path | None = None) -> dict[str, Any]:
    path = input_path or DECLARACIONES_SAMPLE_PATH
    payload = json.loads(path.read_text(encoding="utf-8"))
    _validate_sample_payload(payload)
    return payload


def build_declaraciones_intereses_sample_batch(
    session: Session,
    payload: dict[str, Any] | None = None,
) -> GraphBatch:
    _ = session
    sample = payload or load_declaraciones_intereses_sample_payload()
    records = sample.get("records") or []
    if not records:
        raise ValueError("Declaraciones sample must include at least one record")

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
        name=DECLARACIONES_SAMPLE_SOURCE_NAME,
        publisher="DatosEnOrden",
        url=DECLARACIONES_SAMPLE_SOURCE_URL,
        license=f"{LOCAL_TEST_DATA} / {NOT_OFFICIAL_DATA}",
        retrieved_at=datetime.now(timezone.utc),
        metadata={
            "classification": classification,
            "official_status": official_status,
            "dataset": DECLARACIONES_SAMPLE_DATASET_NAME,
        },
    )
    dataset = DatasetRecord(
        source_name=DECLARACIONES_SAMPLE_SOURCE_NAME,
        name=DECLARACIONES_SAMPLE_DATASET_NAME,
        description=(
            "LOCAL_TEST_DATA / NOT_OFFICIAL_DATA sample used to validate neutral "
            "declaration of interests graph links"
        ),
        version="local-sample-1",
        dataset_url=f"{DECLARACIONES_SAMPLE_SOURCE_URL}/dataset",
        content_hash=stable_json_hash(sample),
        loaded_at=datetime.now(timezone.utc),
        metadata={
            "classification": classification,
            "official_status": official_status,
            "dataset": DECLARACIONES_SAMPLE_DATASET_NAME,
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


def load_declaraciones_intereses_sample(
    session: Session,
    input_path: Path | None = None,
) -> DeclaracionesInteresesImportResult:
    payload = load_declaraciones_intereses_sample_payload(input_path)
    batch = build_declaraciones_intereses_sample_batch(session, payload)
    GraphLoader(session).load(batch, dry_run=False)

    return DeclaracionesInteresesImportResult(
        source_records=_count_rows(session, SourceRecord),
        claims=_count_rows(session, Claim),
        evidences=_count_rows(session, Evidence),
        entities=_count_rows(session, Entity),
        relationship_public=_count_rows(session, RelationshipPublic),
        declarations=len(payload["records"]),
        people=_count_entities(session, EntityType.PERSON.value),
        roles=_count_entities(session, EntityType.ROLE.value),
        companies=_count_entities(session, EntityType.COMPANY.value),
        organizations=_count_entities(session, EntityType.PUBLIC_ORGANIZATION.value),
    )


def read_declaraciones_intereses_summary(session: Session) -> DeclaracionesInteresesSummary:
    declaration_claims = _load_declaration_claims(session)
    rows: list[DeclaracionesInteresesSummaryRow] = []
    for declaration_claim in declaration_claims:
        person = declaration_claim.subject_entity
        source_record = declaration_claim.source_record
        if person is None or source_record is None:
            continue

        object_value = declaration_claim.object_value if isinstance(declaration_claim.object_value, dict) else {}
        claims = _load_claims_for_source_record(session, source_record.id)
        relationships = _load_relationships_for_source_record(session, source_record.id)
        rows.append(
            DeclaracionesInteresesSummaryRow(
                person_id=str(person.id),
                person_name=person.name,
                declaration_period=str(object_value.get("declaration_period", "")),
                declaration_date=_parse_date(object_value.get("declaration_date")),
                role_name=str(object_value.get("role_name", "")),
                organization_name=str(object_value.get("organization_name", "")),
                referenced_companies=tuple(object_value.get("declared_companies", ()) or ()),
                referenced_organizations=tuple(object_value.get("declared_organizations", ()) or ()),
                claims=tuple(sorted({claim.predicate for claim in claims})),
                relationships=tuple(sorted({relationship.relationship_type for relationship in relationships})),
                evidence=_count_evidence_for_source_record(session, source_record.id),
            )
        )

    return DeclaracionesInteresesSummary(
        declarations=len(rows),
        people=len({row.person_id for row in rows}),
        roles=len({row.role_name for row in rows if row.role_name}),
        companies=len({company for row in rows for company in row.referenced_companies}),
        organizations=len({row.organization_name for row in rows if row.organization_name}),
        relationships=len({(row.person_id, relationship) for row in rows for relationship in row.relationships}),
        evidence=sum(row.evidence for row in rows),
        rows=tuple(sorted(rows, key=lambda item: (item.person_name.lower(), item.declaration_period))),
    )


def render_declaraciones_intereses_summary_text(summary: DeclaracionesInteresesSummary) -> str:
    lines = [
        "declaraciones_intereses_summary:",
        f"  declarations={summary.declarations}",
        f"  people={summary.people}",
        f"  roles={summary.roles}",
        f"  companies={summary.companies}",
        f"  organizations={summary.organizations}",
        f"  relationships={summary.relationships}",
        f"  evidence={summary.evidence}",
    ]
    if not summary.rows:
        lines.append("  (no declaraciones intereses sample records found)")
        return "\n".join(lines)
    for row in summary.rows:
        lines.extend(
            [
                "  declaration_connection:",
                f"    person={row.person_name}",
                f"    role={row.role_name}",
                f"    organization={row.organization_name}",
                f"    period={row.declaration_period}",
                f"    declaration_date={row.declaration_date.isoformat() if row.declaration_date else 'None'}",
                f"    referenced_companies={', '.join(row.referenced_companies) if row.referenced_companies else 'none'}",
            ]
        )
    return "\n".join(lines)


def render_declaraciones_intereses_import_result_text(result: DeclaracionesInteresesImportResult) -> str:
    return "\n".join(
        [
            "declaraciones_intereses_sample_loaded:",
            f"  source_records={result.source_records}",
            f"  claims={result.claims}",
            f"  evidences={result.evidences}",
            f"  entities={result.entities}",
            f"  relationship_public={result.relationship_public}",
            f"  declarations={result.declarations}",
            f"  people={result.people}",
            f"  roles={result.roles}",
            f"  companies={result.companies}",
            f"  organizations={result.organizations}",
        ]
    )


def _build_record_components(record: dict[str, Any], classification: str, official_status: str) -> dict[str, Any]:
    external_id = str(record["external_id"])
    person_name = str(record["person_name"])
    role_name = str(record["role_name"])
    organization_name = str(record["organization_name"])
    declaration_date = _parse_date(record.get("declaration_date"))
    declaration_period = str(record.get("declaration_period", ""))
    declared_company_names = tuple(str(item["company_name"]) for item in record.get("declared_companies", ()))
    declared_organization_names = tuple(str(item["organization_name"]) for item in record.get("declared_organizations", ()))

    person_entity = _entity(EntityType.PERSON, "person", person_name, external_id, classification, official_status)
    role_entity = _entity(EntityType.ROLE, "role", role_name, external_id, classification, official_status)
    organization_entity = _entity(
        EntityType.PUBLIC_ORGANIZATION,
        "organization",
        organization_name,
        external_id,
        classification,
        official_status,
    )
    company_entities = tuple(
        _entity(EntityType.COMPANY, "company", company_name, external_id, classification, official_status)
        for company_name in declared_company_names
    )
    referenced_organization_entities = tuple(
        _entity(EntityType.PUBLIC_ORGANIZATION, "referenced-organization", org_name, external_id, classification, official_status)
        for org_name in declared_organization_names
    )

    source_record_payload = {
        **record,
        "classification": classification,
        "official_status": official_status,
        "sample_markers": [LOCAL_TEST_DATA, NOT_OFFICIAL_DATA],
    }
    source_record = SourceRecordPayload(
        external_id=external_id,
        record_type=DECLARACIONES_SAMPLE_RECORD_TYPE,
        payload_hash=stable_json_hash(source_record_payload),
        raw_payload=source_record_payload,
        retrieved_at=datetime.now(timezone.utc),
        status=WorkflowStatus.NORMALIZED,
    )

    evidence = _build_evidence(
        source_record,
        external_id=f"{external_id}:declaration",
        title=f"Declaraciones local sample - {person_name}",
        url=str(record["source_url"]),
        excerpt=(
            f"{LOCAL_TEST_DATA} / {NOT_OFFICIAL_DATA} declaration sample for "
            f"{person_name} in period {declaration_period}."
        ),
        published_at=declaration_date,
    )
    declaration_claim = ClaimRecord(
        subject_entity=person_entity,
        predicate=PERSON_HAS_DECLARATION_PREDICATE,
        object_entity=None,
        source_record=source_record,
        evidence=evidence,
        object_value={
            "declaration_period": declaration_period,
            "declaration_date": declaration_date.isoformat() if declaration_date else None,
            "role_name": role_name,
            "organization_name": organization_name,
            "declared_companies": declared_company_names,
            "declared_organizations": declared_organization_names,
            "dataset": DECLARACIONES_SAMPLE_DATASET_NAME,
        },
        valid_from=declaration_date,
        confidence=1.0,
        status=WorkflowStatus.VALIDATED,
        metadata={"dataset": DECLARACIONES_SAMPLE_DATASET_NAME},
    )
    role_claim = ClaimRecord(
        subject_entity=person_entity,
        predicate=PERSON_HOLDS_PUBLIC_ROLE_PREDICATE,
        object_entity=role_entity,
        source_record=source_record,
        evidence=evidence,
        object_value={"role_name": role_name, "organization_name": organization_name, "dataset": DECLARACIONES_SAMPLE_DATASET_NAME},
        valid_from=declaration_date,
        confidence=1.0,
        status=WorkflowStatus.VALIDATED,
        metadata={"dataset": DECLARACIONES_SAMPLE_DATASET_NAME},
    )
    role_org_claim = ClaimRecord(
        subject_entity=role_entity,
        predicate=RelationshipType.ROLE_BELONGS_TO_ORGANIZATION.value,
        object_entity=organization_entity,
        source_record=source_record,
        evidence=evidence,
        object_value={"role_name": role_name, "organization_name": organization_name, "dataset": DECLARACIONES_SAMPLE_DATASET_NAME},
        valid_from=declaration_date,
        confidence=1.0,
        status=WorkflowStatus.VALIDATED,
        metadata={"dataset": DECLARACIONES_SAMPLE_DATASET_NAME},
    )

    claims = [declaration_claim, role_claim, role_org_claim]
    public_relationships = [
        PublicRelationshipRecord(
            source_entity=person_entity,
            target_entity=role_entity,
            relationship_type=RelationshipType.PERSON_HOLDS_PUBLIC_ROLE,
            claim=role_claim,
            published_at=datetime.now(timezone.utc),
            status=WorkflowStatus.PUBLISHED,
            metadata={"classification": classification, "official_status": official_status, "dataset": DECLARACIONES_SAMPLE_DATASET_NAME},
        ),
        PublicRelationshipRecord(
            source_entity=role_entity,
            target_entity=organization_entity,
            relationship_type=RelationshipType.ROLE_BELONGS_TO_ORGANIZATION,
            claim=role_org_claim,
            published_at=datetime.now(timezone.utc),
            status=WorkflowStatus.PUBLISHED,
            metadata={"classification": classification, "official_status": official_status, "dataset": DECLARACIONES_SAMPLE_DATASET_NAME},
        ),
    ]

    for company_entity in company_entities:
        company_claim = ClaimRecord(
            subject_entity=person_entity,
            predicate=DECLARATION_REFERENCES_COMPANY_PREDICATE,
            object_entity=company_entity,
            source_record=source_record,
            evidence=evidence,
            object_value={"company_name": company_entity.name, "dataset": DECLARACIONES_SAMPLE_DATASET_NAME},
            valid_from=declaration_date,
            confidence=1.0,
            status=WorkflowStatus.VALIDATED,
            metadata={"dataset": DECLARACIONES_SAMPLE_DATASET_NAME},
        )
        claims.append(company_claim)
        public_relationships.append(
            PublicRelationshipRecord(
                source_entity=person_entity,
                target_entity=company_entity,
                relationship_type=RelationshipType.PERSON_REPRESENTS_COMPANY,
                claim=company_claim,
                published_at=datetime.now(timezone.utc),
                status=WorkflowStatus.PUBLISHED,
                metadata={"classification": classification, "official_status": official_status, "dataset": DECLARACIONES_SAMPLE_DATASET_NAME},
            )
        )

    for referenced_org_entity in referenced_organization_entities:
        claims.append(
            ClaimRecord(
                subject_entity=person_entity,
                predicate=DECLARATION_REFERENCES_ORGANIZATION_PREDICATE,
                object_entity=referenced_org_entity,
                source_record=source_record,
                evidence=evidence,
                object_value={"organization_name": referenced_org_entity.name, "dataset": DECLARACIONES_SAMPLE_DATASET_NAME},
                valid_from=declaration_date,
                confidence=1.0,
                status=WorkflowStatus.VALIDATED,
                metadata={"dataset": DECLARACIONES_SAMPLE_DATASET_NAME},
            )
        )

    return {
        "source_record": source_record,
        "entities": (person_entity, role_entity, organization_entity, *company_entities, *referenced_organization_entities),
        "evidence": (evidence,),
        "claims": tuple(claims),
        "public_relationships": tuple(public_relationships),
    }


def _entity(
    entity_type: EntityType,
    prefix: str,
    name: str,
    external_id: str,
    classification: str,
    official_status: str,
) -> EntityRecord:
    return EntityRecord(
        entity_type=entity_type,
        external_id=f"declaraciones-intereses:{prefix}:{normalized_key(name) or external_id}",
        name=name,
        description=f"{LOCAL_TEST_DATA} / {NOT_OFFICIAL_DATA} declaration sample entity.",
        normalized_key=normalized_key(name),
        metadata={
            "classification": classification,
            "official_status": official_status,
            "dataset": DECLARACIONES_SAMPLE_DATASET_NAME,
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
        source_name=DECLARACIONES_SAMPLE_SOURCE_NAME,
        title=title,
        url=url,
        published_at=published_at,
        excerpt=excerpt,
        metadata={
            "classification": LOCAL_TEST_DATA,
            "official_status": NOT_OFFICIAL_DATA,
            "dataset": DECLARACIONES_SAMPLE_DATASET_NAME,
            "external_id": external_id,
        },
    )


def _load_declaration_claims(session: Session) -> list[Claim]:
    return list(
        session.scalars(
            select(Claim)
            .join(SourceRecord, Claim.source_record_id == SourceRecord.id)
            .options(joinedload(Claim.subject_entity), joinedload(Claim.source_record))
            .where(
                SourceRecord.record_type == DECLARACIONES_SAMPLE_RECORD_TYPE,
                Claim.predicate == PERSON_HAS_DECLARATION_PREDICATE,
            )
            .order_by(Claim.created_at, Claim.id)
        ).all()
    )


def _load_claims_for_source_record(session: Session, source_record_id) -> tuple[Claim, ...]:  # type: ignore[no-untyped-def]
    return tuple(
        session.scalars(
            select(Claim)
            .where(Claim.source_record_id == source_record_id)
            .order_by(Claim.predicate.asc(), Claim.id.asc())
        ).all()
    )


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
    return int(session.scalar(select(func.count()).select_from(Evidence).where(Evidence.source_record_id == source_record_id)) or 0)


def _validate_sample_payload(payload: dict[str, Any]) -> None:
    if payload.get("classification") != LOCAL_TEST_DATA:
        raise ValueError("Declaraciones sample must be marked LOCAL_TEST_DATA")
    if payload.get("official_status") != NOT_OFFICIAL_DATA:
        raise ValueError("Declaraciones sample must be marked NOT_OFFICIAL_DATA")
    if "records" not in payload or not isinstance(payload["records"], list):
        raise ValueError("Declaraciones sample must include a records array")
    for record in payload["records"]:
        for key in ("external_id", "source_url", "person_name", "role_name", "organization_name", "declaration_date"):
            if not record.get(key):
                raise ValueError(f"Declaraciones sample record must include {key}")


def _parse_date(value: object | None) -> date | None:
    if value in (None, ""):
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

