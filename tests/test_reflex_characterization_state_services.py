from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import Mock

from reflex_app.app.state import AppState
from reflex_app.constants.demo import DEMO_INVESTIGATION_TARGET
from reflex_app.constants.routes import INVESTIGATION_STATUS_ERROR, INVESTIGATION_STATUS_LOADED
from reflex_app.features.public_record import state as public_record_state
from reflex_app.features.public_record.state import PublicRecordState
from datosenorden.application.document_reading import service as document_reading_service
from datosenorden.application.search import service as search_service
from reflex_app.features.dashboard import state as dashboard_state
from reflex_app.features.demo import state as demo_state
from reflex_app.features.demo.state import DemoState
from reflex_app.features.dashboard.state import DashboardState
from reflex_app.features.document_reading.state import DocumentReadingState
from reflex_app.features.reports import state as reports_state
from reflex_app.features.reports.state import ReportsState
from reflex_app.features.search.state import SearchState
from reflex_app.features.pulse import state as pulse_state
from reflex_app.features.pulse.state import PulseState
from reflex_app.serialization.json_safe import to_json_safe
from reflex_app.features.sources import state as sources_state
from reflex_app.features.sources.state import SourcesState
from reflex_app.features.tracking import state as tracking_state
from reflex_app.features.tracking.state import TrackingState


PUBLIC_STATE_HANDLERS = {
    "toggle_header_search",
    "toggle_sidebar",
    "set_header_search_query",
    "submit_header_search",
}

DOCUMENT_READING_HANDLERS = {
    "set_topic_view_mode",
    "load_knowledge",
    "load_topic",
    "open_knowledge_investigation",
    "select_document_anchor",
}


class _Graph:
    def __init__(self, payload: dict | None = None) -> None:
        self._payload = payload or {"summary": {}, "nodes": [], "edges": []}

    def to_dict(self) -> dict:
        return self._payload


def _assert_json_safe(payload: object) -> None:
    json.dumps(to_json_safe(payload))


def _investigation_state(target: str) -> SimpleNamespace:
    return SimpleNamespace(
        error_message="",
        selected_entity_id="",
        selected_entity_name="",
        entity_name="",
        entity_summary="",
        dataset_badges=[],
        contracts=0,
        suppliers=0,
        lobby_meetings=0,
        evidence_count=0,
        relationship_count=0,
        datasets_involved=0,
        connected_entities=0,
        last_loaded_investigation_target="",
        last_valid_investigation_target="",
        requested_investigation_target="",
        investigation_loaded=False,
        investigation_loading=False,
        router=SimpleNamespace(
            url=SimpleNamespace(
                query_parameters={"id": target},
                raw_path=f"/investigation?id={target}",
            )
        ),
    )


def _investigation_payload() -> dict:
    return {
        "found": True,
        "entity": {"name": "Entidad de prueba"},
        "narrative_summary": "Resumen de prueba.",
        "summary": "Resumen de prueba.",
        "dataset_badges": ["ChileCompra"],
        "key_metrics": {
            "contracts": 1,
            "suppliers": 1,
            "lobby_meetings": 0,
            "evidence": 2,
            "relationships": 1,
        },
        "compact_metrics": {
            "datasets_involved": 1,
            "evidence_count": 2,
            "relationship_count": 1,
            "connected_entities": 1,
        },
        "connections": {"summary": "Conexión documentada.", "relationship_cards": []},
        "contracts_compras": [],
        "lobby": [],
        "transparencia": [],
        "registro_empresas": [],
        "timeline": [],
        "evidence": [],
        "neutral_explanation": "Lectura neutral.",
    }


def test_public_appstate_handlers_are_limited_to_transversal_shell_and_error_work() -> None:
    registered_handlers = AppState.event_handlers

    assert PUBLIC_STATE_HANDLERS <= set(registered_handlers)
    assert all(callable(registered_handlers[name].fn) for name in PUBLIC_STATE_HANDLERS)
    assert not {"load_home", "load_demo", "toggle_advanced_nav"} & set(registered_handlers)

