from __future__ import annotations

import ast
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys

from reflex.page import DECORATED_PAGES

from reflex_app.app.styles import style
from reflex_app.constants.routes import PAGE_HOME
from reflex_app.layouts.shell import app_sidebar
from reflex_app.navigation.config import NAVIGATION_ICON_PREFIXES, PRIMARY_NAVIGATION_GROUPS, PRIMARY_NAVIGATION_ITEMS
from reflex_app.navigation.models import NavigationGroup, NavigationItem
from reflex_app.navigation.sidebar import _nav_icon_for_label


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_GROUPS = [
    (
        "primary",
        "",
        [
            ("home", "Inicio", "/", "I", "home"),
            ("explore", "Explorar", "/search", "E", "search"),
            ("sources", "Fuentes", "/sources", "F", "ecosystem"),
            ("laboratory", "Laboratorio", "/laboratory", "L", "laboratory"),
            ("about", "Acerca de", "/project", "A", "project"),
        ],
    ),
]
EXPECTED_ROUTES = {
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
}


def _render_nodes(value: object) -> list[dict]:
    nodes: list[dict] = []

    def visit(node: object) -> None:
        if isinstance(node, dict):
            nodes.append(node)
            for child in node.get("children", []):
                visit(child)
            for key in ("true_value", "false_value"):
                if key in node:
                    visit(node[key])
        elif isinstance(node, list):
            for item in node:
                visit(item)

    visit(value)
    return nodes


def _contents(value: object) -> list[str]:
    return [
        str(node["contents"])
        for node in _render_nodes(value)
        if "contents" in node
    ]


def _props(value: object) -> list[str]:
    return [
        prop
        for node in _render_nodes(value)
        for prop in node.get("props", [])
    ]


def test_navigation_config_imports_without_services_core_or_app_registration() -> None:
    probe = """
import importlib
import json
import sys

config = importlib.import_module("reflex_app.navigation.config")
models = importlib.import_module("reflex_app.navigation.models")
blocked = [
    name for name in sys.modules
    if name == "datosenorden"
    or name.startswith("datosenorden.")
    or name == "deo_core"
    or name.startswith("deo_core.")
    or name == "reflex_app.reflex_app"
]
print("NAV_CONFIG_IMPORT=" + json.dumps({
    "groups": len(config.PRIMARY_NAVIGATION_GROUPS),
    "items": len(config.PRIMARY_NAVIGATION_ITEMS),
    "model": models.NavigationItem.__name__,
    "blocked": blocked,
}))
"""
    result = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=ROOT,
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload_line = next(line for line in result.stdout.splitlines() if line.startswith("NAV_CONFIG_IMPORT="))
    assert json.loads(payload_line.removeprefix("NAV_CONFIG_IMPORT=")) == {
        "groups": 1,
        "items": 5,
        "model": "NavigationItem",
        "blocked": [],
    }


def test_navigation_config_has_exact_groups_order_labels_icons_and_hrefs() -> None:
    assert isinstance(PRIMARY_NAVIGATION_GROUPS, tuple)
    assert isinstance(PRIMARY_NAVIGATION_ITEMS, tuple)
    assert all(isinstance(group, NavigationGroup) for group in PRIMARY_NAVIGATION_GROUPS)
    assert all(isinstance(item, NavigationItem) for item in PRIMARY_NAVIGATION_ITEMS)

    observed = [
        (
            group.id,
            group.label,
            [(item.id, item.label, item.href, item.icon, item.active_page) for item in group.items],
        )
        for group in PRIMARY_NAVIGATION_GROUPS
    ]
    assert observed == EXPECTED_GROUPS

    assert [(item.label, item.href, item.icon) for item in PRIMARY_NAVIGATION_ITEMS] == [
        ("Inicio", "/", "I"),
        ("Explorar", "/search", "E"),
        ("Fuentes", "/sources", "F"),
        ("Laboratorio", "/laboratory", "L"),
        ("Acerca de", "/project", "A"),
    ]
    assert [(item.group, item.order, item.visibility, item.external, item.contextual) for item in PRIMARY_NAVIGATION_ITEMS] == [
        ("primary", 1, "visible", False, False),
        ("primary", 2, "visible", False, False),
        ("primary", 3, "visible", False, False),
        ("primary", 4, "visible", False, False),
        ("primary", 5, "visible", False, False),
    ]


def test_navigation_config_has_laboratory_but_no_legacy_laboratorio_aliases() -> None:
    serialized = json.dumps(
        [
            item.__dict__
            for item in PRIMARY_NAVIGATION_ITEMS
        ],
        ensure_ascii=False,
    ).lower()
    assert "laboratorio" in serialized
    assert "/laboratory" in serialized
    assert "/laboratorio" not in serialized

    routes = {kwargs["route"] for _, kwargs in DECORATED_PAGES["reflex_app"]}
    assert routes == EXPECTED_ROUTES
    assert not any("laboratorio" in route.lower() or route.strip("/").lower() == "lab" for route in routes)


