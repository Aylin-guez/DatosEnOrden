from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
import json
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import distinct, func, select
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
from datosenorden.maintenance.entity_matching import EntityMatchCandidate
from datosenorden.maintenance.entity_matching import match_entity_candidates
from datosenorden.models import Claim, Entity, Evidence, RelationshipPublic, SourceRecord

LOCAL_TEST_DATA = "LOCAL_TEST_DATA"
NOT_OFFICIAL_DATA = "NOT_OFFICIAL_DATA"
DIPRES_SAMPLE_DATASET_NAME = "dipres-budget-sample"
DIPRES_SAMPLE_SOURCE_NAME = "DatosEnOrden DIPRES Sample"
DIPRES_SAMPLE_SOURCE_URL = "local://sample/dipres-budget"
DIPRES_SAMPLE_RECORD_TYPE = "dipres:budget_sample"
DIPRES_APPROVED_BUDGET_PREDICATE = "HAS_APPROVED_BUDGET"
DIPRES_EXECUTED_BUDGET_PREDICATE = "HAS_EXECUTED_BUDGET"
DIPRES_MATCH_PREDICATE = "MATCHED_TO_ORGANIZATION"
DIPRES_SAMPLE_PATH = PROJECT_ROOT / "data" / "sample" / "dipres_budget_sample.json"


@dataclass(frozen=True)
class DipresMatchResult:
    entity: Entity
    match_method: str
    confidence: float


@dataclass(frozen=True)
class DipresImportResult:
    source_records: int
    claims: int
    evidences: int
    entities: int
    relationship_public: int
    matched_entity_id: str
    matched_entity_name: str
    budget_entity_id: str
    budget_entity_name: str


@dataclass(frozen=True)
class BudgetSummaryRow:
    budget_entity_id: str
    budget_entity_name: str
    organization_id: str
    organization_name: str
    fiscal_year: int | None
    approved_budget: int
    executed_budget: int
    purchase_orders: int
    suppliers: int
    match_method: str
    match_confidence: float
    currency: str


def load_dipres_sample_payload(input_path: Path | None = None) -> dict[str, Any]:
    path = input_path or DIPRES_SAMPLE_PATH
    payload = json.loads(path.read_text(encoding="utf-8"))
    _validate_sample_payload(payload)
    return payload


