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

from reflex_app.app.state import AppState
from reflex_app.components.common import badges
from reflex_app.metadata.pages import PUBLIC_OG_IMAGE_URL
from reflex_app.features.sources import components as sources_components
from reflex_app.features.sources import pages as sources_pages
from reflex_app.features.sources.state import SourcesState


ROOT = Path(__file__).resolve().parents[1]
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


def _registered_pages() -> dict[str, tuple[object, dict]]:
    return {
        kwargs["route"]: (page_function, kwargs)
        for page_function, kwargs in DECORATED_PAGES["reflex_app"]
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


def _render_text(value: object) -> str:
    return "\n".join(
        str(node["contents"])
        for node in _render_nodes(value)
        if "contents" in node
    )


def _render_props(value: object) -> list[str]:
    return [
        prop
        for node in _render_nodes(value)
        for prop in node.get("props", [])
    ]


def _imports_for(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    return imports


def test_sources_feature_owns_registered_pages_and_components() -> None:
    entrypoint = importlib.import_module("reflex_app.reflex_app")
    registered = _registered_pages()

    assert registered["/ecosystem"][0] is sources_pages.ecosystem
    assert registered["/sources"][0] is sources_pages.sources
    for component_name in (
        "ecosystem_source_card",
        "ecosystem_concept_card",
        "ecosystem_roadmap_card",
        "real_data_source_card",
    ):
        assert callable(getattr(sources_components, component_name))
        assert not hasattr(entrypoint, component_name)
    assert callable(badges._accent_badge_class)
    for page_name in ("ecosystem", "sources"):
        assert not hasattr(entrypoint, page_name)

def test_routes_paths_order_metadata_on_mount_and_no_laboratorio_are_preserved() -> None:
    route_rows = [(kwargs["route"], page_function.__name__) for page_function, kwargs in DECORATED_PAGES["reflex_app"]]
    assert {route for route, _ in route_rows} == set(EXPECTED_ROUTES)
    assert len(route_rows) == 21
    assert len({route for route, _ in route_rows}) == 21

    registered = _registered_pages()
    ecosystem_kwargs = registered["/ecosystem"][1]
    sources_kwargs = registered["/sources"][1]

    assert ecosystem_kwargs["title"] == "Fuentes - DatosEnOrden Ciudadano"
    assert ecosystem_kwargs["description"] == "Catalogo honesto de fuentes conocidas, conectores, datos disponibles y cobertura publica."
    assert ecosystem_kwargs["image"] == PUBLIC_OG_IMAGE_URL
    assert "on_load" not in ecosystem_kwargs

    assert sources_kwargs["title"] == ecosystem_kwargs["title"]
    assert sources_kwargs["description"] == ecosystem_kwargs["description"]
    assert sources_kwargs["image"] == PUBLIC_OG_IMAGE_URL
    assert "on_load" not in sources_kwargs

    assert not any("laboratorio" in route.lower() or route.strip("/").lower() == "lab" for route, _ in route_rows)


def test_sources_pages_preserve_copy_links_styles_active_page_and_on_mount() -> None:
    ecosystem_render = sources_pages.ecosystem().render()
    ecosystem_text = _render_text(ecosystem_render)
    ecosystem_props = "\n".join(_render_props(ecosystem_render))
    ecosystem_source = inspect.getsource(sources_pages.ecosystem)

    assert '"Fuentes"' in ecosystem_text
    assert '"Resumen del mapa"' in ecosystem_source
    assert '"Catalogo y cobertura"' in ecosystem_source
    assert '"Catálogo de metadatos"' in ecosystem_source
    assert '"Ir a Explorar"' in ecosystem_source
    assert '"Ir a Explorar"' in ecosystem_source
    assert '"/sources"' in ecosystem_source
    assert '"/reports"' in ecosystem_source
    assert "on_mount=SourcesState.load_ecosystem" in ecosystem_source
    assert "active_page=PAGE_ECOSYSTEM" in ecosystem_source
    assert any("page-ecosystem" in prop for prop in ecosystem_props.splitlines())

    sources_source = inspect.getsource(sources_pages.sources)
    assert 'sys.modules.get("reflex_app.reflex_app")' not in sources_source
    assert "return legacy_module.ecosystem()" not in sources_source
    assert sources_source.strip().endswith("return ecosystem()")


def test_sources_components_preserve_signatures_copy_and_styles() -> None:
    assert str(inspect.signature(sources_components.ecosystem_source_card)) == "(row: 'dict') -> 'rx.Component'"
    assert str(inspect.signature(sources_components.real_data_source_card)) == "(row: 'dict') -> 'rx.Component'"
    assert badges._accent_badge_class("active") == "badge badge-teal"
    assert badges._accent_badge_class("prototype") == "badge badge-purple"
    assert badges._accent_badge_class("planned") == "badge badge-amber"
    assert badges._accent_badge_class("unknown") == "badge"

    source = inspect.getsource(sources_components)
    for token in [
        "ecosystem-card",
        "concept-card",
        "real-data-card",
            "Vista tecnica de metadata",
            "catalogo:",
            "coverage_status_label",
        "loader:",
    ]:
        assert token in source

def test_sources_modules_do_not_import_core_services_database_or_datosenorden() -> None:
    for path in [
        ROOT / "reflex_app" / "features" / "sources" / "__init__.py",
        ROOT / "reflex_app" / "features" / "sources" / "components.py",
        ROOT / "reflex_app" / "features" / "sources" / "pages.py",
        ROOT / "reflex_app" / "components" / "common" / "badges.py",
    ]:
        imports = _imports_for(path)
        assert [name for name in imports if name == "deo_core" or name.startswith("deo_core.")] == []
        assert [name for name in imports if name == "datosenorden" or name.startswith("datosenorden.")] == []
        assert [name for name in imports if "app_services" in name or "postgres" in name.lower()] == []


def test_sources_components_import_without_registering_app_or_monolith() -> None:
    probe = """
import importlib
import json
import sys

modules = [
    importlib.import_module("reflex_app.components.common.badges"),
    importlib.import_module("reflex_app.features.sources.components"),
]
blocked = [
    name for name in sys.modules
    if name == "datosenorden"
    or name.startswith("datosenorden.")
    or name == "deo_core"
    or name.startswith("deo_core.")
    or name == "reflex_app.reflex_app"
]
print("SOURCES_COMPONENTS_IMPORT=" + json.dumps({
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
    payload_line = next(line for line in result.stdout.splitlines() if line.startswith("SOURCES_COMPONENTS_IMPORT="))
    assert json.loads(payload_line.removeprefix("SOURCES_COMPONENTS_IMPORT=")) == {
        "modules": ["reflex_app.components.common.badges", "reflex_app.features.sources.components"],
        "blocked": [],
    }


def test_sources_pages_keep_only_documented_temporary_monolith_imports() -> None:
    tree = ast.parse((ROOT / "reflex_app" / "features" / "sources" / "pages.py").read_text(encoding="utf-8"))
    legacy_imports = [
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module == "reflex_app.reflex_app"
        for alias in node.names
    ]
    assert legacy_imports == []


def test_monolith_has_no_duplicate_definitions_for_sources_feature() -> None:
    tree = ast.parse((ROOT / "reflex_app" / "reflex_app.py").read_text(encoding="utf-8"))
    function_names = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}

    for name in [
        "ecosystem",
        "sources",
        "ecosystem_source_card",
        "ecosystem_concept_card",
        "ecosystem_roadmap_card",
        "real_data_source_card",
        "_accent_badge_class",
    ]:
        assert name not in function_names


def test_sources_state_owns_current_ecosystem_members() -> None:
    assert AppState.__module__ == "reflex_app.app.state"
    for name in [
        "load_ecosystem",
        "ecosystem_sources",
        "ecosystem_active_sources",
        "ecosystem_prototype_sources",
        "ecosystem_planned_sources",
        "ecosystem_concepts",
        "ecosystem_roadmap",
        "real_data_sources",
    ]:
        assert hasattr(SourcesState, name)
        assert not hasattr(AppState, name)

def test_fresh_import_registers_one_app_and_sources_routes_once() -> None:
    probe = r"""
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
entrypoint = importlib.import_module("reflex_app.reflex_app")
feature = importlib.import_module("reflex_app.features.sources.pages")
routes = tuple(kwargs["route"] for _, kwargs in DECORATED_PAGES["reflex_app"])
print("SOURCES_FEATURE_IMPORT=" + json.dumps({
    "app_count": len(created),
    "route_count": len(routes),
    "unique_route_count": len(set(routes)),
    "entrypoint_exports_app_only": tuple(entrypoint.__all__) == ("app",),
    "ecosystem_owner": feature.ecosystem.__module__,
    "sources_owner": feature.sources.__module__,
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
    payload_line = next(line for line in result.stdout.splitlines() if line.startswith("SOURCES_FEATURE_IMPORT="))
    assert json.loads(payload_line.removeprefix("SOURCES_FEATURE_IMPORT=")) == {
        "app_count": 1,
        "route_count": 21,
        "unique_route_count": 21,
        "entrypoint_exports_app_only": True,
        "ecosystem_owner": "reflex_app.features.sources.pages",
        "sources_owner": "reflex_app.features.sources.pages",
    }
