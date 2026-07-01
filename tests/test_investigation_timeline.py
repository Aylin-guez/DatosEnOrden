from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from uuid import UUID

import datosenorden.maintenance.investigation_timeline as investigation_timeline


class _SessionContext:
    def __enter__(self):  # noqa: ANN001
        return object()

    def __exit__(self, exc_type, exc, tb):  # noqa: ANN001
        _ = (exc_type, exc, tb)
        return False


def test_build_investigation_timeline_groups_events_by_year_and_category(monkeypatch) -> None:
    timeline = SimpleNamespace(
        entity=SimpleNamespace(id=UUID("11111111-1111-1111-1111-111111111111"), name="Entidad demo", entity_type="PUBLIC_ORGANIZATION"),
        events=(
            SimpleNamespace(
                event_date=date(2026, 1, 3),
                dataset="DIPRES",
                dataset_name="DIPRES",
                title="Budget approved",
                explanation="Budget approved.",
                claim_id="c1",
                predicate="HAS_APPROVED_BUDGET",
                source_record_id="s1",
                evidence_count=1,
                relationship_count=1,
            ),
            SimpleNamespace(
                event_date=date(2026, 3, 15),
                dataset="ChileCompra",
                dataset_name="ChileCompra",
                title="Procurement record",
                explanation="Procurement record.",
                claim_id="c2",
                predicate="ISSUES_PURCHASE_ORDER",
                source_record_id="s2",
                evidence_count=1,
                relationship_count=1,
            ),
            SimpleNamespace(
                event_date=date(2026, 4, 2),
                dataset="Registro Empresas",
                dataset_name="registro-empresas-sample",
                title="Company registry record",
                explanation="Company registry record.",
                claim_id="c4",
                predicate="COMPANY_REGISTERED_ON",
                source_record_id="s4",
                evidence_count=1,
                relationship_count=1,
            ),
            SimpleNamespace(
                event_date=date(2025, 7, 12),
                dataset="SERVEL",
                dataset_name="SERVEL",
                title="Authority record",
                explanation="Authority record.",
                claim_id="c3",
                predicate="AUTHORITY_ELECTED_TO_OFFICE",
                source_record_id="s3",
                evidence_count=1,
                relationship_count=1,
            ),
        )
    )
    monkeypatch.setattr(investigation_timeline, "SessionLocal", lambda: _SessionContext())
    monkeypatch.setattr(investigation_timeline, "build_entity_timeline", lambda session, entity_id: timeline)

    report = investigation_timeline.build_investigation_timeline(str(timeline.entity.id))

    assert report["entity"]["name"] == "Entidad demo"
    assert [year["year"] for year in report["years"]] == [2026, 2025]
    first_year = report["years"][0]
    assert first_year["categories"][0]["category"] == "Budget"
    assert any(category["category"] == "Procurement" for category in first_year["categories"])
    assert any(category["category"] == "Company Registry" for category in first_year["categories"])
    first_item = first_year["categories"][0]["items"][0]
    assert first_item["origin"] == "derived_from_expediente"
    assert first_item["source_id"] == "s1"
    assert first_item["claim_id"] == "c1"
    assert report["summary"]
