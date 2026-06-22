from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from types import SimpleNamespace
from uuid import UUID

import datosenorden.maintenance.investigation_story as investigation_story
import datosenorden.web.app_services as app_services


class _SessionContext:
    def __enter__(self):  # noqa: ANN001
        return object()

    def __exit__(self, exc_type, exc, tb):  # noqa: ANN001
        _ = (exc_type, exc, tb)
        return False


@dataclass(frozen=True)
class _StoryFixture:
    view: SimpleNamespace
    comparison: dict[str, object]


def test_build_investigation_story_generates_neutral_multi_source_story(monkeypatch) -> None:
    fixture = _multi_source_fixture()
    _patch_story_fixture(monkeypatch, fixture)

    story = investigation_story.build_investigation_story(str(fixture.view.profile.entity.id))

    assert story["headline"] == fixture.view.profile.entity.name
    assert "multiple public datasets" in story["summary"].lower()
    assert story["sources_consulted"] == [
        "ChileCompra",
        "Lobby",
        "Transparencia Activa",
        "SERVEL",
        "Contraloria",
        "Municipalidades",
    ]
    assert story["timeline_highlights"]
    assert story["timeline_highlights"][0].startswith("2024:")
    assert any("procurement records" in item.lower() for item in story["key_findings"])
    assert any("public meetings" in item.lower() for item in story["important_connections"])
    assert any("compare information across datasets" in item.lower() for item in story["questions_for_citizens"])
    assert any("elected authority records" in item.lower() for item in story["questions_for_citizens"])
    _assert_neutral(story)


def test_build_investigation_story_handles_empty_dataset_story(monkeypatch) -> None:
    fixture = _empty_fixture()
    _patch_story_fixture(monkeypatch, fixture)

    story = investigation_story.build_investigation_story(str(fixture.view.profile.entity.id))

    assert story["sources_consulted"] == []
    assert story["timeline_highlights"] == []
    assert story["important_connections"] == []
    assert story["questions_for_citizens"] == [
        "Would you like to search another organization?",
        "Would you like to compare information across datasets?",
    ]
    assert story["key_findings"] == ["No public source records were found for this organization."]
    assert "no public source records" in story["summary"].lower()
    _assert_neutral(story)


def test_build_investigation_story_timeline_highlights_are_human_readable(monkeypatch) -> None:
    fixture = _timeline_fixture()
    _patch_story_fixture(monkeypatch, fixture)

    story = investigation_story.build_investigation_story(str(fixture.view.profile.entity.id))

    assert story["timeline_highlights"] == [
        "2023: Procurement activity appears in public records.",
        "2024: Public transparency records reference the organization.",
    ]
    _assert_neutral(story)


def test_get_investigation_story_passthrough(monkeypatch) -> None:
    payload = {
        "headline": "Demo",
        "summary": "Demo summary",
        "key_findings": [],
        "important_connections": [],
        "timeline_highlights": [],
        "sources_consulted": [],
        "questions_for_citizens": [],
    }
    monkeypatch.setattr(app_services, "build_investigation_story", lambda entity_id: payload)

    result = app_services.get_investigation_story("11111111-1111-1111-1111-111111111111")

    assert result == payload


def _patch_story_fixture(monkeypatch, fixture: _StoryFixture) -> None:
    monkeypatch.setattr(investigation_story, "SessionLocal", lambda: _SessionContext())
    monkeypatch.setattr(investigation_story, "build_investigation_view", lambda session, entity_id: fixture.view)
    monkeypatch.setattr(investigation_story, "build_entity_comparison", lambda entity_id: fixture.comparison)


def _assert_neutral(story: dict[str, object]) -> None:
    text = _flatten(story).lower()
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


