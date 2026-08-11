from __future__ import annotations

import ast
from pathlib import Path

from reflex.page import DECORATED_PAGES

from reflex_app.app.state import AppState
from reflex_app.features.document_reading.state import DocumentReadingState
from reflex_app.features.public_record.state import PublicRecordState


ROOT = Path(__file__).resolve().parents[1]
MONOLITH = ROOT / "reflex_app" / "app" / "state.py"
DOC = ROOT / "docs" / "architecture" / "frontend" / "DEO_CIUDADANO_DOCUMENT_READING_SUBDOMAIN_MAP_2026-07-24.md"


EXPECTED_ROUTES = {
    "404",
    "/",
    "/ecosystem",
    "/sources",
    "/demo",
    "/topic",
    "/tracking",
    "/chronology",
    "/knowledge",
    "/official-document",
    "/library",
    "/reports",
    "/project",
    "/studio",
    "/support",
    "/search",
    "/discover",
    "/investigation",
    "/dashboard",
    "/laboratory",
    "/laboratory/expedient",
}

DOCUMENT_METHODS = {
    "set_topic_view_mode",
    "load_knowledge",
    "load_topic",
    "open_knowledge_investigation",
    "select_document_anchor",
    "_set_document_reading_context",
    "_set_document_share_links",
}

SUBDOMAINS = {
    "PDF Reading",
    "Fragment Navigation",
    "Highlighting",
    "Citation",
    "Knowledge",
    "Timeline",
    "Graph",
    "Metadata",
    "Document Navigation",
    "Reading Progress",
    "Related Documents",
    "Evidence Candidates",
}


def _tree() -> ast.Module:
    return ast.parse(MONOLITH.read_text(encoding="utf-8"), filename=str(MONOLITH))


def _appstate_class() -> ast.ClassDef:
    return next(node for node in ast.walk(_tree()) if isinstance(node, ast.ClassDef) and node.name == "AppState")


def test_document_reading_subdomain_map_exists_and_lists_required_subdomains() -> None:
    source = DOC.read_text(encoding="utf-8")

    for subdomain in SUBDOMAINS:
        assert subdomain in source
    assert "No se mueve Public Record" in source
    assert "Laboratory" in source
    assert "No se reducen lineas de `reflex_app.py`" in source or "Fase productiva posterior" in source


def test_document_reading_moved_from_appstate_after_productive_sprint() -> None:
    appstate = _appstate_class()
    method_names = {node.name for node in appstate.body if isinstance(node, ast.FunctionDef)}

    assert DOCUMENT_METHODS.isdisjoint(method_names)
    assert hasattr(DocumentReadingState, "load_knowledge")
    assert hasattr(DocumentReadingState, "load_topic")
    assert hasattr(DocumentReadingState, "select_document_anchor")
    assert "knowledge_documents" in DocumentReadingState.vars
    assert "topic_state_graph_rows" in DocumentReadingState.vars
    assert "knowledge_documents" not in AppState.vars
    assert "topic_state_graph_rows" not in AppState.vars


def test_public_record_and_laboratory_keep_feature_ownership() -> None:
    assert not hasattr(AppState, "load_investigation")
    assert hasattr(PublicRecordState, "load_investigation")
    assert "selected_entity_id" in PublicRecordState.vars
    assert "relationship_rows" in PublicRecordState.vars
    assert "selected_entity_id" not in AppState.vars
    assert "relationship_rows" not in AppState.vars

    laboratory_root = ROOT / "reflex_app" / "features" / "laboratory"
    for path in laboratory_root.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        assert [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("deo_core")
        ] == []


def test_document_reading_routes_remain_registered_without_new_routes() -> None:
    route_rows = [(kwargs["route"], page.__name__) for page, kwargs in DECORATED_PAGES["reflex_app"]]
    routes = {route for route, _ in route_rows}

    assert routes == EXPECTED_ROUTES
    assert len(route_rows) == 21
    assert {"/topic", "/knowledge", "/official-document", "/library"} <= routes
