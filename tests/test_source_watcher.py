from __future__ import annotations

from datetime import UTC, datetime
import importlib.util
from pathlib import Path

from datosenorden.etl.core.contracts import DatasetRecord, EntityRecord, EntityType, GraphBatch, SourceInfo, SourceRecordPayload
from datosenorden.studio.source_watcher import (
    ChangeCandidate,
    ChangeType,
    ExistingSourceRecordSnapshot,
    LEGISLATIVE_WATCH_SOURCE,
    WatchRun,
    WatchResult,
    candidates_from_graph_batch,
    summarize_watch_result,
)


def _record(external_id: str, payload_hash: str = "hash-1", date: str = "2026-07-02T10:00:00") -> SourceRecordPayload:
    return SourceRecordPayload(
        external_id=external_id,
        record_type="legislative_vote",
        payload_hash=payload_hash,
        raw_payload={
            "source_id": external_id,
            "bulletin_id": "8575-05",
            "date": date,
            "session": {"date": date},
        },
        retrieved_at=datetime(2026, 7, 2, 12, 0, tzinfo=UTC),
    )


def _batch(*records: SourceRecordPayload) -> GraphBatch:
    return GraphBatch(
        source=SourceInfo(
            name="Datos Abiertos Legislativos Congreso Nacional",
            publisher="Camara",
            url="https://opendata.camara.cl/",
            retrieved_at=datetime(2026, 7, 2, 12, 0, tzinfo=UTC),
        ),
        dataset=DatasetRecord(
            source_name="Datos Abiertos Legislativos Congreso Nacional",
            name="congreso-votaciones-boletin",
            description="Votaciones oficiales",
            version="8575-05",
            dataset_url="https://opendata.camara.cl/",
        ),
        source_records=tuple(records),
        entities=(
            EntityRecord(
                entity_type=EntityType.PUBLIC_PROJECT,
                name="Boletin 8575-05",
                external_id="cl-congreso-boletin-8575-05",
            ),
        ),
        evidence=(),
        claims=(),
        public_relationships=(),
        raw_count=len(records),
    )


def test_watcher_generates_candidates_from_mock_entries() -> None:
    result = candidates_from_graph_batch(
        _batch(_record("camara-votacion-1")),
        snapshot=ExistingSourceRecordSnapshot(),
        detected_at=datetime(2026, 7, 2, 12, 0, tzinfo=UTC),
    )

    assert [candidate.change_type for candidate in result] == [ChangeType.NEW, ChangeType.NEW]
    assert result[0].suggested_action == "import_bill"
    assert result[1].suggested_action == "import_bill"
    assert result[1].source_id == LEGISLATIVE_WATCH_SOURCE.id
    assert result[1].url.endswith("prmVotacionID=1")


def test_watcher_marks_updated_and_ignored_against_existing_snapshot() -> None:
    snapshot = ExistingSourceRecordSnapshot(
        payload_hash_by_external_id={
            "camara-votacion-1": "old-hash",
            "camara-votacion-2": "same-hash",
        },
        entity_external_ids={"cl-congreso-boletin-8575-05"},
    )

    result = candidates_from_graph_batch(
        _batch(_record("camara-votacion-1", "new-hash"), _record("camara-votacion-2", "same-hash")),
        snapshot=snapshot,
        detected_at=datetime(2026, 7, 2, 12, 0, tzinfo=UTC),
    )

    assert [candidate.change_type for candidate in result] == [ChangeType.UPDATED, ChangeType.IGNORED]
    assert result[0].suggested_action == "update_topic"
    assert result[1].suggested_action == "ignore"


def test_watcher_does_not_publish_or_load_automatically() -> None:
    result = candidates_from_graph_batch(
        _batch(_record("camara-votacion-3")),
        snapshot=ExistingSourceRecordSnapshot(entity_external_ids={"cl-congreso-boletin-8575-05"}),
    )

    assert all(candidate.suggested_action in {"import_bill", "update_topic", "ignore"} for candidate in result)
    assert not any(candidate.suggested_action in {"publish", "run_publication_engine", "run_graph_loader"} for candidate in result)


def test_watcher_does_not_require_ai() -> None:
    import datosenorden.studio.source_watcher as source_watcher

    assert "openai" not in Path(source_watcher.__file__).read_text(encoding="utf-8").lower()
    assert "llm" not in Path(source_watcher.__file__).read_text(encoding="utf-8").lower()


def test_watcher_handles_no_results() -> None:
    result = candidates_from_graph_batch(_batch(), snapshot=ExistingSourceRecordSnapshot(entity_external_ids={"cl-congreso-boletin-8575-05"}))

    assert result == ()


def test_watch_result_summary_prints_candidate_groups() -> None:
    run = WatchRun(source=LEGISLATIVE_WATCH_SOURCE, started_at=datetime(2026, 7, 2, 12, 0, tzinfo=UTC))
    result = WatchResult(
        run=run,
        candidates=(
            ChangeCandidate(
                source_id=LEGISLATIVE_WATCH_SOURCE.id,
                external_id="camara-votacion-1",
                title="Votacion 1",
                url="https://opendata.camara.cl/",
                detected_at=run.started_at,
                change_type=ChangeType.NEW,
                reason="mock",
                priority=80,
                suggested_action="import_bill",
            ),
        ),
    )

    summary = summarize_watch_result(result)

    assert "candidatos_nuevos=1" in summary
    assert "acciones_sugeridas=" in summary
    assert "import_bill: 1" in summary


def test_watch_legislative_source_script_uses_watcher_without_network(monkeypatch, capsys) -> None:
    script_path = Path("scripts/watch_legislative_source.py")
    spec = importlib.util.spec_from_file_location("watch_legislative_source_script", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    run = WatchRun(source=LEGISLATIVE_WATCH_SOURCE, started_at=datetime(2026, 7, 2, 12, 0, tzinfo=UTC))
    monkeypatch.setattr(module, "watch_legislative_source", lambda **kwargs: WatchResult(run=run))

    exit_code = module.main(["--limit", "0"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "source_watcher:" in output
    assert "candidatos_nuevos=0" in output