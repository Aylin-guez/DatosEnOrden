from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import reflex_app.reflex_app as reflex_app


@dataclass
class _Dumpable:
    name: str

    def model_dump(self) -> dict[str, str]:
        return {"name": self.name}


def test_field_supports_dicts_and_typed_objects() -> None:
    assert reflex_app._field({"name": "dict-value"}, "name") == "dict-value"
    assert reflex_app._field(SimpleNamespace(name="attr-value"), "name") == "attr-value"
    assert reflex_app._field(_Dumpable("dump-value"), "name") == "dump-value"
    assert reflex_app._field(None, "name", "fallback") == "fallback"


def test_load_home_populates_connection_preview(monkeypatch) -> None:
    state = SimpleNamespace(error_message="old")

    monkeypatch.setattr(
        reflex_app,
        "get_dataset_summary",
        lambda: {
            "datasets": [{"name": "ChileCompra", "health": "active"}],
            "totals": {
                "datasets": 1,
                "active_datasets": 1,
                "claims": 2,
                "relationships": 3,
            },
        },
    )
    monkeypatch.setattr(
        reflex_app,
        "get_cross_dataset_connections",
        lambda: [
            {
                "organization_id": str(index),
                "organization_name": f"Entidad {index}",
                "datasets": ["ChileCompra", "Lobby"],
                "contracts": 1,
                "lobby_meetings": 1,
                "evidence": 2,
                "relationships": 3,
            }
            for index in range(7)
        ],
    )
    monkeypatch.setattr(
        reflex_app,
        "get_demo_status",
        lambda: {"missing": [{"label": "Carga lista"}]},
    )
    monkeypatch.setattr(
        reflex_app,
        "get_guided_questions",
        lambda: {
            "questions": [
                {
                    "id": "who_sells_to_this_body",
                    "title": "¿Quién vende a este organismo?",
                    "description": "Demo.",
                    "concepts": ["Organismo"],
                    "suggested_sources": ["ChileCompra"],
                    "example_query": "Demo",
                    "search_query": "Demo",
                    "cta": "Buscar",
                }
            ],
            "categories": [
                {
                    "id": "public_organizations",
                    "title": "Organismos públicos",
                    "description": "Demo.",
                    "examples": ["Entidad demo"],
                    "suggested_sources": ["ChileCompra"],
                    "search_query": "Entidad demo",
                    "cta": "Explorar",
                }
            ],
        },
    )

    reflex_app.AppState.load_home.fn(state)

    assert state.error_message == ""
    assert len(state.connection_rows) == 7
    assert len(state.connection_rows_preview) == 6
    assert state.connection_rows_preview == state.connection_rows[:6]
    assert state.demo_missing == ["Carga lista"]
    assert state.total_datasets == 1
    assert state.active_datasets == 1
    assert state.total_claims == 2
    assert state.total_relationships == 3
    assert state.guided_question_rows[0]["id"] == "who_sells_to_this_body"
    assert state.guided_category_rows[0]["id"] == "public_organizations"


def test_load_investigation_without_selection_uses_guided_empty_state(monkeypatch) -> None:
    calls: list[str] = []

    def fake_load_home(self) -> None:  # noqa: ANN001
        calls.append("load_home")
        self.connection_rows = [
            {
                "organization_id": str(index),
                "organization_name": f"Entidad {index}",
                "datasets_text": "ChileCompra | Lobby",
                "contracts": 1,
                "lobby_meetings": 1,
                "evidence": 2,
                "relationships": 3,
            }
            for index in range(7)
        ]
        self.connection_rows_preview = self.connection_rows[:6]
        self.demo_missing = ["Carga lista"]
        self.total_datasets = 1
        self.active_datasets = 1
        self.total_claims = 2
        self.total_relationships = 3

    state = SimpleNamespace(
        error_message="old",
        selected_entity_id="",
        selected_entity_name="Old entity",
        router=SimpleNamespace(url=SimpleNamespace(query_parameters={})),
        report_path="reports/old.html",
    )

    state.load_home = lambda: fake_load_home(state)

    reflex_app.AppState.load_investigation.fn(state)

    assert calls == ["load_home"]
    assert state.error_message == ""
    assert state.selected_entity_id == ""
    assert state.selected_entity_name == ""
    assert state.report_path == ""
    assert len(state.connection_rows_preview) == 6
    assert state.connection_rows_preview == state.connection_rows[:6]


def test_empty_state_helpers_render_without_error() -> None:
    assert reflex_app.search_empty_state() is not None
    assert reflex_app.investigation_empty_state() is not None


def test_load_dashboard_populates_summary_metrics(monkeypatch) -> None:
    state = SimpleNamespace(error_message="old")

    monkeypatch.setattr(
        reflex_app,
        "get_citizen_dashboard",
        lambda: {
            "title": "¿Dónde fue mi plata?",
            "summary": "Resumen demo.",
            "metrics": {
                "budget_total": 123,
                "budget_currency": "CLP",
                "contracts": 4,
                "suppliers": 5,
                "meetings": 6,
                "authorities": 7,
            },
            "budget_rows": [
                {
                    "organization_name": "Entidad demo",
                    "budget_entity_name": "Entidad demo",
                    "fiscal_year": 2026,
                    "approved_budget": 10,
                    "executed_budget": 8,
                    "purchase_orders": 2,
                    "suppliers": 1,
                    "currency": "CLP",
                }
            ],
            "featured_entities": [
                {
                    "organization_id": "11111111-1111-1111-1111-111111111111",
                    "organization_name": "Entidad demo",
                    "datasets": ["ChileCompra"],
                    "contracts": 1,
                    "lobby_meetings": 1,
                    "evidence": 2,
                    "relationships": 3,
                }
            ],
            "discovery_cases": [
                {
                    "id": "public_spending",
                    "title": "Demo",
                    "description": "Demo",
                    "concepts": ["Presupuesto"],
                    "suggested_sources": ["DIPRES"],
                    "search_query": "Entidad demo",
                    "example_query": "Entidad demo",
                    "cta": "Explorar",
                }
            ],
        },
    )

    reflex_app.AppState.load_dashboard.fn(state)

    assert state.dashboard_title == "¿Dónde fue mi plata?"
    assert state.dashboard_budget_total == 123
    assert state.dashboard_contracts == 4
    assert state.dashboard_featured_entities[0]["organization_name"] == "Entidad demo"
