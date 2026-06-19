from __future__ import annotations

from datetime import datetime, timezone

from datosenorden.maintenance.dataset_exploration import DatasetExploration
from datosenorden.maintenance.dataset_exploration import MetricRow
from datosenorden.maintenance.dataset_exploration import render_dataset_exploration_text
from datosenorden.maintenance.dataset_exploration import render_dataset_report_html


def _sample_exploration() -> DatasetExploration:
    return DatasetExploration(
        generated_at=datetime(2026, 6, 18, 12, 30, tzinfo=timezone.utc),
        summary_metrics=(
            MetricRow("purchase_orders", 12),
            MetricRow("claims", 24),
            MetricRow("relationship_public", 24),
        ),
        top_buyers=(MetricRow("Servicio de Salud Arauco", 5),),
        top_suppliers=(MetricRow("Proveedor Uno", 4),),
        purchase_orders_by_status=(MetricRow("normalized", 11), MetricRow("rejected", 1)),
        rejected_source_records_by_error=(MetricRow("no claims could be derived", 1),),
        claims_by_predicate=(MetricRow("ISSUES_PURCHASE_ORDER", 12),),
        relationships_by_type=(MetricRow("RECEIVES_CONTRACT", 12),),
    )


def test_render_dataset_exploration_text_contains_required_sections() -> None:
    report = render_dataset_exploration_text(_sample_exploration())

    assert "dataset_exploration: generated_at=2026-06-18T12:30:00+00:00" in report
    assert "summary_metrics:" in report
    assert "top_buyers_by_purchase_orders:" in report
    assert "top_suppliers_by_purchase_orders:" in report
    assert "purchase_orders_by_status:" in report
    assert "rejected_source_records_by_error_log:" in report
    assert "claims_by_predicate:" in report
    assert "relationship_public_by_relationship_type:" in report
    assert "Servicio de Salud Arauco: 5" in report
    assert "no claims could be derived: 1" in report


def test_render_dataset_report_html_contains_metrics_tables_charts_and_timestamp() -> None:
    html = render_dataset_report_html(_sample_exploration())

    assert "<!doctype html>" in html
    assert "DatosEnOrden dataset report" in html
    assert "Generated at 2026-06-18T12:30:00+00:00" in html
    assert "Top buyers by purchase orders" in html
    assert "Top suppliers by purchase orders" in html
    assert "Purchase orders by status" in html
    assert "Rejected source_records by error_log" in html
    assert "Claims by predicate" in html
    assert "relationship_public by relationship_type" in html
    assert "<table>" in html
    assert "bar-fill" in html
    assert "max-width: 1800px" in html
    assert "width: 95%" in html
    assert "repeat(6, minmax(0, 1fr))" in html
    assert "repeat(3, minmax(0, 1fr))" in html
    assert "repeat(2, minmax(0, 1fr))" in html
    assert "rejected-records" in html
    assert "white-space: pre-wrap" in html
    assert "position: sticky" in html
    assert "overflow: auto" in html
    assert "Source: DatosEnOrden local dataset" in html
    assert "ticket" not in html.lower()
    assert "DATABASE_URL" not in html
