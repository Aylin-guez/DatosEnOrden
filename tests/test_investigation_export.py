from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from uuid import UUID

import datosenorden.maintenance.investigation_export as investigation_export


class _SessionContext:
    def __enter__(self):  # noqa: ANN001
        return object()

    def __exit__(self, exc_type, exc, tb):  # noqa: ANN001
        _ = (exc_type, exc, tb)
        return False


def test_export_investigation_markdown_contains_required_sections(monkeypatch) -> None:
    view = _view_fixture()
    story = {
        "headline": "DIVISION LOGISTICA DEL EJERCITO",
        "summary": "Neutral summary.",
        "key_findings": ["The organization appears in multiple public datasets."],
        "important_connections": ["ChileCompra: procurement records are present."],
        "timeline_highlights": [
            "2026: Procurement activity appears in public records.",
            "2026: Elected authority records are present.",
        ],
        "sources_consulted": ["ChileCompra", "Lobby", "SERVEL"],
        "questions_for_citizens": ["Would you like to inspect procurement records?"],
    }
    trace = {
        "entity": {
            "id": "11111111-1111-1111-1111-111111111111",
            "name": "DIVISION LOGISTICA DEL EJERCITO",
            "type": "PUBLIC_ORGANIZATION",
        },
        "sources": [
            {
                "dataset": "ChileCompra",
                "contribution": "Procurement records associated with this entity.",
                "evidence_count": 2,
                "relationship_count": 1,
                "facts": ["Procurement activity is present."],
                "technical": ["claim_id=22222222-2222-2222-2222-222222222222"],
            },
            {
                "dataset": "SERVEL",
                "contribution": "Elected authority records associated with this entity.",
                "evidence_count": 1,
                "relationship_count": 1,
                "facts": ["Elected authority records are present."],
                "technical": ["claim_id=44444444-4444-4444-4444-444444444444"],
            },
        ],
        "connections": [],
        "overlap_summary": "Coverage summary.",
        "neutrality_notice": "This trace is descriptive only.",
    }
    monkeypatch.setattr(investigation_export, "SessionLocal", lambda: _SessionContext())
    monkeypatch.setattr(investigation_export, "build_investigation_view", lambda session, entity_id: view)
    monkeypatch.setattr(investigation_export, "build_investigation_story", lambda entity_id: story)
    monkeypatch.setattr(investigation_export, "build_source_trace", lambda entity_id: trace)

    markdown = investigation_export.export_investigation_markdown(str(view.profile.entity.id))

    for heading in (
        "# DIVISION LOGISTICA DEL EJERCITO",
        "## Neutral Summary",
        "## Sources Consulted",
        "## What Each Source Contributes",
        "## Timeline Highlights",
        "## Important Connections",
        "## Evidence Summary",
        "## Technical Appendix",
    ):
        assert heading in markdown
    assert "https://example.test/1" in markdown
    assert "relationship_type: RECEIVES_CONTRACT" in markdown or "relationship_type:" in markdown
    assert "predicate:" in markdown
    assert "This trace is descriptive only." in markdown
    _assert_neutral(markdown)


def test_export_investigation_markdown_handles_empty_view(monkeypatch) -> None:
    monkeypatch.setattr(investigation_export, "SessionLocal", lambda: _SessionContext())
    monkeypatch.setattr(investigation_export, "build_investigation_view", lambda session, entity_id: None)
    monkeypatch.setattr(investigation_export, "build_investigation_story", lambda entity_id: {"summary": ""})
    monkeypatch.setattr(investigation_export, "build_source_trace", lambda entity_id: {"sources": [], "overlap_summary": "No public source records were found for this entity.", "neutrality_notice": "Neutral."})

    markdown = investigation_export.export_investigation_markdown("11111111-1111-1111-1111-111111111111")

    assert "# Investigation" in markdown
    assert "## Neutral Summary" in markdown
    assert "No public source records were found for this entity." in markdown
    _assert_neutral(markdown)


def _view_fixture() -> SimpleNamespace:
    entity = SimpleNamespace(
        id=UUID("11111111-1111-1111-1111-111111111111"),
        name="DIVISION LOGISTICA DEL EJERCITO",
        entity_type="PUBLIC_ORGANIZATION",
    )
    profile = SimpleNamespace(
        entity=entity,
        direct_neighbors=(
            SimpleNamespace(
                relationship_id="66666666-6666-6666-6666-666666666666",
                relationship_type="AUTHORITY_ELECTED_TO_OFFICE",
                direction="outgoing",
                neighbor=SimpleNamespace(id="77777777-7777-7777-7777-777777777777"),
            ),
        ),
    )
    timeline = SimpleNamespace(
        events=(
            SimpleNamespace(
                claim_id="22222222-2222-2222-2222-222222222222",
                dataset="ChileCompra",
                dataset_name="ChileCompra",
                predicate="ISSUES_PURCHASE_ORDER",
                source_record_id="33333333-3333-3333-3333-333333333333",
            ),
            SimpleNamespace(
                claim_id="44444444-4444-4444-4444-444444444444",
                dataset="SERVEL",
                dataset_name="SERVEL",
                predicate="AUTHORITY_ELECTED_TO_OFFICE",
                source_record_id="55555555-5555-5555-5555-555555555555",
            ),
        )
    )
    return SimpleNamespace(
        profile=profile,
        summary="Neutral summary.",
        metrics=SimpleNamespace(evidence=3, relationships=2),
        timeline=timeline,
        evidence_groups=(
            SimpleNamespace(
                dataset="ChileCompra",
                links=(
                    SimpleNamespace(title="Evidence 1", url="https://example.test/1", published_at=date(2026, 1, 1)),
                ),
            ),
        ),
    )


def _assert_neutral(value: object) -> None:
    text = _flatten(value).lower()
    bad_terms = (
        "accus",
        "accuse",
        "culp",
        "corrupt",
        "fraud",
        "illicit",
        "irregular",
        "risk",
        "suspicious",
        "wrongdo",
    )
    assert not any(term in text for term in bad_terms)


def _flatten(value: object) -> str:
    if isinstance(value, dict):
        return " ".join(_flatten(item) for item in value.values())
    if isinstance(value, list | tuple | set):
        return " ".join(_flatten(item) for item in value)
    return str(value)
