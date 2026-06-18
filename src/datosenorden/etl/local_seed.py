from dataclasses import dataclass
from datetime import date, datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

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
from datosenorden.models import Claim, Evidence, RelationshipPublic, SourceRecord

LOCAL_SEED_CLASSIFICATION = "LOCAL_TEST_DATA"
LOCAL_SEED_OFFICIAL_STATUS = "NOT_OFFICIAL_DATA"
LOCAL_SEED_SOURCE_NAME = "DatosEnOrden Local Seed"
LOCAL_SEED_DATASET_NAME = "local-seed-traceability-flow"
LOCAL_SEED_SOURCE_URL = "local://seed/traceability-flow"
LOCAL_SEED_EVIDENCE_URL = "local://seed/traceability-flow/evidence/001"


@dataclass(frozen=True)
class LocalSeedResult:
    source_records: int
    claims: int
    evidences: int
    relationship_public: int


def build_local_traceability_seed_batch() -> GraphBatch:
    seed_payload = {
        "seed_type": "purchase_order_like",
        "classification": LOCAL_SEED_CLASSIFICATION,
        "official_status": LOCAL_SEED_OFFICIAL_STATUS,
        "purchase_order_code": "LOCAL-SEED-PO-001",
        "purchase_order_name": "Seed purchase order for persistence validation",
        "buyer_name": "DatosEnOrden Local Buyer",
        "supplier_name": "DatosEnOrden Local Supplier",
        "amount": 123456,
        "currency": "CLP",
    }
    source_record = SourceRecordPayload(
        external_id="local-seed:purchase-order:001",
        record_type="local_seed:purchase_order",
        payload_hash=stable_json_hash(seed_payload),
        raw_payload=seed_payload,
        retrieved_at=datetime.now(timezone.utc),
        status=WorkflowStatus.NORMALIZED,
    )
    buyer = EntityRecord(
        entity_type=EntityType.PUBLIC_ORGANIZATION,
        external_id="local-seed:buyer:001",
        name="DatosEnOrden Local Buyer",
        normalized_key=normalized_key("DatosEnOrden Local Buyer"),
        metadata={
            "classification": LOCAL_SEED_CLASSIFICATION,
            "official_status": LOCAL_SEED_OFFICIAL_STATUS,
        },
    )
    contract = EntityRecord(
        entity_type=EntityType.CONTRACT,
        external_id="local-seed:contract:001",
        name="Seed purchase order for persistence validation",
        normalized_key=normalized_key("LOCAL-SEED-PO-001"),
        metadata={
            "classification": LOCAL_SEED_CLASSIFICATION,
            "official_status": LOCAL_SEED_OFFICIAL_STATUS,
            "seed_type": "purchase_order_like",
        },
    )
    evidence = EvidenceRecord(
        source_record=source_record,
        source_name=LOCAL_SEED_SOURCE_NAME,
        title="LOCAL_TEST_DATA / NOT_OFFICIAL_DATA seed evidence",
        url=LOCAL_SEED_EVIDENCE_URL,
        published_at=date(2026, 1, 1),
        excerpt="LOCAL_TEST_DATA / NOT_OFFICIAL_DATA purchase-order-like seed record.",
        metadata={
            "classification": LOCAL_SEED_CLASSIFICATION,
            "official_status": LOCAL_SEED_OFFICIAL_STATUS,
            "seed_type": "purchase_order_like",
        },
    )
    claim = ClaimRecord(
        subject_entity=buyer,
        predicate=RelationshipType.ISSUES_PURCHASE_ORDER.value,
        object_entity=contract,
        source_record=source_record,
        evidence=evidence,
        valid_from=date(2026, 1, 1),
        status=WorkflowStatus.VALIDATED,
        metadata={
            "classification": LOCAL_SEED_CLASSIFICATION,
            "official_status": LOCAL_SEED_OFFICIAL_STATUS,
            "seed_type": "purchase_order_like",
        },
    )
    relationship_public = PublicRelationshipRecord(
        source_entity=buyer,
        target_entity=contract,
        relationship_type=RelationshipType.ISSUES_PURCHASE_ORDER,
        claim=claim,
        published_at=datetime.now(timezone.utc),
        status=WorkflowStatus.PUBLISHED,
        metadata={
            "classification": LOCAL_SEED_CLASSIFICATION,
            "official_status": LOCAL_SEED_OFFICIAL_STATUS,
            "seed_type": "purchase_order_like",
        },
    )
    source = SourceInfo(
        name=LOCAL_SEED_SOURCE_NAME,
        publisher="DatosEnOrden",
        url=LOCAL_SEED_SOURCE_URL,
        license=f"{LOCAL_SEED_CLASSIFICATION} / {LOCAL_SEED_OFFICIAL_STATUS}",
        retrieved_at=datetime.now(timezone.utc),
        metadata={
            "classification": LOCAL_SEED_CLASSIFICATION,
            "official_status": LOCAL_SEED_OFFICIAL_STATUS,
            "seed_type": "purchase_order_like",
        },
    )
    dataset = DatasetRecord(
        source_name=LOCAL_SEED_SOURCE_NAME,
        name=LOCAL_SEED_DATASET_NAME,
        description=(
            "LOCAL_TEST_DATA / NOT_OFFICIAL_DATA seed used only to validate persistence "
            "without a ChileCompra ticket"
        ),
        version="local-seed-1",
        dataset_url=f"{LOCAL_SEED_SOURCE_URL}/dataset",
        content_hash=source_record.payload_hash,
        loaded_at=datetime.now(timezone.utc),
        metadata={
            "classification": LOCAL_SEED_CLASSIFICATION,
            "official_status": LOCAL_SEED_OFFICIAL_STATUS,
            "seed_type": "purchase_order_like",
        },
    )
    return GraphBatch(
        source=source,
        dataset=dataset,
        source_records=(source_record,),
        entities=(buyer, contract),
        evidence=(evidence,),
        claims=(claim,),
        public_relationships=(relationship_public,),
        raw_count=1,
        rejected_count=0,
        errors=(),
    )


def persist_local_traceability_seed(session: Session) -> LocalSeedResult:
    batch = build_local_traceability_seed_batch()
    GraphLoader(session).load(batch, dry_run=False)
    return LocalSeedResult(
        source_records=_count_rows(session, SourceRecord),
        claims=_count_rows(session, Claim),
        evidences=_count_rows(session, Evidence),
        relationship_public=_count_rows(session, RelationshipPublic),
    )


def _count_rows(session: Session, model) -> int:  # type: ignore[no-untyped-def]
    return int(session.scalar(select(func.count()).select_from(model)) or 0)
