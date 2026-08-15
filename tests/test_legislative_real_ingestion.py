from __future__ import annotations

from datetime import UTC, datetime

import pytest

from datosenorden.adapters.legislature.foundation import AcquisitionManifest, AcquisitionMethod, IdentityConfidence
from datosenorden.adapters.legislature.normalization import LegislativeEvent, LegislativeEventType, LegislativeMatter, LegislativeResourceType, LegislativeStatus, SourceObservation, compare_snapshots, matter_identity, normalize_bulletin_number, normalize_matter, snapshot_matter
from datosenorden.application.legislative_ingestion.service import BULLETIN_15975_25, ingest_bulletin_15975_25
from datosenorden.application.provenance import PROVENANCE_MANIFEST


def _manifest(source: str = "senado") -> AcquisitionManifest:
    return AcquisitionManifest(source, "bulletin:15975-25", "https://tramitacion.senado.cl/resource", datetime.now(UTC), "application/xml", 10, "a" * 64, AcquisitionMethod.STRUCTURED_ENDPOINT, 200)


def _matter():
    matter = LegislativeMatter("CL", "BILL", "15975 25", matter_identity("15975-25"), "Crea el Subsistema de Inteligencia Econica", "Senado")
    observation = SourceObservation("senado", LegislativeResourceType.MATTER_SUMMARY, "project", _manifest(), matter.title, LegislativeStatus.IN_DISCUSSION, "Comision Mixta", IdentityConfidence.EXACT)
    event = LegislativeEvent(LegislativeEventType.MIXED_COMMISSION, None, "senado", "news", datetime.now(UTC), "https://www.senado.cl/news", IdentityConfidence.STRONG)
    return normalize_matter(matter, (observation,), (event,))


def test_bulletin_identity_is_deterministic_not_fuzzy() -> None:
    assert normalize_bulletin_number("15975 25") == BULLETIN_15975_25
    with pytest.raises(ValueError):
        normalize_bulletin_number("15975 foo")


def test_normalization_keeps_source_conflict_fail_closed() -> None:
    matter = LegislativeMatter("CL", "BILL", BULLETIN_15975_25, matter_identity(BULLETIN_15975_25), "X", "Senado")
    left = SourceObservation("senado", LegislativeResourceType.MATTER_SUMMARY, "a", _manifest(), "X", LegislativeStatus.IN_DISCUSSION, None, IdentityConfidence.EXACT)
    right = SourceObservation("camara", LegislativeResourceType.VOTE, "b", _manifest("camara"), "Y", LegislativeStatus.UNKNOWN, None, IdentityConfidence.EXACT)
    assert normalize_matter(matter, (left, right), ()).source_conflict is True


def test_snapshot_baseline_unchanged_and_event_change() -> None:
    current = snapshot_matter(_matter())
    assert compare_snapshots(None, current).state == "BASELINE"
    assert compare_snapshots(current, current).state == "UNCHANGED"
    changed = current.__class__(current.canonical_identifier, "b" * 64, current.retrieved_at, current.matter_status, current.event_keys + ("new",))
    assert compare_snapshots(current, changed).significance == "MEANINGFUL_CHANGE"


def test_legislative_provenance_entries_are_exact_real() -> None:
    entries = [item for item in PROVENANCE_MANIFEST if item.dataset_version == BULLETIN_15975_25 and item.dataset_name.endswith("legislative-matter")]
    assert len(entries) == 2
    assert all(item.provenance_class.value == "REAL" and item.public_countable for item in entries)


def test_repeated_ingestion_reuses_without_graph_loader(monkeypatch) -> None:
    class Existing:
        external_id = "senado:project"
        payload_hash = "same"
        raw_payload = {"observation": {"manifest": {"sha256": "same", "retrieved_at": "first"}}}
    class Session:
        def scalars(self, _query):
            class Result:
                def all(self): return [Existing()]
            return Result()
    class Record:
        external_id = "senado:project"
        payload_hash = "same"
        raw_payload = {"observation": {"manifest": {"sha256": "same", "retrieved_at": "second"}}}
    class Batch:
        source_records = (Record(),)
    class Preview:
        batches = (Batch(),)
        snapshot_hash = "s"
    result = ingest_bulletin_15975_25(Session(), Preview())  # type: ignore[arg-type]
    assert result.reused is True and result.created is False


def test_observation_comparison_ignores_only_acquisition_timestamp() -> None:
    from datosenorden.application.legislative_ingestion.service import _same_observation
    left = {"observation": {"manifest": {"sha256": "a", "retrieved_at": "first"}}}
    right = {"observation": {"manifest": {"sha256": "a", "retrieved_at": "second"}}}
    changed = {"observation": {"manifest": {"sha256": "b", "retrieved_at": "second"}}}
    assert _same_observation(left, right) is True
    assert _same_observation(left, changed) is False
