from __future__ import annotations

import ast
import importlib
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys

from reflex.page import DECORATED_PAGES

from reflex_app.features.public_record.state import PublicRecordState
from reflex_app.layouts.footer import footer_text_link
from reflex_app.layouts.shell import app_footer, app_sidebar
from reflex_app.layouts.page import _page_class
from reflex_app.constants.routes import PAGE_HOME, PAGE_KNOWLEDGE, PAGE_SEARCH, PAGE_TOPIC
from reflex_app.navigation.config import PRIMARY_NAVIGATION_ITEMS
from reflex_app.layouts.shell_controls import scroll_top_control
from reflex_app.navigation.sidebar import (
    _nav_icon_for_label,
    _sidebar_nav_class,
    hamburger_icon,
    sidebar_group_label,
    sidebar_nav_link,
)


ROOT = Path(__file__).resolve().parents[1]
APP_NAME = "reflex_app"
EXTRACTED_SYMBOLS = {
    "_nav_icon_for_label",
    "_page_class",
    "_sidebar_nav_class",
    "footer_text_link",
    "hamburger_icon",
    "scroll_top_control",
    "sidebar_group_label",
    "sidebar_nav_link",
}
NEW_MODULES = [
    "reflex_app.layouts",
    "reflex_app.layouts.footer",
    "reflex_app.layouts.page",
    "reflex_app.layouts.shell_controls",
    "reflex_app.navigation",
    "reflex_app.navigation.sidebar",
]
NEW_PATHS = [
    ROOT / "reflex_app" / "layouts" / "__init__.py",
    ROOT / "reflex_app" / "layouts" / "footer.py",
    ROOT / "reflex_app" / "layouts" / "page.py",
    ROOT / "reflex_app" / "layouts" / "shell_controls.py",
    ROOT / "reflex_app" / "navigation" / "__init__.py",
    ROOT / "reflex_app" / "navigation" / "sidebar.py",
]
EXPECTED_ROUTES = {
    "404": ("not_found", "Pagina no encontrada - DatosEnOrden Ciudadano"),
    "/": ("home", "DatosEnOrden Ciudadano - Informacion publica conectada"),
    "/ecosystem": ("ecosystem", "Fuentes - DatosEnOrden Ciudadano"),
    "/sources": ("sources", "Fuentes - DatosEnOrden Ciudadano"),
    "/demo": ("demo", "Recorrido guiado - DatosEnOrden"),
    "/discover": ("discover", "Explorar - DatosEnOrden Ciudadano"),
    "/topic": ("topic", "Lectura documentada - Ley de Presupuestos 2013 - DatosEnOrden"),
    "/tracking": ("tracking", "Cronología - DatosEnOrden"),
    "/chronology": ("chronology", "Cronología - DatosEnOrden"),
    "/knowledge": ("knowledge", "Conocimiento - DatosEnOrden"),
    "/official-document": ("official_document", "Documento fuente - DatosEnOrden"),
    "/library": ("library", "Más lecturas - DatosEnOrden"),
    "/reports": ("reports", "Informes ciudadanos - DatosEnOrden"),
    "/project": ("project", "Estado del proyecto - DatosEnOrden"),
    "/studio": ("studio", "DatosEnOrden Studio"),
    "/support": ("support", "Apoyar DatosEnOrden"),
    "/search": ("search", "Explorar - DatosEnOrden Ciudadano"),
    "/investigation": ("investigation", "Expediente - DatosEnOrden"),
    "/dashboard": ("dashboard", "Vista ciudadana - DatosEnOrden"),
    "/laboratory": ("laboratory", "Laboratorio de Políticas Públicas - DatosEnOrden"),
    "/laboratory/expedient": ("laboratory_expedient", "Expediente del Laboratorio - DatosEnOrden"),
}


def _registered_pages() -> dict[str, tuple[object, dict]]:
    return {
        kwargs["route"]: (page_function, kwargs)
        for page_function, kwargs in DECORATED_PAGES[APP_NAME]
    }
def _contents(component: object) -> list[str]:
    rendered = component.render()
    values: list[str] = []

    def visit(node: object) -> None:
        if isinstance(node, dict):
            if "contents" in node:
                values.append(str(node["contents"]))
            for child in node.get("children", []):
                visit(child)
        elif isinstance(node, list):
            for item in node:
                visit(item)

    visit(rendered)
    return values


