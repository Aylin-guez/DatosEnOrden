from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import sys

from datosenorden.maintenance.dipres_prototype import BudgetSummaryRow
from datosenorden.maintenance.dipres_prototype import DipresImportResult

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import budget_summary
import load_dipres_sample


def _session_manager(session):
    @contextmanager
    def _manager():
        yield session

    return _manager()


def test_load_dipres_sample_script_prints_result(monkeypatch, capsys) -> None:
    monkeypatch.setattr(load_dipres_sample, "SessionLocal", lambda: _session_manager(object()))
    monkeypatch.setattr(
        load_dipres_sample,
        "persist_dipres_sample",
        lambda session, input_path: DipresImportResult(  # noqa: ARG005
            source_records=1,
            claims=3,
            evidences=3,
            entities=2,
            relationship_public=1,
            matched_entity_id="11111111-1111-1111-1111-111111111111",
            matched_entity_name="SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO",
            budget_entity_id="22222222-2222-2222-2222-222222222222",
            budget_entity_name="DIPRES budget 2026 - SERVICIO DE SALUD ARAUCO",
        ),
    )

    exit_code = load_dipres_sample.main([])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "dipres_sample_loaded:" in captured.out
    assert "matched_entity_name=SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO" in captured.out
    assert captured.err == ""


def test_budget_summary_script_prints_rows(monkeypatch, capsys) -> None:
    monkeypatch.setattr(budget_summary, "SessionLocal", lambda: _session_manager(object()))
    monkeypatch.setattr(
        budget_summary,
        "read_budget_summary",
        lambda session: (
            BudgetSummaryRow(
                budget_entity_id="22222222-2222-2222-2222-222222222222",
                budget_entity_name="DIPRES budget 2026 - SERVICIO DE SALUD ARAUCO",
                organization_id="11111111-1111-1111-1111-111111111111",
                organization_name="SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO",
                fiscal_year=2026,
                approved_budget=1000000000,
                executed_budget=950000000,
                purchase_orders=4,
                suppliers=2,
                match_method="contains_normalized_match",
                match_confidence=0.95,
                currency="CLP",
            ),
        ),
    )

    exit_code = budget_summary.main([])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "budget_summary:" in captured.out
    assert "approved_budget=1000000000" in captured.out
    assert "suppliers=2" in captured.out
    assert captured.err == ""
