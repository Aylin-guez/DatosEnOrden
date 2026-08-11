from __future__ import annotations

import reflex as rx

from reflex_app.constants.demo import DEMO_INVESTIGATION_URL
from reflex_app.constants.public import PUBLIC_SITE_URL
from reflex_app.constants.routes import (
    INVESTIGATION_STATUS_EMPTY,
    INVESTIGATION_STATUS_ERROR,
    INVESTIGATION_STATUS_IDLE,
    INVESTIGATION_STATUS_LOADED,
    INVESTIGATION_STATUS_LOADING,
)
from reflex_app.features.public_record.view_models import (
    _build_related_entity_group_rows,
    _build_relationship_journey_rows,
    _build_source_coverage_rows,
    _build_story_cards,
    _citizen_summary_text,
    _clear_investigation_state,
    _debug_investigation,
    _field,
    _format_evidence_rows,
    _format_lobby_rows,
    _format_procurement_rows,
    _format_registry_rows,
    _format_relationship_rows,
    _format_state_graph_connection_rows,
    _format_state_graph_source_rows,
    _format_timeline_rows,
    _format_transparency_rows,
    _investigation_response_has_data,
    _public_error_message,
    _state_has_investigation_data,
)
from reflex_app.helpers.routing import _investigation_href, _router_query_value
from reflex_app.serialization.json_safe import _json_dict, _json_list
from datosenorden.web.app_services import (
    export_investigation_report,
    get_entity_comparison,
    get_investigation,
    get_investigation_graph,
    get_investigation_knowledge,
    get_investigation_story,
    get_investigation_timeline,
    get_source_contributions,
    get_source_trace,
    resolve_canonical_expediente_target,
    resolve_investigation_target,
)
from datosenorden.web.entity_engine import build_state_graph


