from __future__ import annotations

import ast
from pathlib import Path

from reflex.page import DECORATED_PAGES

import reflex_app.reflex_app as entrypoint
from reflex_app.app.state import AppState

ROOT = Path(__file__).resolve().parents[1]
MONOLITH = ROOT / "reflex_app" / "reflex_app.py"
FEATURES = ROOT / "reflex_app" / "features"

DOMAIN_FIELDS = {
    "query",
    "results",
    "knowledge_documents",
    "topic_title",
    "selected_entity_id",
    "relationship_rows",
    "tracking_items",
    "citizen_report_sections",
    "dashboard_budget_rows",
    "real_sources",
}


def test_final_routes_are_unique_and_still_21() -> None:
    pages = [(page, kwargs) for page, kwargs in DECORATED_PAGES["reflex_app"]]
    routes = [kwargs["route"] for _, kwargs in pages]

    assert len(routes) == 21
    assert len(set(routes)) == 21
    assert "/investigation" in routes
    assert {"/laboratory", "/laboratory/expedient"} <= set(routes)
    assert not any(route == "/lab" or route == "/laboratorio" for route in routes)


def test_feature_modules_do_not_import_entrypoint() -> None:
    offenders = []
    for path in FEATURES.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        source = path.read_text(encoding="utf-8")
        if "reflex_app.reflex_app" in source:
            offenders.append(path.relative_to(ROOT).as_posix())
    assert offenders == []


def test_entrypoint_keeps_bootstrap_not_domain_state() -> None:
    source = MONOLITH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    top_classes = {node.name for node in tree.body if isinstance(node, ast.ClassDef)}

    assert "AppState" not in top_classes
    assert "create_app(" in source
    assert source.count("@rx.page") == 0
    assert DOMAIN_FIELDS.isdisjoint(AppState.vars)
    for adapter in ["load_investigation", "open_investigation", "open_canonical_investigation"]:
        assert not hasattr(AppState, adapter)
