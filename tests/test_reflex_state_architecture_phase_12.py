from __future__ import annotations

import ast
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys

from reflex.page import DECORATED_PAGES

from reflex_app.app.state import AppState
from reflex_app.features.demo.state import DemoState
from reflex_app.features.pulse.state import PulseState
from reflex_app.navigation.config import PRIMARY_NAVIGATION_GROUPS, PRIMARY_NAVIGATION_ITEMS


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
EXPECTED_ENTRYPOINT_PAGE_FUNCTIONS: set[str] = set()
EXPECTED_FIELD_NAMES = {
    "error_message",
    "header_search_open",
    "header_search_query",
    "sidebar_collapsed",
}
PAGE_OWNERS = {
    "not_found": "reflex_app.app.not_found",
    "home": "reflex_app.features.pulse.pages",
    "ecosystem": "reflex_app.features.sources.pages",
    "sources": "reflex_app.features.sources.pages",
    "demo": "reflex_app.features.demo.pages",
    "topic": "reflex_app.features.document_reading.pages",
    "knowledge": "reflex_app.features.document_reading.pages",
    "official_document": "reflex_app.features.document_reading.pages",
    "library": "reflex_app.features.document_reading.pages",
    "project": "reflex_app.features.institutional.pages",
    "studio": "reflex_app.features.institutional.pages",
    "support": "reflex_app.features.institutional.pages",
    "search": "reflex_app.features.search.pages",
    "discover": "reflex_app.features.search.pages",
    "tracking": "reflex_app.features.tracking.pages",
    "chronology": "reflex_app.features.tracking.pages",
    "reports": "reflex_app.features.reports.pages",
    "dashboard": "reflex_app.features.dashboard.pages",
    "investigation": "reflex_app.features.public_record.pages",
    "laboratory": "reflex_app.features.laboratory.pages",
    "laboratory_expedient": "reflex_app.features.laboratory.pages",
}


def _tree(path: Path = MONOLITH) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _registered_pages() -> list[tuple[str, str, str]]:
    return [
        (kwargs["route"], page_function.__name__, page_function.__module__)
        for page_function, kwargs in DECORATED_PAGES["reflex_app"]
    ]


def _decorated_pages_in(path: Path) -> list[tuple[str, str, int]]:
    pages: list[tuple[str, str, int]] = []
    for node in ast.walk(_tree(path)):
        if not isinstance(node, ast.FunctionDef):
            continue
        for decorator in node.decorator_list:
            if not (
                isinstance(decorator, ast.Call)
                and isinstance(decorator.func, ast.Attribute)
                and isinstance(decorator.func.value, ast.Name)
                and decorator.func.value.id == "rx"
                and decorator.func.attr == "page"
            ):
                continue
            route = ""
            for keyword in decorator.keywords:
                if keyword.arg == "route":
                    route = ast.literal_eval(keyword.value)
            pages.append((route, node.name, node.lineno))
    return pages


def _imports_for(path: Path) -> list[str]:
    imports: list[str] = []
    for node in ast.walk(_tree(path)):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    return imports


def test_appstate_is_transversal_outside_the_entrypoint() -> None:
    classes = [node for node in ast.walk(_tree()) if isinstance(node, ast.ClassDef)]
    assert [node.name for node in classes] == []
    assert AppState.__module__ == "reflex_app.app.state"
    assert EXPECTED_FIELD_NAMES <= set(AppState.vars)
    assert not {"dataset_rows", "demo_report_path"} & set(AppState.vars)
    assert hasattr(PulseState, "load_home")
    assert hasattr(DemoState, "load_demo")

def test_laboratory_architecture_exists_with_public_routes() -> None:
    laboratory = ROOT / "reflex_app" / "features" / "laboratory"
    assert laboratory.exists()
    assert not (ROOT / "reflex_app" / "features" / "laboratorio").exists()
    assert sorted(path.name for path in laboratory.glob("*.py")) == [
        "__init__.py",
        "components.py",
        "models.py",
        "pages.py",
        "state.py",
    ]

    for path in laboratory.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        assert [
            name
            for name in _imports_for(path)
            if name == "reflex_app.reflex_app" or name.startswith("reflex_app.reflex_app.")
        ] == []
        assert [node.name for node in ast.walk(tree) if isinstance(node, ast.AsyncFunctionDef)] == []

    registered = _registered_pages()
    routes = {route for route, _, _ in registered}
    assert {"/laboratory", "/laboratory/expedient"} <= routes