class PublicRecordState(rx.State):
    selected_entity_id: str = ""
    selected_entity_name: str = ""
    error_message: str = ""

    entity_name: str = ""
    entity_summary: str = ""
    dataset_badges: list[str] = []
    contracts: int = 0
    suppliers: int = 0
    lobby_meetings: int = 0
    evidence_count: int = 0
    relationship_count: int = 0
    datasets_involved: int = 0
    connected_entities: int = 0
    story_cards: list[dict] = []
    connection_summary: str = ""
    procurement_rows: list[dict] = []
    lobby_rows: list[dict] = []
    transparencia_rows: list[dict] = []
    registry_rows: list[dict] = []
    relationship_rows: list[dict] = []
    evidence_rows: list[dict] = []
    state_graph_connection_rows: list[dict] = []
    state_graph_source_rows: list[dict] = []
    state_graph_summary_text: str = ""
    technical_details: list[dict] = []
    neutral_explanation: str = ""
    story_headline: str = ""
    story_summary: str = ""
    story_key_findings: list[str] = []
    story_important_connections: list[str] = []
    story_timeline_highlights: list[str] = []
    story_questions: list[str] = []
    timeline_rows: list[dict] = []
    timeline_overflow_rows: list[dict] = []
    primary_dataset_label: str = ""
    primary_entity_label: str = ""
    citizen_narrative: str = ""
    source_trace_sources: list[dict] = []
    source_trace_left_rows: list[dict] = []
    source_trace_right_rows: list[dict] = []
    comparison_summary: str = ""
    comparison_observations: list[str] = []
    comparison_overlap_areas: list[str] = []
    comparison_dataset_rows: list[dict] = []
    source_trace_overlap_summary: str = ""
    source_trace_notice: str = ""
    graph_summary: str = ""
    graph_dataset_nodes: list[dict] = []
    graph_relationship_nodes: list[dict] = []
    graph_evidence_nodes: list[dict] = []
    timeline_year_rows: list[dict] = []
    timeline_older_year_rows: list[dict] = []
    source_contribution_rows: list[dict] = []
    source_coverage_rows: list[dict] = []
    relationship_journey_rows: list[dict] = []
    related_entity_group_rows: list[dict] = []
    report_available: bool = False
    citizen_summary: str = ""
    investigation_key_points: list[dict] = []
    investigation_questions: list[str] = []
    investigation_limitations: list[str] = []
    investigation_neutrality_notice: str = ""
    canonical_investigation_link: str = DEMO_INVESTIGATION_URL
    investigation_status_message: str = ""
    investigation_status: str = INVESTIGATION_STATUS_IDLE
    requested_investigation_target: str = ""
    last_loaded_investigation_target: str = ""
    last_valid_investigation_target: str = ""
    investigation_loaded: bool = False
    investigation_loading: bool = False


    def open_investigation(self, entity_id: str, entity_name: str):
        return self.open_canonical_investigation(entity_id or entity_name)

    def open_canonical_investigation(self, target: str):
        canonical = _json_dict(resolve_canonical_expediente_target(target))
        self.selected_entity_id = str(canonical.get("canonical_entity_id", target))
        self.selected_entity_name = str(canonical.get("canonical_entity_name", target))
        stable_target = self.selected_entity_id or self.selected_entity_name or target
        self.last_valid_investigation_target = stable_target
        _debug_investigation("open canonical", received=target, resolved=stable_target)
        return rx.redirect(_investigation_href(stable_target))

    def load_investigation(self) -> None:
        self.error_message = ""
        query_id = _router_query_value(self.router, "id")
        target = query_id
        had_valid_state = bool(_field(self, "investigation_loaded", False)) and _state_has_investigation_data(self)
        _debug_investigation(
            "load start",
            received=query_id,
            chosen=target,
            had_valid_state=had_valid_state,
        )
        if query_id:
            self.requested_investigation_target = query_id
            self.last_valid_investigation_target = query_id
        if not target:
            self.requested_investigation_target = ""
            self.investigation_loading = False
            if had_valid_state:
                self.investigation_status = INVESTIGATION_STATUS_LOADED
                _debug_investigation("preserved previous state", reason="missing target")
                return
            _clear_investigation_state(self)
            self.investigation_status = INVESTIGATION_STATUS_EMPTY
            _debug_investigation("empty state", reason="missing target and no previous state")
            return
        self.investigation_loading = True
        self.investigation_status = INVESTIGATION_STATUS_LOADING
        try:
            resolved = _json_dict(resolve_investigation_target(target))
            if not bool(_field(resolved, "found", False)):
                _clear_investigation_state(self)
                self.requested_investigation_target = target
                self.last_valid_investigation_target = target
                self.investigation_status = INVESTIGATION_STATUS_ERROR
                self.investigation_status_message = str(
                    _field(resolved, "warning", "No se encontro una entidad local para abrir el expediente.")
                )
                self.error_message = self.investigation_status_message
                _debug_investigation("empty state", received=target, reason="target not found")
                return
            resolved_entity_id = str(_field(resolved, "entity_id", target))
            resolved_entity_name = str(_field(resolved, "entity_name", ""))
            _debug_investigation("target resolved", received=target, resolved=resolved_entity_id, name=resolved_entity_name)
            data = _json_dict(get_investigation(resolved_entity_id))
            if not _investigation_response_has_data(data):
                if had_valid_state:
                    self.investigation_loading = False
                    self.investigation_status = INVESTIGATION_STATUS_LOADED
                    self.requested_investigation_target = ""
                    self.investigation_status_message = "La respuesta local no trajo datos suficientes; se conserva el expediente cargado."
                    _debug_investigation("preserved previous state", received=target, resolved=resolved_entity_id, reason="empty response")
                    return
                _clear_investigation_state(self)
                self.requested_investigation_target = target
                self.last_valid_investigation_target = target
                self.investigation_status = INVESTIGATION_STATUS_ERROR
                self.investigation_status_message = "La respuesta local no trajo datos suficientes para este expediente."
                self.error_message = self.investigation_status_message
                _debug_investigation("rejected empty response", received=target, resolved=resolved_entity_id)
                return
            comparison = _json_dict(get_entity_comparison(resolved_entity_id))
            trace = _json_dict(get_source_trace(resolved_entity_id))
            story = _json_dict(get_investigation_story(resolved_entity_id))
            graph = _json_dict(get_investigation_graph(resolved_entity_id))
            timeline = _json_dict(get_investigation_timeline(resolved_entity_id))
            contributions = _json_dict(get_source_contributions(resolved_entity_id))
            export_investigation_report(resolved_entity_id)
            report_available = False
            try:
                state_graph = build_state_graph(resolved_entity_id).to_dict()
            except Exception:
                state_graph = {}
        except Exception as exc:  # noqa: BLE001
            if had_valid_state:
                self.investigation_status = INVESTIGATION_STATUS_LOADED
                self.requested_investigation_target = ""
                self.investigation_status_message = "No se pudo refrescar el expediente ahora mismo; se conserva la vista ya cargada."
                _debug_investigation("preserved previous state", received=target, reason=type(exc).__name__)
                return
            _clear_investigation_state(self)
            self.requested_investigation_target = target
            self.last_valid_investigation_target = target
            self.investigation_status = INVESTIGATION_STATUS_ERROR
            self.error_message = _public_error_message("abrir el expediente")
            self.investigation_status_message = self.error_message
            return
        finally:
            self.investigation_loading = False

        metrics = data.get("key_metrics", {})
        compact_metrics = data.get("compact_metrics", {})
        self.selected_entity_id = resolved_entity_id
        self.selected_entity_name = resolved_entity_name
        self.report_available = report_available
        self.entity_name = str(_field(_field(data, "entity", {}), "name", ""))
        self.selected_entity_name = self.entity_name
        self.entity_summary = str(data.get("narrative_summary") or data.get("summary", ""))
        self.dataset_badges = [str(item) for item in _json_list(data.get("dataset_badges", []))]
        self.contracts = int(metrics.get("contracts", 0))
        self.suppliers = int(metrics.get("suppliers", 0))
        self.lobby_meetings = int(metrics.get("lobby_meetings", 0))
        self.evidence_count = int(compact_metrics.get("evidence_count", metrics.get("evidence", 0)))
        self.relationship_count = int(compact_metrics.get("relationship_count", metrics.get("relationships", 0)))
        self.datasets_involved = int(compact_metrics.get("datasets_involved", len(self.dataset_badges)))
        self.connected_entities = int(compact_metrics.get("connected_entities", 0))
        self.connection_summary = data.get("connections", {}).get("summary", "")
        self.procurement_rows = _format_procurement_rows(data.get("contracts_compras", []))
        self.lobby_rows = _format_lobby_rows(data.get("lobby", []))
        self.transparencia_rows = _format_transparency_rows(data.get("transparencia", []))
        self.registry_rows = _format_registry_rows(data.get("registro_empresas", []))
        timeline_rows = _format_timeline_rows(data.get("timeline", []))
        self.timeline_rows = timeline_rows[:5]
        self.timeline_overflow_rows = timeline_rows[5:]
        self.relationship_rows = _format_relationship_rows(
            data.get("connections", {}).get("relationship_cards")
            or data.get("connections", {}).get("direct_neighbors", [])
        )[:5]
        self.evidence_rows = _format_evidence_rows(data.get("evidence", []))
        self.state_graph_connection_rows = _format_state_graph_connection_rows(state_graph)
        self.state_graph_source_rows = _format_state_graph_source_rows(state_graph)
        state_summary = _json_dict(state_graph.get("summary", {}))
        self.state_graph_summary_text = (
            f"{int(state_summary.get('nodes', 0) or 0)} nodos y {int(state_summary.get('edges', 0) or 0)} conexiones observadas desde evidencia disponible."
            if state_summary
            else "Conexiones observadas desde evidencia disponible."
        )
        self.story_cards = _build_story_cards(
            transparency=self.transparencia_rows,
            lobby=self.lobby_rows,
            procurement=self.procurement_rows,
            registry=self.registry_rows,
            relationships=self.relationship_rows,
            evidence=self.evidence_rows,
        )
        self.relationship_journey_rows = _build_relationship_journey_rows(
            entity_name=self.entity_name,
            procurement=self.procurement_rows,
            registry=self.registry_rows,
            lobby=self.lobby_rows,
            transparency=self.transparencia_rows,
            timeline=timeline_rows,
            evidence=self.evidence_rows,
        )
        self.related_entity_group_rows = _build_related_entity_group_rows(
            self.relationship_rows,
            self.registry_rows,
            self.lobby_rows,
            self.procurement_rows,
        )
        self.technical_details = [
            *self.procurement_rows,
            *self.lobby_rows,
            *self.transparencia_rows,
            *self.registry_rows,
            *self.relationship_rows,
            *self.evidence_rows,
        ]
        self.neutral_explanation = data.get("neutral_explanation", "")
        self.story_headline = str(story.get("headline", self.entity_name))
        self.story_summary = str(story.get("summary", self.entity_summary))
        self.story_key_findings = [str(item) for item in story.get("key_findings", [])]
        self.story_important_connections = [str(item) for item in story.get("important_connections", [])]
        self.story_timeline_highlights = [str(item) for item in story.get("timeline_highlights", [])]
        self.story_questions = [str(item) for item in story.get("questions_for_citizens", [])]
        self.source_trace_sources = [
            {
                "dataset": str(_field(item, "dataset", "")),
                "contribution": str(_field(item, "contribution", "")),
                "evidence_count": int(_field(item, "evidence_count", 0) or 0),
                "relationship_count": int(_field(item, "relationship_count", 0) or 0),
                "facts_text": " | ".join(str(fact) for fact in _field(item, "facts", [])),
                "technical_text": " | ".join(str(value) for value in _field(item, "technical", [])),
            }
            for item in _field(trace, "sources", [])
        ]
        midpoint = max(1, len(self.source_trace_sources) // 2) if self.source_trace_sources else 0
        self.source_trace_left_rows = self.source_trace_sources[:midpoint]
        self.source_trace_right_rows = self.source_trace_sources[midpoint:]
        self.comparison_summary = str(comparison.get("coverage_summary", ""))
        self.comparison_observations = [str(item) for item in comparison.get("consistency_observations", [])]
        self.comparison_overlap_areas = [str(item) for item in comparison.get("overlap_areas", [])]
        self.comparison_dataset_rows = [
            {
                "dataset": str(_field(item, "dataset", "")),
                "summary": str(_field(item, "summary", "")),
                "contributes_text": " | ".join(str(value) for value in _field(item, "contributes", [])),
                "category": str(_field(item, "category", "")),
            }
            for item in _field(comparison, "dataset_contributions", [])
        ]
        self.source_trace_overlap_summary = str(_field(trace, "overlap_summary", ""))
        self.source_trace_notice = str(_field(trace, "neutrality_notice", ""))
        self.primary_dataset_label = self.dataset_badges[0] if self.dataset_badges else "Dataset"
        self.primary_entity_label = self.entity_name or "Entity"
        self.citizen_narrative = self.entity_summary or self.connection_summary or self.story_summary
        self.graph_summary = str(_field(graph, "summary", ""))
        graph_nodes = [
            {
                "label": str(_field(item, "label", "")),
                "summary": str(_field(item, "summary", "")),
                "dataset": str(_field(item, "dataset", "")),
                "category": str(_field(item, "category", "")),
            }
            for item in _field(graph, "nodes", [])
        ]
        self.graph_dataset_nodes = [node for node in graph_nodes if node.get("category") == "dataset"]
        self.graph_relationship_nodes = [node for node in graph_nodes if node.get("category") == "relationship"]
        self.graph_evidence_nodes = [node for node in graph_nodes if node.get("category") == "evidence"]
        self.timeline_year_rows = []
        self.timeline_older_year_rows = []
        for index, year in enumerate(_field(timeline, "years", [])):
            items = []
            for category_group in _field(year, "categories", []):
                items.extend(_field(category_group, "items", []))
            item_texts = [
                f"{str(_field(item, 'category', ''))}: {str(_field(item, 'label', ''))} ({str(_field(item, 'dataset', ''))})"
                for item in items
            ]
            row = {
                "year": str(_field(year, "year", "")),
                "items_text": " | ".join(item_texts[:3]),
                "items_overflow_text": " | ".join(item_texts[3:]),
            }
            self.timeline_year_rows.append(row)
        source_counts = {
            str(_field(item, "dataset", "")): {
                "evidence_count": int(_field(item, "evidence_count", 0) or 0),
                "relationship_count": int(_field(item, "relationship_count", 0) or 0),
            }
            for item in self.source_trace_sources
        }
        self.source_contribution_rows = [
            {
                "dataset": str(_field(item, "dataset", "")),
                "summary": str(_field(item, "summary", "")),
                "contributes_text": " | ".join(str(value) for value in _field(item, "contributes", [])),
                "overlap_note": str(_field(item, "overlap_note", "")),
                "category": str(_field(item, "category", "")),
                "status": str(_field(item, "status", "")),
                "concepts_text": str(_field(item, "concepts_text", "")),
                "evidence_types_text": str(_field(item, "evidence_types_text", "")),
                "timeline_contribution": str(_field(item, "timeline_contribution", "")),
                "evidence_count": int(source_counts.get(str(_field(item, "dataset", "")), {}).get("evidence_count", 0)),
                "relationship_count": int(source_counts.get(str(_field(item, "dataset", "")), {}).get("relationship_count", 0)),
                "commands_text": str(_field(item, "commands_text", "")),
            }
            for item in _field(contributions, "sources", [])
        ]
        self.source_coverage_rows = _build_source_coverage_rows(self.source_contribution_rows)
        knowledge = _json_dict(data.get("knowledge") or get_investigation_knowledge(data))
        self.citizen_summary = str(
            _field(knowledge, "citizen_summary", "")
            or _citizen_summary_text(
                self.entity_name,
                self.datasets_involved,
                self.evidence_count,
                self.relationship_count,
                self.connected_entities,
                self.dataset_badges,
            )
        )
        self.investigation_key_points = [
            {
                "text": str(_field(item, "text", "")),
                "sources_text": " | ".join(str(value) for value in _field(item, "source_ids", [])),
                "evidence_text": " | ".join(str(value) for value in _field(item, "evidence_ids", [])),
            }
            for item in _json_list(_field(knowledge, "key_points", []))
        ]
        self.investigation_questions = [str(item) for item in _field(knowledge, "suggested_questions", [])]
        self.investigation_limitations = [str(item) for item in _field(knowledge, "limitations", [])]
        self.investigation_neutrality_notice = str(_field(knowledge, "neutrality_notice", ""))
        self.canonical_investigation_link = f"{PUBLIC_SITE_URL}{_investigation_href(self.entity_name or target)}"
        self.last_loaded_investigation_target = self.selected_entity_id
        self.last_valid_investigation_target = target
        self.requested_investigation_target = ""
        self.investigation_loaded = True
        self.investigation_status = INVESTIGATION_STATUS_LOADED
        self.investigation_status_message = ""
        _debug_investigation(
            "load complete",
            received=target,
            resolved=self.selected_entity_id,
            evidence=self.evidence_count,
            relationships=self.relationship_count,
            sources=self.datasets_involved,
        )
