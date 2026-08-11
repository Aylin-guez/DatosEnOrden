from __future__ import annotations

import inspect
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from reflex.page import DECORATED_PAGES

from reflex_app.app import state as app_state
from reflex_app.app.state import AppState
from reflex_app.features.document_reading.state import DocumentReadingState
from datosenorden.application.search import service as search_service
from reflex_app.features.search import pages as search_pages
from reflex_app.features.search.state import SearchState


SEARCH_FIELDS = {
    "query",
    "results",
    "workspace_matches",
    "guided_search_title",
    "guided_question_rows",
    "guided_category_rows",
    "selected_guided_category_id",
    "selected_guided_category_title",
    "selected_guided_category_description",
    "selected_guided_category_examples",
    "selected_guided_category_sources",
    "selected_guided_category_query",
    "selected_guided_category_cta",
    "selected_guided_category_href",
    "selected_guided_category_path",
    "guided_option_rows",
    "search_error",
}


def _routes() -> dict[str, object]:
    return {kwargs["route"]: page for page, kwargs in DECORATED_PAGES["reflex_app"]}


def test_search_routes_are_registered_once_from_feature() -> None:
    routes = _routes()

    assert len(routes) == 21
    assert routes["/search"] is search_pages.search
    assert routes["/discover"] is search_pages.discover
    assert (Path(__file__).resolve().parents[1] / "reflex_app" / "reflex_app.py").read_text(encoding="utf-8").count('route="/search"') == 0
    assert (Path(__file__).resolve().parents[1] / "reflex_app" / "reflex_app.py").read_text(encoding="utf-8").count('route="/discover"') == 0


def test_search_state_owns_defaults_and_appstate_does_not_duplicate_fields() -> None:
    for field in SEARCH_FIELDS:
        assert field in SearchState.vars
        assert field not in AppState.vars

    annotations = SearchState.__annotations__
    assert annotations["query"] == "str"
    assert annotations["results"] == "list[dict]"
    assert annotations["selected_guided_category_href"] == "str"
    assert annotations["search_error"] == "str"
    assert inspect.getsource(SearchState).count('selected_guided_category_href: str = "/search"') == 1


def test_search_events_and_results_preserve_service_shape(monkeypatch) -> None:
    workspace = Mock(
        return_value={
            "matches": [
                {
                    "id": "result-1",
                    "entity_id": "entity-1",
                    "entity_name": "Entidad",
                    "canonical_entity_id": "canonical-1",
                    "canonical_entity_name": "Entidad canonica",
                    "datasets": ["ChileCompra", "InfoLobby"],
                    "relationship_count": 1,
                    "evidence_count": 2,
                }
            ]
        }
    )
    state = SimpleNamespace(query="", guided_search_title="stale", search_error="")

    monkeypatch.setattr(search_service, "search_workspace", workspace)

    SearchState.set_query.fn(state, "Entidad")
    SearchState.run_search.fn(state)

    workspace.assert_called_once_with("Entidad")
    assert state.search_error == ""
    assert state.results == state.workspace_matches
    assert state.results[0]["canonical_entity_id"] == "canonical-1"
    assert state.results[0]["canonical_investigation_href"] == "/investigation?id=canonical-1"
    assert state.results[0]["state_graph_badges_text"] == "Conexiones disponibles: compras | reuniones | eventos"


def test_guided_filters_loading_and_error_state(monkeypatch) -> None:
    monkeypatch.setattr(
        search_service,
        "get_guided_questions",
        Mock(
            return_value={
                "questions": [{"id": "q1", "title": "Pregunta", "description": "Demo", "concepts": [], "suggested_sources": [], "example_query": "Entidad", "search_query": "Entidad"}],
                "categories": [{"id": "cat1", "title": "Categoria", "description": "Demo", "examples": ["Entidad"], "suggested_sources": ["ChileCompra"], "search_query": "Entidad", "cta": "Buscar"}],
            }
        ),
    )
    monkeypatch.setattr(search_service, "get_guided_discovery_options", Mock(return_value=[]))
    state = SimpleNamespace(
        search_error="",
        guided_category_rows=[],
        guided_question_rows=[],
        selected_guided_category_id="",
        _load_guided_rows=lambda: None,
        _select_category_row=lambda row: None,
    )

    def load_guided_rows() -> None:
        state.guided_question_rows = search_service.build_guided_questions()
        state.guided_category_rows = search_service.build_guided_categories()

    def select_category_row(row: dict) -> None:
        state.selected_guided_category_id = str(row.get("id", ""))
        state.selected_guided_category_href = str(row.get("search_href", "/search"))

    state._load_guided_rows = load_guided_rows
    state._select_category_row = select_category_row

    SearchState.load_discover.fn(state)

    assert state.search_error == ""
    assert state.guided_question_rows[0]["search_href"] == "/search?q=Entidad"
    assert state.guided_category_rows[0]["id"] == "cat1"
    assert state.selected_guided_category_id == "cat1"
    assert state.selected_guided_category_href == "/search?q=Entidad"


def test_header_search_adapter_redirects_without_owning_search_state(monkeypatch) -> None:
    redirect = Mock(return_value="redirect-event")
    state = SimpleNamespace(header_search_open=True, header_search_query="Entidad")

    monkeypatch.setattr(app_state.rx, "redirect", redirect)

    assert AppState.submit_header_search.fn(state) == "redirect-event"
    redirect.assert_called_once_with("/search?q=Entidad")
    assert state.header_search_open is False
    assert state.header_search_query == ""
    assert "query" not in AppState.vars


def test_search_boundaries_do_not_touch_public_record_document_reading_or_laboratory() -> None:
    assert hasattr(DocumentReadingState, "load_knowledge")
    assert hasattr(DocumentReadingState, "load_topic")
    assert not hasattr(AppState, "load_knowledge")
    assert not hasattr(AppState, "load_topic")
    assert not hasattr(AppState, "load_investigation")

    laboratory_root = Path("reflex_app/features/laboratory")
    laboratory_source = "\n".join(path.read_text(encoding="utf-8") for path in laboratory_root.glob("*.py"))
    assert "reflex_app.features.search" not in laboratory_source
    assert "deo_core" not in laboratory_source

    for path in Path("reflex_app/features/search").glob("*.py"):
        source = path.read_text(encoding="utf-8")
        assert "reflex_app.reflex_app import AppState" not in source
        assert "datosenorden.core" not in source


def test_reflex_compile_dry_run_after_search_extraction() -> None:
    result = subprocess.run(
        [sys.executable, "-B", "-m", "reflex", "compile", "--dry", "--no-rich"],
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
