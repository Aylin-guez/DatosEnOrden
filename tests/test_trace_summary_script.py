from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from datosenorden.maintenance.traceability_inspector import TraceClaimSummary
from datosenorden.maintenance.traceability_inspector import TraceCompactSummary
from datosenorden.maintenance.traceability_inspector import TraceEntitySummary
from datosenorden.maintenance.traceability_inspector import TraceEvidenceSummary
from datosenorden.maintenance.traceability_inspector import TraceRelationshipSummary
from datosenorden.maintenance.traceability_inspector import TraceSourceRecordSummary
from trace_summary import main


def _sample_trace() -> tuple[TraceSourceRecordSummary, ...]:
    buyer = TraceEntitySummary("PUBLIC_ORGANIZATION", "Direccion de Compras y Contratacion Publica", "buyer")
    supplier = TraceEntitySummary("COMPANY", "Camara de Comercio de Santiago A.G.", "supplier")
    contract = TraceEntitySummary("CONTRACT", "Compra de servicios", "contract")
    evidence = TraceEvidenceSummary(
        id="11111111-1111-1111-1111-111111111111",
        title="Ficha Mercado Publico orden de compra 2097-241-SE14",
        url="https://example.invalid/evidence",
        published_at=None,
        claim_id="22222222-2222-2222-2222-222222222222",
    )
    second_evidence = TraceEvidenceSummary(
        id="44444444-4444-4444-4444-444444444444",
        title="Ficha Mercado Publico orden de compra 2097-241-SE14",
        url="https://example.invalid/evidence",
        published_at=None,
        claim_id="55555555-5555-5555-5555-555555555555",
    )
    relationship = TraceRelationshipSummary(
        id="33333333-3333-3333-3333-333333333333",
        relationship_type="ISSUES_PURCHASE_ORDER",
        status="published",
        source_entity=buyer,
        target_entity=contract,
        claim_id="22222222-2222-2222-2222-222222222222",
    )
    second_relationship = TraceRelationshipSummary(
        id="66666666-6666-6666-6666-666666666666",
        relationship_type="RECEIVES_CONTRACT",
        status="published",
        source_entity=supplier,
        target_entity=contract,
        claim_id="55555555-5555-5555-5555-555555555555",
    )
    claim = TraceClaimSummary(
        id="22222222-2222-2222-2222-222222222222",
        predicate="ISSUES_PURCHASE_ORDER",
        status="validated",
        subject_entity=buyer,
        object_entity=contract,
        valid_from=None,
        evidences=(evidence,),
        relationship_public=(relationship,),
    )
    second_claim = TraceClaimSummary(
        id="55555555-5555-5555-5555-555555555555",
        predicate="RECEIVES_CONTRACT",
        status="validated",
        subject_entity=supplier,
        object_entity=contract,
        valid_from=None,
        evidences=(second_evidence,),
        relationship_public=(second_relationship,),
    )
    return (
        TraceSourceRecordSummary(
            id="12345678-1234-1234-1234-123456789012",
            status="published",
            record_type="chilecompra:purchase_order",
            external_id="2097-241-SE14",
            claims=(claim, second_claim),
        ),
    )


def _session_manager(session):
    @contextmanager
    def _manager():
        yield session

    return _manager()


def test_main_prints_compact_summary(monkeypatch, capsys) -> None:
    monkeypatch.setattr("trace_summary.SessionLocal", lambda: _session_manager(object()))
    monkeypatch.setattr("trace_summary.inspect_traceability_chain", lambda session, external_id: _sample_trace())

    exit_code = main(["--external-id", "2097-241-SE14"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "trace_summary: external_id=2097-241-SE14 source_records=1" in captured.out
    assert "buyer organization=Direccion de Compras y Contratacion Publica" in captured.out
    assert "supplier/company=Camara de Comercio de Santiago A.G." in captured.out
    assert "contract/purchase order name=Compra de servicios" in captured.out
    assert "claims count=2" in captured.out
    assert "public relationships count=2" in captured.out
    assert captured.err == ""


def test_main_reports_missing_summary(monkeypatch, capsys) -> None:
    monkeypatch.setattr("trace_summary.SessionLocal", lambda: _session_manager(object()))
    monkeypatch.setattr("trace_summary.inspect_traceability_chain", lambda session, external_id: tuple())

    exit_code = main(["--external-id", "2097-241-SE14"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "No se encontro source_record persistido" in captured.err
    assert captured.out == ""
