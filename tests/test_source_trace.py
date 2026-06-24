from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from uuid import UUID

import datosenorden.maintenance.source_trace as source_trace


class _SessionContext:
    def __enter__(self):  # noqa: ANN001
        return object()

    def __exit__(self, exc_type, exc, tb):  # noqa: ANN001
        _ = (exc_type, exc, tb)
        return False


def test_build_source_trace_groups_sources_by_dataset_and_stays_neutral(monkeypatch) -> None:
    view = _view_fixture()
    comparison = {
        "entity_name": view.profile.entity.name,
        "entity_type": view.profile.entity.entity_type,
        "datasets_present": ["ChileCompra", "Lobby", "SERVEL"],
        "dataset_facts": [
            {"dataset": "ChileCompra", "headline": "ChileCompra records", "facts": ["Procurement activity is present."]},
            {"dataset": "Lobby", "headline": "Lobby records", "facts": ["Registered meetings are present."]},
            {"dataset": "SERVEL", "headline": "SERVEL records", "facts": ["Elected authority records are present."]},
        ],
        "consistency_observations": [
            "The organization appears in procurement records and registered meetings.",
            "The organization is also represented in elected authority records.",
        ],
        "coverage_summary": "Coverage summary.",
    }
    story = {
        "headline": view.profile.entity.name,
        "summary": "Neutral summary.",
        "key_findings": [],
        "important_connections": [],
        "timeline_highlights": [],
        "sources_consulted": ["ChileCompra", "Lobby", "SERVEL"],
        "questions_for_citizens": [],
    }
    monkeypatch.setattr(source_trace, "SessionLocal", lambda: _SessionContext())
    monkeypatch.setattr(source_trace, "build_investigation_view", lambda session, entity_id: view)
    monkeypatch.setattr(source_trace, "build_entity_comparison", lambda entity_id: comparison)
    monkeypatch.setattr(source_trace, "build_investigation_story", lambda entity_id: story)

    trace = source_trace.build_source_trace(str(view.profile.entity.id))

    assert trace["entity"]["name"] == "DIVISION LOGISTICA DEL EJERCITO"
    assert trace["entity"]["type"] == "PUBLIC_ORGANIZATION"
    assert trace["neutrality_notice"].startswith("This trace is descriptive only.")
    assert set(source["dataset"] for source in trace["sources"]) == {"ChileCompra", "Lobby", "SERVEL"}
    assert len(trace["connections"]) == 3
    assert "multiple public sources" in trace["overlap_summary"].lower()
    _assert_neutral(trace)


def test_build_source_trace_handles_empty_view_neutrally(monkeypatch) -> None:
    monkeypatch.setattr(source_trace, "SessionLocal", lambda: _SessionContext())
    monkeypatch.setattr(source_trace, "build_investigation_view", lambda session, entity_id: None)
    monkeypatch.setattr(source_trace, "build_entity_comparison", lambda entity_id: {"datasets_present": [], "dataset_facts": []})
    monkeypatch.setattr(source_trace, "build_investigation_story", lambda entity_id: {"sources_consulted": []})

    trace = source_trace.build_source_trace("11111111-1111-1111-1111-111111111111")

    assert trace["entity"] == {"id": "", "name": "", "type": ""}
    assert trace["sources"] == []
    assert trace["connections"] == []
    assert "No public source records" in trace["overlap_summary"]
    _assert_neutral(trace)


def test_render_source_trace_text_is_citizen_facing(monkeypatch) -> None:
    trace = {
        "entity": {"id": "1", "name": "Demo entity", "type": "PUBLIC_ORGANIZATION"},
        "sources": [
            {
                "dataset": "ChileCompra",
                "contribution": "Procurement records associated with this entity.",
                "evidence_count": 2,
                "relationship_count": 1,
                "facts": ["Procurement activity is present."],
                "technical": ["claim_id=abc123"],
            }
        ],
        "connections": [],
        "overlap_summary": "Coverage summary.",
        "neutrality_notice": "This trace is descriptive only.",
    }

    text = source_trace.render_source_trace_text(trace)

    assert "source_trace:" in text
    assert "Demo entity" in text
    assert "ChileCompra" in text
    assert "claim_id=abc123" in text
    _assert_neutral(text)