def _multi_source_fixture() -> _StoryFixture:
    entity = _entity()
    view = _base_view(entity)
    view.summary = "DIVISION LOGISTICA DEL EJERCITO appears in multiple public datasets."
    view.timeline = SimpleNamespace(
        events=(
            _event("2024-01-01", "ChileCompra", "Procurement activity appears in public records."),
            _event("2024-03-01", "Lobby", "Public meetings are recorded."),
            _event("2024-04-01", "Transparencia", "Public transparency records reference the organization."),
            _event("2024-05-01", "SERVEL", "Elected authority records reference the organization."),
            _event("2024-05-01", "Contraloria", "Control records contain observations."),
            _event("2024-06-01", "Municipalidades", "Municipal records reference the organization."),
        )
    )
    view.procurement_items = (
        SimpleNamespace(dataset="ChileCompra", contract_name="Order 1", supplier="Supplier 1"),
    )
    view.lobby_items = (
        SimpleNamespace(
            dataset="Lobby",
            date=date(2024, 3, 1),
            organization=entity.name,
            counterparty="Persona Demo",
        ),
    )
    view.role_items = (
        SimpleNamespace(
            dataset="Transparencia",
            holder="Persona Demo",
            role_title="Cargo publico",
            period="2024",
        ),
        SimpleNamespace(
            dataset="SERVEL",
            holder="Autoridad Electa de Muestra Uno",
            role_title="Alcaldia de muestra",
            period="Periodo electoral 2024-2028",
        ),
    )
    comparison = {
        "entity_name": entity.name,
        "entity_type": entity.entity_type,
        "datasets_present": [
            "ChileCompra",
            "Lobby",
            "Transparencia Activa",
            "SERVEL",
            "Contraloria",
            "Municipalidades",
        ],
        "dataset_facts": [
            {"dataset": "ChileCompra", "headline": "ChileCompra records", "facts": ["1 source record"]},
            {"dataset": "Lobby", "headline": "Lobby records", "facts": ["1 source record"]},
            {"dataset": "Transparencia Activa", "headline": "Transparencia Activa records", "facts": ["1 source record"]},
            {"dataset": "SERVEL", "headline": "SERVEL records", "facts": ["1 source record", "Records describe elected authorities, public offices, territories, and electoral periods."]},
            {"dataset": "Contraloria", "headline": "Contraloria records", "facts": ["1 source record"]},
            {"dataset": "Municipalidades", "headline": "Municipalidades records", "facts": ["1 source record"]},
        ],
        "consistency_observations": [
            "The organization appears in multiple public datasets.",
            "The organization appears in procurement records and also has registered meetings.",
            "The organization is connected to public transparency records.",
            "SERVEL records describe elected authority information.",
            "Contraloria records contain observations related to the organization.",
            "Municipal records reference the organization.",
        ],
        "coverage_summary": "Summary text.",
    }
    return _StoryFixture(view=view, comparison=comparison)


def _empty_fixture() -> _StoryFixture:
    entity = _entity()
    view = _base_view(entity)
    view.summary = "No public source records were found for this organization."
    view.timeline = SimpleNamespace(events=())
    view.procurement_items = ()
    view.lobby_items = ()
    view.role_items = ()
    comparison = {
        "entity_name": entity.name,
        "entity_type": entity.entity_type,
        "datasets_present": [],
        "dataset_facts": [],
        "consistency_observations": [],
        "coverage_summary": "No public source records were found for this organization.",
    }
    return _StoryFixture(view=view, comparison=comparison)


def _timeline_fixture() -> _StoryFixture:
    entity = _entity()
    view = _base_view(entity)
    view.summary = "Timeline ready."
    view.timeline = SimpleNamespace(
        events=(
            _event("2023-02-01", "ChileCompra", "Procurement activity appears in public records."),
            _event("2024-04-01", "Transparencia", "Public transparency records reference the organization."),
        )
    )
    view.procurement_items = ()
    view.lobby_items = ()
    view.role_items = ()
    comparison = {
        "entity_name": entity.name,
        "entity_type": entity.entity_type,
        "datasets_present": ["ChileCompra", "Transparencia Activa"],
        "dataset_facts": [],
        "consistency_observations": ["The organization appears in multiple public datasets."],
        "coverage_summary": "Timeline summary.",
    }
    return _StoryFixture(view=view, comparison=comparison)


def _base_view(entity: SimpleNamespace) -> SimpleNamespace:
    return SimpleNamespace(
        profile=SimpleNamespace(entity=entity),
        summary="Base summary.",
        timeline=SimpleNamespace(events=()),
        procurement_items=(),
        lobby_items=(),
        role_items=(),
    )


def _entity(
    *,
    entity_id: str = "12345678-1234-1234-1234-123456789012",
    name: str = "DIVISION LOGISTICA DEL EJERCITO",
    entity_type: str = "PUBLIC_ORGANIZATION",
) -> SimpleNamespace:
    return SimpleNamespace(id=UUID(entity_id), name=name, entity_type=entity_type)


def _event(event_date: str, dataset: str, title: str) -> SimpleNamespace:
    return SimpleNamespace(event_date=date.fromisoformat(event_date), dataset=dataset, title=title)
