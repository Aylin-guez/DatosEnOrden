from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from datosenorden.maintenance.traceability_inspector import TraceCompactSummary
from export_trace_graph import main


def _sample_summary():
    return (object(),)


def _session_manager(session):
    @contextmanager
    def _manager():
        yield session

    return _manager()


def test_main_exports_graph_html(monkeypatch, tmp_path, capsys) -> None:
    output = tmp_path / "graph_exports" / "2097-241-SE14.html"
    monkeypatch.setattr("export_trace_graph.SessionLocal", lambda: _session_manager(object()))
    monkeypatch.setattr("export_trace_graph.inspect_traceability_chain", lambda session, external_id: _sample_summary())
    monkeypatch.setattr(
        "export_trace_graph.summarize_traceability_chain",
        lambda traces: (
            TraceCompactSummary(
                source_record_id="6a0d2d24-5fe9-4dad-adfb-db5eceedf2b4",
                source_record_status="normalized",
                record_type="chilecompra:purchase_order",
                external_id="2097-241-SE14",
                buyer_organization="SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO",
                supplier_company="MARLENE BEATRIZ FLORES PATIÑO",
                contract_name="Insumos dentales especialidades",
                public_evidence_url="https://www.mercadopublico.cl/PurchaseOrder/Modules/PO/DetailsPurchaseOrder.aspx?qs=2097-241-SE14",
                claims_count=2,
                public_relationships_count=2,
            ),
        ),
    )

    exit_code = main(["--external-id", "2097-241-SE14", "--output", str(output)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert output.exists()
    html = output.read_text(encoding="utf-8")
    assert "graph_export: wrote" in captured.out
    assert "Primer grafo exportable: 2097-241-SE14" in html
    assert 'data-full-label="SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO"' in html
    assert 'data-full-label="MARLENE BEATRIZ FLORES PATIÑO"' in html
    assert captured.err == ""


def test_main_reports_missing_trace(monkeypatch, capsys) -> None:
    monkeypatch.setattr("export_trace_graph.SessionLocal", lambda: _session_manager(object()))
    monkeypatch.setattr("export_trace_graph.inspect_traceability_chain", lambda session, external_id: tuple())

    exit_code = main(["--external-id", "2097-241-SE14"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "No se encontro source_record persistido" in captured.err
    assert captured.out == ""
