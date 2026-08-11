from __future__ import annotations

from dataclasses import dataclass
import inspect
import pickle
from types import MappingProxyType, SimpleNamespace

from datosenorden.application.document_reading import context as document_context
from datosenorden.application.search import service as search_service
from datosenorden.maintenance.safe_access import _field
from reflex_app.app import bootstrap as app_bootstrap
from reflex_app.app import not_found as not_found_page
from reflex_app.app import state as app_state
from reflex_app.constants import public as public_constants
from reflex_app.constants.routes import INVESTIGATION_STATUS_EMPTY, INVESTIGATION_STATUS_ERROR, INVESTIGATION_STATUS_LOADED
from reflex_app.features.dashboard import state as dashboard_state
from reflex_app.features.dashboard.state import DashboardState
from reflex_app.features.demo import pages as demo_pages
from reflex_app.features.demo import state as demo_state
from reflex_app.features.demo.state import DemoState
from reflex_app.features.document_reading import components as document_components
from reflex_app.features.document_reading import pages as document_pages
from reflex_app.features.document_reading import state as document_state
from reflex_app.features.document_reading.state import DocumentReadingState
from reflex_app.features.institutional import pages as institutional_pages
from reflex_app.features.public_record import components as public_record_components
from reflex_app.features.public_record import pages as public_record_pages
from reflex_app.features.public_record import state as public_record_state
from reflex_app.features.public_record import view_models as public_record_view_models
from reflex_app.features.public_record.state import PublicRecordState
from reflex_app.features.pulse import components as pulse_components
from reflex_app.features.pulse import pages as pulse_pages
from reflex_app.features.pulse import state as pulse_state
from reflex_app.features.pulse.state import PulseState
from reflex_app.features.reports import pages as reports_pages
from reflex_app.features.reports import state as reports_state
from reflex_app.features.reports.state import ReportsState
from reflex_app.features.search import components as search_components
from reflex_app.features.search import pages as search_pages
from reflex_app.features.search.state import SearchState
from reflex_app.features.sources import components as source_components
from reflex_app.features.sources import state as sources_state
from reflex_app.features.sources.state import SourcesState
from reflex_app.features.tracking import pages as tracking_pages
from reflex_app.features.tracking import state as tracking_state
from reflex_app.features.tracking.state import TrackingState
from reflex_app.helpers import routing
from reflex_app.layouts import shell as shell_layout
from reflex_app.models.document import PDFHighlightTarget
from reflex_app.navigation.config import PRIMARY_NAVIGATION_ITEMS
from reflex_app.serialization.json_safe import to_json_safe


@dataclass
class _Dumpable:
    name: str

    def model_dump(self) -> dict[str, str]:
        return {"name": self.name}


def test_safe_value_helpers_are_owned_by_leaf_modules() -> None:
    assert _field({"name": "dict-value"}, "name") == "dict-value"
    assert _field(SimpleNamespace(name="attr-value"), "name") == "attr-value"
    assert _field(_Dumpable("dump-value"), "name") == "dump-value"
    payload = MappingProxyType({"typed": _Dumpable("demo"), "values": (1, 2)})
    safe = to_json_safe(payload)
    assert safe == {"typed": {"name": "demo"}, "values": [1, 2]}
    pickle.dumps(safe)


def test_pulse_state_loads_the_public_preview_from_its_owner(monkeypatch) -> None:
    state = SimpleNamespace()
    monkeypatch.setattr(
        pulse_state,
        "get_dataset_summary",
        lambda: {"datasets": [{"name": "ChileCompra"}], "totals": {"datasets": 1, "active_datasets": 1, "claims": 2, "relationships": 3}},
    )
    monkeypatch.setattr(
        pulse_state,
        "get_cross_dataset_connections",
        lambda: [{"organization_name": "Entidad", "datasets": ["ChileCompra", "Lobby"]}],
    )
    monkeypatch.setattr(pulse_state, "get_demo_status", lambda: {"missing": [{"label": "Carga lista"}]})
    monkeypatch.setattr(pulse_state, "get_current_topics", lambda limit=3: [{"title": "Tema", "updated_at": "2026-04-12"}])

    result = PulseState.load_home.fn(state)

    assert result is not None
    assert state.connection_rows[0]["datasets_text"] == "ChileCompra | Lobby"
    assert state.current_topic_rows[0]["updated_at"] == "12-04-2026"
    assert state.demo_missing == ["Carga lista"]
    assert (state.total_datasets, state.active_datasets, state.total_claims, state.total_relationships) == (1, 1, 2, 3)
    source = inspect.getsource(PulseState.load_home.fn)
    assert "AppState.clear_global_error" in source
    assert "AppState.set_global_error" in source


