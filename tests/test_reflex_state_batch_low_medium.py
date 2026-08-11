from __future__ import annotations

import ast
import importlib
import os
from pathlib import Path
import subprocess
import sys

from reflex.page import DECORATED_PAGES

from reflex_app.app.state import AppState
from reflex_app.features.dashboard.state import DashboardState
from reflex_app.features.document_reading.state import DocumentReadingState
from reflex_app.features.reports.state import ReportsState
from reflex_app.features.search.state import SearchState
from reflex_app.features.sources.state import SourcesState
from reflex_app.features.tracking.state import TrackingState


ROOT = Path(__file__).resolve().parents[1]
MONOLITH = ROOT / "reflex_app" / "reflex_app.py"
EXPECTED_ROUTES = [
    "404",
    "/",
    "/ecosystem",
    "/sources",
    "/demo",
    "/discover",
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
    "/investigation",
    "/dashboard",
    "/laboratory",
    "/laboratory/expedient",
]
FIELD_OWNERS = {
    SourcesState: {
        "ecosystem_sources",
        "ecosystem_active_sources",
        "ecosystem_prototype_sources",
        "ecosystem_planned_sources",
        "ecosystem_concepts",
        "ecosystem_roadmap",
        "ecosystem_active_count",
        "ecosystem_prototype_count",
        "ecosystem_planned_count",
        "ecosystem_concept_count",
        "real_data_sources",
        "real_data_ready_count",
        "real_data_partial_count",
        "real_data_demo_count",
        "real_data_without_loader_count",
    },
    ReportsState: {
        "citizen_reports",
        "citizen_report",
        "citizen_report_title",
        "citizen_report_summary",
        "citizen_report_subject",
        "citizen_report_status",
        "citizen_report_sources",
        "citizen_report_sections",
        "citizen_report_evidence_refs",
        "citizen_report_available",
        "citizen_report_error",
    },
    TrackingState: {
        "tracking_items",
        "tracking_item",
        "tracking_title",
        "tracking_summary",
        "tracking_current_status",
        "tracking_expediente_target",
        "tracking_events",
        "tracking_documents",
        "tracking_evidence",
        "tracking_follow_targets",
        "tracking_related_sources",
        "tracking_status_label",
        "tracking_error",
    },
    DashboardState: {
        "dashboard_title",
        "dashboard_summary",
        "dashboard_budget_total",
        "dashboard_budget_currency",
        "dashboard_contracts",
        "dashboard_suppliers",
        "dashboard_meetings",
        "dashboard_authorities",
        "dashboard_budget_rows",
        "dashboard_featured_entities",
        "dashboard_discovery_cases",
    },
    SearchState: {
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
    },
}


def _registered_pages() -> dict[str, tuple[object, dict]]:
    return {
        kwargs["route"]: (page_function, kwargs)
        for page_function, kwargs in DECORATED_PAGES["reflex_app"]
    }


def _root_on_mount_handler(page_function: object) -> object | None:
    component = page_function()
    chain = component.event_triggers.get("on_mount")
    if chain is None:
        return None
    return chain.events[0].handler.fn


