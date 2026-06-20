from __future__ import annotations

from contextlib import contextmanager
from datetime import date
from pathlib import Path
from types import SimpleNamespace
import sys

from datosenorden.maintenance.timeline_explorer import TimelineEvent

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import entity_timeline
import export_entity_timeline


def _session_manager(session):
    @contextmanager
    def _manager():
        yield session

    return _manager()


def _sample_timeline():
    return SimpleNamespace(
        entity=SimpleNamespace(
            id="11111111-1111-1111-1111-111111111111",
            entity_type="PUBLIC_ORGANIZATION",
            name="DIVISION LOGISTICA DEL EJERCITO",
            external_id="buyer-1",
        ),
        events=(
            TimelineEvent(
                event_date=date(2026, 3, 15),
                dataset="LOBBY",
                dataset_name="lobby-meeting-sample",
                title="Lobby meeting",
                explanation="Registro de reunion de lobby asociado a la entidad.",
                claim_id="22222222-2222-2222-2222-222222222222",
                predicate="ORGANIZATION_HELD_LOBBY_MEETING",
                source_record_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                evidence_count=1,
                relationship_count=1,
            ),
        ),
        explanation="Esta cronologia reune los eventos publicos encontrados para esta entidad en distintas fuentes de informacion.",
        caution="El orden temporal no implica relacion causal.",
    )


def test_entity_timeline_script_prints_timeline(monkeypatch, capsys) -> None:
    monkeypatch.setattr(entity_timeline, "SessionLocal", lambda: _session_manager(object()))
    monkeypatch.setattr(entity_timeline, "build_entity_timeline", lambda session, entity_id: _sample_timeline())

    exit_code = entity_timeline.main(["--entity-id", "11111111-1111-1111-1111-111111111111"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "entity_timeline:" in captured.out
    assert "DIVISION LOGISTICA DEL EJERCITO" in captured.out
    assert "[LOBBY]" in captured.out
    assert "Lobby meeting" in captured.out
    assert captured.err == ""


def test_export_entity_timeline_script_writes_html(monkeypatch, tmp_path, capsys) -> None:
    output_path = tmp_path / "reports" / "entity_timeline_11111111-1111-1111-1111-111111111111.html"
    monkeypatch.setattr(export_entity_timeline, "REPORTS_DIR", tmp_path / "reports")
    monkeypatch.setattr(export_entity_timeline, "SessionLocal", lambda: _session_manager(object()))
    monkeypatch.setattr(export_entity_timeline, "build_entity_timeline", lambda session, entity_id: _sample_timeline())

    exit_code = export_entity_timeline.main(["--entity-id", "11111111-1111-1111-1111-111111111111"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert f"entity_timeline_exported: path={output_path.as_posix()}" in captured.out
    html = output_path.read_text(encoding="utf-8")
    assert "DIVISION LOGISTICA DEL EJERCITO" in html
    assert "LOBBY" in html
    assert "evidence 1" in html
    assert captured.err == ""
