from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import sys

from datosenorden.maintenance.dataset_metrics import DatasetSummaryCounts

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import dataset_summary as script


def _session_manager(session):
    @contextmanager
    def _manager():
        yield session

    return _manager()


def test_main_prints_dataset_summary(monkeypatch, capsys) -> None:
    monkeypatch.setattr(script, "SessionLocal", lambda: _session_manager(object()))
    monkeypatch.setattr(
        script,
        "read_dataset_summary",
        lambda session: DatasetSummaryCounts(
            total_purchase_orders=11,
            total_public_organizations=4,
            total_suppliers=8,
            total_claims=22,
            total_relationships=22,
        ),
    )

    exit_code = script.main([])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "dataset_summary:" in captured.out
    assert "total purchase orders=11" in captured.out
    assert "total public organizations=4" in captured.out
    assert "total suppliers=8" in captured.out
    assert "total claims=22" in captured.out
    assert "total relationships=22" in captured.out
    assert captured.err == ""
