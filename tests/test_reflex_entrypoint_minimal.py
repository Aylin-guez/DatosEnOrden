from __future__ import annotations

import ast
import copy
import json
import subprocess
import sys
from pathlib import Path

from reflex.page import DECORATED_PAGES

import reflex_app.reflex_app as entrypoint
from reflex_app.app.registry import registered_page_modules
from reflex_app.app.state import AppState
from reflex_app.features.demo import pages as demo_pages
from reflex_app.features.demo.state import DemoState
from reflex_app.features.document_reading.state import DocumentReadingState
from reflex_app.features.dashboard.state import DashboardState
from reflex_app.features.pulse import pages as pulse_pages
from reflex_app.features.pulse.state import PulseState
from reflex_app.features.public_record.state import PublicRecordState
from reflex_app.features.reports.state import ReportsState
from reflex_app.features.search.state import SearchState
from reflex_app.features.sources.state import SourcesState
from reflex_app.features.tracking.state import TrackingState
from reflex_app.features.laboratory.state import LaboratoryState


ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINT = ROOT / "reflex_app" / "reflex_app.py"

EXPECTED_ROUTES = [
    "404",
    "/",
    "/ecosystem",
    "/sources",
    "/demo",
    "/topic",
    "/knowledge",
    "/official-document",
    "/library",
    "/project",
    "/studio",
    "/support",
    "/search",
    "/discover",
    "/tracking",
    "/chronology",
    "/reports",
    "/dashboard",
    "/investigation",
    "/laboratory",
    "/laboratory/expedient",
]
EXPECTED_MODULES = [
    "reflex_app.app.not_found",
    "reflex_app.features.pulse.pages",
    "reflex_app.features.sources.pages",
    "reflex_app.features.demo.pages",
    "reflex_app.features.document_reading.pages",
    "reflex_app.features.institutional.pages",
    "reflex_app.features.search.pages",
    "reflex_app.features.tracking.pages",
    "reflex_app.features.reports.pages",
    "reflex_app.features.dashboard.pages",
    "reflex_app.features.public_record.pages",
    "reflex_app.features.laboratory.pages",
]
EXPECTED_MOUNT_HANDLERS = {
    "/": PulseState.load_home,
    "/ecosystem": SourcesState.load_ecosystem,
    "/sources": SourcesState.load_ecosystem,
    "/demo": DemoState.load_demo,
    "/topic": DocumentReadingState.load_topic,
    "/knowledge": DocumentReadingState.load_knowledge,
    "/official-document": DocumentReadingState.load_knowledge,
    "/library": DocumentReadingState.load_knowledge,
    "/search": SearchState.load_search,
    "/discover": SearchState.load_discover,
    "/tracking": TrackingState.load_tracking,
    "/chronology": TrackingState.load_tracking,
    "/reports": ReportsState.load_reports,
    "/dashboard": DashboardState.load_dashboard,
}


def _registered_routes() -> list[tuple[object, dict]]:
    return [(page, kwargs) for page, kwargs in DECORATED_PAGES["reflex_app"]]


def _on_mount_handler(page: object) -> object | None:
    component = page()
    chain = component.event_triggers.get("on_mount")
    return None if chain is None else chain.events[0].handler.fn


def _route_order_in_clean_process() -> list[str]:
    script = (
        "import json; "
        "import reflex_app.reflex_app; "
        "from reflex.page import DECORATED_PAGES; "
        "print(json.dumps([kwargs['route'] for _, kwargs in DECORATED_PAGES['reflex_app']]))"
    )
    result = subprocess.run(
        [sys.executable, "-B", "-c", script],
        cwd=ROOT,
        capture_output=True,
        check=True,
        text=True,
    )
    return json.loads(result.stdout.splitlines()[-1])


def test_entrypoint_is_bootstrap_only() -> None:
    source = ENTRYPOINT.read_text(encoding="utf-8")
    tree = ast.parse(source)

    assert "@rx.page" not in source
    assert not [node for node in tree.body if isinstance(node, ast.ClassDef)]
    assert not [node for node in tree.body if isinstance(node, ast.FunctionDef)]
    assert "reflex_app.features" not in source
    assert entrypoint.__all__ == ("app",)
    assert hasattr(entrypoint, "app")
    assert not hasattr(entrypoint, "AppState")
    assert {name for name in vars(entrypoint) if not name.startswith("__")} == {"annotations", "app"}


def test_explicit_registry_keeps_the_exact_21_route_order_without_duplicates() -> None:
    modules = registered_page_modules()
    assert [module.__name__ for module in modules] == EXPECTED_MODULES

    routes = _registered_routes()
    assert {kwargs["route"] for _, kwargs in routes} == set(EXPECTED_ROUTES)
    assert len({kwargs["route"] for _, kwargs in routes}) == 21
    assert _route_order_in_clean_process() == EXPECTED_ROUTES


def test_moved_routes_keep_metadata_and_lifecycle_owners() -> None:
    by_route = {kwargs["route"]: (page, kwargs) for page, kwargs in _registered_routes()}

    assert by_route["404"][0].__module__ == "reflex_app.app.not_found"
    assert by_route["/"][0] is pulse_pages.home
    assert by_route["/demo"][0] is demo_pages.demo

    assert by_route["404"][1]["title"] == "Pagina no encontrada - DatosEnOrden Ciudadano"
    assert by_route["/"][1]["title"] == "DatosEnOrden Ciudadano - Informacion publica conectada"
    assert by_route["/demo"][1]["title"] == "Recorrido guiado - DatosEnOrden"
    for route in ("404", "/", "/demo"):
        kwargs = by_route[route][1]
        assert kwargs["description"]
        assert kwargs["image"]
        assert kwargs["meta"]

    for route, handler in EXPECTED_MOUNT_HANDLERS.items():
        assert _on_mount_handler(by_route[route][0]) is handler.fn

    assert by_route["/investigation"][1]["on_load"].fn is PublicRecordState.load_investigation.fn
    assert by_route["/laboratory"][1]["on_load"].fn is LaboratoryState.load_catalog.fn
    assert by_route["/laboratory/expedient"][1]["on_load"].fn is LaboratoryState.load_expedient.fn


def test_appstate_is_limited_to_documented_transversal_responsibilities() -> None:
    source = (ROOT / "reflex_app" / "app" / "state.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    state_class = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "AppState")
    declared_fields = {
        node.target.id
        for node in state_class.body
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
    }
    assert declared_fields == {
        "error_message",
        "header_search_open",
        "header_search_query",
        "sidebar_collapsed",
    }
    for handler in {
        "set_global_error",
        "clear_global_error",
        "toggle_header_search",
        "toggle_sidebar",
        "set_header_search_query",
        "submit_header_search",
    }:
        assert handler in AppState.event_handlers

    forbidden = {"load_home", "load_demo", "advanced_nav_open", "toggle_advanced_nav"}
    assert forbidden.isdisjoint(AppState.vars)
    assert forbidden.isdisjoint(AppState.event_handlers)
    assert "Cross-feature shell state" in source


def test_feature_owners_have_no_ast_identical_top_level_function_bodies() -> None:
    groups: dict[str, list[str]] = {}
    for path in (ROOT / "reflex_app").rglob("*.py"):
        if path.name == "__init__.py" or "__pycache__" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            normalized = copy.deepcopy(node)
            normalized.name = "_"
            normalized.decorator_list = []
            key = ast.dump(normalized, include_attributes=False)
            groups.setdefault(key, []).append(f"{path.relative_to(ROOT)}:{node.name}")

    duplicates = [members for members in groups.values() if len(members) > 1]
    assert duplicates == []