def test_document_reading_handlers_live_in_feature_state() -> None:
    registered_handlers = DocumentReadingState.event_handlers

    assert DOCUMENT_READING_HANDLERS <= set(registered_handlers)
    assert DOCUMENT_READING_HANDLERS.isdisjoint(AppState.event_handlers)
    assert all(callable(registered_handlers[name].fn) for name in DOCUMENT_READING_HANDLERS)

def test_load_home_calls_current_service_boundary_and_produces_json_safe_view_data(monkeypatch) -> None:
    summary = Mock(
        return_value={
            "datasets": [{"name": "ChileCompra"}],
            "totals": {
                "datasets": 1,
                "active_datasets": 1,
                "claims": 2,
                "relationships": 3,
            },
        }
    )
    connections = Mock(return_value=[])
    current_topics = Mock(return_value=[])
    demo_status = Mock(return_value={"missing": []})
    state = SimpleNamespace()

    monkeypatch.setattr(pulse_state, "get_dataset_summary", summary)
    monkeypatch.setattr(pulse_state, "get_cross_dataset_connections", connections)
    monkeypatch.setattr(pulse_state, "get_current_topics", current_topics)
    monkeypatch.setattr(pulse_state, "get_demo_status", demo_status)

    result = PulseState.load_home.fn(state)

    summary.assert_called_once_with()
    connections.assert_called_once_with()
    current_topics.assert_called_once_with(limit=3)
    demo_status.assert_called_once_with()
    assert result.handler.fn is AppState.clear_global_error.fn
    assert state.total_datasets == 1
    _assert_json_safe(
        {
            "datasets": state.dataset_rows,
            "connections": state.connection_rows,
        }
    )

def test_load_ecosystem_calls_current_service_boundary_and_preserves_public_shape(monkeypatch) -> None:
    ecosystem = Mock(
        return_value={
            "sources": [{"name": "ChileCompra", "status": "active"}],
            "concepts": [{"name": "Compra", "datasets": ["ChileCompra"]}],
            "roadmap": [{"status": "prototype", "sources": ["ChileCompra"]}],
        }
    )
    readiness = Mock(
        return_value={
            "entries": [{"name": "ChileCompra", "entity_types": []}],
            "totals": {"ready": 1, "partial": 0, "demo": 0, "without_loader": 0},
        }
    )
    state = SimpleNamespace(error_message="old")

    monkeypatch.setattr(sources_state, "get_data_ecosystem", ecosystem)
    monkeypatch.setattr(sources_state, "get_real_data_readiness", readiness)

    SourcesState.load_ecosystem.fn(state)

    ecosystem.assert_called_once_with()
    readiness.assert_called_once_with()
    assert state.sources_error == ""
    assert state.ecosystem_active_count == 1
    assert state.real_data_ready_count == 1
    _assert_json_safe(
        {
            "sources": state.ecosystem_sources,
            "concepts": state.ecosystem_concepts,
            "readiness": state.real_data_sources,
        }
    )


def test_run_search_calls_service_and_keeps_workspace_matches_json_safe(monkeypatch) -> None:
    search = Mock(
        return_value={
            "matches": [
                {
                    "entity_id": "entity-1",
                    "entity_name": "Entidad de prueba",
                    "canonical_entity_id": "canonical-1",
                    "canonical_entity_name": "Entidad canónica",
                    "datasets": ["ChileCompra"],
                    "relationship_count": 1,
                    "evidence_count": 2,
                }
            ]
        }
    )
    state = SimpleNamespace(search_error="old", query="Entidad")

    monkeypatch.setattr(search_service, "search_workspace", search)

    SearchState.run_search.fn(state)

    search.assert_called_once_with("Entidad")
    assert state.search_error == ""
    assert state.results == state.workspace_matches
    assert state.workspace_matches[0]["canonical_entity_id"] == "canonical-1"
    _assert_json_safe(state.workspace_matches)


