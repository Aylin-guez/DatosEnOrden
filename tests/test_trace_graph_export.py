from __future__ import annotations

from datosenorden.maintenance.trace_graph_export import render_trace_graph_html
from datosenorden.maintenance.traceability_inspector import TraceCompactSummary


def _sample_summary() -> tuple[TraceCompactSummary, ...]:
    return (
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
    )


def test_render_trace_graph_html_contains_visible_graph() -> None:
    html = render_trace_graph_html(_sample_summary(), "2097-241-SE14")

    assert "Primer grafo exportable: 2097-241-SE14" in html
    assert "Servicio de Salud Arauco" in html
    assert "Orden de compra" in html
    assert "Proveedor" in html
    assert 'data-full-label="SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO"' in html
    assert 'data-full-label="Insumos dentales especialidades"' in html
    assert 'data-full-label="MARLENE BEATRIZ FLORES PATIÑO"' in html
    assert "https://www.mercadopublico.cl/PurchaseOrder/Modules/PO/DetailsPurchaseOrder.aspx?qs=2097-241-SE14" in html
    assert "ticket" not in html.lower()


def test_render_trace_graph_html_is_utf8_safe_and_read_only() -> None:
    html = render_trace_graph_html(_sample_summary(), "2097-241-SE14")

    assert "DATABASE_URL" not in html
    assert "\u2192" in html