def test_demo_state_owns_its_readiness_check(monkeypatch) -> None:
    state = SimpleNamespace()
    monkeypatch.setattr(demo_state, "get_dataset_summary", lambda: {"totals": {"datasets": 2, "source_records": 5}})
    monkeypatch.setattr(demo_state, "get_investigation", lambda target: {"found": True, "compact_metrics": {"evidence_count": 2}})
    monkeypatch.setattr(demo_state, "resolve_investigation_target", lambda target: {"entity_id": "entity-demo"})
    monkeypatch.setattr(demo_state, "export_investigation_report", lambda entity_id: "reports/demo.html")

    result = DemoState.load_demo.fn(state)

    assert result is not None
    assert state.demo_sources_ready is True
    assert state.demo_investigation_ready is True
    assert state.demo_report_ready is True
    assert not hasattr(state, "demo_report_path")


def test_app_state_remains_the_transversal_shell_search_adapter() -> None:
    state = SimpleNamespace(header_search_open=True, header_search_query="", sidebar_collapsed=True)
    assert app_state.AppState.submit_header_search.fn(state) is None
    assert state.header_search_open is False
    state.header_search_query = "servicio salud"
    event = app_state.AppState.submit_header_search.fn(state)
    assert event is not None
    assert state.header_search_query == ""
    app_state.AppState.toggle_sidebar.fn(state)
    assert state.sidebar_collapsed is False
    source = inspect.getsource(app_state.AppState.submit_header_search.fn)
    assert "_search_href" in source
    assert "return None" in source


def test_moved_root_demo_and_not_found_pages_have_direct_owners() -> None:
    home_source = inspect.getsource(pulse_pages.home)
    demo_source = inspect.getsource(demo_pages.demo)
    not_found_source = inspect.getsource(not_found_page.not_found)

    assert 'route="/"' in home_source
    assert "PulseState.load_home" in home_source
    assert "home_pulse_card" in home_source
    assert "DatosEnOrden Ciudadano" in home_source
    assert 'route="/demo"' in demo_source
    assert "DemoState.load_demo" in demo_source
    assert "Recorrido guiado" in demo_source
    assert 'route="404"' in not_found_source
    assert "not_found_document_illustration" in not_found_source
    assert 'rx.redirect("/search")' in not_found_source
    assert "current_topic_card" not in home_source
    assert "row" in inspect.getsource(pulse_components.home_pulse_card)


def test_declared_navigation_and_routing_helpers_keep_public_urls_stable() -> None:
    assert [(item.label, item.href) for item in PRIMARY_NAVIGATION_ITEMS] == [
        ("Inicio", "/"),
        ("Explorar", "/search"),
        ("Fuentes", "/sources"),
        ("Laboratorio", "/laboratory"),
        ("Acerca de", "/project"),
    ]
    router = SimpleNamespace(url=SimpleNamespace(query_parameters={}, raw_path="/investigation?id=SERVICIO+DE+SALUD"))
    assert routing._router_query_value(router, "id") == "SERVICIO DE SALUD"
    assert routing._investigation_href("SERVICIO DE SALUD ARAUCO") == "/investigation?id=SERVICIO+DE+SALUD+ARAUCO"
    assert routing._search_href("salud publica") == "/search?q=salud+publica"
    assert "toggle_header_search" in inspect.getsource(shell_layout.shell)
    assert "sidebar_nav_item(item, active_page)" in inspect.getsource(shell_layout.app_sidebar)


def _investigation_state(query: str) -> SimpleNamespace:
    return SimpleNamespace(
        error_message="",
        selected_entity_id="",
        selected_entity_name="",
        entity_name="",
        entity_summary="",
        evidence_count=0,
        relationship_count=0,
        datasets_involved=0,
        connected_entities=0,
        last_loaded_investigation_target="",
        last_valid_investigation_target="",
        requested_investigation_target="",
        investigation_loaded=False,
        investigation_loading=False,
        router=SimpleNamespace(url=SimpleNamespace(query_parameters={"id": query}, raw_path=f"/investigation?id={query}")),
    )


