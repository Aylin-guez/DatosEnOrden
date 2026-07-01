from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

from datosenorden.etl.core.contracts import DatasetRecord
from datosenorden.etl.core.contracts import GraphBatch
from datosenorden.etl.core.contracts import SourceInfo
from datosenorden.etl.core.pipeline import DatasetLoadRequest
from datosenorden.etl.core.pipeline import load_dataset
import datosenorden.etl.core.pipeline as pipeline


class FakeAdapter:
    dataset_id = "fake"

    def __init__(self, errors=()):
        self.errors = tuple(errors)

    def validate(self, request):  # noqa: ANN001
        return self.errors

    def normalize(self, request):  # noqa: ANN001
        return {"dataset_id": request.dataset_id}

    def build_relationships(self, normalized):  # noqa: ANN001
        return GraphBatch(
            source=SourceInfo(name="Fake", publisher="Local", url="local://fake"),
            dataset=DatasetRecord(
                source_name="Fake",
                name="fake-dataset",
                description="Fake dataset",
                version="test",
                dataset_url="local://fake",
            ),
            source_records=(),
            entities=(),
            evidence=(),
            claims=(),
            public_relationships=(),
            raw_count=2,
            rejected_count=0,
            errors=(),
        )


def test_load_dataset_runs_common_pipeline(monkeypatch) -> None:
    calls: dict[str, object] = {}

    def fake_publish(session, batch, dry_run=False):  # noqa: ANN001
        calls["session"] = session
        calls["batch"] = batch
        calls["dry_run"] = dry_run

    monkeypatch.setattr(pipeline, "publish", fake_publish)

    result = load_dataset(SimpleNamespace(), FakeAdapter(), DatasetLoadRequest(dataset_id="fake", dry_run=True))

    assert result.dataset_id == "fake"
    assert result.loaded is False
    assert result.dry_run is True
    assert result.raw_count == 2
    assert calls["dry_run"] is True


def test_load_dataset_stops_on_validation_errors(monkeypatch) -> None:
    monkeypatch.setattr(pipeline, "publish", lambda *args, **kwargs: None)

    result = load_dataset(SimpleNamespace(), FakeAdapter(errors=("missing file",)), DatasetLoadRequest(dataset_id="fake"))

    assert result.loaded is False
    assert result.errors == ("missing file",)
    assert result.raw_count == 0
