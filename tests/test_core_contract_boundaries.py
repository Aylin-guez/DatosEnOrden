from __future__ import annotations

import ast
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CORE_CANDIDATE_MODULES = (
    "src/datosenorden/studio/source_watcher.py",
    "src/datosenorden/studio/topic_classifier.py",
    "src/datosenorden/studio/state_events.py",
    "src/datosenorden/maintenance/entity_resolution.py",
)
DISALLOWED_IMPORT_PREFIXES = (
    "reflex_app",
    "streamlit_app",
    "datosenorden.web",
    "datosenorden.maintenance.product_navigation",
    "datosenorden.maintenance.citizen_dashboard",
    "datosenorden.maintenance.citizen_reports",
    "datosenorden.maintenance.discovery_cases",
)


def test_core_candidate_modules_do_not_import_module_1_public_layers() -> None:
    violations: list[str] = []

    for relative_path in CORE_CANDIDATE_MODULES:
        module_path = PROJECT_ROOT / relative_path
        tree = ast.parse(module_path.read_text(encoding="utf-8-sig"), filename=str(module_path))
        imports = sorted(_collect_imports(tree))
        forbidden = [
            name
            for name in imports
            if any(name == prefix or name.startswith(f"{prefix}.") for prefix in DISALLOWED_IMPORT_PREFIXES)
        ]
        if forbidden:
            violations.append(f"{relative_path}: {', '.join(forbidden)}")

    assert violations == []


def _collect_imports(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names
