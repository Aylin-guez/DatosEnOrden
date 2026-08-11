from __future__ import annotations

import ast
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys

from reflex.page import DECORATED_PAGES

from reflex_app.helpers.document import (
    _format_chilean_date,
    _official_document_fragment_href,
    _pdf_page_value,
)
from reflex_app.helpers.public_values import _clean, _safe_public_values
from reflex_app.helpers.routing import (
    _investigation_href,
    _query_value_from_mapping,
    _query_value_from_text,
    _router_query_value,
    _search_href,
    _shallow_getattr,
)


ROOT = Path(__file__).resolve().parents[1]
HELPER_MODULES = [
    "reflex_app.helpers.public_values",
    "reflex_app.helpers.routing",
    "reflex_app.helpers.document",
]
HELPER_PATHS = [
    ROOT / "reflex_app" / "helpers" / "__init__.py",
    ROOT / "reflex_app" / "helpers" / "public_values.py",
    ROOT / "reflex_app" / "helpers" / "routing.py",
    ROOT / "reflex_app" / "helpers" / "document.py",
]
EXTRACTED_HELPERS = {
    "_clean",
    "_format_chilean_date",
    "_investigation_href",
    "_official_document_fragment_href",
    "_pdf_page_value",
    "_query_value_from_mapping",
    "_query_value_from_text",
    "_router_query_value",
    "_safe_public_values",
    "_search_href",
    "_shallow_getattr",
}


class _AttrRouter:
    def __init__(self) -> None:
        self.query_parameters = {"q": ["consulta principal", "ignorada"]}


class _NestedRouter:
    def __init__(self) -> None:
        self.url = {"full_path": "/search?q=desde+url"}
        self.session = {"query_params": {"q": "desde session"}}


class _PublicValuesRouter:
    def __init__(self) -> None:
        self.visible_mapping = {"id": ("expediente-7", "otro")}
        self.visible_text = "/investigation?id=texto"
        self._private_text = "/investigation?id=privado"
        self.callback = lambda: None


class _BrokenGetattr:
    def __getattribute__(self, name: str) -> object:
        if name == "broken":
            raise RuntimeError("current fallback contract")
        return super().__getattribute__(name)


class _BrokenMapping:
    def get(self, key: str, fallback: object = "") -> object:
        raise RuntimeError("current fallback contract")


