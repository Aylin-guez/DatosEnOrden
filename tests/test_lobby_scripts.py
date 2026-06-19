from __future__ import annotations

from contextlib import contextmanager
from datetime import date
from pathlib import Path
import sys

from datosenorden.maintenance.lobby_prototype import LobbyImportResult
from datosenorden.maintenance.lobby_prototype import LobbySummaryRow

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import load_lobby_sample
import lobby_summary


def _session_manager(session):
    @contextmanager
    def _manager():
        yield session

    return _manager()


def test_load_lobby_sample_script_prints_result(monkeypatch, capsys) -> None:
    monkeypatch.setattr(load_lobby_sample, "SessionLocal", lambda: _session_manager(object()))
    monkeypatch.setattr(
        load_lobby_sample,
        "persist_lobby_sample",
        lambda session, input_path: LobbyImportResult(  # noqa: ARG005
            source_records=1,
            claims=3,
            evidences=3,
            entities=3,
            relationship_public=2,
            organization_entity_id="11111111-1111-1111-1111-111111111111",
            organization_name="SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO",
            counterparty_entity_id="22222222-2222-2222-2222-222222222222",
            counterparty_name="MARLENE BEATRIZ FLORES PATIÑO",
            lobby_meeting_entity_id="33333333-3333-3333-3333-333333333333",
            lobby_meeting_name="Lobby meeting 2026-03-15",
        ),
    )

    exit_code = load_lobby_sample.main([])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "lobby_sample_loaded:" in captured.out
    assert "relationship_public=2" in captured.out
    assert captured.err == ""


def test_lobby_summary_script_prints_rows(monkeypatch, capsys) -> None:
    monkeypatch.setattr(lobby_summary, "SessionLocal", lambda: _session_manager(object()))
    monkeypatch.setattr(
        lobby_summary,
        "read_lobby_summary",
        lambda session: (  # noqa: ARG005
            LobbySummaryRow(
                lobby_meeting_id="33333333-3333-3333-3333-333333333333",
                lobby_meeting_name="Lobby meeting 2026-03-15",
                organization_id="11111111-1111-1111-1111-111111111111",
                organization_name="SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO",
                counterparty_id="22222222-2222-2222-2222-222222222222",
                counterparty_name="MARLENE BEATRIZ FLORES PATIÑO",
                counterparty_type="COMPANY",
                meeting_subject="Presentacion de servicios",
                meeting_date=date(2026, 3, 15),
                claims=("ORGANIZATION_HELD_LOBBY_MEETING",),
                relationships=("ORGANIZATION_HELD_LOBBY_MEETING",),
                organization_match_method="contains_normalized_match",
                organization_match_confidence=0.95,
                counterparty_match_method="exact_normalized_match",
                counterparty_match_confidence=1.0,
            ),
        ),
    )

    exit_code = lobby_summary.main([])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "lobby_summary:" in captured.out
    assert "matched_entities:" in captured.out
    assert captured.err == ""