def build_dipres_sample_batch(session: Session, payload: dict[str, Any] | None = None) -> GraphBatch:
    sample = payload or load_dipres_sample_payload()
    records = sample.get("records") or []
    if not records:
        raise ValueError("DIPRES sample must include at least one record")

    record = records[0]
    classification = str(sample["classification"])
    official_status = str(sample["official_status"])
    ministry_name = str(record["ministry_name"])
    service_name = str(record["service_name"])
    fiscal_year = int(record["fiscal_year"])
    approved_budget = int(record["approved_budget"])
    executed_budget = int(record["executed_budget"])
    currency = str(record.get("currency", "CLP"))

    match = _match_existing_organization(session, service_name)
    budget_entity = _build_budget_entity(record, classification, official_status)
    organization_entity = _build_matched_organization_entity(match)

    source_record_payload = {
        **record,
        "classification": classification,
        "official_status": official_status,
        "sample_markers": [LOCAL_TEST_DATA, NOT_OFFICIAL_DATA],
    }
    source_record = SourceRecordPayload(
        external_id=str(record["external_id"]),
        record_type=DIPRES_SAMPLE_RECORD_TYPE,
        payload_hash=stable_json_hash(source_record_payload),
        raw_payload=source_record_payload,
        retrieved_at=datetime.now(timezone.utc),
        status=WorkflowStatus.NORMALIZED,
    )

    approved_evidence = _build_evidence(
        source_record,
        external_id=f"{record['external_id']}:approved",
        title=f"DIPRES approved budget sample - {service_name}",
        url=f"local://sample/dipres-budget/{record['external_id']}/approved",
        excerpt=(
            f"{LOCAL_TEST_DATA} / {NOT_OFFICIAL_DATA} approved budget sample for "
            f"{service_name} ({fiscal_year})"
        ),
        fiscal_year=fiscal_year,
    )
    executed_evidence = _build_evidence(
        source_record,
        external_id=f"{record['external_id']}:executed",
        title=f"DIPRES executed budget sample - {service_name}",
        url=f"local://sample/dipres-budget/{record['external_id']}/executed",
        excerpt=(
            f"{LOCAL_TEST_DATA} / {NOT_OFFICIAL_DATA} executed budget sample for "
            f"{service_name} ({fiscal_year})"
        ),
        fiscal_year=fiscal_year,
    )
    match_evidence = _build_evidence(
        source_record,
        external_id=f"{record['external_id']}:match",
        title=f"DIPRES entity match sample - {service_name}",
        url=f"local://sample/dipres-budget/{record['external_id']}/match",
        excerpt=(
            f"{LOCAL_TEST_DATA} / {NOT_OFFICIAL_DATA} normalized match from {service_name} "
            f"to {organization_entity.name}"
        ),
        fiscal_year=fiscal_year,
    )

    approved_claim = ClaimRecord(
        subject_entity=organization_entity,
        predicate=DIPRES_APPROVED_BUDGET_PREDICATE,
        source_record=source_record,
        evidence=approved_evidence,
        object_value={
            "amount": approved_budget,
            "currency": currency,
            "fiscal_year": fiscal_year,
            "ministry_name": ministry_name,
            "service_name": service_name,
            "dataset": DIPRES_SAMPLE_DATASET_NAME,
        },
        valid_from=date(fiscal_year, 1, 1),
        valid_to=date(fiscal_year, 12, 31),
        confidence=1.0,
        status=WorkflowStatus.VALIDATED,
        metadata={},
    )
    executed_claim = ClaimRecord(
        subject_entity=organization_entity,
        predicate=DIPRES_EXECUTED_BUDGET_PREDICATE,
        source_record=source_record,
        evidence=executed_evidence,
        object_value={
            "amount": executed_budget,
            "currency": currency,
            "fiscal_year": fiscal_year,
            "ministry_name": ministry_name,
            "service_name": service_name,
            "dataset": DIPRES_SAMPLE_DATASET_NAME,
        },
        valid_from=date(fiscal_year, 1, 1),
        valid_to=date(fiscal_year, 12, 31),
        confidence=1.0,
        status=WorkflowStatus.VALIDATED,
        metadata={},
    )
    match_claim = ClaimRecord(
        subject_entity=budget_entity,
        predicate=DIPRES_MATCH_PREDICATE,
        source_record=source_record,
        evidence=match_evidence,
        object_entity=organization_entity,
        object_value={
            "matching_method": match.match_method,
            "confidence": match.confidence,
            "source_service_name": service_name,
            "matched_entity_name": match.entity.name,
            "matched_entity_external_id": match.entity.external_id,
            "dataset": DIPRES_SAMPLE_DATASET_NAME,
        },
        valid_from=date(fiscal_year, 1, 1),
        valid_to=date(fiscal_year, 12, 31),
        confidence=match.confidence,
        status=WorkflowStatus.VALIDATED,
        metadata={},
    )
    relationship = PublicRelationshipRecord(
        source_entity=budget_entity,
        target_entity=organization_entity,
        relationship_type=RelationshipType.BUDGET_ALLOCATED_TO,
        claim=match_claim,
        published_at=datetime.now(timezone.utc),
        status=WorkflowStatus.PUBLISHED,
        metadata={
            "classification": classification,
            "official_status": official_status,
            "dataset": DIPRES_SAMPLE_DATASET_NAME,
        },
    )

    source = SourceInfo(
        name=DIPRES_SAMPLE_SOURCE_NAME,
        publisher="DatosEnOrden",
        url=DIPRES_SAMPLE_SOURCE_URL,
        license=f"{LOCAL_TEST_DATA} / {NOT_OFFICIAL_DATA}",
        retrieved_at=datetime.now(timezone.utc),
        metadata={
            "classification": classification,
            "official_status": official_status,
            "dataset": DIPRES_SAMPLE_DATASET_NAME,
        },
    )
    dataset = DatasetRecord(
        source_name=DIPRES_SAMPLE_SOURCE_NAME,
        name=DIPRES_SAMPLE_DATASET_NAME,
        description=(
            "LOCAL_TEST_DATA / NOT_OFFICIAL_DATA sample used to validate the first "
            "cross-dataset link prototype"
        ),
        version="local-sample-1",
        dataset_url=f"{DIPRES_SAMPLE_SOURCE_URL}/dataset",
        content_hash=stable_json_hash(sample),
        loaded_at=datetime.now(timezone.utc),
        metadata={
            "classification": classification,
            "official_status": official_status,
            "dataset": DIPRES_SAMPLE_DATASET_NAME,
        },
    )
    return GraphBatch(
        source=source,
        dataset=dataset,
        source_records=(source_record,),
        entities=(budget_entity, organization_entity),
        evidence=(approved_evidence, executed_evidence, match_evidence),
        claims=(approved_claim, executed_claim, match_claim),
        public_relationships=(relationship,),
        raw_count=len(records),
        rejected_count=0,
        errors=(),
    )


