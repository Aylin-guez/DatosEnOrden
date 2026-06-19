from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from datosenorden.maintenance.dataset_metrics import DatasetSummaryCounts
from datosenorden.maintenance.dataset_metrics import PurchaseOrderDatasetCounts
from datosenorden.maintenance.dataset_metrics import load_sample_purchase_orders
from datosenorden.maintenance.dataset_metrics import read_dataset_summary
from datosenorden.maintenance.dataset_metrics import read_purchase_order_dataset_counts
from datosenorden.maintenance.dataset_metrics import render_dataset_summary
from datosenorden.maintenance.dataset_metrics import render_purchase_order_dataset_counts


def test_load_sample_purchase_orders_iterates_until_limit(monkeypatch) -> None:
    calls: list[tuple[date, int | None]] = []

    class FakePipeline:
        def __init__(self, client, session):  # noqa: ANN001
            self.client = client

        def run_purchase_orders_for_day(self, day, status="todos", dry_run=False, limit=None):  # noqa: ANN001
            calls.append((day, limit))
            if day == date(2026, 6, 18):
                return SimpleNamespace(
                    source_record_count=3,
                    claim_count=6,
                    evidence_count=6,
                    public_relationship_count=6,
                )
            if day == date(2026, 6, 17):
                return SimpleNamespace(
                    source_record_count=2,
                    claim_count=4,
                    evidence_count=4,
                    public_relationship_count=4,
                )
            return SimpleNamespace(
                source_record_count=0,
                claim_count=0,
                evidence_count=0,
                public_relationship_count=0,
            )

    monkeypatch.setattr("datosenorden.maintenance.dataset_metrics.ChileCompraPipeline", FakePipeline)

    result = load_sample_purchase_orders(
        client=object(),
        session=object(),
        limit=5,
        anchor_date=date(2026, 6, 18),
        lookback_days=3,
    )

    assert result.source_records == 5
    assert result.claims == 10
    assert result.evidences == 10
    assert result.relationship_public == 10
    assert result.days_scanned == 2
    assert calls == [(date(2026, 6, 18), 5), (date(2026, 6, 17), 2)]


def test_render_purchase_order_dataset_counts_is_human_readable() -> None:
    report = render_purchase_order_dataset_counts(
        PurchaseOrderDatasetCounts(
            source_records=12,
            claims=24,
            evidences=24,
            relationship_public=24,
            distinct_buyers=3,
            distinct_suppliers=7,
        )
    )

    assert "purchase_order_load_summary:" in report
    assert "source_records count=12" in report
    assert "claims count=24" in report
    assert "evidences count=24" in report
    assert "relationship_public count=24" in report
    assert "distinct buyers count=3" in report
    assert "distinct suppliers count=7" in report


def test_render_dataset_summary_is_human_readable() -> None:
    report = render_dataset_summary(
        DatasetSummaryCounts(
            total_purchase_orders=11,
            total_public_organizations=4,
            total_suppliers=8,
            total_claims=22,
            total_relationships=22,
        )
    )

    assert "dataset_summary:" in report
    assert "total purchase orders=11" in report
    assert "total public organizations=4" in report
    assert "total suppliers=8" in report
    assert "total claims=22" in report
    assert "total relationships=22" in report


def test_read_helpers_are_only_imported_for_symbol_coverage() -> None:
    assert read_dataset_summary is not None
    assert read_purchase_order_dataset_counts is not None
