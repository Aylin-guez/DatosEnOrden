from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from datosenorden.etl.chilecompra.client import ChileCompraClient
from datosenorden.etl.chilecompra.pipeline import ChileCompraPipeline
from datosenorden.models import Claim, Entity, RelationshipPublic, SourceRecord
from datosenorden.models import Evidence

PURCHASE_ORDER_RECORD_TYPE = "chilecompra:purchase_order"
PUBLIC_ORGANIZATION_ENTITY_TYPE = "PUBLIC_ORGANIZATION"
COMPANY_ENTITY_TYPE = "COMPANY"
DEFAULT_LOOKBACK_DAYS = 180


@dataclass(frozen=True)
class PurchaseOrderLoadCounts:
    source_records: int
    claims: int
    evidences: int
    relationship_public: int
    days_scanned: int


@dataclass(frozen=True)
class PurchaseOrderDatasetCounts:
    source_records: int
    claims: int
    evidences: int
    relationship_public: int
    distinct_buyers: int
    distinct_suppliers: int


@dataclass(frozen=True)
class DatasetSummaryCounts:
    total_purchase_orders: int
    total_public_organizations: int
    total_suppliers: int
    total_claims: int
    total_relationships: int


def load_sample_purchase_orders(
    client: ChileCompraClient,
    session: Session,
    limit: int,
    anchor_date: date | None = None,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
) -> PurchaseOrderLoadCounts:
    if limit < 1:
        raise ValueError("limit must be greater than zero")
    if lookback_days < 1:
        raise ValueError("lookback_days must be greater than zero")

    pipeline = ChileCompraPipeline(client=client, session=session)
    remaining = limit
    total_source_records = 0
    total_claims = 0
    total_evidences = 0
    total_relationships = 0
    days_scanned = 0
    current_day = anchor_date or date.today()

    for offset in range(lookback_days):
        if remaining <= 0:
            break

        day = current_day - timedelta(days=offset)
        days_scanned += 1
        result = pipeline.run_purchase_orders_for_day(day, status="todos", dry_run=False, limit=remaining)

        total_source_records += result.source_record_count
        total_claims += result.claim_count
        total_evidences += result.evidence_count
        total_relationships += result.public_relationship_count
        remaining -= result.source_record_count

    return PurchaseOrderLoadCounts(
        source_records=total_source_records,
        claims=total_claims,
        evidences=total_evidences,
        relationship_public=total_relationships,
        days_scanned=days_scanned,
    )


def read_purchase_order_dataset_counts(session: Session) -> PurchaseOrderDatasetCounts:
    source_records = _scalar_count(
        session,
        select(func.count()).select_from(SourceRecord).where(SourceRecord.record_type == PURCHASE_ORDER_RECORD_TYPE),
    )
    claims = _scalar_count(
        session,
        select(func.count())
        .select_from(Claim)
        .join(SourceRecord, Claim.source_record_id == SourceRecord.id)
        .where(SourceRecord.record_type == PURCHASE_ORDER_RECORD_TYPE),
    )
    evidences = _scalar_count(
        session,
        select(func.count())
        .select_from(Evidence)
        .join(Claim, Evidence.claim_id == Claim.id)
        .join(SourceRecord, Claim.source_record_id == SourceRecord.id)
        .where(SourceRecord.record_type == PURCHASE_ORDER_RECORD_TYPE),
    )
    relationship_public = _scalar_count(
        session,
        select(func.count())
        .select_from(RelationshipPublic)
        .join(Claim, RelationshipPublic.claim_id == Claim.id)
        .join(SourceRecord, Claim.source_record_id == SourceRecord.id)
        .where(SourceRecord.record_type == PURCHASE_ORDER_RECORD_TYPE),
    )
    distinct_buyers = _scalar_count(
        session,
        select(func.count(distinct(Entity.id)))
        .select_from(Claim)
        .join(SourceRecord, Claim.source_record_id == SourceRecord.id)
        .join(Entity, Claim.subject_entity_id == Entity.id)
        .where(
            SourceRecord.record_type == PURCHASE_ORDER_RECORD_TYPE,
            Entity.entity_type == PUBLIC_ORGANIZATION_ENTITY_TYPE,
        ),
    )
    distinct_suppliers = _scalar_count(
        session,
        select(func.count(distinct(Entity.id)))
        .select_from(Claim)
        .join(SourceRecord, Claim.source_record_id == SourceRecord.id)
        .join(Entity, Claim.subject_entity_id == Entity.id)
        .where(
            SourceRecord.record_type == PURCHASE_ORDER_RECORD_TYPE,
            Entity.entity_type == COMPANY_ENTITY_TYPE,
        ),
    )

    return PurchaseOrderDatasetCounts(
        source_records=source_records,
        claims=claims,
        evidences=evidences,
        relationship_public=relationship_public,
        distinct_buyers=distinct_buyers,
        distinct_suppliers=distinct_suppliers,
    )