def persist_dipres_sample(session: Session, input_path: Path | None = None) -> DipresImportResult:
    payload = load_dipres_sample_payload(input_path)
    batch = build_dipres_sample_batch(session, payload)
    GraphLoader(session).load(batch, dry_run=False)

    matched = _match_existing_organization(session, str(payload["records"][0]["service_name"]))
    budget_entity = _build_budget_entity(
        payload["records"][0],
        str(payload["classification"]),
        str(payload["official_status"]),
    )
    persisted_budget_entity = session.scalar(
        select(Entity).where(
            Entity.entity_type == EntityType.BUDGET.value,
            Entity.external_id == budget_entity.external_id,
        )
    )
    if persisted_budget_entity is None:
        raise LookupError(f"Budget entity not found after load: {budget_entity.external_id}")
    return DipresImportResult(
        source_records=_count_rows(session, SourceRecord),
        claims=_count_rows(session, Claim),
        evidences=_count_rows(session, Evidence),
        entities=_count_rows(session, Entity),
        relationship_public=_count_rows(session, RelationshipPublic),
        matched_entity_id=str(matched.entity.id),
        matched_entity_name=matched.entity.name,
        budget_entity_id=str(persisted_budget_entity.id),
        budget_entity_name=persisted_budget_entity.name,
    )


def read_budget_summary(session: Session) -> tuple[BudgetSummaryRow, ...]:
    match_claims = _load_budget_match_claims(session)
    rows: list[BudgetSummaryRow] = []
    for match_claim in match_claims:
        if match_claim.object_entity is None:
            continue
        organization = match_claim.object_entity
        match_data = match_claim.object_value or {}
        source_record = match_claim.source_record
        if source_record is None:
            continue
        budget_claims = _load_budget_amount_claims(session, source_record.id, organization.id)
        approved_budget = _extract_budget_amount(budget_claims, DIPRES_APPROVED_BUDGET_PREDICATE)
        executed_budget = _extract_budget_amount(budget_claims, DIPRES_EXECUTED_BUDGET_PREDICATE)
        fiscal_year = _extract_fiscal_year(budget_claims)
        currency = _extract_currency(budget_claims)
        rows.append(
            BudgetSummaryRow(
                budget_entity_id=str(match_claim.subject_entity.id),
                budget_entity_name=match_claim.subject_entity.name,
                organization_id=str(organization.id),
                organization_name=organization.name,
                fiscal_year=fiscal_year,
                approved_budget=approved_budget,
                executed_budget=executed_budget,
                purchase_orders=_count_purchase_orders_for_entity(session, organization.id),
                suppliers=_count_suppliers_for_entity(session, organization.id),
                match_method=str(match_data.get("matching_method", "unknown")),
                match_confidence=float(match_data.get("confidence", match_claim.confidence)),
                currency=currency,
            )
        )
    return tuple(sorted(rows, key=lambda row: (-row.approved_budget, row.organization_name.lower(), row.organization_id)))


