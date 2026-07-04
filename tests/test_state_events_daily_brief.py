from __future__ import annotations

from datetime import UTC, datetime
import importlib.util
from pathlib import Path

from datosenorden.studio.daily_brief import build_daily_brief
from datosenorden.studio.source_watcher import ChangeCandidate, ChangeType, LEGISLATIVE_WATCH_SOURCE
from datosenorden.studio.state_events import (
    StateEventImportance,
    StateEventType,
    build_state_event,
    build_state_events,
    load_state_events,
    save_state_events,
)
from datosenorden.studio.topic_classifier import classify_candidate


def _candidate(
    title: str = "Registro legislativo camara-votacion-1",
    *,
    external_id: str = "camara-votacion-1",
    suggested_action: str = "import_bill",
    change_type: ChangeType = ChangeType.NEW,
) -> ChangeCandidate:
    return ChangeCandidate(
        source_id=LEGISLATIVE_WATCH_SOURCE.id,
        external_id=external_id,
        title=title,
        url="https://opendata.camara.cl/",
        detected_at=datetime(2026, 7, 3, 12, 0, tzinfo=UTC),
        change_type=change_type,
        reason="mock oficial",
        priority=80,
        suggested_action=suggested_action,
    )


def test_state_event_generation_from_candidate_and_classification() -> None:
    candidate = _candidate()
    classification = classify_candidate(candidate)

    event = build_state_event(candidate, classification)

    assert event.event_id
    assert event.topic_id in {"presupuesto-publico", "actividad-legislativa"}
    assert event.source_id == LEGISLATIVE_WATCH_SOURCE.id
    assert event.document_available is True
    assert event.evidence_available is True


def test_state_event_classifies_type_and_importance_by_rules() -> None:
    candidate = _candidate("Nueva votacion de proyecto de ley", external_id="camara-votacion-99")
    classification = classify_candidate(candidate)

    event = build_state_event(candidate, classification)

    assert event.event_type == StateEventType.NEW_VOTE
    assert event.importance == StateEventImportance.HIGH


def test_state_event_classifies_bill_as_medium_importance() -> None:
    candidate = _candidate("Boletin legislativo detectado 8575-05", external_id="cl-congreso-boletin-8575-05")
    classification = classify_candidate(candidate)

    event = build_state_event(candidate, classification)

    assert event.event_type == StateEventType.NEW_BILL
    assert event.importance == StateEventImportance.MEDIUM
    assert event.topic_id == "presupuesto-publico"


def test_daily_brief_is_built_from_events_not_topics() -> None:
    candidate = _candidate()
    classification = classify_candidate(candidate)
    events = [build_state_event(candidate, classification)]

    brief = build_daily_brief([event.__dict__ | {"detected_at": event.detected_at.isoformat(), "importance": event.importance.value, "event_type": event.event_type.value} for event in events], now=datetime(2026, 7, 3, 13, 0, tzinfo=UTC))

    entry = brief.sections[0].entries[0]
    assert entry.event_id == events[0].event_id
    assert entry.link_to_topic == "/topic"
    assert entry.title.startswith("Nueva votacion")


def test_state_events_can_be_saved_and_loaded_as_topic_chronology(tmp_path) -> None:
    candidate = _candidate()
    classification = classify_candidate(candidate)
    events = build_state_events(((candidate, classification),))
    save_state_events(events, output_dir=tmp_path, generated_at=datetime(2026, 7, 3, 13, 0, tzinfo=UTC))

    rows = load_state_events(topic_id=events[0].topic_id, root=tmp_path)

    assert rows[0]["event_id"] == events[0].event_id
    assert rows[0]["event_type"] == StateEventType.NEW_VOTE.value


def test_generate_daily_brief_script_uses_local_events(tmp_path, capsys) -> None:
    candidate = _candidate()
    classification = classify_candidate(candidate)
    event_dir = tmp_path / "events"
    brief_dir = tmp_path / "briefs"
    save_state_events(build_state_events(((candidate, classification),)), output_dir=event_dir, generated_at=datetime(2026, 7, 3, 12, 0, tzinfo=UTC))

    script_path = Path("scripts/generate_daily_brief.py")
    spec = importlib.util.spec_from_file_location("generate_daily_brief_script", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    exit_code = module.main(["--events-dir", str(event_dir), "--output-dir", str(brief_dir), "--max-age-days", "9999"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "daily_brief:" in output
    assert "entries=1" in output
    assert len(list(brief_dir.glob("daily_brief_*.json"))) == 1