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
from reflex_app.components.common.cards import _flow_accent_class, flow_card, help_card
from reflex_app.features.pulse.state import PulseState
from reflex_app.metadata.pages import PUBLIC_OG_IMAGE_URL
from reflex_app.features.institutional import pages as institutional_pages


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


def test_feature_pages_are_the_registered_institutional_owners() -> None:
    registered = _registered_pages()

    assert registered["/project"][0] is institutional_pages.project
    assert registered["/studio"][0] is institutional_pages.studio
    assert registered["/support"][0] is institutional_pages.support
    assert all(
        page.__module__ == "reflex_app.features.institutional.pages"
        for page, _ in (registered["/project"], registered["/studio"], registered["/support"])
    )

def test_routes_paths_order_metadata_and_no_laboratorio_are_preserved() -> None:
    route_rows = [(kwargs["route"], page_function.__name__) for page_function, kwargs in DECORATED_PAGES["reflex_app"]]
    assert {route for route, _ in route_rows} == set(EXPECTED_ROUTES)
    assert len(route_rows) == 21
    assert len({route for route, _ in route_rows}) == 21

    registered = _registered_pages()
    assert registered["/project"][1]["title"] == "Estado del proyecto - DatosEnOrden"
    assert registered["/project"][1]["description"] == "Estado público del proyecto DatosEnOrden, su propósito, alcance y límites."
    assert registered["/project"][1]["image"] == PUBLIC_OG_IMAGE_URL
    assert "on_load" not in registered["/project"][1]
    assert registered["/studio"][1]["title"] == "DatosEnOrden Studio"
    assert registered["/studio"][1]["description"] == "Entrada comercial para organizaciones que necesitan expedientes, fuentes y automatización documental verificable."
    assert registered["/studio"][1]["image"] == PUBLIC_OG_IMAGE_URL
    assert "on_load" not in registered["/studio"][1]
    assert registered["/support"][1]["title"] == "Apoyar DatosEnOrden"
    assert registered["/support"][1]["description"] == "Página pública de apoyo y colaboración para el lanzamiento de DatosEnOrden."
    assert registered["/support"][1]["image"] == PUBLIC_OG_IMAGE_URL
    assert "on_load" not in registered["/support"][1]

    assert not any("laboratorio" in route.lower() or route.strip("/").lower() == "lab" for route, _ in route_rows)


def test_extracted_pages_preserve_copy_links_styles_and_active_pages() -> None:
    project_render = institutional_pages.project().render()
    project_text = _render_text(project_render)
    project_props = _render_props(project_render)
    project_source = inspect.getsource(institutional_pages.project)
    assert '"Acerca de DatosEnOrden Ciudadano"' in project_text
    assert '"MVP con datos locales de prueba. No representa datos oficiales reales."' in project_text
    assert '"Abrir expediente de ejemplo"' in project_source
    assert '"Qué es DatosEnOrden"' in project_source
    assert "launch-notice" in "\n".join(project_props)
    assert any("page-project" in prop for prop in project_props)

    studio_render = institutional_pages.studio().render()
    studio_text = _render_text(studio_render)
    studio_props = _render_props(studio_render)
    studio_source = inspect.getsource(institutional_pages.studio)
    assert '"DatosEnOrden Studio"' in studio_text
    assert '"Solicitar una conversación"' in studio_source
    assert '"Enviar correo"' in studio_source
    assert '"Qué obtiene una organización"' in studio_source
    assert "studio-hero" in "\n".join(studio_props)
    assert any("page-project" in prop for prop in studio_props)

    support_render = institutional_pages.support().render()
    support_text = _render_text(support_render)
    support_props = _render_props(support_render)
    support_source = inspect.getsource(institutional_pages.support)
    assert '"Apoyar DatosEnOrden"' in support_text
    assert '"Evidencia primero."' in support_text
    assert '"Abrir enlace de apoyo"' in support_source
    assert '"Sugerir una fuente"' in support_source
    assert "support-action-card" in "\n".join(support_props)
    assert any("page-project" in prop for prop in support_props)


def test_appstate_is_transversal_and_pulse_owns_home_loading() -> None:
    tree = ast.parse((ROOT / "reflex_app" / "reflex_app.py").read_text(encoding="utf-8"))
    class_names = {node.name for node in tree.body if isinstance(node, ast.ClassDef)}
    assert "AppState" not in class_names

    for name in [
        "toggle_sidebar",
        "toggle_header_search",
        "submit_header_search",
    ]:
        assert hasattr(AppState, name)

    assert not hasattr(AppState, "load_home")
    assert hasattr(PulseState, "load_home")
    for name in ["load_ecosystem", "load_reports"]:
        assert not hasattr(AppState, name)

def test_reflex_app_no_longer_defines_extracted_pages_directly() -> None:
    tree = ast.parse((ROOT / "reflex_app" / "reflex_app.py").read_text(encoding="utf-8"))
    function_names = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
    assert "project" not in function_names
    assert "studio" not in function_names
    assert "support" not in function_names
    assert "help_card" not in function_names
    assert "flow_card" not in function_names
    assert "_flow_accent_class" not in function_names


def test_feature_modules_do_not_import_core_services_or_database() -> None:
    paths = [
        ROOT / "reflex_app" / "features" / "institutional" / "__init__.py",
        ROOT / "reflex_app" / "features" / "institutional" / "pages.py",
    ]
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)

        assert [name for name in imports if name == "deo_core" or name.startswith("deo_core.")] == []
        assert [name for name in imports if name == "datosenorden" or name.startswith("datosenorden.")] == []
        assert [name for name in imports if "app_services" in name or "postgres" in name.lower()] == []


def test_fresh_import_registers_one_app_and_feature_routes_once() -> None:
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
feature = importlib.import_module("reflex_app.features.institutional.pages")
routes = tuple(kwargs["route"] for _, kwargs in DECORATED_PAGES["reflex_app"])
print("FEATURE_IMPORT=" + json.dumps({
    "app_count": len(created),
    "route_count": len(routes),
    "unique_route_count": len(set(routes)),
    "entrypoint_exports_app_only": tuple(entrypoint.__all__) == ("app",),
    "project_owner": feature.project.__module__,
    "studio_owner": feature.studio.__module__,
    "support_owner": feature.support.__module__,
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
    payload_line = next(line for line in result.stdout.splitlines() if line.startswith("FEATURE_IMPORT="))
    assert json.loads(payload_line.removeprefix("FEATURE_IMPORT=")) == {
        "app_count": 1,
        "route_count": 21,
        "unique_route_count": 21,
        "entrypoint_exports_app_only": True,
        "project_owner": "reflex_app.features.institutional.pages",
        "studio_owner": "reflex_app.features.institutional.pages",
        "support_owner": "reflex_app.features.institutional.pages",
    }


def test_shared_medium_components_are_owned_by_common_cards() -> None:
    entrypoint = importlib.import_module("reflex_app.reflex_app")

    assert callable(help_card)
    assert callable(flow_card)
    assert _flow_accent_class(1) == "flow-accent flow-accent-teal"
    assert _flow_accent_class(2) == "flow-accent flow-accent-purple"
    assert _flow_accent_class(3) == "flow-accent flow-accent-amber"
    for name in ("help_card", "flow_card", "_flow_accent_class"):
        assert not hasattr(entrypoint, name)
