from __future__ import annotations

from datetime import UTC, datetime
import importlib.util
from pathlib import Path

from datosenorden.studio.source_watcher import ChangeCandidate, ChangeType, LEGISLATIVE_WATCH_SOURCE, WatchRun, WatchResult
from datosenorden.studio.topic_classifier import TopicClassifierConfig, TopicRule, classify_candidate
from datosenorden.studio.topic_update import build_topic_update


def _candidate(
    title: str = "Ley de presupuestos del sector publico",
    *,
    external_id: str = "camara-votacion-8575-05-1",
    suggested_action: str = "import_bill",
    change_type: ChangeType = ChangeType.NEW,
) -> ChangeCandidate:
    return ChangeCandidate(
        source_id=LEGISLATIVE_WATCH_SOURCE.id,
        external_id=external_id,
        title=title,
        url="https://opendata.camara.cl/camaradiputados/WServices/ws.asmx/getVotacionProyectoLey?prmVotacionID=1",
        detected_at=datetime(2026, 7, 2, 12, 0, tzinfo=UTC),
        change_type=change_type,
        reason="mock oficial",
        priority=80,
        suggested_action=suggested_action,
    )


def test_classifier_matches_budget_keywords() -> None:
    classification = classify_candidate(_candidate("Ley de presupuestos, erario y hacienda publica"))

    assert classification.topic_id == "presupuesto-publico"
    assert classification.category_id == "presupuesto"
    assert classification.confidence > 0.5
    assert "keyword=presupuesto" in classification.reason


def test_classifier_uses_fallback_when_no_rule_matches() -> None:
    config = TopicClassifierConfig(
        default_topic_id="fallback-topic",
        categories={},
        rules=(
            TopicRule(
                topic_id="fallback-topic",
                category_id="legislacion",
                title="Fallback",
                keywords=("no-match",),
                source_ids=("otra-fuente",),
                external_ids=("otra-fuente-1",),
                external_id_prefixes=("otra-",),
                suggested_actions=("download_document",),
                document_types=("oficio",),
            ),
        ),
    )

    classification = classify_candidate(
        _candidate("Materia municipal sin palabras configuradas", external_id="x-1", suggested_action="ignore"),
        config,
    )

    assert classification.topic_id == "fallback-topic"
    assert classification.confidence == 0.25
    assert "Fallback configurado" in classification.reason


def test_topic_update_is_generated_without_publication_side_effects() -> None:
    candidate = _candidate()
    classification = classify_candidate(candidate)

    update = build_topic_update(candidate, classification)

    assert update.topic_id == "presupuesto-publico"
    assert update.status == "detected"
    assert update.suggested_action == "import_bill"
    assert update.timeline_event["origin"] == "state_event"
    assert update.timeline_event["event_type"] in {"NEW_BILL", "NEW_VOTE"}
    assert update.timeline_event["suggested_action"] == "import_bill"
    assert update.state_event["event_id"]
    assert "run_publication_engine" not in update.summary


def test_auto_topic_update_script_generates_local_output(monkeypatch, tmp_path, capsys) -> None:
    script_path = Path("scripts/update_topics_from_sources.py")
    spec = importlib.util.spec_from_file_location("update_topics_from_sources_script", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    run = WatchRun(source=LEGISLATIVE_WATCH_SOURCE, started_at=datetime(2026, 7, 2, 12, 0, tzinfo=UTC))
    monkeypatch.setattr(module, "watch_legislative_source", lambda **kwargs: WatchResult(run=run, candidates=(_candidate(),)))

    events_dir = tmp_path / "events"
    exit_code = module.main(["--limit", "1", "--output-dir", str(tmp_path), "--events-output-dir", str(events_dir)])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "auto_topic_update:" in output
    assert "updates=1" in output
    assert "events=1" in output
    assert "presupuesto-publico: 1" in output
    assert len(list(tmp_path.glob("topic_updates_*.json"))) == 1
    assert len(list(events_dir.glob("state_events_*.json"))) == 1