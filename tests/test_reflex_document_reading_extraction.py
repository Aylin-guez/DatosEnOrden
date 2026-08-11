from __future__ import annotations

import ast
from pathlib import Path

from reflex.page import DECORATED_PAGES

from reflex_app.app.state import AppState
from datosenorden.application.document_reading import DocumentReadingPort, EvidenceCandidatePort
from reflex_app.features.document_reading import pages as document_reading_pages
from reflex_app.features.document_reading.state import DocumentReadingState
from reflex_app.features.public_record.state import PublicRecordState


ROOT = Path(__file__).resolve().parents[1]
MONOLITH = ROOT / "reflex_app" / "reflex_app.py"
DOC = ROOT / "docs" / "architecture" / "frontend" / "DEO_CIUDADANO_DOCUMENT_READING_EXTRACTION_2026-07-24.md"

DOCUMENT_FIELDS = {
    "knowledge_documents",
    "knowledge_document",
    "knowledge_selected_page",
    "knowledge_selected_fragment_id",
    "knowledge_document_pdf_page_href",
    "knowledge_pdf_highlight_target",
    "knowledge_share_url",
    "topic_view_mode",
    "topic_timeline_rows",
    "topic_state_graph_rows",
    "topic_evidence_rows",
}

DOCUMENT_HANDLERS = {
    "set_topic_view_mode",
    "load_knowledge",
    "load_topic",
    "open_knowledge_investigation",
    "select_document_anchor",
}


def _registered_pages() -> dict[str, tuple[object, dict]]:
    return {kwargs["route"]: (page, kwargs) for page, kwargs in DECORATED_PAGES["reflex_app"]}


def _root_on_mount_handler(page_function: object) -> object | None:
    component = page_function()
    chain = component.event_triggers.get("on_mount")
    if chain is None:
        return None
    return chain.events[0].handler.fn


def test_document_reading_ports_exist_without_private_implementation() -> None:
    assert DocumentReadingPort.__module__ == "datosenorden.application.document_reading.ports"
    assert EvidenceCandidatePort.__module__ == "datosenorden.application.document_reading.ports"

    source = (ROOT / "src" / "datosenorden" / "application" / "document_reading" / "ports.py").read_text(encoding="utf-8")
    assert "class DocumentReadingPort(Protocol)" in source
    assert "class EvidenceCandidatePort(Protocol)" in source
    assert "deo_core" not in source
    assert "deo_document_search" not in source


def test_document_reading_state_is_single_source_in_feature_state() -> None:
    for field in DOCUMENT_FIELDS:
        assert field in DocumentReadingState.vars
        assert field not in AppState.vars
    for handler in DOCUMENT_HANDLERS:
        assert handler in DocumentReadingState.event_handlers
        assert handler not in AppState.event_handlers


def test_document_reading_routes_lifecycle_and_metadata_are_preserved() -> None:
    registered = _registered_pages()

    assert len(registered) == 21
    assert registered["/topic"][0] is document_reading_pages.topic
    assert registered["/knowledge"][0] is document_reading_pages.knowledge
    assert registered["/official-document"][0] is document_reading_pages.official_document
    assert registered["/library"][0] is document_reading_pages.library
    assert _root_on_mount_handler(registered["/topic"][0]) is DocumentReadingState.load_topic.fn
    for route in ["/knowledge", "/official-document", "/library"]:
        assert _root_on_mount_handler(registered[route][0]) is DocumentReadingState.load_knowledge.fn

    assert registered["/official-document"][1]["title"] == "Documento fuente - DatosEnOrden"
    assert registered["/library"][1]["title"] == "Más lecturas - DatosEnOrden"
    assert registered["/topic"][1]["title"] == "Lectura documentada - Ley de Presupuestos 2013 - DatosEnOrden"


def test_document_reading_viewer_navigation_uses_feature_state() -> None:
    components_source = (ROOT / "reflex_app" / "features" / "document_reading" / "components.py").read_text(encoding="utf-8")
    pages_source = (ROOT / "reflex_app" / "features" / "document_reading" / "pages.py").read_text(encoding="utf-8")
    state_source = (ROOT / "reflex_app" / "features" / "document_reading" / "state.py").read_text(encoding="utf-8")
    service_source = (ROOT / "src" / "datosenorden" / "application" / "document_reading" / "service.py").read_text(encoding="utf-8")

    assert "official_document_pdf_viewer" in components_source
    assert "official_document_viewer" in components_source
    assert "document_fragment_panel" in components_source
    assert "DocumentReadingState.knowledge_pdf_location_notice" in components_source
    assert "DocumentReadingState.select_document_anchor" in components_source
    assert "DocumentReadingState.knowledge_share_copy_script" in components_source
    assert "official_document_pdf_viewer" in pages_source
    assert "build_knowledge_payload" in state_source
    assert "deo_core" not in service_source
    assert "deo_document_search" not in service_source


def test_public_record_and_laboratory_keep_feature_ownership() -> None:
    assert not hasattr(AppState, "load_investigation")
    assert hasattr(PublicRecordState, "load_investigation")
    assert "selected_entity_id" in PublicRecordState.vars
    assert "relationship_rows" in PublicRecordState.vars
    assert "selected_entity_id" not in AppState.vars
    assert "relationship_rows" not in AppState.vars

    laboratory = ROOT / "reflex_app" / "features" / "laboratory"
    for path in laboratory.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        assert [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("deo_core")
        ] == []


def test_document_reading_extraction_document_exists() -> None:
    source = DOC.read_text(encoding="utf-8")

    assert "DocumentReadingState" in source
    assert "PUBLIC_PRODUCT_APPLICATION" in source
    assert "DocumentReadingState" in source
