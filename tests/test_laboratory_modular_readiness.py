from __future__ import annotations

import ast
import json
from pathlib import Path

from reflex.page import DECORATED_PAGES

import reflex_app.reflex_app  # noqa: F401


ROOT = Path(__file__).resolve().parents[1]
LABORATORY = ROOT / "reflex_app" / "features" / "laboratory"
ARCHITECTURE = ROOT / "docs" / "architecture" / "frontend" / "DEO_CIUDADANO_LABORATORY_ARCHITECTURE_2026-07-24.md"


def _imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    return imports


def test_laboratory_has_the_declared_modular_boundary() -> None:
    assert sorted(path.name for path in LABORATORY.glob("*.py")) == [
        "__init__.py",
        "components.py",
        "models.py",
        "pages.py",
        "state.py",
    ]

    for path in LABORATORY.glob("*.py"):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        imports = _imports(path)
        forbidden = [
            name
            for name in imports
            if name == "reflex_app.reflex_app"
            or name.startswith("reflex_app.reflex_app.")
            or name == "deo_core"
            or name.startswith("deo_core.")
            or "bricks" in name.lower()
        ]
        assert forbidden == []
        assert not [node for node in ast.walk(tree) if isinstance(node, ast.AsyncFunctionDef)]


def test_laboratory_has_route_and_navigation_registration() -> None:
    routes = [kwargs["route"] for _, kwargs in DECORATED_PAGES["reflex_app"]]
    assert {"/laboratory", "/laboratory/expedient"} <= set(routes)

    registry = (ROOT / "reflex_app" / "app" / "registry.py").read_text(encoding="utf-8").lower()
    navigation = (ROOT / "reflex_app" / "navigation" / "config.py").read_text(encoding="utf-8").lower()
    assert "features.laboratory" in registry
    assert "laboratory" in navigation


def test_laboratory_documentation_requires_the_future_modular_contract() -> None:
    text = ARCHITECTURE.read_text(encoding="utf-8")
    for requirement in (
        "state propio",
        "modelos",
        "clientes o casos de uso propios",
        "navegacion declarativa",
        "imports explicitos",
        "navegacion declarativa",
        "AppState",
    ):
        assert requirement in text