def test_build_source_trace_handles_dict_views_and_links(monkeypatch) -> None:
    view = {
        "profile": {
            "entity": {
                "id": UUID("11111111-1111-1111-1111-111111111111"),
                "name": "DIVISION LOGISTICA DEL EJERCITO",
                "entity_type": "PUBLIC_ORGANIZATION",
            },
            "relationships": (),
            "direct_neighbors": (),
        },
        "dataset_badges": ("ChileCompra", "Lobby", "SERVEL"),
        "procurement_items": (
            {
                "dataset": "ChileCompra",
                "contract_name": "Order 1",
                "supplier": "Supplier A",
                "evidence_count": 1,
            },
        ),
        "lobby_items": (),
        "role_items": (),
        "evidence_groups": (
            {
                "dataset": "ChileCompra",
                "links": (
                    {"title": "Evidencia dict", "url": "https://example.test/dict", "published_at": None},
                ),
            },
        ),
        "timeline": {
            "events": (
                {
                    "dataset": "SERVEL",
                    "dataset_name": "SERVEL",
                    "title": "Elected authority records are present.",
                    "predicate": "AUTHORITY_ELECTED_TO_OFFICE",
                    "claim_id": "44444444-4444-4444-4444-444444444444",
                    "source_record_id": "55555555-5555-5555-5555-555555555555",
                    "evidence_count": 1,
                },
            ),
        },
    }
    comparison = {
        "datasets_present": ["ChileCompra", "SERVEL"],
        "dataset_facts": [
            {"dataset": "ChileCompra", "facts": ["Procurement activity is present."]},
            {"dataset": "SERVEL", "facts": ["Elected authority records are present."]},
        ],
        "coverage_summary": "Coverage summary.",
    }
    story = {"sources_consulted": ["ChileCompra", "SERVEL"]}
    monkeypatch.setattr(source_trace, "SessionLocal", lambda: _SessionContext())
    monkeypatch.setattr(source_trace, "build_investigation_view", lambda session, entity_id: view)
    monkeypatch.setattr(source_trace, "build_entity_comparison", lambda entity_id: comparison)
    monkeypatch.setattr(source_trace, "build_investigation_story", lambda entity_id: story)

    trace = source_trace.build_source_trace(str(view["profile"]["entity"]["id"]))

    assert trace["entity"]["name"] == "DIVISION LOGISTICA DEL EJERCITO"
    assert trace["sources"][0]["dataset"] == "ChileCompra"
    assert trace["sources"][0]["evidence_count"] >= 1
    assert trace["connections"]


def _view_fixture() -> SimpleNamespace:
    entity = SimpleNamespace(
        id=UUID("11111111-1111-1111-1111-111111111111"),
        name="DIVISION LOGISTICA DEL EJERCITO",
        entity_type="PUBLIC_ORGANIZATION",
    )
    timeline = SimpleNamespace(
        events=(
            SimpleNamespace(
                dataset="ChileCompra",
                dataset_name="ChileCompra",
                title="Procurement activity appears in public records.",
                predicate="ISSUES_PURCHASE_ORDER",
                claim_id="22222222-2222-2222-2222-222222222222",
                source_record_id="33333333-3333-3333-3333-333333333333",
                evidence_count=1,
            ),
            SimpleNamespace(
                dataset="SERVEL",
                dataset_name="SERVEL",
                title="Elected authority records are present.",
                predicate="AUTHORITY_ELECTED_TO_OFFICE",
                claim_id="44444444-4444-4444-4444-444444444444",
                source_record_id="55555555-5555-5555-5555-555555555555",
                evidence_count=1,
            ),
        )
    )
    profile = SimpleNamespace(
        entity=entity,
        direct_neighbors=(),
    )
    return SimpleNamespace(
        profile=profile,
        summary="Neutral summary.",
        dataset_badges=("ChileCompra", "Lobby", "SERVEL"),
        procurement_items=(
            SimpleNamespace(dataset="ChileCompra", contract_name="Order 1", supplier="Supplier A", evidence_count=1),
            SimpleNamespace(dataset="ChileCompra", contract_name="Order 2", supplier="Supplier B", evidence_count=2),
        ),
        lobby_items=(
            SimpleNamespace(
                dataset="Lobby",
                date=date(2026, 3, 15),
                organization="DIVISION LOGISTICA DEL EJERCITO",
                counterparty="Persona Demo",
                subject="Public meeting",
                evidence_count=2,
            ),
        ),
        role_items=(
            SimpleNamespace(
                dataset="SERVEL",
                holder="Autoridad Electa de Muestra Uno",
                role_title="Alcaldia de muestra",
                period="Periodo electoral 2024-2028",
                evidence_count=1,
            ),
        ),
        evidence_groups=(
            SimpleNamespace(
                dataset="ChileCompra",
                links=(
                    SimpleNamespace(title="Evidencia compra 1", url="https://example.test/1", published_at=None),
                    SimpleNamespace(title="Evidencia compra 2", url="https://example.test/2", published_at=None),
                ),
            ),
        ),
        timeline=timeline,
        graph=SimpleNamespace(),
        graph_explanation="Resumen neutral.",
        metrics=SimpleNamespace(evidence=6, relationships=4),
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