def test_routes_remain_exactly_the_current_21() -> None:
    registered = _registered_pages()

    assert {route for route, _, _ in registered} == set(EXPECTED_ROUTES)
    assert len(registered) == 21
    assert len({route for route, _, _ in registered}) == 21


def test_all_registered_pages_have_feature_or_app_owners_outside_entrypoint() -> None:
    monolith_function_defs = {
        node.name for node in _tree().body if isinstance(node, ast.FunctionDef)
    }
    assert monolith_function_defs == set()

    registered = _registered_pages()
    assert {name for _, name, _ in registered} == set(PAGE_OWNERS)
    for _, function_name, module_name in registered:
        assert module_name == PAGE_OWNERS[function_name]
        assert getattr(importlib.import_module(module_name), function_name).__module__ == module_name

def test_entrypoint_defines_no_rx_page_functions() -> None:
    decorated = _decorated_pages_in(MONOLITH)

    assert {function_name for _, function_name, _ in decorated} == EXPECTED_ENTRYPOINT_PAGE_FUNCTIONS
    assert decorated == []

def test_no_large_domain_models_or_deo_core_imports_in_reflex_app_py() -> None:
    tree = _tree()
    assert [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)] == []

    imports = _imports_for(MONOLITH)
    assert [name for name in imports if name == "deo_core" or name.startswith("deo_core.")] == []
    assert [name for name in imports if name == "datosenorden.core" or name.startswith("datosenorden.core.")] == []


def test_navigation_config_remains_the_sidebar_source_of_truth() -> None:
    shell_path = ROOT / "reflex_app" / "layouts" / "shell.py"
    source = shell_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    sidebar = next(
        node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "app_sidebar"
    )
    sidebar_source = ast.get_source_segment(source, sidebar) or ""

    assert len(PRIMARY_NAVIGATION_GROUPS) == 1
    assert len(PRIMARY_NAVIGATION_ITEMS) == 5
    assert "PRIMARY_NAVIGATION_GROUPS" in sidebar_source
    assert "sidebar_nav_item(item, active_page)" in sidebar_source
    assert "Pulso" not in sidebar_source
    assert "Expediente" not in sidebar_source


def test_future_feature_guardrail_rules_are_documented_and_current_modules_import() -> None:
    domain_map = (
        ROOT
        / "docs"
        / "architecture"
        / "frontend"
        / "DEO_CIUDADANO_APPSTATE_DOMAIN_MAP_2026-07-24.md"
    )
    text = domain_map.read_text(encoding="utf-8")

    for rule in [
        "Toda feature nueva debe nacer bajo `reflex_app/features/<feature>/`",
        "Laboratory sera una feature independiente",
        "El frontend no conoce API keys",
        "nuevas entidades de dominio no deben definirse en `reflex_app/reflex_app.py`",
    ]:
        assert rule in text

    for module_name in [
        "reflex_app.components.common.cards",
        "reflex_app.layouts.page",
        "reflex_app.navigation.config",
        "reflex_app.features.institutional.pages",
        "reflex_app.features.sources.components",
        "reflex_app.features.sources.pages",
    ]:
        assert importlib.import_module(module_name).__name__ == module_name


def test_extracted_feature_files_do_not_hardcode_secret_or_internal_integration_details() -> None:
    feature_files = [
        path
        for path in (ROOT / "reflex_app" / "features").rglob("*.py")
        if "__pycache__" not in path.parts
    ]
    assert feature_files

    forbidden_tokens = [
        "api_key",
        "apikey",
        "rapidapi",
        "apify",
        "localhost:",
        "127.0.0.1:",
        "deo_core",
        "datosenorden.core",
    ]
    for path in feature_files:
        text = path.read_text(encoding="utf-8").lower()
        assert [token for token in forbidden_tokens if token in text] == []


def test_reflex_compile_dry_run_still_passes() -> None:
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
