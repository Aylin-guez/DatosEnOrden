from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _source(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_public_cards_do_not_render_decorative_asterisks() -> None:
    for relative in (
        "reflex_app/features/pulse/components.py",
        "reflex_app/features/search/components.py",
        "reflex_app/components/common/cards.py",
        "reflex_app/features/public_record/components.py",
    ):
        assert 'rx.text("*", class_name="source-card-icon")' not in _source(relative)


def test_public_components_do_not_stringify_reflex_conditional_state() -> None:
    """A conditional must choose components, never become text content itself."""
    for relative in (
        "reflex_app/components/common/cards.py",
        "reflex_app/components/common/indicators.py",
    ):
        source = _source(relative)
        assert "rx.text(rx.cond(" not in source
        assert "row_rx_state" not in source
        assert "LiteralObjectVar" not in source
        assert "ObjectVar" not in source


def test_guided_questions_execute_the_existing_search_route_without_a_second_click() -> None:
    source = _source("reflex_app/features/search/state.py")
    method = source[source.index("def explore_guided_question"):source.index("def select_guided_category")]
    assert "self.run_search()" in method
    assert "search-results" in method
    assert "return rx.redirect(_search_href(query))" not in method


def test_home_pulse_events_open_their_known_context_directly() -> None:
    source = _source("src/datosenorden/web/app_services.py")
    method = source[source.index("def _connector_pulse_events"):source.index("def _apply_connectors_to_tracking")]
    assert '"href": "/investigation?id=' in method
    assert '"href": "/search?' not in method


def test_public_record_never_keeps_a_previous_expedient_for_a_failed_new_target() -> None:
    source = _source("reflex_app/features/public_record/state.py")
    empty_response = source[source.index("if not _investigation_response_has_data(data)"):source.index("comparison =")]
    exception_path = source[source.index("except Exception as exc"):source.index("finally:")]
    assert "_clear_investigation_state(self)" in empty_response
    assert "preserved previous state" not in empty_response
    assert "_clear_investigation_state(self)" in exception_path


def test_expedient_question_has_a_shared_visual_hierarchy() -> None:
    components = _source("reflex_app/features/laboratory/components.py")
    styles = _source("reflex_app/app/styles.py")
    assert "expedient-question-panel" in components
    assert "expedient-question-panel" in styles


def test_document_fragments_are_below_the_reader_and_pdf_is_a_real_new_tab_resource() -> None:
    pages = _source("reflex_app/features/document_reading/pages.py")
    components = _source("reflex_app/features/document_reading/components.py")
    styles = _source("reflex_app/app/styles.py")
    assert pages.index("document-fragments-full-width") > pages.index("official-document-layout")
    assert 'is_external=True, target="_blank"' in components
    assert "document-fragments-full-width .fragment-nav-grid" in styles


def test_guided_result_replaces_the_initial_question_block_until_reset() -> None:
    pages = _source("reflex_app/features/search/pages.py")
    state = _source("reflex_app/features/search/state.py")
    assert "SearchState.guided_question_active" in pages
    assert "Explorar otra pregunta" in pages
    assert "def explore_another_question" in state
    assert "self.run_search()" in state


def test_collection_counts_and_human_labels_are_projection_backed() -> None:
    source = _source("reflex_app/features/search/state.py")
    assert "public_collection_counts(session)" in source
    assert '"count_text"' in source
    topic_source = _source("reflex_app/models/investigation.py")
    for key in ("organisms", "companies", "contracts"):
        assert f'"collection_key": "{key}"' in topic_source


def test_citizen_documents_use_exact_persisted_senate_urls() -> None:
    source = _source("src/datosenorden/application/legislative_ingestion/golden_expedient.py")
    assert "https://www.senado.cl/docto-" not in source
    assert "iddocto=16514&tipodoc=mensaje_mocion" in source
    assert "iddocto=36701&tipodoc=ofic" in source


def test_detail_views_have_contextual_back_navigation_and_epistemic_classes() -> None:
    laboratory = _source("reflex_app/features/laboratory/components.py")
    assert "window.history.back()" in laboratory
    for css_class in ("epistemic-fact", "epistemic-unknown", "epistemic-limitation", "epistemic-evidence", "epistemic-question"):
        assert css_class in laboratory or css_class in _source("reflex_app/app/styles.py")
    assert "window.history.back()" in _source("reflex_app/features/public_record/pages.py")
    assert "window.history.back()" in _source("reflex_app/features/document_reading/pages.py")


def test_public_copy_has_no_mojibake_markers() -> None:
    markers = tuple(map(chr, (0xC3, 0xC2, 0xE2, 0xF0, 0xFFFD)))
    public_roots = (ROOT / "reflex_app", ROOT / "src" / "datosenorden" / "application")
    allowed_detector = ROOT / "src" / "datosenorden" / "application" / "chilecompra_expedient" / "models.py"
    matches = [
        path for root in public_roots for path in root.rglob("*.py")
        if path != allowed_detector and any(marker in path.read_text(encoding="utf-8") for marker in markers)
    ]
    assert matches == []


def test_explore_uses_real_or_generic_guidance_instead_of_demo_fixture_copy() -> None:
    source = _source("src/datosenorden/application/public_explore.py")
    assert "public_collection(session" in source
    assert "Servicio de Salud Arauco" not in source
    assert '"example_authority"] = "REAL"' in source
    assert '"example_authority"] = "GENERIC"' in source


def test_sources_prioritizes_persisted_real_coverage_before_the_technical_catalog() -> None:
    source = _source("reflex_app/features/sources/pages.py")
    assert source.index('"Fuentes con datos incorporados"') < source.index('"Fuentes en desarrollo y catálogo técnico"')
    assert "SourcesState.public_sources" in source
    assert "metric(\"Conectores activos\", SourcesState.connector_active_count)" in source


def test_workspace_results_mark_demo_content_explicitly() -> None:
    source = _source("src/datosenorden/application/search/service.py")
    assert '"Contenido DEMO (separado de datos incorporados)"' in source
    assert '"classification": str(row.get("classification", "REAL"))' in source