def _imports_for(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    return imports


def test_routes_and_on_mount_handlers_are_preserved_with_feature_state_owners() -> None:
    registered = _registered_pages()
    assert set(registered) == set(EXPECTED_ROUTES)
    assert len(registered) == 21

    expected_handlers = {
        "/ecosystem": SourcesState.load_ecosystem.fn,
        "/sources": SourcesState.load_ecosystem.fn,
        "/tracking": TrackingState.load_tracking.fn,
        "/chronology": TrackingState.load_tracking.fn,
        "/reports": ReportsState.load_reports.fn,
        "/dashboard": DashboardState.load_dashboard.fn,
        "/search": SearchState.load_search.fn,
        "/discover": SearchState.load_discover.fn,
    }
    for route, handler in expected_handlers.items():
        assert _root_on_mount_handler(registered[route][0]) is handler


def test_extracted_state_defaults_and_events_match_domain_contracts() -> None:
    expected_events = {
        SourcesState: {"load_ecosystem", "setvar"},
        ReportsState: {"load_reports", "open_report_investigation", "setvar"},
        TrackingState: {"load_tracking", "open_tracking_investigation", "setvar"},
        DashboardState: {"load_dashboard", "setvar"},
        SearchState: {
            "submit_main_search",
            "load_discover",
            "load_search",
            "set_query",
            "run_search",
            "explore_discovery_case",
            "explore_guided_question",
            "select_guided_category",
            "select_result",
            "setvar",
        },
    }
    for state_cls, field_names in FIELD_OWNERS.items():
        assert field_names <= set(state_cls.vars)
        assert set(state_cls.event_handlers) == expected_events[state_cls]
        assert state_cls.computed_vars == {}

    assert SourcesState.ecosystem_sources._var_type == list[dict]
    assert ReportsState.citizen_report_subject._var_type == str
    assert TrackingState.tracking_expediente_target._var_type == str
    assert DashboardState.dashboard_budget_currency._var_type == str
    assert SearchState.query._var_type == str


def test_appstate_is_limited_to_transversal_shell_error_and_search_adapter() -> None:
    extracted_fields = set().union(*FIELD_OWNERS.values())
    declared_fields = {
        "error_message",
        "header_search_open",
        "header_search_query",
        "sidebar_collapsed",
    }
    expected_handlers = {
        "clear_global_error",
        "set_global_error",
        "set_header_search_query",
        "setvar",
        "submit_header_search",
        "toggle_header_search",
        "toggle_sidebar",
    }

    assert declared_fields <= set(AppState.vars)
    assert set(AppState.event_handlers) == expected_handlers
    assert extracted_fields.isdisjoint(AppState.vars)
    for handler_name in [
        "load_ecosystem",
        "load_reports",
        "load_tracking",
        "load_dashboard",
        "open_report_investigation",
        "open_tracking_investigation",
        "submit_main_search",
        "load_discover",
        "load_search",
        "set_query",
        "run_search",
        "explore_discovery_case",
        "explore_guided_question",
        "select_guided_category",
        "select_result",
    ]:
        assert handler_name not in AppState.event_handlers

def test_feature_state_modules_import_without_monolith_core_or_cycles() -> None:
    modules = [
        "reflex_app.features.sources.state",
        "reflex_app.features.reports.state",
        "reflex_app.features.tracking.state",
        "reflex_app.features.dashboard.state",
        "reflex_app.features.search.state",
        "reflex_app.features.document_reading.state",
    ]
    for module_name in modules:
        module = importlib.import_module(module_name)
        path = Path(module.__file__)
        imports = _imports_for(path)
        assert "reflex_app.reflex_app" not in imports
        assert [name for name in imports if name == "deo_core" or name.startswith("deo_core.")] == []
        assert [name for name in imports if name == "datosenorden.core" or name.startswith("datosenorden.core.")] == []


def test_search_document_reading_public_record_and_laboratory_boundaries_hold() -> None:
    assert hasattr(SearchState, "run_search")
    for name in ["load_knowledge", "load_topic"]:
        assert hasattr(DocumentReadingState, name)
        assert not hasattr(AppState, name)
    for name in ["load_investigation"]:
        assert not hasattr(AppState, name)

    laboratory = ROOT / "reflex_app" / "features" / "laboratory"
    for path in laboratory.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        assert [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
            and node.module
            and node.module.startswith("reflex_app.features.search")
        ] == []
        assert [name for name in _imports_for(path) if name == "deo_core" or name.startswith("deo_core.")] == []


def test_reflex_compile_dry_run_after_batch_state_extraction() -> None:
    result = subprocess.run(
        [sys.executable, "-B", "-m", "reflex", "compile", "--dry", "--no-rich"],
        cwd=ROOT,
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        check=False,
        timeout=180,
    )
    assert result.returncode == 0, result.stderr + result.stdout
