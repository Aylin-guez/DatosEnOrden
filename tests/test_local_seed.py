from __future__ import annotations

from pathlib import Path
import sys
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from datosenorden.etl.local_seed import (  # noqa: E402
    LOCAL_SEED_CLASSIFICATION,
    LOCAL_SEED_OFFICIAL_STATUS,
    LocalSeedResult,
    build_local_traceability_seed_batch,
    persist_local_traceability_seed,
)
from datosenorden.etl.loaders.graph_loader import GraphLoader  # noqa: E402
import seed_traceability_flow as seed_script  # noqa: E402


def test_local_seed_batch_is_clearly_marked_non_official() -> None:
    batch = build_local_traceability_seed_batch()

    assert batch.raw_count == 1
    assert batch.rejected_count == 0
    assert len(batch.source_records) == 1
    assert len(batch.claims) == 1
    assert len(batch.evidence) == 1
    assert len(batch.public_relationships) == 1
    assert batch.source.metadata["classification"] == LOCAL_SEED_CLASSIFICATION
    assert batch.source.metadata["official_status"] == LOCAL_SEED_OFFICIAL_STATUS
    assert batch.dataset.metadata["classification"] == LOCAL_SEED_CLASSIFICATION
    assert batch.source_records[0].raw_payload["classification"] == LOCAL_SEED_CLASSIFICATION
    assert batch.evidence[0].metadata["official_status"] == LOCAL_SEED_OFFICIAL_STATUS
    assert batch.claims[0].metadata["official_status"] == LOCAL_SEED_OFFICIAL_STATUS
    assert batch.public_relationships[0].metadata["classification"] == LOCAL_SEED_CLASSIFICATION


def test_persist_local_traceability_seed_counts_rows_without_ticket(monkeypatch) -> None:
    session = MagicMock()
    captured: dict[str, object] = {}

    def fake_load(self, batch, dry_run=False):  # noqa: ANN001
        captured["batch"] = batch
        captured["dry_run"] = dry_run
        return None

    monkeypatch.setattr(GraphLoader, "load", fake_load)
    monkeypatch.setattr(
        "datosenorden.etl.local_seed._count_rows",
        lambda session, model: {"source_record": 1, "claim": 1, "evidence": 1, "relationship_public": 1}[  # noqa: E501
            model.__tablename__
        ],
    )

    result = persist_local_traceability_seed(session)

    assert captured["dry_run"] is False
    assert result.source_records == 1
    assert result.claims == 1
    assert result.evidences == 1
    assert result.relationship_public == 1


def test_seed_script_prints_counts_without_ticket(monkeypatch, capsys) -> None:
    class DummySession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(seed_script, "SessionLocal", lambda: DummySession())
    monkeypatch.setattr(
        seed_script,
        "persist_local_traceability_seed",
        lambda session: LocalSeedResult(source_records=1, claims=1, evidences=1, relationship_public=1),
    )

    exit_code = seed_script.main()

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "local_seed:" in captured.out
    assert "source_records=1" in captured.out
    assert "claims=1" in captured.out
    assert "evidences=1" in captured.out
    assert "relationship_public=1" in captured.out