def render_budget_summary_text(rows: tuple[BudgetSummaryRow, ...]) -> str:
    lines = ["budget_summary:"]
    if not rows:
        lines.append("  (no budget matches found)")
        return "\n".join(lines)
    for row in rows:
        lines.extend(
            [
                "  organization:",
                f"    id={row.organization_id}",
                f"    name={row.organization_name}",
                f"    budget_entity_id={row.budget_entity_id}",
                f"    budget_entity_name={row.budget_entity_name}",
                f"    fiscal_year={row.fiscal_year if row.fiscal_year is not None else 'None'}",
                f"    approved_budget={row.approved_budget}",
                f"    executed_budget={row.executed_budget}",
                f"    purchase_orders={row.purchase_orders}",
                f"    suppliers={row.suppliers}",
                f"    match_method={row.match_method}",
                f"    match_confidence={row.match_confidence}",
                f"    currency={row.currency}",
                "",
            ]
        )
    return "\n".join(lines).rstrip()


def render_dipres_import_result_text(result: DipresImportResult) -> str:
    return "\n".join(
        [
            "dipres_sample_loaded:",
            f"  source_records={result.source_records}",
            f"  claims={result.claims}",
            f"  evidences={result.evidences}",
            f"  entities={result.entities}",
            f"  relationship_public={result.relationship_public}",
            f"  matched_entity_id={result.matched_entity_id}",
            f"  matched_entity_name={result.matched_entity_name}",
            f"  budget_entity_id={result.budget_entity_id}",
            f"  budget_entity_name={result.budget_entity_name}",
        ]
    )


def _validate_sample_payload(payload: dict[str, Any]) -> None:
    if payload.get("classification") != LOCAL_TEST_DATA:
        raise ValueError("DIPRES sample must be marked LOCAL_TEST_DATA")
    if payload.get("official_status") != NOT_OFFICIAL_DATA:
        raise ValueError("DIPRES sample must be marked NOT_OFFICIAL_DATA")
    if "records" not in payload or not isinstance(payload["records"], list):
        raise ValueError("DIPRES sample must include a records array")


def _match_existing_organization(session: Session, service_name: str) -> DipresMatchResult:
    candidates = match_entity_candidates(
        session,
        entity_type=EntityType.PUBLIC_ORGANIZATION.value,
        name=service_name,
        limit=1,
    )
    if not candidates:
        raise LookupError(f"No PUBLIC_ORGANIZATION match found for {service_name}")

    candidate = candidates[0]
    entity = session.get(Entity, candidate_entity_uuid(candidate)) if hasattr(session, "get") else None
    if entity is None:
        entity = _candidate_to_entity(candidate)
    if entity is None:
        raise LookupError(f"Matched entity not found after lookup: {candidate.candidate_entity_id}")

    return DipresMatchResult(entity=entity, match_method=candidate.match_method, confidence=candidate.score)


def _build_budget_entity(record: dict[str, Any], classification: str, official_status: str) -> EntityRecord:
    fiscal_year = int(record["fiscal_year"])
    service_name = str(record["service_name"])
    external_id = str(record["external_id"])
    return EntityRecord(
        entity_type=EntityType.BUDGET,
        external_id=external_id,
        name=f"DIPRES budget {fiscal_year} - {service_name}",
        description=(
            f"{LOCAL_TEST_DATA} / {NOT_OFFICIAL_DATA} budget source for {service_name} "
            f"({fiscal_year})"
        ),
        normalized_key=normalized_key(f"{service_name} {fiscal_year}"),
        metadata={
            "classification": classification,
            "official_status": official_status,
            "dataset": DIPRES_SAMPLE_DATASET_NAME,
            "service_name": service_name,
            "ministry_name": str(record["ministry_name"]),
            "fiscal_year": fiscal_year,
        },
    )


