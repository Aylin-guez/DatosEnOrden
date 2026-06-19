from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import sys

from datosenorden.maintenance.dataset_exploration import DatasetExploration
from datosenorden.maintenance.dataset_exploration import MetricRow

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import export_dataset_report as script


def _session_manager(session):
    @contextmanager
    def _manager():
        yield session

    return _manager()


def _sample_exploration() -> DatasetExploration:
    return DatasetExploration(
        generated_at=datetime(2026, 6, 18, 12, 30, tzinfo=timezone.utc),
        summary_metrics=(MetricRow("purchase_orders", 12),),
        top_buyers=(MetricRow("Servicio de Salud Arauco", 5),),
        top_suppliers=(MetricRow("Proveedor Uno", 4),),
        purchase_orders_by_status=(MetricRow("normalized", 11),),
        rejected_source_records_by_error=(MetricRow("no claims could be derived", 1),),
        claims_by_predicate=(MetricRow("ISSUES_PURCHASE_ORDER", 12),),
        relationships_by_type=(MetricRow("RECEIVES_CONTRACT", 12),),
    )


def test_main_exports_dataset_report(monkeypatch, tmp_path, capsys) -> None:
    output_path = tmp_path / "reports" / "dataset_report.html"
    monkeypatch.setattr(script, "DEFAULT_OUTPUT_PATH", output_path)
    monkeypatch.setattr(script, "SessionLocal", lambda: _session_manager(object()))
    monkeypatch.setattr(script, "explore_dataset", lambda session: _sample_exploration())

    exit_code = script.main([])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert f"dataset_report_exported: path={output_path.as_posix()}" in captured.out
    html = output_path.read_text(encoding="utf-8")
    assert "DatosEnOrden dataset report" in html
    assert "Generated at 2026-06-18T12:30:00+00:00" in html
    assert "Servicio de Salud Arauco" in html
    assert "bar-fill" in html
    assert captured.err == ""


def test_main_reports_export_error(monkeypatch, capsys) -> None:
    def raise_error(session):  # noqa: ANN001
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(script, "SessionLocal", lambda: _session_manager(object()))
    monkeypatch.setattr(script, "explore_dataset", raise_error)

    exit_code = script.main([])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "No se pudo exportar el reporte del dataset." in captured.err
    assert "database unavailable" in captured.err
