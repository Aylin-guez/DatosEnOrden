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

from reflex_app.constants.public import PUBLIC_OG_IMAGE_ALT, PUBLIC_SITE_AUTHOR, PUBLIC_SITE_NAME, PUBLIC_SITE_URL, PUBLIC_THEME_COLOR
from reflex_app.features.institutional import pages as institutional_pages
from reflex_app.layouts import page as page_layout
from reflex_app.metadata import pages as page_metadata


ROOT = Path(__file__).resolve().parents[1]
APP_NAME = "reflex_app"
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


def _imported_modules(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    return imports


def _module_source_names(path: Path) -> tuple[set[str], set[str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    functions = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
    assignments = {
        target.id
        for node in tree.body
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name)
    }
    return functions, assignments


def _render_contents(value: object) -> list[str]:
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

    visit(value)
    return values


def test_page_section_and_metadata_are_owned_by_boundary_modules() -> None:
    entrypoint = importlib.import_module("reflex_app.reflex_app")

    assert callable(page_layout.page_section)
    assert callable(page_layout._section_icon)
    assert callable(page_metadata._page_meta)
    assert callable(page_metadata._public_url)
    assert page_metadata.PUBLIC_OG_IMAGE_URL

    assert inspect.signature(page_layout.page_section).parameters["title"].annotation == "str"
    assert "path" in inspect.signature(page_metadata._page_meta).parameters
    assert "path" in inspect.signature(page_metadata._public_url).parameters
    for name in ("page_section", "_section_icon", "_page_meta", "_public_url", "PUBLIC_OG_IMAGE_URL"):
        assert not hasattr(entrypoint, name)

def test_page_section_preserves_icons_classes_subtitle_and_id() -> None:
    rendered = page_layout.page_section(
        "Buscar fuentes",
        page_layout.rx.text("Contenido"),
        subtitle="Subtitulo",
        class_name="custom-section",
        element_id="section-id",
    ).render()

    props = [prop for node in rendered["children"] for prop in node.get("props", [])]
    contents = _render_contents(rendered)

    assert any("page-section custom-section" in prop for prop in rendered["props"])
    assert 'id:"section-id"' in rendered["props"]
    assert '"?"' in contents
    assert '"Buscar fuentes"' in contents
    assert any('className:"section-subtitle"' == prop for prop in props)


def test_metadata_preserves_exact_public_values_open_graph_and_canonical() -> None:
    assert page_metadata.PUBLIC_OG_IMAGE_URL == f"{PUBLIC_SITE_URL}/og-image.png"
    assert page_metadata._public_url("project") == f"{PUBLIC_SITE_URL}/project"
    assert page_metadata._public_url("/project") == f"{PUBLIC_SITE_URL}/project"

    meta = page_metadata._page_meta(
        "/project",
        "kw",
        "Title",
        "Desc",
        og_type="article",
    )
    assert meta[:-1] == [
        {"name": "keywords", "content": "kw"},
        {"name": "author", "content": PUBLIC_SITE_AUTHOR},
        {"name": "theme-color", "content": PUBLIC_THEME_COLOR},
        {"property": "og:type", "content": "article"},
        {"property": "og:site_name", "content": PUBLIC_SITE_NAME},
        {"property": "og:locale", "content": "es_CL"},
        {"property": "og:url", "content": f"{PUBLIC_SITE_URL}/project"},
        {"property": "og:title", "content": "Title"},
        {"property": "og:description", "content": "Desc"},
        {"property": "og:image", "content": page_metadata.PUBLIC_OG_IMAGE_URL},
        {"property": "og:image:alt", "content": PUBLIC_OG_IMAGE_ALT},
        {"name": "twitter:card", "content": "summary_large_image"},
        {"name": "twitter:title", "content": "Title"},
        {"name": "twitter:description", "content": "Desc"},
        {"name": "twitter:image", "content": page_metadata.PUBLIC_OG_IMAGE_URL},
    ]
    assert meta[-1].render() == {
        "name": '"link"',
        "props": [f'href:"{PUBLIC_SITE_URL}/project"', 'rel:"canonical"'],
        "children": [],
    }


def test_new_boundary_modules_import_without_services_core_appstate_or_app_registration() -> None:
    probe = """
import importlib
import json
import sys

modules = [
    importlib.import_module("reflex_app.metadata"),
    importlib.import_module("reflex_app.metadata.pages"),
    importlib.import_module("reflex_app.layouts.page"),
]
blocked = [
    name for name in sys.modules
    if name == "datosenorden"
    or name.startswith("datosenorden.")
    or name == "deo_core"
    or name.startswith("deo_core.")
    or name == "reflex_app.reflex_app"
]
print("PHASE10_BOUNDARIES=" + json.dumps({
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
    payload_line = next(line for line in result.stdout.splitlines() if line.startswith("PHASE10_BOUNDARIES="))
    assert json.loads(payload_line.removeprefix("PHASE10_BOUNDARIES=")) == {
        "modules": ["reflex_app.metadata", "reflex_app.metadata.pages", "reflex_app.layouts.page"],
        "blocked": [],
    }


def test_new_boundary_modules_do_not_import_forbidden_layers_or_appstate() -> None:
    for path in [
        ROOT / "reflex_app" / "metadata" / "__init__.py",
        ROOT / "reflex_app" / "metadata" / "pages.py",
        ROOT / "reflex_app" / "layouts" / "page.py",
    ]:
        source = path.read_text(encoding="utf-8")
        imports = _imported_modules(path)
        assert [name for name in imports if name == "datosenorden" or name.startswith("datosenorden.")] == []
        assert [name for name in imports if name == "deo_core" or name.startswith("deo_core.")] == []
        assert [name for name in imports if "app_services" in name or "postgres" in name.lower()] == []
        assert "AppState" not in source
        assert "@rx.page" not in source


def test_institutional_only_keeps_monolith_imports_blocked_by_appstate_or_shell() -> None:
    tree = ast.parse((ROOT / "reflex_app" / "features" / "institutional" / "pages.py").read_text(encoding="utf-8"))
    legacy_imports = [
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module == "reflex_app.reflex_app"
        for alias in node.names
    ]
    assert legacy_imports == []

    assert institutional_pages.PUBLIC_OG_IMAGE_URL == page_metadata.PUBLIC_OG_IMAGE_URL
    assert institutional_pages._page_meta is page_metadata._page_meta
    assert institutional_pages.page_section is page_layout.page_section


def test_monolith_has_no_duplicate_definitions_for_extracted_boundaries() -> None:
    functions, assignments = _module_source_names(ROOT / "reflex_app" / "reflex_app.py")
    assert "page_section" not in functions
    assert "_section_icon" not in functions
    assert "_public_url" not in functions
    assert "_page_meta" not in functions
    assert "PUBLIC_OG_IMAGE_URL" not in assignments


def test_routes_appstate_and_laboratory_absence_are_preserved() -> None:
    from reflex_app.app.state import AppState

    routes = {kwargs["route"] for _, kwargs in DECORATED_PAGES[APP_NAME]}
    assert routes == EXPECTED_ROUTES
    assert len(routes) == 21
    assert not any("laboratorio" in route.lower() or route.strip("/").lower() == "lab" for route in routes)

    functions, _ = _module_source_names(ROOT / "reflex_app" / "reflex_app.py")
    assert "shell" not in functions
    assert "support_cta_block" not in functions
    assert AppState.__module__ == "reflex_app.app.state"
