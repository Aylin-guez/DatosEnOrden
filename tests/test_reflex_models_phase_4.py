from __future__ import annotations

import ast
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import get_type_hints

from reflex.page import DECORATED_PAGES

from reflex_app.models.investigation import INVESTIGATION_TOPICS, InvestigationTopic
from reflex_app.models.source import SOURCE_COVERAGE_TEMPLATE, SourceCoverageTemplateRow


ROOT = Path(__file__).resolve().parents[1]
MODEL_PATHS = [
    ROOT / "reflex_app" / "models" / "__init__.py",
    ROOT / "reflex_app" / "models" / "document.py",
    ROOT / "reflex_app" / "models" / "investigation.py",
    ROOT / "reflex_app" / "models" / "source.py",
]
EXTRACTED_MODEL_VALUES = {"INVESTIGATION_TOPICS", "SOURCE_COVERAGE_TEMPLATE"}


def test_models_import_without_reflex_appstate_services_or_core() -> None:
    probe = """
import importlib
import json
import sys

modules = [
    importlib.import_module("reflex_app.models"),
    importlib.import_module("reflex_app.models.investigation"),
    importlib.import_module("reflex_app.models.source"),
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
print("MODELS_IMPORT=" + json.dumps({
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
    payload_line = next(line for line in result.stdout.splitlines() if line.startswith("MODELS_IMPORT="))
    assert json.loads(payload_line.removeprefix("MODELS_IMPORT=")) == {
        "modules": [
            "reflex_app.models",
            "reflex_app.models.investigation",
            "reflex_app.models.source",
        ],
        "blocked": [],
    }


def test_model_modules_have_no_forbidden_imports_or_appstate_class() -> None:
    forbidden_roots = {"reflex", "datosenorden", "deo_core"}

    for module_path in MODEL_PATHS:
        tree = ast.parse(module_path.read_text(encoding="utf-8"), filename=str(module_path))
        imports = []
        classes = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
            elif isinstance(node, ast.ClassDef):
                classes.append(node.name)

        assert [name for name in imports if name.split(".")[0] in forbidden_roots] == []
        assert [name for name in imports if name == "reflex_app.reflex_app"] == []
        assert "AppState" not in classes


def test_extracted_model_values_keep_current_shape_and_values() -> None:
    assert len(SOURCE_COVERAGE_TEMPLATE) == 11
    assert SOURCE_COVERAGE_TEMPLATE[0] == {
        "source": "ChileCompra",
        "status": "activo con datos",
        "contribution": "Compras publicas, proveedores, contratos y evidencia de adquisiciones.",
    }
    assert SOURCE_COVERAGE_TEMPLATE[-1] == {
        "source": "Sanciones y Procedimientos",
        "status": "prototipo con datos",
        "contribution": "Procedimientos y resoluciones administrativas de prueba con trazabilidad local.",
    }
    assert all(set(row) == {"source", "status", "contribution"} for row in SOURCE_COVERAGE_TEMPLATE)

    assert len(INVESTIGATION_TOPICS) == 11
    assert INVESTIGATION_TOPICS[0] == {
        "label": "Organismos publicos",
        "example": "SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO",
    }
    assert INVESTIGATION_TOPICS[-1] == {
        "label": "Sanciones y procedimientos",
        "example": "Procedimientos y resoluciones administrativas de prueba",
    }
    assert all(set(row) == {"label", "example"} for row in INVESTIGATION_TOPICS)


def test_typed_dict_models_expose_expected_annotations() -> None:
    assert get_type_hints(SourceCoverageTemplateRow) == {
        "source": str,
        "status": str,
        "contribution": str,
    }
    assert get_type_hints(InvestigationTopic) == {
        "label": str,
        "example": str,
    }


def test_models_are_owned_by_model_modules_without_entrypoint_reexports() -> None:
    entrypoint = importlib.import_module("reflex_app.reflex_app")
    models = importlib.import_module("reflex_app.models")
    investigation = importlib.import_module("reflex_app.models.investigation")
    source = importlib.import_module("reflex_app.models.source")

    assert models.INVESTIGATION_TOPICS is investigation.INVESTIGATION_TOPICS
    assert models.SOURCE_COVERAGE_TEMPLATE is source.SOURCE_COVERAGE_TEMPLATE
    assert not hasattr(entrypoint, "INVESTIGATION_TOPICS")
    assert not hasattr(entrypoint, "SOURCE_COVERAGE_TEMPLATE")

    routes = [kwargs["route"] for _, kwargs in DECORATED_PAGES["reflex_app"]]
    assert len(routes) == 21
    assert len(set(routes)) == 21

def test_reflex_app_no_longer_defines_extracted_models_directly() -> None:
    tree = ast.parse((ROOT / "reflex_app" / "reflex_app.py").read_text(encoding="utf-8"))
    assigned = set()
    for node in tree.body:
        if isinstance(node, ast.Assign):
            assigned.update(target.id for target in node.targets if isinstance(target, ast.Name))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            assigned.add(node.target.id)

    assert assigned.isdisjoint(EXTRACTED_MODEL_VALUES)
