from __future__ import annotations

from contextlib import contextmanager
from datetime import date
from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import load_sample_purchase_orders as script
from datosenorden.maintenance.dataset_metrics import PurchaseOrderDatasetCounts
from datosenorden.maintenance.dataset_metrics import PurchaseOrderLoadCounts


def _session_manager(session):
    @contextmanager
    def _manager():
        yield session

    return _manager()


def test_main_prints_load_and_dataset_counts(monkeypatch, capsys) -> None:
    monkeypatch.setattr(script, "get_chilecompra_settings", lambda: SimpleNamespace(ticket="x", base_url="https://example.invalid"))
    monkeypatch.setattr(script, "SessionLocal", lambda: _session_manager(object()))
    monkeypatch.setattr(
        script,
        "load_sample_purchase_orders",
        lambda client, session, limit, progress_callback=None: (
            progress_callback(
                SimpleNamespace(
                    scanned_date=date(2026, 6, 18),
                    raw_found=7,
                    loaded=7,
                    rejected=1,
                    claims=14,
                    relationships=14,
                )
            )
            if progress_callback
            else None
        )
        or PurchaseOrderLoadCounts(
            source_records=7,
            claims=14,
            evidences=14,
            relationship_public=14,
            days_scanned=3,
            raw_found=7,
            rejected=1,
        ),
    )
    monkeypatch.setattr(
        script,
        "read_purchase_order_dataset_counts",
        lambda session: PurchaseOrderDatasetCounts(
            source_records=7,
            claims=14,
            evidences=14,
            relationship_public=14,
            distinct_buyers=3,
            distinct_suppliers=4,
        ),
    )

    exit_code = script.main(["--limit", "100"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "sample_purchase_orders_loaded:" in captured.out
    assert "sample_purchase_orders_progress:" in captured.out
    assert "date=2026-06-18" in captured.out
    assert "raw_found=7" in captured.out
    assert "rejected=1" in captured.out
    assert "source_records=7" in captured.out
    assert "claims=14" in captured.out
    assert "evidences=14" in captured.out
    assert "relationship_public=14" in captured.out
    assert "days_scanned=3" in captured.out
    assert "purchase_order_load_summary:" in captured.out
    assert "distinct buyers count=3" in captured.out
    assert "distinct suppliers count=4" in captured.out
    assert captured.err == ""


def test_main_reports_missing_ticket(monkeypatch, capsys) -> None:
    def raise_missing_ticket():
        raise ValueError("DATOSENORDEN_CHILECOMPRA_TICKET is required")

    monkeypatch.setattr(script, "get_chilecompra_settings", raise_missing_ticket)

    exit_code = script.main(["--limit", "100"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Falta DATOSENORDEN_CHILECOMPRA_TICKET" in captured.err
    assert "DATOSENORDEN_CHILECOMPRA_TICKET is required" in captured.err
    assert captured.out == ""