def test_sidebar_consumes_navigation_config_without_duplicate_literal_links() -> None:
    source = (ROOT / "reflex_app" / "layouts" / "shell.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    app_sidebar = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "app_sidebar")
    app_sidebar_source = ast.get_source_segment(source, app_sidebar) or ""

    assert "PRIMARY_NAVIGATION_GROUPS" in app_sidebar_source
    assert "sidebar_nav_item(item, active_page)" in app_sidebar_source
    for label in ["Inicio", "Explorar", "Fuentes", "Laboratorio", "Acerca de"]:
        assert label not in app_sidebar_source
    assert 'rx.box(class_name="sidebar-spacer")' in app_sidebar_source
    assert "AppState.toggle_sidebar" in app_sidebar_source
    assert "AppState.sidebar_collapsed" in app_sidebar_source


def test_app_sidebar_render_preserves_visible_order_active_collapsed_and_mobile_contract() -> None:
    rendered = app_sidebar(PAGE_HOME).render()
    contents = _contents(rendered)
    props = _props(rendered)

    assert contents == ['"I"', '"Inicio"', '"E"', '"Explorar"', '"F"', '"Fuentes"', '"L"', '"Laboratorio"', '"A"', '"Acerca de"']
    assert props.count('className:"sidebar-spacer"') == 0
    assert 'className:"sidebar-menu-button"' in props
    assert 'className:"sidebar-nav-link sidebar-nav-link-active"' in props
    assert props.count('className:"sidebar-nav-link"') == 4
    assert any("app-sidebar app-sidebar-collapsed" in prop and "app-sidebar" in prop for prop in rendered["props"])

    assert style["@media (max-width: 900px)"][".app-sidebar"]["display"] == "none"
    assert style["@media (max-width: 900px)"][".shell-main"]["margin_left"] == "0"


def test_navigation_icon_prefixes_preserve_current_icon_semantics() -> None:
    assert NAVIGATION_ICON_PREFIXES == (
        ("inicio", "I"),
        ("explorar", "E"),
        ("fuentes", "F"),
        ("laboratorio", "L"),
        ("acerca de", "A"),
        ("studio", "S"),
        ("apoyar", "A"),
        ("ayuda", "?"),
    )
    assert _nav_icon_for_label("Ayuda") == "?"
    assert _nav_icon_for_label("Studio") == "S"
    assert _nav_icon_for_label("Otro") == "O"


def test_navigation_config_is_canonical_and_not_reexported_by_entrypoint() -> None:
    entrypoint = importlib.import_module("reflex_app.reflex_app")

    assert all(isinstance(group, NavigationGroup) for group in PRIMARY_NAVIGATION_GROUPS)
    assert all(isinstance(item, NavigationItem) for item in PRIMARY_NAVIGATION_ITEMS)
    assert NAVIGATION_ICON_PREFIXES
    for name in (
        "NavigationItem",
        "NavigationGroup",
        "PRIMARY_NAVIGATION_GROUPS",
        "PRIMARY_NAVIGATION_ITEMS",
        "NAVIGATION_ICON_PREFIXES",
    ):
        assert not hasattr(entrypoint, name)

def test_navigation_modules_have_no_forbidden_imports_or_route_decorators() -> None:
    paths = [
        ROOT / "reflex_app" / "navigation" / "models.py",
        ROOT / "reflex_app" / "navigation" / "config.py",
        ROOT / "reflex_app" / "navigation" / "sidebar.py",
    ]
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imports = []
        decorators = []
        names = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
            elif isinstance(node, ast.FunctionDef):
                decorators.extend(ast.unparse(decorator) for decorator in node.decorator_list)
            elif isinstance(node, ast.Name):
                names.append(node.id)

        assert [name for name in imports if name == "datosenorden" or name.startswith("datosenorden.")] == []
        assert [name for name in imports if name == "deo_core" or name.startswith("deo_core.")] == []
        assert [name for name in imports if "app_services" in name] == []
        assert "AppState" not in names
        assert not any("rx.page" in decorator for decorator in decorators)


def test_fresh_import_still_creates_one_app_and_21_routes() -> None:
    probe = r'''
import importlib
import json

import reflex as rx
from reflex.page import DECORATED_PAGES

created = []
real_app = rx.App

def recording_app(*args, **kwargs):
    instance = real_app(*args, **kwargs)
    created.append(instance)
    return instance

rx.App = recording_app
first = importlib.import_module("reflex_app.reflex_app")
second = importlib.import_module("reflex_app.reflex_app")
routes = tuple(kwargs["route"] for _, kwargs in DECORATED_PAGES["reflex_app"])
print("APP_IMPORT=" + json.dumps({
    "same_module": first is second,
    "app_count": len(created),
    "route_count": len(routes),
    "unique_route_count": len(set(routes)),
}))
'''
    result = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=ROOT,
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload_line = next(line for line in result.stdout.splitlines() if line.startswith("APP_IMPORT="))
    assert json.loads(payload_line.removeprefix("APP_IMPORT=")) == {
        "same_module": True,
        "app_count": 1,
        "route_count": 21,
        "unique_route_count": 21,
    }
