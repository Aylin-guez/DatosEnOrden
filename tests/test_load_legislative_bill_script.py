from __future__ import annotations

from datetime import UTC, datetime
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy.orm.exc import DetachedInstanceError

from datosenorden.etl.core.contracts import (
    ClaimRecord,
    DatasetRecord,
    EntityRecord,
    EntityType,
    EvidenceRecord,
    GraphBatch,
    SourceInfo,
    SourceRecordPayload,
    WorkflowStatus,
)


def _load_script_module(name: str):
    script_path = Path(__file__).resolve().parents[1] / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class _SessionContext:
    def __init__(self, on_exit=None):  # noqa: ANN001
        self._on_exit = on_exit

    def __enter__(self):  # noqa: ANN001
        return object()

    def __exit__(self, exc_type, exc, tb):  # noqa: ANN001
        _ = (exc_type, exc, tb)
        if self._on_exit is not None:
            self._on_exit()
        return False


class _DetachingImportJob:
    def __init__(self, value: str) -> None:
        self._value = value
        self.detached = False

    @property
    def id(self) -> str:
        if self.detached:
            raise DetachedInstanceError("import job is detached")
        return self._value


def test_load_legislative_bill_real_load_captures_import_job_id_before_session_close(monkeypatch, capsys) -> None:
    module = _load_script_module("load_legislative_bill")
    batch = _sample_batch()
    import_job = _DetachingImportJob("job-123")

    class FakeAdapter:
        def load_bill(self, bulletin_id: str) -> GraphBatch:
            assert bulletin_id == "8575-05"
            return batch

    class FakeGraphLoader:
        def __init__(self, session) -> None:  # noqa: ANN001
            self.session = session

        def load(self, loaded_batch: GraphBatch, dry_run: bool = False):  # noqa: ANN001
            assert loaded_batch is batch
            assert dry_run is False
            return import_job

    monkeypatch.setattr(module, "LegislativeAdapter", FakeAdapter)
    monkeypatch.setattr(module, "GraphLoader", FakeGraphLoader)
    monkeypatch.setattr(module, "SessionLocal", lambda: _SessionContext(lambda: setattr(import_job, "detached", True)))

    exit_code = module.main(["8575-05"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert import_job.detached is True
    assert "loaded=True" in output
    assert "import_job_id=job-123" in output


def test_load_legislative_bill_dry_run_keeps_empty_import_job_id(monkeypatch, capsys) -> None:
    module = _load_script_module("load_legislative_bill")
    batch = _sample_batch()

    class FakeAdapter:
        def load_bill(self, bulletin_id: str) -> GraphBatch:
            assert bulletin_id == "8575-05"
            return batch

    class FakeGraphLoader:
        def __init__(self, session) -> None:  # noqa: ANN001
            self.session = session

        def load(self, loaded_batch: GraphBatch, dry_run: bool = False):  # noqa: ANN001
            assert loaded_batch is batch
            assert dry_run is True
            return None

    monkeypatch.setattr(module, "LegislativeAdapter", FakeAdapter)
    monkeypatch.setattr(module, "GraphLoader", FakeGraphLoader)
    monkeypatch.setattr(module, "SessionLocal", lambda: _SessionContext())

    exit_code = module.main(["--dry-run", "--bill", "8575-05"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "loaded=False" in output
    assert "import_job_id=" in output


def test_verify_legislative_bill_passes_with_detached_objects(monkeypatch, capsys) -> None:
    module = _load_script_module("verify_legislative_bill")
    entity = SimpleNamespace(id="entity-1", external_id="cl-congreso-boletin-8575-05")
    dataset = SimpleNamespace(id="dataset-1")
    calls = {"count": 0}

    class FakeSession:
        def scalar(self, statement):  # noqa: ANN001
            _ = statement
            calls["count"] += 1
            values = [entity, dataset, 1, 2, 3, 3]
            return values[calls["count"] - 1]

    monkeypatch.setattr(module, "SessionLocal", lambda: _SessionContext())

    def enter_session(self):  # noqa: ANN001
        return FakeSession()

    monkeypatch.setattr(_SessionContext, "__enter__", enter_session)
    monkeypatch.setattr(
        module,
        "_verify_visibility",
        lambda bulletin_id, external_id: {
            "search_found": True,
            "investigation_found": True,
            "timeline_non_empty": True,
            "evidence_count": 3,
            "source_count": 3,
            "error": "",
        },
    )

    exit_code = module.main(["8575-05"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "exists=True" in output
    assert "external_id_resolved=True" in output
    assert "claims=2" in output
    assert "evidencias=3" in output
    assert "documentos=3" in output


def _sample_batch() -> GraphBatch:
    retrieved_at = datetime(2026, 1, 2, 13, 0, tzinfo=UTC)
    entity = EntityRecord(
        entity_type=EntityType.PUBLIC_PROJECT,
        external_id="cl-congreso-boletin-8575-05",
        name="Boletin 8575-05",
    )
    source_record = SourceRecordPayload(
        external_id="cl-congreso-boletin-8575-05",
        record_type="legislature:bill",
        payload_hash="hash",
        raw_payload={"bill": "8575-05"},
        retrieved_at=retrieved_at,
        status=WorkflowStatus.VALIDATED,
    )
    evidence = EvidenceRecord(
        source_record=source_record,
        source_name="Datos Abiertos Legislativos Congreso Nacional",
        title="Votacion camara-votacion-1 asociada al boletin 8575-05",
        url="https://opendata.camara.cl/vote/1",
    )
    claim = ClaimRecord(
        subject_entity=entity,
        predicate="LEGISLATIVE_BILL_HAS_VOTE",
        source_record=source_record,
        evidence=evidence,
        object_value={"vote_id": "camara-votacion-1"},
    )
    return GraphBatch(
        source=SourceInfo(
            name="Datos Abiertos Legislativos Congreso Nacional",
            publisher="Congreso Nacional de Chile",
            url="https://opendata.camara.cl/",
        ),
        dataset=DatasetRecord(
            source_name="Datos Abiertos Legislativos Congreso Nacional",
            name="congreso-votaciones-boletin",
            description="Demo",
            version="8575-05",
            dataset_url="https://opendata.camara.cl/",
        ),
        source_records=(source_record,),
        entities=(entity,),
        evidence=(evidence,),
        claims=(claim,),
        public_relationships=(),
        raw_count=1,
    )