def _build_matched_organization_entity(match: DipresMatchResult) -> EntityRecord:
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


def _build_evidence(
    source_record: SourceRecordPayload,
    *,
    external_id: str,
    title: str,
    url: str,
    excerpt: str,
    fiscal_year: int,
) -> EvidenceRecord:
    return EvidenceRecord(
        source_record=source_record,
        source_name=DIPRES_SAMPLE_SOURCE_NAME,
        title=title,
        url=url,
        published_at=date(fiscal_year, 12, 31),
        excerpt=excerpt,
        metadata={
            "classification": LOCAL_TEST_DATA,
            "official_status": NOT_OFFICIAL_DATA,
            "dataset": DIPRES_SAMPLE_DATASET_NAME,
            "external_id": external_id,
        },
    )


def _load_budget_match_claims(session: Session) -> list[Claim]:
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
                SourceRecord.record_type == DIPRES_SAMPLE_RECORD_TYPE,
                Claim.predicate == DIPRES_MATCH_PREDICATE,
            )
            .order_by(Claim.created_at, Claim.id)
        ).all()
    )


def _load_budget_amount_claims(session: Session, source_record_id, organization_id) -> list[Claim]:  # type: ignore[no-untyped-def]
    return list(
        session.scalars(
            select(Claim)
            .where(
                Claim.source_record_id == source_record_id,
                Claim.subject_entity_id == organization_id,
                Claim.predicate.in_(
                    (DIPRES_APPROVED_BUDGET_PREDICATE, DIPRES_EXECUTED_BUDGET_PREDICATE)
                ),
            )
            .order_by(Claim.created_at, Claim.id)
        ).all()
    )


def _extract_budget_amount(claims: list[Claim], predicate: str) -> int:
    for claim in claims:
        if claim.predicate != predicate:
            continue
        value = claim.object_value or {}
        if isinstance(value, dict):
            amount = value.get("amount")
            if amount is not None:
                return int(amount)
    return 0


def _extract_fiscal_year(claims: list[Claim]) -> int | None:
    for claim in claims:
        value = claim.object_value or {}
        if isinstance(value, dict) and value.get("fiscal_year") is not None:
            return int(value["fiscal_year"])
    return None


def _extract_currency(claims: list[Claim]) -> str:
    for claim in claims:
        value = claim.object_value or {}
        if isinstance(value, dict) and value.get("currency") is not None:
            return str(value["currency"])
    return "CLP"


def _count_purchase_orders_for_entity(session: Session, entity_id) -> int:  # type: ignore[no-untyped-def]
    return int(
        session.scalar(
            select(func.count(distinct(Claim.source_record_id)))
            .select_from(Claim)
            .where(
                Claim.subject_entity_id == entity_id,
                Claim.predicate == "ISSUES_PURCHASE_ORDER",
            )
        )
        or 0
    )


def _count_suppliers_for_entity(session: Session, entity_id) -> int:  # type: ignore[no-untyped-def]
    purchase_order_source_records = select(distinct(Claim.source_record_id)).where(
        Claim.subject_entity_id == entity_id,
        Claim.predicate == "ISSUES_PURCHASE_ORDER",
    )
    return int(
        session.scalar(
            select(func.count(distinct(Claim.subject_entity_id)))
            .select_from(Claim)
            .where(
                Claim.predicate == "RECEIVES_CONTRACT",
                Claim.source_record_id.in_(purchase_order_source_records),
            )
        )
        or 0
    )


def _count_rows(session: Session, model) -> int:  # type: ignore[no-untyped-def]
    return int(session.scalar(select(func.count()).select_from(model)) or 0)


def candidate_entity_uuid(candidate: EntityMatchCandidate) -> UUID:
    return UUID(candidate.candidate_entity_id)


def _candidate_to_entity(candidate: EntityMatchCandidate) -> Entity:
    return Entity(
        id=candidate_entity_uuid(candidate),
        entity_type=candidate.entity_type,
        name=candidate.candidate_name,
        external_id=candidate.candidate_entity_id,
        status="active",
    )