def test_new_layout_navigation_modules_import_without_services_core_or_app() -> None:
    probe = """
import importlib
import json
import sys

modules = [
    importlib.import_module("reflex_app.layouts"),
    importlib.import_module("reflex_app.layouts.footer"),
    importlib.import_module("reflex_app.layouts.page"),
    importlib.import_module("reflex_app.layouts.shell_controls"),
    importlib.import_module("reflex_app.navigation"),
    importlib.import_module("reflex_app.navigation.sidebar"),
]
blocked = [
    name for name in sys.modules
    if name == "datosenorden"
    or name.startswith("datosenorden.")
    or name == "deo_core"
    or name.startswith("deo_core.")
    or name == "reflex_app.reflex_app"
]
print("NAV_MODULES=" + json.dumps({
    "modules": [module.__name__ for module in modules],
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
    payload_line = next(line for line in result.stdout.splitlines() if line.startswith("NAV_MODULES="))
    assert json.loads(payload_line.removeprefix("NAV_MODULES=")) == {
        "modules": NEW_MODULES,
        "blocked": [],
    }


def test_new_modules_do_not_access_appstate_services_core_or_register_routes() -> None:
    for module_path in NEW_PATHS:
        tree = ast.parse(module_path.read_text(encoding="utf-8"), filename=str(module_path))
        imports = []
        names = []
        attributes = []
        decorators = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
            elif isinstance(node, ast.Name):
                names.append(node.id)
            elif isinstance(node, ast.Attribute):
                attributes.append(node.attr)
            elif isinstance(node, ast.FunctionDef):
                decorators.extend(ast.unparse(decorator) for decorator in node.decorator_list)

        assert [name for name in imports if name == "datosenorden" or name.startswith("datosenorden.")] == []
        assert [name for name in imports if name == "deo_core" or name.startswith("deo_core.")] == []
        assert [name for name in imports if "app_services" in name] == []
        assert "AppState" not in names
        assert "page" not in attributes
        assert decorators == []


def test_layout_and_navigation_objects_have_direct_owners_and_stable_signatures() -> None:
    entrypoint = importlib.import_module("reflex_app.reflex_app")
    new_sources = {
        "_page_class": importlib.import_module("reflex_app.layouts.page"),
        "footer_text_link": importlib.import_module("reflex_app.layouts.footer"),
        "scroll_top_control": importlib.import_module("reflex_app.layouts.shell_controls"),
        "_nav_icon_for_label": importlib.import_module("reflex_app.navigation.sidebar"),
        "_sidebar_nav_class": importlib.import_module("reflex_app.navigation.sidebar"),
        "hamburger_icon": importlib.import_module("reflex_app.navigation.sidebar"),
        "sidebar_group_label": importlib.import_module("reflex_app.navigation.sidebar"),
        "sidebar_nav_link": importlib.import_module("reflex_app.navigation.sidebar"),
    }

    for name, module in new_sources.items():
        assert callable(getattr(module, name))
        assert not hasattr(entrypoint, name)

    assert str(inspect.signature(_page_class)) == "(active_page: 'str') -> 'str'"
    assert str(inspect.signature(_sidebar_nav_class)) == "(active: 'bool') -> 'str'"
    assert str(inspect.signature(_nav_icon_for_label)) == "(label: 'str') -> 'str'"
    assert str(inspect.signature(sidebar_nav_link)) == "(label: 'str', href: 'str', active: 'bool') -> 'rx.Component'"
    assert str(inspect.signature(hamburger_icon)) == "() -> 'rx.Component'"
    assert str(inspect.signature(sidebar_group_label)) == "(label: 'str') -> 'rx.Component'"
    assert str(inspect.signature(scroll_top_control)) == "() -> 'rx.Component'"
    assert str(inspect.signature(footer_text_link)) == "(icon: 'str', label: 'str', href: 'str') -> 'rx.Component'"

def test_routes_paths_titles_metadata_and_no_laboratorio_routes() -> None:
    registered = _registered_pages()

    assert set(registered) == set(EXPECTED_ROUTES)
    assert len(registered) == 21
    assert len({metadata["route"] for _, metadata in registered.values()}) == 21
    assert not any("laboratorio" in route.lower() or "lab" == route.strip("/").lower() for route in registered)

    for route, (function_name, title) in EXPECTED_ROUTES.items():
        page_function, metadata = registered[route]
        assert page_function.__name__ == function_name
        assert metadata["title"] == title
        assert metadata["image"] == "https://datosenorden.cl/og-image.png"
        assert "DatosEnOrden" in metadata["title"] or route == "404"

    assert registered["/investigation"][1]["on_load"].fn is PublicRecordState.load_investigation.fn


def test_navigation_order_links_visible_labels_and_active_classes_are_preserved() -> None:
    sidebar_source = inspect.getsource(app_sidebar)
    expected_items = [
        ("Inicio", "/", "I"),
        ("Explorar", "/search", "E"),
        ("Fuentes", "/sources", "F"),
        ("Laboratorio", "/laboratory", "L"),
        ("Acerca de", "/project", "A"),
    ]
    assert "PRIMARY_NAVIGATION_GROUPS" in sidebar_source
    assert "sidebar_nav_item(item, active_page)" in sidebar_source
    assert [(item.label, item.href, item.icon) for item in PRIMARY_NAVIGATION_ITEMS] == expected_items

    assert _sidebar_nav_class(True) == "sidebar-nav-link sidebar-nav-link-active"
    assert _sidebar_nav_class(False) == "sidebar-nav-link"
    assert [_nav_icon_for_label(label) for label in ["Inicio", "Explorar", "Fuentes", "Laboratorio", "Acerca de"]] == [
        "I",
        "E",
        "F",
        "L",
        "A",
    ]

    rendered_link = sidebar_nav_link("Inicio", "/", True).render()
    assert 'className:"sidebar-nav-link sidebar-nav-link-active"' in rendered_link["props"]
    assert _contents(sidebar_nav_link("Inicio", "/", True)) == ['"I"', '"Inicio"']


def test_footer_links_scroll_control_and_page_classes_are_preserved() -> None:
    footer_source = inspect.getsource(app_footer)
    footer_calls = [
        '"Apoyar DatosEnOrden", "/support"',
        '"Explorar", "/search"',
        '"Sugerir una fuente", SUPPORT_SOURCE_SUGGESTION_URL',
        '"Acerca de", "/project"',
        '"Studio", "/studio"',
        '"Contacto comercial", STUDIO_CONVERSATION_URL',
    ]
    assert [footer_source.index(call) for call in footer_calls] == sorted(footer_source.index(call) for call in footer_calls)

    footer_link = footer_text_link("+", "Sugerir una fuente", "mailto:test@example.test").render()
    assert 'className:"footer-link footer-column-link"' in footer_link["props"]
    assert '"aria-label":"Sugerir una fuente"' in footer_link["props"]

    scroll_render = scroll_top_control().render()
    scroll_props = str(scroll_render)
    assert "scroll-top-button" in scroll_props
    assert "window.__deoScrollTopReady" in scroll_props
    assert "window.scrollTo({ top: 0, behavior: 'smooth' })" in inspect.getsource(scroll_top_control)

    assert _page_class(PAGE_HOME) == "page-home"
    assert _page_class(PAGE_TOPIC) == "page-topic"
    assert _page_class(PAGE_KNOWLEDGE) == "page-library"
    assert _page_class(PAGE_SEARCH) == "page-discover"
    assert _page_class("unknown") == "page-home"


def test_reflex_app_no_longer_defines_extracted_symbols_and_appstate_remains_monolith() -> None:
    tree = ast.parse((ROOT / "reflex_app" / "reflex_app.py").read_text(encoding="utf-8"))
    function_names = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
    class_names = {node.name for node in tree.body if isinstance(node, ast.ClassDef)}

    assert function_names.isdisjoint(EXTRACTED_SYMBOLS)
    assert "AppState" not in class_names
    assert {"shell", "app_sidebar", "app_footer"}.isdisjoint(function_names)


def test_fresh_import_creates_one_app_and_no_duplicate_routes() -> None:
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
