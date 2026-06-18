from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from datosenorden.maintenance.traceability_inspector import TraceClaimSummary
from datosenorden.maintenance.traceability_inspector import TraceEntitySummary
from datosenorden.maintenance.traceability_inspector import TraceEvidenceSummary
from datosenorden.maintenance.traceability_inspector import TraceRelationshipSummary
from datosenorden.maintenance.traceability_inspector import TraceSourceRecordSummary
from inspect_trace import main


def _sample_trace() -> tuple[TraceSourceRecordSummary, ...]:
    source_entity = TraceEntitySummary("PUBLIC_ORGANIZATION", "Direccion de Compras y Contratacion Publica", "buyer")
    target_entity = TraceEntitySummary("CONTRACT", "Compra de servicios", "contract")
    evidence = TraceEvidenceSummary(
        id="11111111-1111-1111-1111-111111111111",
        title="Ficha Mercado Publico orden de compra 2097-241-SE14",
        url="https://example.invalid/evidence",
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
    return (
        TraceSourceRecordSummary(
            id="12345678-1234-1234-1234-123456789012",
            status="published",
            record_type="chilecompra:purchase_order",
            external_id="2097-241-SE14",
            claims=(claim,),
        ),
    )


def _session_manager(session):
    @contextmanager
    def _manager():
        yield session

    return _manager()


def test_main_prints_persisted_trace(monkeypatch, capsys) -> None:
    monkeypatch.setattr("inspect_trace.SessionLocal", lambda: _session_manager(object()))
    monkeypatch.setattr("inspect_trace.inspect_traceability_chain", lambda session, external_id: _sample_trace())

    exit_code = main(["--external-id", "2097-241-SE14"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "traceability_inspection: external_id=2097-241-SE14 source_records=1" in captured.out
    assert "source_record[1]:" in captured.out
    assert "relationship_public[1]:" in captured.out
    assert captured.err == ""


def test_main_reports_missing_trace(monkeypatch, capsys) -> None:
    monkeypatch.setattr("inspect_trace.SessionLocal", lambda: _session_manager(object()))
    monkeypatch.setattr("inspect_trace.inspect_traceability_chain", lambda session, external_id: tuple())

    exit_code = main(["--external-id", "2097-241-SE14"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "No se encontro source_record persistido" in captured.err
    assert captured.out == ""
