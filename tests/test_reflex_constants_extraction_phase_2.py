from __future__ import annotations

import ast
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys

from reflex.page import DECORATED_PAGES


ROOT = Path(__file__).resolve().parents[1]
EXTRACTED_NAMES = {
    "PAGE_HOME",
    "PAGE_ECOSYSTEM",
    "PAGE_DISCOVER",
    "PAGE_SEARCH",
    "PAGE_INVESTIGATION",
    "PAGE_TRACKING",
    "PAGE_KNOWLEDGE",
    "PAGE_LIBRARY",
    "PAGE_TOPIC",
    "PAGE_DOCUMENT",
    "PAGE_REPORTS",
    "PAGE_DASHBOARD",
    "PAGE_DEMO",
    "PAGE_PROJECT",
    "PAGE_SUPPORT",
    "PAGE_STUDIO",
    "PAGE_NOT_FOUND",
    "INVESTIGATION_STATUS_IDLE",
    "INVESTIGATION_STATUS_LOADING",
    "INVESTIGATION_STATUS_LOADED",
    "INVESTIGATION_STATUS_ERROR",
    "INVESTIGATION_STATUS_EMPTY",
    "PUBLIC_SITE_URL",
    "PUBLIC_SITE_NAME",
    "PUBLIC_SITE_AUTHOR",
    "PUBLIC_THEME_COLOR",
    "PUBLIC_OG_IMAGE_PATH",
    "PUBLIC_MANIFEST_PATH",
    "PUBLIC_OG_IMAGE_ALT",
    "SUPPORT_DONATION_URL",
    "SUPPORT_SOURCE_SUGGESTION_URL",
    "STUDIO_CONVERSATION_URL",
    "STUDIO_CONTACT_EMAIL",
}


