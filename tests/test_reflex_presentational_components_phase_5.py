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

from reflex_app.components.common.cards import support_action_card, tracking_evidence_card
from reflex_app.components.common.indicators import (
    demo_check_item,
    journey_connection,
    relationship_badge,
    search_chip,
)
from reflex_app.components.common.metrics import document_metric, metric, metric_card


ROOT = Path(__file__).resolve().parents[1]
COMPONENT_MODULES = [
    "reflex_app.components",
    "reflex_app.components.common",
    "reflex_app.components.common.cards",
    "reflex_app.components.common.indicators",
    "reflex_app.components.common.metrics",
]
COMPONENT_PATHS = [
    ROOT / "reflex_app" / "components" / "__init__.py",
    ROOT / "reflex_app" / "components" / "common" / "__init__.py",
    ROOT / "reflex_app" / "components" / "common" / "cards.py",
    ROOT / "reflex_app" / "components" / "common" / "indicators.py",
    ROOT / "reflex_app" / "components" / "common" / "metrics.py",
]
EXTRACTED_COMPONENTS = {
    "demo_check_item",
    "document_metric",
    "journey_connection",
    "metric",
    "metric_card",
    "relationship_badge",
    "search_chip",
    "support_action_card",
    "tracking_evidence_card",
}


def _props(component: object) -> list[str]:
    return component.render()["props"]


def _child_contents(component: object) -> list[str]:
    rendered = component.render()
    contents: list[str] = []

    def visit(node: object) -> None:
        if isinstance(node, dict):
            if "contents" in node:
                contents.append(str(node["contents"]))
            for child in node.get("children", []):
                visit(child)
            for key in ("true_value", "false_value"):
                if key in node:
                    visit(node[key])
        elif isinstance(node, list):
            for item in node:
                visit(item)

    visit(rendered)
    return contents


def test_component_modules_import_without_appstate_services_or_core() -> None:
    probe = """
import importlib
import json
import sys

modules = [
    importlib.import_module("reflex_app.components"),
    importlib.import_module("reflex_app.components.common"),
    importlib.import_module("reflex_app.components.common.cards"),
    importlib.import_module("reflex_app.components.common.indicators"),
    importlib.import_module("reflex_app.components.common.metrics"),
]
blocked = [
    name for name in sys.modules
    if name == "datosenorden"
    or name.startswith("datosenorden.")
    or name == "deo_core"
    or name.startswith("deo_core.")
    or name == "reflex_app.reflex_app"
]
print("COMPONENTS_IMPORT=" + json.dumps({
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
    payload_line = next(line for line in result.stdout.splitlines() if line.startswith("COMPONENTS_IMPORT="))
    assert json.loads(payload_line.removeprefix("COMPONENTS_IMPORT=")) == {
        "modules": COMPONENT_MODULES,
        "blocked": [],
    }


def test_component_modules_do_not_import_services_access_appstate_or_register_routes() -> None:
    for module_path in COMPONENT_PATHS:
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


def test_components_are_owned_by_common_modules_without_entrypoint_reexports() -> None:
    entrypoint = importlib.import_module("reflex_app.reflex_app")
    common = importlib.import_module("reflex_app.components.common")
    cards = importlib.import_module("reflex_app.components.common.cards")
    indicators = importlib.import_module("reflex_app.components.common.indicators")
    metrics = importlib.import_module("reflex_app.components.common.metrics")

    for name in EXTRACTED_COMPONENTS:
        source = (
            cards
            if hasattr(cards, name)
            else indicators
            if hasattr(indicators, name)
            else metrics
        )
        assert getattr(common, name) is getattr(source, name)
        assert not hasattr(entrypoint, name)

    routes = [kwargs["route"] for _, kwargs in DECORATED_PAGES["reflex_app"]]
    assert len(routes) == 21
    assert len(set(routes)) == 21

def test_component_signatures_keep_current_props_defaults_and_annotations() -> None:
    assert str(inspect.signature(metric)) == "(label: 'str', value) -> 'rx.Component'"
    assert str(inspect.signature(metric_card)) == "(label: 'str', value, helper: 'str' = '') -> 'rx.Component'"
    assert str(inspect.signature(document_metric)) == "(label: 'str', value: 'rx.Var | int') -> 'rx.Component'"
    assert str(inspect.signature(relationship_badge)) == "(label: 'str') -> 'rx.Component'"
    assert str(inspect.signature(journey_connection)) == "() -> 'rx.Component'"
    assert str(inspect.signature(search_chip)) == "(label: 'str') -> 'rx.Component'"
    assert str(inspect.signature(demo_check_item)) == "(label: 'str', ready) -> 'rx.Component'"
    assert str(inspect.signature(support_action_card)) == "(title: 'str', body: 'str', label: 'str', href: 'str') -> 'rx.Component'"
    assert str(inspect.signature(tracking_evidence_card)) == "(row: 'dict') -> 'rx.Component'"


def test_presentational_components_keep_class_names_and_copy() -> None:
    assert _props(metric("Fuentes", 7)) == ['className:"metric-card"']
    assert _child_contents(metric("Fuentes", 7)) == ["7", '"Fuentes"']

    assert _props(metric_card("Evidencia", 12, "registros")) == ['className:"summary-card product-metric-card"']
    assert '"registros"' in _child_contents(metric_card("Evidencia", 12, "registros"))

    assert _props(document_metric("referencias", 3)) == ['className:"document-metric"']
    assert _child_contents(document_metric("referencias", 3)) == ["3", '"referencias"']

    assert _props(relationship_badge("vinculo")) == ['as:"p"', 'className:"mini-pill mini-pill-purple"']
    assert _child_contents(journey_connection()) == ['"\\u2193"']
    assert _props(search_chip("ChileCompra")) == ['className:"search-chip"']

    demo = demo_check_item("Fuentes cargadas", True).render()
    assert 'className:"rx-Stack demo-check-row"' in demo["props"]
    assert '(true ? "Listo" : "Pendiente")' in _child_contents(demo_check_item("Fuentes cargadas", True))

    support = support_action_card("Titulo", "Cuerpo", "Abrir", "/support")
    assert _props(support) == ['className:"card support-action-card"']
    assert '"Titulo"' in _child_contents(support)
    assert '"Cuerpo"' in _child_contents(support)
    assert '"Abrir"' in _child_contents(support)

    evidence = tracking_evidence_card({"source": "Fuente", "label": "Etiqueta", "excerpt": "Extracto", "url": "https://example.test"})
    assert _props(evidence) == ['className:"context-item"']
    assert _child_contents(evidence) == ['"Fuente"', '"Etiqueta"', '"Extracto"', '"https://example.test"']


def test_reflex_app_no_longer_defines_extracted_components_directly() -> None:
    tree = ast.parse((ROOT / "reflex_app" / "reflex_app.py").read_text(encoding="utf-8"))
    function_names = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}

    assert function_names.isdisjoint(EXTRACTED_COMPONENTS)


def test_fresh_import_creates_one_app_and_keeps_19_routes() -> None:
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