def test_load_dashboard_calls_service_and_keeps_metrics_json_safe(monkeypatch) -> None:
    dashboard = Mock(
        return_value={
            "title": "Dashboard",
            "summary": "Resumen",
            "metrics": {
                "budget_total": 100,
                "budget_currency": "CLP",
                "contracts": 1,
                "suppliers": 2,
                "meetings": 3,
                "authorities": 4,
            },
            "budget_rows": [],
            "featured_entities": [],
            "discovery_cases": [],
        }
    )
    state = SimpleNamespace(error_message="old")

    monkeypatch.setattr(dashboard_state, "get_citizen_dashboard", dashboard)

    DashboardState.load_dashboard.fn(state)

    dashboard.assert_called_once_with()
    assert state.dashboard_error == ""
    assert state.dashboard_budget_total == 100
    _assert_json_safe(
        {
            "budget_rows": state.dashboard_budget_rows,
            "featured_entities": state.dashboard_featured_entities,
            "discovery_cases": state.dashboard_discovery_cases,
        }
    )


def test_load_demo_characterizes_report_export_without_writing_files(monkeypatch) -> None:
    summary = Mock(return_value={"totals": {"datasets": 1, "source_records": 1}})
    investigation = Mock(return_value={"found": True, "compact_metrics": {"evidence_count": 1}})
    resolve = Mock(return_value={"entity_id": "entity-1"})
    export = Mock(return_value="virtual/reports/investigation.html")
    state = SimpleNamespace()

    monkeypatch.setattr(demo_state, "get_dataset_summary", summary)
    monkeypatch.setattr(demo_state, "get_investigation", investigation)
    monkeypatch.setattr(demo_state, "resolve_investigation_target", resolve)
    monkeypatch.setattr(demo_state, "export_investigation_report", export)

    result = DemoState.load_demo.fn(state)

    summary.assert_called_once_with()
    investigation.assert_called_once_with(DEMO_INVESTIGATION_TARGET)
    resolve.assert_called_once_with(DEMO_INVESTIGATION_TARGET)
    export.assert_called_once_with("entity-1")
    assert result.handler.fn is AppState.clear_global_error.fn
    assert not hasattr(state, "demo_report_path")
    assert state.demo_report_ready is True

def test_load_tracking_calls_current_service_boundary_with_no_database_access(monkeypatch) -> None:
    items = Mock(return_value=[])
    demo = Mock(
        return_value={
            "item": {
                "title": "Seguimiento",
                "summary": "Resumen",
                "current_status": "published",
                "related_expediente_target": "entity-1",
                "related_sources": [],
            },
            "events": [],
            "documents": [],
            "evidence": [],
            "follow_targets": [],
        }
    )
    state = SimpleNamespace(error_message="")

    monkeypatch.setattr(tracking_state, "get_tracking_items", items)
    monkeypatch.setattr(tracking_state, "get_tracking_demo", demo)

    TrackingState.load_tracking.fn(state)

    items.assert_called_once_with()
    demo.assert_called_once_with()
    assert state.tracking_error == ""
    assert state.tracking_title == "Seguimiento"
    _assert_json_safe({"events": state.tracking_events, "item": state.tracking_item})


def test_load_knowledge_calls_services_and_uses_mocked_document_boundary(monkeypatch, tmp_path) -> None:
    documents = Mock(return_value=[])
    demo = Mock(
        return_value={
            "document": {},
            "pages": [],
            "citations": [],
            "key_points": [],
            "citizen_questions": [],
            "claims": [],
            "references": [],
            "fragments": [],
            "fragment_contexts": [],
            "selected_context": {},
            "connections": {},
            "metrics": [],
            "document_coverage": {},
        }
    )
    fragments = Mock(return_value=([], "fixture-document", True))
    state = SimpleNamespace(
        error_message="",
        router=SimpleNamespace(url=SimpleNamespace(query_parameters={}, raw_path="/knowledge")),
    )

    monkeypatch.setattr(document_reading_service, "get_knowledge_documents", documents)
    monkeypatch.setattr(document_reading_service, "get_knowledge_demo", demo)
    monkeypatch.setattr(document_reading_service, "load_document_fragments_with_source", fragments)
    monkeypatch.setattr("reflex_app.features.document_reading.state.PUBLISHED_DOCUMENT_PDF_ASSET_PATH", tmp_path / "absent.pdf")

    DocumentReadingState.load_knowledge.fn(state)

    documents.assert_called_once_with()
    demo.assert_called_once_with()
    assert fragments.call_args.kwargs["fallback_fragments"] == []
    assert state.knowledge_error == ""
    assert state.knowledge_document_has_pdf is False
    assert state.knowledge_document_source_reference == "Lectura publicada de respaldo"
    _assert_json_safe(
        {
            "document": state.knowledge_document,
            "paragraphs": state.knowledge_document_paragraphs,
            "highlight": state.knowledge_pdf_highlight_target,
        }
    )