def _patch_public_record_services(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(
        public_record_state,
        "resolve_investigation_target",
        lambda value: {"found": True, "entity_id": "entity-demo", "entity_name": "Entidad demo"},
    )
    monkeypatch.setattr(
        public_record_state,
        "get_investigation",
        lambda entity_id: {
            "found": True,
            "entity": {"name": "Entidad demo"},
            "narrative_summary": "Resumen demo.",
            "dataset_badges": ["ChileCompra", "DIPRES"],
            "key_metrics": {"contracts": 1, "suppliers": 1, "lobby_meetings": 1, "evidence": 2, "relationships": 3},
            "compact_metrics": {"datasets_involved": 2, "evidence_count": 2, "relationship_count": 3, "connected_entities": 1},
            "connections": {"summary": "Conexion demo.", "relationship_cards": []},
            "contracts_compras": [],
            "lobby": [],
            "transparencia": [],
            "registro_empresas": [],
            "timeline": [],
            "evidence": [],
            "neutral_explanation": "Neutral.",
            "knowledge": {"citizen_summary": "Resumen ciudadano.", "key_points": [], "suggested_questions": [], "limitations": []},
        },
    )
    monkeypatch.setattr(public_record_state, "get_entity_comparison", lambda entity_id: {"coverage_summary": "", "overlap_areas": [], "dataset_contributions": []})
    monkeypatch.setattr(public_record_state, "get_source_trace", lambda entity_id: {"sources": [], "overlap_summary": "", "neutrality_notice": ""})
    monkeypatch.setattr(public_record_state, "get_investigation_story", lambda entity_id: {"headline": "Historia", "summary": "Resumen", "key_findings": [], "important_connections": [], "timeline_highlights": [], "questions_for_citizens": []})
    monkeypatch.setattr(public_record_state, "get_investigation_graph", lambda entity_id: {"summary": "", "nodes": []})
    monkeypatch.setattr(public_record_state, "get_investigation_timeline", lambda entity_id: {"years": []})
    monkeypatch.setattr(public_record_state, "get_source_contributions", lambda entity_id: {"sources": []})
    monkeypatch.setattr(public_record_state, "export_investigation_report", lambda entity_id: "reports/demo.html")
    monkeypatch.setattr(public_record_state, "build_state_graph", lambda entity_id: SimpleNamespace(to_dict=lambda: {}))


def test_public_record_state_handles_empty_success_and_failure_states(monkeypatch) -> None:
    empty = _investigation_state("")
    PublicRecordState.load_investigation.fn(empty)
    assert empty.investigation_status == INVESTIGATION_STATUS_EMPTY

    _patch_public_record_services(monkeypatch)
    loaded = _investigation_state("Entidad demo")
    PublicRecordState.load_investigation.fn(loaded)
    assert loaded.selected_entity_id == "entity-demo"
    assert loaded.entity_name == "Entidad demo"
    assert (loaded.evidence_count, loaded.relationship_count, loaded.datasets_involved) == (2, 3, 2)
    assert loaded.investigation_status == INVESTIGATION_STATUS_LOADED
    assert loaded.citizen_summary == "Resumen ciudadano."

    failed = _investigation_state("Entidad demo")
    monkeypatch.setattr(public_record_state, "get_investigation", lambda entity_id: (_ for _ in ()).throw(RuntimeError("backend down")))
    PublicRecordState.load_investigation.fn(failed)
    assert failed.investigation_loading is False
    assert failed.investigation_status == INVESTIGATION_STATUS_ERROR
    assert failed.investigation_status_message == public_record_view_models._public_error_message("abrir el expediente")


def test_public_record_page_uses_error_loading_and_empty_components_in_order() -> None:
    page_source = inspect.getsource(public_record_pages.investigation)
    empty_source = inspect.getsource(public_record_components.investigation_empty_state)
    error_source = inspect.getsource(public_record_components.investigation_error_state)

    assert 'route="/investigation"' in page_source
    assert page_source.index("investigation_error_state()") < page_source.index("investigation_loading_state()")
    assert page_source.index("investigation_loading_state()") < page_source.index("investigation_empty_state()")
    assert "_investigation_href(DEMO_INVESTIGATION_TARGET)" in empty_source
    assert "Reintentar" in error_source


def test_tracking_and_reports_states_keep_their_feature_data(monkeypatch) -> None:
    tracking = SimpleNamespace()
    monkeypatch.setattr(tracking_state, "get_tracking_items", lambda: [{"id": "tracking-demo"}])
    monkeypatch.setattr(
        tracking_state,
        "get_tracking_demo",
        lambda: {
            "item": {"title": "Seguimiento demo", "summary": "Resumen", "current_status": "published", "related_expediente_target": "Entidad demo", "related_sources": ["DIPRES"]},
            "events": [{"title": "Evento"}],
            "documents": [],
            "evidence": [],
            "follow_targets": [],
        },
    )
    TrackingState.load_tracking.fn(tracking)
    assert tracking.tracking_title == "Seguimiento demo"
    assert tracking.tracking_events[0]["title"] == "Evento"

    reports = SimpleNamespace()
    monkeypatch.setattr(reports_state, "get_citizen_reports", lambda: [{"id": "report-demo"}])
    monkeypatch.setattr(
        reports_state,
        "get_citizen_report_demo",
        lambda: {"title": "Reporte demo", "subject": "Entidad demo", "summary": "Resumen", "sources": ["ChileCompra"], "sections": [{"evidence_refs": ["ev1"]}], "evidence_refs": ["ev1"]},
    )
    monkeypatch.setattr(reports_state, "export_citizen_report_demo", lambda: "reports/demo.html")
    ReportsState.load_reports.fn(reports)
    assert reports.citizen_report_title == "Reporte demo"
    assert reports.citizen_report_sections[0]["evidence_text"] == "ev1"
    assert 'route="/chronology"' in inspect.getsource(tracking_pages.chronology)
    assert "Sin informe seleccionado" in inspect.getsource(reports_pages.reports)


def test_dashboard_and_sources_states_format_public_view_models(monkeypatch) -> None:
    dashboard = SimpleNamespace()
    monkeypatch.setattr(
        dashboard_state,
        "get_citizen_dashboard",
        lambda: {
            "title": "Presupuesto",
            "summary": "Resumen",
            "metrics": {"budget_total": 123, "budget_currency": "CLP"},
            "budget_rows": [{"fiscal_year": 2026}],
            "featured_entities": [{"datasets": ["ChileCompra"]}],
            "discovery_cases": [{"id": "public_spending", "concepts": ["Presupuesto"], "suggested_sources": ["DIPRES"], "search_query": "Entidad demo"}],
        },
    )
    DashboardState.load_dashboard.fn(dashboard)
    assert dashboard.dashboard_budget_total == 123
    assert dashboard.dashboard_featured_entities[0]["datasets_text"] == "ChileCompra"
    assert dashboard.dashboard_discovery_cases[0]["search_href"] == "/search?q=Entidad+demo"

    sources = SimpleNamespace()
    monkeypatch.setattr(
        sources_state,
        "get_data_ecosystem",
        lambda: {
            "sources": [{"status": "active", "concepts": [], "relationships": [], "connects_with": [], "entities": [], "population_records": 2, "population_status_label": "visible", "population_summary": "Demo", "connector_status": "ready", "connector_entities": 2, "connector_relationships": 3, "connector_events": 1}],
            "concepts": [],
            "roadmap": [],
        },
    )
    monkeypatch.setattr(sources_state, "get_real_data_readiness", lambda: {"entries": [], "totals": {"ready": 1}})
    SourcesState.load_ecosystem.fn(sources)
    assert sources.ecosystem_active_count == 1
    assert "connector: ready" in sources.ecosystem_sources[0]["connector_label"]
    assert "StateGraph" in sources.ecosystem_sources[0]["state_graph_contribution_label"]
    source_card = inspect.getsource(source_components.ecosystem_source_card)
    assert "population_label" in source_card
    assert "connector_label" in source_card


def test_search_feature_exposes_guided_entry_and_state_graph_badges() -> None:
    assert "SearchState.load_discover" in inspect.getsource(search_pages.discover)
    assert "guided_discovery_panel" in inspect.getsource(search_pages._search_view)
    assert "state_graph_badges_text" in inspect.getsource(search_components.workspace_match_card)
    assert "run_workspace_search" in inspect.getsource(SearchState.run_search.fn)
    assert search_service.state_graph_badges_for_match(
        {"datasets": ["ChileCompra", "InfoLobby"], "entity_type": "Organismo", "relationship_count": 1, "evidence_count": 1}
    ) == "Conexiones disponibles: compras | reuniones | eventos"


def test_document_reader_components_and_state_keep_pdf_fallback_behavior() -> None:
    assert 'route="/topic"' in inspect.getsource(document_pages.topic)
    assert 'route="/official-document"' in inspect.getsource(document_pages.official_document)
    assert "topic_mode_selector" in inspect.getsource(document_pages.topic)
    assert "official_document_pdf_viewer" in inspect.getsource(document_pages.official_document)
    assert "topic_pdf_document_viewer" in inspect.getsource(document_components.topic_source_panel)
    assert "document-current-anchor" in inspect.getsource(document_components.official_document_viewer)
    assert 'loading="lazy"' in inspect.getsource(document_components.official_document_pdf_viewer)

    state = SimpleNamespace(
        knowledge_selected_page=1,
        knowledge_selected_fragment_id="frag-a",
        knowledge_selected_reference_label="",
        knowledge_selected_excerpt="",
        knowledge_selected_summary=[],
        knowledge_selected_questions=[],
        knowledge_selected_claims=[],
        knowledge_selected_evidence=[],
        knowledge_selected_connections=[],
        knowledge_fragment_contexts=[{"fragment_id": "frag-a", "order": 1, "excerpt": "A"}, {"fragment_id": "frag-b", "order": 5, "excerpt": "B"}],
        knowledge_document_has_pdf=True,
        knowledge_document_pdf_page_href="",
        knowledge_pdf_highlight_target={},
        knowledge_selected_page_is_approximate=False,
        knowledge_pdf_location_notice="",
    )
    DocumentReadingState.select_document_anchor.fn(state, 0, "frag-b")
    assert state.knowledge_selected_page == 5
    assert state.knowledge_selected_page_is_approximate is True
    assert state.knowledge_pdf_location_notice == document_context.PDF_LOCATION_APPROXIMATE_NOTICE
    assert state.knowledge_pdf_highlight_target["coordinates"] is None


def test_document_context_uses_published_paths_without_invented_coordinates() -> None:
    assert document_state.PUBLISHED_DOCUMENT_VIEW_PATH.as_posix().endswith("document_view.json")
    assert document_state.PUBLISHED_DOCUMENT_PDF_PATH.as_posix().endswith("document.pdf")
    assert document_context.document_pdf_href(document_state.PUBLISHED_DOCUMENT_PDF_PUBLIC_HREF, 19).endswith("document.pdf#page=19")
    assert document_context.pdf_highlight_target("frag-7", 3, "Texto citado")["coordinates"] is None
    assert PDFHighlightTarget("frag-7", 3, "Texto citado").coordinates is None


def test_institutional_state_graph_and_bootstrap_owners_remain_explicit() -> None:
    assert 'route="/project"' in inspect.getsource(institutional_pages.project)
    assert 'route="/studio"' in inspect.getsource(institutional_pages.studio)
    assert 'route="/support"' in inspect.getsource(institutional_pages.support)
    assert "SUPPORT_SOURCE_SUGGESTION_URL" in inspect.getsource(shell_layout.app_footer)
    assert public_constants.SUPPORT_DONATION_URL == "https://link.mercadopago.cl/datosenorden"

    graph = {
        "entity_id": "organismo:arauco",
        "nodes": [{"id": "organismo:arauco", "label": "Servicio", "node_type": "Organismo"}, {"id": "empresa:demo", "label": "Proveedor", "node_type": "Empresa"}],
        "edges": [{"source": "empresa:demo", "target": "organismo:arauco", "edge_type": "COMPANY_APPEARS_IN_PURCHASES", "source_connector": "ChileCompra", "confidence": 0.82, "evidence": [{"title": "Orden"}]}],
    }
    row = public_record_view_models._format_state_graph_connection_rows(graph)[0]
    assert row["relation_type"] == "aparece en compras"
    assert row["confidence_label"] == "confianza 82%"
    assert "sospechoso" not in " ".join(str(value).lower() for value in row.values())
    assert "html_lang" in inspect.getsource(app_bootstrap)
    assert "public_hydrate_fallback" in inspect.getsource(app_bootstrap)
