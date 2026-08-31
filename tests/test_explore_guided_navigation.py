from __future__ import annotations

from types import SimpleNamespace

from datosenorden.application.search import service
from reflex_app.features.search import state as search_state
from reflex_app.features.search.state import SearchState


def _row(name: str, href: str, *, classification: str = "REAL") -> dict:
    return {
        "entity_id": name,
        "entity_name": name,
        "entity_type": "Expediente público" if href.startswith("/laboratory/") else "Empresa",
        "entity_type_label": "Expediente público" if href.startswith("/laboratory/") else "Empresa",
        "datasets": ["ChileCompra"],
        "datasets_text": "ChileCompra",
        "evidence_count": 1,
        "relationship_count": 1,
        "action_href": href,
        "action_label": "Abrir expediente" if href.startswith("/laboratory/") else "Ver información disponible",
        "canonical_investigation_href": "/investigation?id=entity" if not href.startswith("/laboratory/") else "/investigation",
        "classification": classification,
        "guidance_eligible": href.startswith("/laboratory/"),
        "source_hint": "Registros públicos vinculados",
        "related_label": "",
        "is_record": False,
        "state_graph_badges_text": "",
        "match_reason": "Coincide con registros públicos incorporados.",
        "coverage_summary": "Cobertura local disponible.",
        "source_contribution": "Fuentes que contribuyen: ChileCompra",
    }


def test_guided_journey_supports_zero_one_and_multiple_direct_expedients(monkeypatch) -> None:
    monkeypatch.setattr(service, "run_workspace_search", lambda query: [])
    empty = service.build_guided_journey("q", "Pregunta", "Descripción", "consulta")
    assert empty["status"] == "EMPTY"
    assert empty["expedient_rows"] == []
    assert empty["result_limit"] == 12
    assert empty["filters_available"] == []
    assert empty["sort_options"] == ["relevancia"]

    monkeypatch.setattr(service, "run_workspace_search", lambda query: [_row("Lectura", "/laboratory/expedient?id=EXP-1")])
    one = service.build_guided_journey("q", "Pregunta", "Descripción", "consulta")
    assert one["status"] == "ONE_EXPEDIENT"
    assert one["result_count"] == 0
    assert [row["action_href"] for row in one["expedient_rows"]] == ["/laboratory/expedient?id=EXP-1"]

    monkeypatch.setattr(
        service,
        "run_workspace_search",
        lambda query: [
            _row("Proveedor", "/investigation?id=provider"),
            _row("Lectura uno", "/laboratory/expedient?id=EXP-1"),
            _row("Lectura dos", "/laboratory/expedient?id=EXP-2"),
        ],
    )
    multiple = service.build_guided_journey("q", "Pregunta", "Descripción", "consulta")
    assert multiple["status"] == "MULTIPLE_RESULTS"
    assert len(multiple["entity_rows"]) == 1
    assert [row["action_href"] for row in multiple["expedient_rows"]] == [
        "/laboratory/expedient?id=EXP-1",
        "/laboratory/expedient?id=EXP-2",
    ]


def test_guided_question_does_not_overwrite_manual_query_or_require_second_search(monkeypatch) -> None:
    redirect = object()
    monkeypatch.setattr(search_state.rx, "redirect", lambda href: (redirect, href))
    state = SimpleNamespace(
        query="consulta manual",
    )

    result = SearchState.explore_guided_question.fn(state, "q", "Pregunta", "Descripción", "LATAM")

    assert state.query == "consulta manual"
    assert result == (redirect, "/search?guided=q&q=consulta+manual")


def test_guided_href_is_deterministic_for_history_refresh_and_manual_query() -> None:
    assert search_state._guided_href("which_suppliers_appear") == "/search?guided=which_suppliers_appear"
    assert search_state._guided_href("which_suppliers_appear", "consulta manual") == "/search?guided=which_suppliers_appear&q=consulta+manual"


def test_manual_search_submission_has_a_deterministic_result_mode_url(monkeypatch) -> None:
    redirect = object()
    monkeypatch.setattr(search_state.rx, "redirect", lambda href: (redirect, href))
    state = SimpleNamespace(query=" Ley 21.719 ")

    result = SearchState.submit_main_search.fn(state)

    assert state.query == "Ley 21.719"
    assert result == (redirect, "/search?q=Ley+21.719")