def test_helper_modules_import_without_reflex_services_or_core() -> None:
    probe = """
import importlib
import json
import sys

modules = [
    importlib.import_module("reflex_app.helpers.public_values"),
    importlib.import_module("reflex_app.helpers.routing"),
    importlib.import_module("reflex_app.helpers.document"),
]
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
print("HELPERS_IMPORT=" + json.dumps({
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
    payload_line = next(line for line in result.stdout.splitlines() if line.startswith("HELPERS_IMPORT="))
    assert json.loads(payload_line.removeprefix("HELPERS_IMPORT=")) == {
        "modules": HELPER_MODULES,
        "blocked": [],
    }


def test_helper_modules_have_no_forbidden_imports_or_import_time_io() -> None:
    forbidden_roots = {"reflex", "datosenorden", "deo_core"}
    forbidden_calls = {"open", "read_text", "read_bytes", "write_text", "write_bytes", "mkdir", "iterdir", "glob", "rglob"}

    for module_path in HELPER_PATHS:
        tree = ast.parse(module_path.read_text(encoding="utf-8"), filename=str(module_path))
        imports = []
        io_calls = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
            elif isinstance(node, ast.Call):
                function = node.func
                if isinstance(function, ast.Name):
                    name = function.id
                elif isinstance(function, ast.Attribute):
                    name = function.attr
                else:
                    name = ""
                if name in forbidden_calls:
                    io_calls.append(name)

        assert [name for name in imports if name.split(".")[0] in forbidden_roots] == []
        assert [name for name in imports if name == "reflex_app.reflex_app"] == []
        assert io_calls == []


def test_helpers_are_owned_by_leaf_modules_without_entrypoint_reexports() -> None:
    entrypoint = importlib.import_module("reflex_app.reflex_app")
    public_values = importlib.import_module("reflex_app.helpers.public_values")
    routing = importlib.import_module("reflex_app.helpers.routing")
    document = importlib.import_module("reflex_app.helpers.document")

    for name in EXTRACTED_HELPERS:
        source = (
            public_values
            if hasattr(public_values, name)
            else document
            if hasattr(document, name)
            else routing
        )
        assert callable(getattr(source, name))
        assert not hasattr(entrypoint, name)

    routes = [kwargs["route"] for _, kwargs in DECORATED_PAGES["reflex_app"]]
    assert len(routes) == 21
    assert len(set(routes)) == 21

def test_public_value_helpers_preserve_current_outputs() -> None:
    assert _clean(None) == "Sin dato"
    assert _clean("  valor  ") == "valor"
    assert _clean("", "fallback") == "fallback"

    values = _safe_public_values(_PublicValuesRouter())
    assert values == [{"id": ("expediente-7", "otro")}, "/investigation?id=texto"]
    assert _safe_public_values(None) == []
    assert _safe_public_values({"a": 1, "b": "dos"}) == [1, "dos"]
    assert _safe_public_values(object()) == []


def test_routing_helpers_preserve_current_href_and_query_outputs() -> None:
    assert _search_href("") == "/search"
    assert _search_href("   ") == "/search"
    assert _search_href("hospital arauco") == "/search?q=hospital+arauco"
    assert _search_href("area salud publica") == "/search?q=area+salud+publica"
    assert _search_href("\u00e1rea salud") == "/search?q=%C3%A1rea+salud"

    assert _investigation_href("") == "/investigation"
    assert _investigation_href(None) == "/investigation"
    assert _investigation_href("Servicio Salud") == "/investigation?id=Servicio+Salud"

    assert _query_value_from_mapping({"q": ["uno", "dos"]}, "q") == "uno"
    assert _query_value_from_mapping({"q": ("tres", "cuatro")}, "q") == "tres"
    assert _query_value_from_mapping({"q": "  cinco  "}, "q") == "cinco"
    assert _query_value_from_mapping({"otro": "x"}, "q") == ""
    assert _query_value_from_mapping(_BrokenMapping(), "q") == ""

    assert _query_value_from_text("?q=uno+dos", "q") == "uno dos"
    assert _query_value_from_text("/search?q=area+salud", "q") == "area salud"
    assert _query_value_from_text("/search?otro=uno", "q") == ""
    assert _query_value_from_text(None, "q") == ""


def test_router_query_value_preserves_current_router_fallbacks() -> None:
    assert _router_query_value({"query_parameters": {"q": "desde dict"}}, "q") == "desde dict"
    assert _router_query_value(_AttrRouter(), "q") == "consulta principal"
    assert _router_query_value(_NestedRouter(), "q") == "desde session"
    assert _router_query_value(_PublicValuesRouter(), "id") == "expediente-7"
    assert _router_query_value({"full_path": "/search?q=texto"}, "q") == "texto"
    assert _router_query_value(object(), "q") == ""

    broken = _BrokenGetattr()
    assert _shallow_getattr(broken, "broken", "fallback") == "fallback"


def test_document_helpers_preserve_current_outputs() -> None:
    assert _format_chilean_date("") == ""
    assert _format_chilean_date(None) == ""
    assert _format_chilean_date("2026-07-23T12:30:00") == "23-07-2026"
    assert _format_chilean_date("no-es-fecha") == "no-es-fecha"

    assert _official_document_fragment_href("", 0) == "/official-document"
    assert _official_document_fragment_href("frag 1", 2) == "/official-document?fragment_id=frag+1&page=2#fragmento-frag+1"
    assert _official_document_fragment_href("frag area", 1) == "/official-document?fragment_id=frag+area&page=1#fragmento-frag+area"
    assert _official_document_fragment_href("frag \u00e1", 2) == "/official-document?fragment_id=frag+%C3%A1&page=2#fragmento-frag+%C3%A1"

    assert _pdf_page_value(None) is None
    assert _pdf_page_value("3") == 3
    assert _pdf_page_value(0) is None
    assert _pdf_page_value("-1") is None
    assert _pdf_page_value("x") is None


def test_reflex_app_no_longer_defines_extracted_helpers_directly() -> None:
    tree = ast.parse((ROOT / "reflex_app" / "reflex_app.py").read_text(encoding="utf-8"))
    function_names = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
    assert function_names.isdisjoint(EXTRACTED_HELPERS)
