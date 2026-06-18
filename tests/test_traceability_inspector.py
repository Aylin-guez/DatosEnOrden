from __future__ import annotations

from datosenorden.maintenance.traceability_inspector import TraceClaimSummary
from datosenorden.maintenance.traceability_inspector import TraceEntitySummary
from datosenorden.maintenance.traceability_inspector import TraceEvidenceSummary
from datosenorden.maintenance.traceability_inspector import TraceRelationshipSummary
from datosenorden.maintenance.traceability_inspector import TraceCompactSummary
from datosenorden.maintenance.traceability_inspector import TraceSourceRecordSummary
from datosenorden.maintenance.traceability_inspector import render_traceability_chain
from datosenorden.maintenance.traceability_inspector import render_trace_summary
from datosenorden.maintenance.traceability_inspector import summarize_traceability_chain


def _sample_trace() -> tuple[TraceSourceRecordSummary, ...]:
    source_entity = TraceEntitySummary(
        entity_type="PUBLIC_ORGANIZATION",
        name="Direccion de Compras y Contratacion Publica",
        external_id="chilecompra:buyer:6945",
    )
    supplier_entity = TraceEntitySummary(
        entity_type="COMPANY",
        name="Camara de Comercio de Santiago A.G.",
        external_id="chilecompra:supplier:17793",
    )
    target_entity = TraceEntitySummary(
        entity_type="CONTRACT",
        name="Compra de servicios",
        external_id="chilecompra:purchase_order:2097-241-SE14",
    )
    evidence = TraceEvidenceSummary(
        id="11111111-1111-1111-1111-111111111111",
        title="Ficha Mercado Publico orden de compra 2097-241-SE14",
        url="https://www.mercadopublico.cl/Compra?codigo=2097-241-SE14",
        published_at=None,
        claim_id="22222222-2222-2222-2222-222222222222",
    )
    relationship = TraceRelationshipSummary(
        id="33333333-3333-3333-3333-333333333333",
        relationship_type="ISSUES_PURCHASE_ORDER",
        status="published",
        source_entity=source_entity,
        target_entity=target_entity,
        claim_id="22222222-2222-2222-2222-222222222222",
    )
    supplier_evidence = TraceEvidenceSummary(
        id="44444444-4444-4444-4444-444444444444",
        title="Ficha Mercado Publico orden de compra 2097-241-SE14",
        url="https://www.mercadopublico.cl/Compra?codigo=2097-241-SE14",
        published_at=None,
        claim_id="55555555-5555-5555-5555-555555555555",
    )
    supplier_relationship = TraceRelationshipSummary(
        id="66666666-6666-6666-6666-666666666666",
        relationship_type="RECEIVES_CONTRACT",
        status="published",
        source_entity=supplier_entity,
        target_entity=target_entity,
        claim_id="55555555-5555-5555-5555-555555555555",
    )
    claim = TraceClaimSummary(
        id="22222222-2222-2222-2222-222222222222",
        predicate="ISSUES_PURCHASE_ORDER",
        status="validated",
        subject_entity=source_entity,
        object_entity=target_entity,
        valid_from=None,
        evidences=(evidence,),
        relationship_public=(relationship,),
    )
    supplier_claim = TraceClaimSummary(
        id="55555555-5555-5555-5555-555555555555",
        predicate="RECEIVES_CONTRACT",
        status="validated",
        subject_entity=supplier_entity,
        object_entity=target_entity,
        valid_from=None,
        evidences=(supplier_evidence,),
        relationship_public=(supplier_relationship,),
    )
    return (
        TraceSourceRecordSummary(
            id="12345678-1234-1234-1234-123456789012",
            status="published",
            record_type="chilecompra:purchase_order",
            external_id="2097-241-SE14",
            claims=(claim, supplier_claim),
        ),
    )


def test_render_traceability_chain_includes_full_chain() -> None:
    report = render_traceability_chain(_sample_trace(), "2097-241-SE14")

    assert "traceability_inspection: external_id=2097-241-SE14 source_records=1" in report
    assert "source_record[1]:" in report
    assert "record_type=chilecompra:purchase_order" in report
    assert "claims=2" in report
    assert "predicate=ISSUES_PURCHASE_ORDER" in report
    assert "subject_entity=PUBLIC_ORGANIZATION | Direccion de Compras y Contratacion Publica" in report
    assert "object_entity=CONTRACT | Compra de servicios" in report
    assert "evidence[1]:" in report
    assert "relationship_public[1]:" in report


def test_render_traceability_chain_is_read_only_and_non_secret() -> None:
    report = render_traceability_chain(_sample_trace(), "2097-241-SE14")

    assert "ticket" not in report.lower()
    assert "DATABASE_URL" not in report


def test_summarize_traceability_chain_compacts_roles_and_counts() -> None:
    summary = summarize_traceability_chain(_sample_trace())

    assert summary == (
        TraceCompactSummary(
            source_record_id="12345678-1234-1234-1234-123456789012",
            source_record_status="published",
            record_type="chilecompra:purchase_order",
            external_id="2097-241-SE14",
            buyer_organization="Direccion de Compras y Contratacion Publica",
            supplier_company="Camara de Comercio de Santiago A.G.",
            contract_name="Compra de servicios",
            public_evidence_url="https://www.mercadopublico.cl/Compra?codigo=2097-241-SE14",
            claims_count=2,
            public_relationships_count=2,
        ),
    )


def test_render_trace_summary_is_compact_and_non_secret() -> None:
    summary = render_trace_summary(summarize_traceability_chain(_sample_trace()), "2097-241-SE14")

    assert "trace_summary: external_id=2097-241-SE14 source_records=1" in summary
    assert "buyer organization=Direccion de Compras y Contratacion Publica" in summary
    assert "supplier/company=Camara de Comercio de Santiago A.G." in summary
    assert "contract/purchase order name=Compra de servicios" in summary
    assert "public evidence URL=https://www.mercadopublico.cl/Compra?codigo=2097-241-SE14" in summary
    assert "claims count=2" in summary
    assert "public relationships count=2" in summary
    assert "ticket" not in summary.lower()