def test_guided_questions_exclude_contextual_questions_from_explore_landing(monkeypatch) -> None:
    from datosenorden.application import public_explore

    rows = {
        "companies": {"items": [{"title": "Empresa real"}]},
        "organisms": {"items": [{"title": "Organismo real"}]},
    }
    monkeypatch.setattr(public_explore, "public_collection", lambda _session, key: rows.get(key, {"items": []}))

    questions = public_explore.public_guided_questions(object())

    assert all(row["interaction_type"] != "CONTEXTUAL" for row in questions)
    assert all(row["id"] != "who_sells_to_this_body" for row in questions)


def test_guided_supplier_result_preserves_the_question_intent(monkeypatch) -> None:
    supplier = _row("Proveedor real", "/investigation?id=provider")
    supplier["entity_type"] = "COMPANY"
    supplier["entity_type_label"] = "Proveedor"
    monkeypatch.setattr(
        service,
        "run_workspace_search",
        lambda query: [
            supplier,
            _row("Lectura", "/laboratory/expedient?id=EXP-1"),
        ],
    )

    journey = service.build_guided_journey("which_suppliers_appear", "¿Qué proveedores aparecen?", "", "proveedor")

    assert journey["result_type_labels"] == ["Proveedor"]
    assert journey["entity_rows"][0]["entity_type_label"] == "Proveedor"


def test_result_view_contract_keeps_landing_and_results_separate() -> None:
    from pathlib import Path

    source = Path("reflex_app/features/search/pages.py").read_text(encoding="utf-8")
    assert "SearchState.manual_result_active" in source
    assert "manual_result_view()" in source
    assert "SearchState.guided_question_active" in source
    assert "SearchState.return_to_explore" in source


def test_public_undefined_state_is_normalized_and_never_rendered() -> None:
    row = service.format_workspace_matches(
        {
            "matches": [
                {
                    "entity_id": "entity",
                    "entity_name": "Entidad",
                    "entity_type": "COMPANY",
                    "datasets": ["ChileCompra"],
                    "evidence_count": "undefined",
                    "relationship_count": None,
                }
            ]
        }
    )[0]

    assert row["evidence_count"] == 0
    assert row["relationship_count"] == 0
    assert row["evidence_label"] == ""
    assert row["relationship_label"] == ""
    assert "undefined" not in " ".join(str(value) for value in row.values())


def test_search_surface_has_landing_navigation_and_responsive_result_contract() -> None:
    from pathlib import Path

    page_source = Path("reflex_app/features/search/pages.py").read_text(encoding="utf-8")
    style_source = Path("reflex_app/app/styles.py").read_text(encoding="utf-8")

    assert "← Volver al Inicio" in page_source
    assert "search-results-grid" in page_source
    assert '"@media (max-width: 640px)"' in style_source
    assert '".search-results-grid"' in style_source


def test_footer_and_scroll_controls_have_single_public_identity_contract() -> None:
    from pathlib import Path

    shell_source = Path("reflex_app/layouts/shell.py").read_text(encoding="utf-8")
    scroll_source = Path("reflex_app/layouts/shell_controls.py").read_text(encoding="utf-8")

    assert shell_source.count('"DATOSENORDEN STUDIO"') == 1
    assert '"Conocer Studio"' in shell_source
    assert "data-deo-scroll-top" in scroll_source
    assert "querySelectorAll" in scroll_source


def test_workspace_projection_rejects_internal_object_representations() -> None:
    class InternalOnly:
        def __repr__(self) -> str:
            return "{raw_state: Entity(type='COMPANY')}"

    row = service.format_workspace_matches(
        {
            "matches": [
                {
                    "entity_id": InternalOnly(),
                    "entity_name": InternalOnly(),
                    "entity_type": InternalOnly(),
                    "datasets": [],
                    "evidence_count": 0,
                    "relationship_count": 0,
                    "why_it_appears": InternalOnly(),
                }
            ]
        }
    )[0]

    public_text = " ".join(str(value) for value in row.values())
    assert "raw_state" not in public_text
    assert "Entity(" not in public_text
    assert row["entity_name"] == "Información pública disponible"


def test_guided_panel_uses_projection_fields_not_object_stringification() -> None:
    from pathlib import Path

    text = Path("reflex_app/features/search/components.py").read_text(encoding="utf-8")
    card = text[text.index("def workspace_match_card"):text.index("def guided_journey_expedient_card")]
    assert "row.get(" not in card
    assert "row[\"entity_name\"]" in card