def test_constants_modules_import_without_reflex_services_or_core() -> None:
    probe = """
import importlib
import json
import sys

routes = importlib.import_module("reflex_app.constants.routes")
public = importlib.import_module("reflex_app.constants.public")
blocked = [
    name for name in sys.modules
    if name == "reflex"
    or name.startswith("reflex.")
    or name == "datosenorden"
    or name.startswith("datosenorden.")
    or name == "deo_core"
    or name.startswith("deo_core.")
    or name == "reflex_app.reflex_app"
]
print("CONSTANTS_IMPORT=" + json.dumps({
    "routes": routes.PAGE_HOME,
    "public": public.PUBLIC_SITE_NAME,
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
    payload_line = next(line for line in result.stdout.splitlines() if line.startswith("CONSTANTS_IMPORT="))
    assert json.loads(payload_line.removeprefix("CONSTANTS_IMPORT=")) == {
        "routes": "home",
        "public": "DatosEnOrden Ciudadano",
        "blocked": [],
    }


def test_constants_modules_do_not_import_forbidden_dependencies() -> None:
    for module_path in [
        ROOT / "reflex_app" / "constants" / "__init__.py",
        ROOT / "reflex_app" / "constants" / "routes.py",
        ROOT / "reflex_app" / "constants" / "public.py",
    ]:
        tree = ast.parse(module_path.read_text(encoding="utf-8"), filename=str(module_path))
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
        forbidden = [
            name
            for name in imports
            if name == "reflex"
            or name.startswith("reflex.")
            or name == "datosenorden"
            or name.startswith("datosenorden.")
            or name == "deo_core"
            or name.startswith("deo_core.")
            or "app_services" in name
        ]
        assert forbidden == []


def test_routes_and_status_constants_keep_exact_values() -> None:
    routes = importlib.import_module("reflex_app.constants.routes")

    assert {
        "PAGE_HOME": routes.PAGE_HOME,
        "PAGE_ECOSYSTEM": routes.PAGE_ECOSYSTEM,
        "PAGE_DISCOVER": routes.PAGE_DISCOVER,
        "PAGE_SEARCH": routes.PAGE_SEARCH,
        "PAGE_INVESTIGATION": routes.PAGE_INVESTIGATION,
        "PAGE_TRACKING": routes.PAGE_TRACKING,
        "PAGE_KNOWLEDGE": routes.PAGE_KNOWLEDGE,
        "PAGE_LIBRARY": routes.PAGE_LIBRARY,
        "PAGE_TOPIC": routes.PAGE_TOPIC,
        "PAGE_DOCUMENT": routes.PAGE_DOCUMENT,
        "PAGE_REPORTS": routes.PAGE_REPORTS,
        "PAGE_DASHBOARD": routes.PAGE_DASHBOARD,
        "PAGE_DEMO": routes.PAGE_DEMO,
        "PAGE_PROJECT": routes.PAGE_PROJECT,
        "PAGE_SUPPORT": routes.PAGE_SUPPORT,
        "PAGE_STUDIO": routes.PAGE_STUDIO,
        "PAGE_NOT_FOUND": routes.PAGE_NOT_FOUND,
    } == {
        "PAGE_HOME": "home",
        "PAGE_ECOSYSTEM": "ecosystem",
        "PAGE_DISCOVER": "discover",
        "PAGE_SEARCH": "search",
        "PAGE_INVESTIGATION": "investigation",
        "PAGE_TRACKING": "tracking",
        "PAGE_KNOWLEDGE": "knowledge",
        "PAGE_LIBRARY": "library",
        "PAGE_TOPIC": "topic",
        "PAGE_DOCUMENT": "official_document",
        "PAGE_REPORTS": "reports",
        "PAGE_DASHBOARD": "dashboard",
        "PAGE_DEMO": "demo",
        "PAGE_PROJECT": "project",
        "PAGE_SUPPORT": "support",
        "PAGE_STUDIO": "studio",
        "PAGE_NOT_FOUND": "not_found",
    }
    assert {
        routes.INVESTIGATION_STATUS_IDLE,
        routes.INVESTIGATION_STATUS_LOADING,
        routes.INVESTIGATION_STATUS_LOADED,
        routes.INVESTIGATION_STATUS_ERROR,
        routes.INVESTIGATION_STATUS_EMPTY,
    } == {"idle", "loading", "loaded", "error", "empty"}


def test_public_constants_keep_exact_values_and_metadata_contract() -> None:
    public = importlib.import_module("reflex_app.constants.public")

    assert public.PUBLIC_SITE_URL == os.getenv("DATOSENORDEN_PUBLIC_BASE_URL", "https://datosenorden.cl").rstrip("/")
    assert public.PUBLIC_SITE_NAME == "DatosEnOrden Ciudadano"
    assert public.PUBLIC_SITE_AUTHOR == "DatosEnOrden Studio"
    assert public.PUBLIC_THEME_COLOR == "#0f766e"
    assert public.PUBLIC_OG_IMAGE_PATH == "/og-image.png"
    assert public.PUBLIC_MANIFEST_PATH == "/site.webmanifest"
    assert public.PUBLIC_OG_IMAGE_ALT == "DatosEnOrden Ciudadano: informacion publica conectada, verificable y comprensible."
    assert public.SUPPORT_DONATION_URL == os.getenv("DATOSENORDEN_SUPPORT_URL", "https://link.mercadopago.cl/datosenorden")
    assert public.SUPPORT_SOURCE_SUGGESTION_URL == "mailto:datosenorden@gmail.com?subject=Sugerir%20fuente%20oficial"
    assert public.STUDIO_CONVERSATION_URL == "mailto:datosenorden@gmail.com?subject=DatosEnOrden%20Studio"
    assert public.STUDIO_CONTACT_EMAIL == "datosenorden@gmail.com"


def test_constants_are_owned_by_constant_modules_and_entrypoint_keeps_only_app() -> None:
    routes = importlib.import_module("reflex_app.constants.routes")
    public = importlib.import_module("reflex_app.constants.public")
    entrypoint = importlib.import_module("reflex_app.reflex_app")

    for name in EXTRACTED_NAMES:
        source = public if hasattr(public, name) else routes
        assert getattr(source, name) is not None
        assert not hasattr(entrypoint, name)

    registered = {
        kwargs["route"]: page_function.__name__
        for page_function, kwargs in DECORATED_PAGES["reflex_app"]
    }
    assert len(registered) == 21
    assert set(registered) == {
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
    assert [(name, value) for name, value in vars(entrypoint).items() if value is entrypoint.app] == [("app", entrypoint.app)]

def test_reflex_app_no_longer_defines_extracted_constants_directly() -> None:
    tree = ast.parse((ROOT / "reflex_app" / "reflex_app.py").read_text(encoding="utf-8"))
    assigned = set()
    for node in tree.body:
        if isinstance(node, ast.Assign):
            assigned.update(target.id for target in node.targets if isinstance(target, ast.Name))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            assigned.add(node.target.id)

    assert assigned.isdisjoint(EXTRACTED_NAMES)
