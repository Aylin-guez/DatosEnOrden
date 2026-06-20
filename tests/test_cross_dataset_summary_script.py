from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import sys
from uuid import UUID

from datosenorden.maintenance.cross_dataset_explorer import CrossDatasetOrganizationSummary

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import cross_dataset_summary


def _session_manager(session):
    @contextmanager
    def _manager():
        yield session

    return _manager()


def test_cross_dataset_summary_script_prints_report(monkeypatch, capsys) -> None:
    row = CrossDatasetOrganizationSummary(
        organization_id=str(UUID("11111111-1111-1111-1111-111111111111")),
        organization_name="SERVICIO DE SALUD ARAUCO",
        datasets=("chilecompra", "lobby"),
        contracts=4,
        lobby_meetings=1,
        evidence=5,
        relationships=6,
        lobby_connections=(),
        procurement_connections=(),
        explanation="Stored public records only.",
    )
    monkeypatch.setattr(cross_dataset_summary, "SessionLocal", lambda: _session_manager(object()))
    monkeypatch.setattr(cross_dataset_summary, "list_cross_dataset_organizations", lambda session: (row,))

    result = cross_dataset_summary.main([])

    assert result == 0
    output = capsys.readouterr().out
    assert "cross_dataset_summary:" in output
    assert "SERVICIO DE SALUD ARAUCO" in output
    assert "relationships:\n6" in output