def read_dataset_summary(session: Session) -> DatasetSummaryCounts:
    total_purchase_orders = _scalar_count(
        session,
        select(func.count(distinct(SourceRecord.external_id))).where(
            SourceRecord.record_type == PURCHASE_ORDER_RECORD_TYPE
        ),
    )
    total_public_organizations = _scalar_count(
        session,
        select(func.count(distinct(Entity.id)))
        .select_from(Claim)
        .join(SourceRecord, Claim.source_record_id == SourceRecord.id)
        .join(Entity, Claim.subject_entity_id == Entity.id)
        .where(
            SourceRecord.record_type == PURCHASE_ORDER_RECORD_TYPE,
            Entity.entity_type == PUBLIC_ORGANIZATION_ENTITY_TYPE,
        ),
    )
    total_suppliers = _scalar_count(
        session,
        select(func.count(distinct(Entity.id)))
        .select_from(Claim)
        .join(SourceRecord, Claim.source_record_id == SourceRecord.id)
        .join(Entity, Claim.subject_entity_id == Entity.id)
        .where(
            SourceRecord.record_type == PURCHASE_ORDER_RECORD_TYPE,
            Entity.entity_type == COMPANY_ENTITY_TYPE,
        ),
    )
    total_claims = _scalar_count(
        session,
        select(func.count())
        .select_from(Claim)
        .join(SourceRecord, Claim.source_record_id == SourceRecord.id)
        .where(SourceRecord.record_type == PURCHASE_ORDER_RECORD_TYPE),
    )
    total_relationships = _scalar_count(
        session,
        select(func.count())
        .select_from(RelationshipPublic)
        .join(Claim, RelationshipPublic.claim_id == Claim.id)
        .join(SourceRecord, Claim.source_record_id == SourceRecord.id)
        .where(SourceRecord.record_type == PURCHASE_ORDER_RECORD_TYPE),
    )

    return DatasetSummaryCounts(
        total_purchase_orders=total_purchase_orders,
        total_public_organizations=total_public_organizations,
        total_suppliers=total_suppliers,
        total_claims=total_claims,
        total_relationships=total_relationships,
    )


def render_purchase_order_dataset_counts(counts: PurchaseOrderDatasetCounts) -> str:
    return "\n".join(
        [
            "purchase_order_load_summary:",
            f"  source_records count={counts.source_records}",
            f"  claims count={counts.claims}",
            f"  evidences count={counts.evidences}",
            f"  relationship_public count={counts.relationship_public}",
            f"  distinct buyers count={counts.distinct_buyers}",
            f"  distinct suppliers count={counts.distinct_suppliers}",
        ]
    )


def render_dataset_summary(counts: DatasetSummaryCounts) -> str:
    return "\n".join(
        [
            "dataset_summary:",
            f"  total purchase orders={counts.total_purchase_orders}",
            f"  total public organizations={counts.total_public_organizations}",
            f"  total suppliers={counts.total_suppliers}",
            f"  total claims={counts.total_claims}",
            f"  total relationships={counts.total_relationships}",
        ]
    )


def _scalar_count(session: Session, statement) -> int:  # type: ignore[no-untyped-def]
    return int(session.scalar(statement) or 0)