def test_load_topic_calls_knowledge_investigation_and_state_graph_boundaries(monkeypatch) -> None:
    investigation = Mock(
        return_value={
            "found": True,
            "entity": {"name": "Boletín"},
            "narrative_summary": "Resumen",
            "compact_metrics": {"evidence_count": 1, "relationship_count": 0},
            "timeline": [],
            "legislative": {"votes_found": 0, "source_records": []},
        }
    )
    state_graph = Mock(return_value=_Graph())
    state = SimpleNamespace(
        knowledge_document={},
        knowledge_title="Lectura",
        knowledge_summary="Resumen",
        knowledge_key_points=[],
        knowledge_claims=[],
        knowledge_notice="",
        knowledge_evidence=[],
        knowledge_fragments=[],
        knowledge_coverage_text="",
        router=SimpleNamespace(url=SimpleNamespace(query_parameters={}, raw_path="/topic")),
    )

    monkeypatch.setattr(document_reading_service, "get_knowledge_documents", Mock(return_value=[]))
    monkeypatch.setattr(
        document_reading_service,
        "get_knowledge_demo",
        Mock(return_value={"document": {}, "fragment_contexts": [], "metrics": [], "document_coverage": {}}),
    )
    monkeypatch.setattr("reflex_app.features.document_reading.state.get_investigation", investigation)
    monkeypatch.setattr("reflex_app.features.document_reading.state.build_state_graph", state_graph)

    DocumentReadingState.load_topic.fn(state)

    investigation.assert_called_once_with(document_reading_service.TOPIC_BUDGET_2013_TARGET)
    state_graph.assert_called_once_with(document_reading_service.TOPIC_BUDGET_2013_TARGET)
    assert state.topic_title == document_reading_service.TOPIC_BUDGET_2013_TITLE
    _assert_json_safe(
        {
            "topic_rows": state.topic_timeline_rows,
            "evidence_rows": state.topic_evidence_rows,
            "graph_rows": state.topic_state_graph_rows,
        }
    )


def test_load_reports_characterizes_report_export_without_writing_files(monkeypatch) -> None:
    reports = Mock(return_value=[])
    report_demo = Mock(
        return_value={
            "title": "Informe",
            "summary": "Resumen",
            "subject": "entity-1",
            "sources": [],
            "sections": [],
            "evidence_refs": [],
        }
    )
    export = Mock(return_value="virtual/reports/citizen.html")
    state = SimpleNamespace(error_message="")

    monkeypatch.setattr(reports_state, "get_citizen_reports", reports)
    monkeypatch.setattr(reports_state, "get_citizen_report_demo", report_demo)
    monkeypatch.setattr(reports_state, "export_citizen_report_demo", export)

    ReportsState.load_reports.fn(state)

    reports.assert_called_once_with()
    report_demo.assert_called_once_with()
    export.assert_called_once_with()
    assert state.citizen_report_available is False
    _assert_json_safe(
        {
            "reports": state.citizen_reports,
            "report": state.citizen_report,
            "sections": state.citizen_report_sections,
        }
    )


