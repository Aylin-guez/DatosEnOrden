from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID

from datosenorden.models import Claim
from datosenorden.models import Dataset
from datosenorden.models import Entity
from datosenorden.models import Evidence
from datosenorden.models import RelationshipPublic
from datosenorden.models import Source
from datosenorden.models import SourceRecord
from datosenorden.maintenance.db_merge import MergeSnapshot
from datosenorden.maintenance.db_merge import build_merge_temp_database_name
from datosenorden.maintenance.db_merge import merge_snapshot_into_current_database
from datosenorden.maintenance.db_merge import render_merge_report_text


class _FakeScalarResult:
    def __init__(self, rows: Iterable[object]):
        self._rows = list(rows)

    def all(self):  # noqa: ANN001
        return list(self._rows)


class _FakeSession:
    def __init__(self, data: dict[type, list[object]]):
        self.data = data
        self.added: list[object] = []
        self.flushed = 0
        self.committed = 0
        self.rolled_back = 0

    def scalars(self, statement):  # noqa: ANN001
        model = statement.column_descriptions[0]["entity"]
        return _FakeScalarResult(self.data.get(model, []))

    def add(self, obj):  # noqa: ANN001
        self.data.setdefault(type(obj), []).append(obj)
        self.added.append(obj)

    def flush(self):  # noqa: D401
        self.flushed += 1

    def get(self, model, identity):  # noqa: ANN001
        for row in self.data.get(model, []):
            if getattr(row, "id", None) == identity:
                return row
        return None

    def commit(self):  # noqa: D401
        self.committed += 1

    def rollback(self):  # noqa: D401
        self.rolled_back += 1


def _uuid(value: str) -> UUID:
    return UUID(value)


def test_build_merge_temp_database_name_uses_timestamp_prefix() -> None:
    name = build_merge_temp_database_name(datetime(2026, 6, 19, 12, 0, tzinfo=timezone.utc))

    assert name.startswith("datosenorden_merge_20260619_120000_")


def test_render_merge_report_text_formats_counts() -> None:
    text = render_merge_report_text(
        type(
            "Report",
            (),
            {
                "inserted_source_records": 1,
                "inserted_entities": 2,
                "inserted_claims": 3,
                "inserted_evidences": 4,
                "inserted_relationships": 5,
                "skipped_duplicates": 6,
            },
        )(),
        dry_run=True,
    )

    assert "merge_report:" in text
    assert "mode=dry-run" in text
    assert "inserted source_records=1" in text
    assert "skipped duplicates=6" in text


def test_merge_snapshot_into_current_database_skips_duplicates_and_inserts_missing() -> None:
    source_existing = Source(
        id=_uuid("11111111-1111-1111-1111-111111111111"),
        name="ChileCompra",
        url="https://example.com/chilecompra",
    )
    entity_existing = Entity(
        id=_uuid("22222222-2222-2222-2222-222222222222"),
        entity_type="PUBLIC_ORGANIZATION",
        name="SERVICIO DE SALUD ARAUCO",
        external_id="org-1",
        status="active",
    )
    dest_session = _FakeSession(
        {
            Source: [source_existing],
            Dataset: [],
            Entity: [entity_existing],
            SourceRecord: [],
            Evidence: [],
            Claim: [],
            RelationshipPublic: [],
        }
    )

    source_duplicate = Source(
        id=_uuid("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        name="ChileCompra",
        url="https://example.com/chilecompra",
    )
    source_new = Source(
        id=_uuid("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
        name="DIPRES Prototype",
        url="https://example.com/dipres",
    )
    dataset = Dataset(
        id=_uuid("33333333-3333-3333-3333-333333333333"),
        source_id=source_duplicate.id,
        name="ChileCompra",
        version="2026-06",
        dataset_url="https://example.com/dataset",
    )
    entity_new = Entity(
        id=_uuid("44444444-4444-4444-4444-444444444444"),
        entity_type="COMPANY",
        name="Proveedor Nuevo",
        external_id="supplier-1",
        status="active",
    )
    source_record = SourceRecord(
        id=_uuid("55555555-5555-5555-5555-555555555555"),
        source_id=source_duplicate.id,
        dataset_id=dataset.id,
        external_id="rec-1",
        record_type="purchase_order",
        payload_hash="hash-1",
        raw_payload={"foo": "bar"},
        retrieved_at=datetime(2026, 6, 19, tzinfo=timezone.utc),
        status="published",
    )
    evidence = Evidence(
        id=_uuid("66666666-6666-6666-6666-666666666666"),
        source_id=source_duplicate.id,
        dataset_id=dataset.id,
        source_record_id=source_record.id,
        title="Orden de compra",
        url="https://example.com/evidence/1",
    )
    claim = Claim(
        id=_uuid("77777777-7777-7777-7777-777777777777"),
        subject_entity_id=entity_existing.id,
        predicate="ISSUES_PURCHASE_ORDER",
        object_entity_id=entity_new.id,
        object_value=None,
        source_record_id=source_record.id,
        evidence_id=evidence.id,
        confidence=Decimal("1.0"),
        status="published",
    )
    relationship = RelationshipPublic(
        id=_uuid("88888888-8888-8888-8888-888888888888"),
        source_entity_id=entity_existing.id,
        target_entity_id=entity_new.id,
        relationship_type="ISSUES_PURCHASE_ORDER",
        claim_id=claim.id,
        status="published",
    )
    snapshot = MergeSnapshot(
        sources=(source_duplicate, source_new),
        datasets=(dataset,),
        entities=(entity_existing, entity_new),
        source_records=(source_record,),
        evidences=(evidence,),
        claims=(claim,),
        relationships=(relationship,),
    )

    report = merge_snapshot_into_current_database(snapshot, dest_session)

    assert report.inserted_source_records == 1
    assert report.inserted_entities == 1
    assert report.inserted_claims == 1
    assert report.inserted_evidences == 1
    assert report.inserted_relationships == 1
    assert report.skipped_duplicates >= 2
    assert len(dest_session.data[Source]) == 2
    assert len(dest_session.data[Entity]) == 2
    assert len(dest_session.data[SourceRecord]) == 1
    assert len(dest_session.data[Evidence]) == 1
    assert len(dest_session.data[Claim]) == 1
    assert len(dest_session.data[RelationshipPublic]) == 1
    assert dest_session.data[Evidence][0].claim_id == claim.id