def test_load_investigation_calls_all_current_service_boundaries_and_mocks_export(monkeypatch) -> None:
    target = "entity-1"
    entity_id = "canonical-1"
    payload = _investigation_payload()
    resolve = Mock(return_value={"found": True, "entity_id": entity_id, "entity_name": "Entidad de prueba"})
    investigation = Mock(return_value=payload)
    comparison = Mock(return_value={"coverage_summary": "", "consistency_observations": [], "overlap_areas": [], "dataset_contributions": []})
    trace = Mock(return_value={"sources": [], "overlap_summary": "", "neutrality_notice": ""})
    story = Mock(return_value={"headline": "", "summary": "", "key_findings": [], "important_connections": [], "timeline_highlights": [], "questions_for_citizens": []})
    graph = Mock(return_value={"summary": "", "nodes": []})
    timeline = Mock(return_value={"years": []})
    contributions = Mock(return_value={"sources": []})
    knowledge = Mock(return_value={"citizen_summary": "", "key_points": [], "suggested_questions": [], "limitations": [], "neutrality_notice": ""})
    export = Mock(return_value="virtual/reports/investigation.html")
    state_graph = Mock(return_value=_Graph())
    state = _investigation_state(target)

    monkeypatch.setattr(public_record_state, "resolve_investigation_target", resolve)
    monkeypatch.setattr(public_record_state, "get_investigation", investigation)
    monkeypatch.setattr(public_record_state, "get_entity_comparison", comparison)
    monkeypatch.setattr(public_record_state, "get_source_trace", trace)
    monkeypatch.setattr(public_record_state, "get_investigation_story", story)
    monkeypatch.setattr(public_record_state, "get_investigation_graph", graph)
    monkeypatch.setattr(public_record_state, "get_investigation_timeline", timeline)
    monkeypatch.setattr(public_record_state, "get_source_contributions", contributions)
    monkeypatch.setattr(public_record_state, "get_investigation_knowledge", knowledge)
    monkeypatch.setattr(public_record_state, "export_investigation_report", export)
    monkeypatch.setattr(public_record_state, "build_state_graph", state_graph)

    PublicRecordState.load_investigation.fn(state)

    resolve.assert_called_once_with(target)
    investigation.assert_called_once_with(entity_id)
    comparison.assert_called_once_with(entity_id)
    trace.assert_called_once_with(entity_id)
    story.assert_called_once_with(entity_id)
    graph.assert_called_once_with(entity_id)
    timeline.assert_called_once_with(entity_id)
    contributions.assert_called_once_with(entity_id)
    knowledge.assert_called_once_with(payload)
    export.assert_called_once_with(entity_id)
    state_graph.assert_called_once_with(entity_id)
    assert state.investigation_loading is False
    assert state.investigation_status == INVESTIGATION_STATUS_LOADED
    assert state.report_available is False
    _assert_json_safe(
        {
            "entity": state.entity_name,
            "rows": state.evidence_rows,
            "graph": state.state_graph_connection_rows,
            "summary": state.citizen_summary,
        }
    )


def test_load_investigation_preserves_valid_state_and_finishes_safe_errors(monkeypatch) -> None:
    resolver = Mock()
    previous = _investigation_state("")
    previous.entity_name = "Entidad cargada"
    previous.evidence_count = 2
    previous.relationship_count = 1
    previous.datasets_involved = 1
    previous.connected_entities = 1
    previous.investigation_loaded = True

    monkeypatch.setattr(public_record_state, "resolve_investigation_target", resolver)

    PublicRecordState.load_investigation.fn(previous)

    resolver.assert_not_called()
    assert previous.investigation_status == INVESTIGATION_STATUS_LOADED
    assert previous.investigation_loading is False

    failed = _investigation_state("missing-entity")
    monkeypatch.setattr(
        public_record_state,
        "resolve_investigation_target",
        Mock(return_value={"found": False, "warning": "No disponible"}),
    )

    PublicRecordState.load_investigation.fn(failed)

    assert failed.investigation_status == INVESTIGATION_STATUS_ERROR
    assert failed.investigation_loading is False
    assert failed.error_message == "No disponible"
