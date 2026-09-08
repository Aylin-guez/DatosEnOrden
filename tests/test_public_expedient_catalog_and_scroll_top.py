from __future__ import annotations

import inspect
from pathlib import Path

from reflex.page import DECORATED_PAGES

from datosenorden.application.real_expedient import public_facade
from reflex_app.layouts.shell import shell
from reflex_app.layouts.shell_controls import scroll_top_control


def test_published_catalog_uses_the_composed_projection_and_excludes_demo(monkeypatch) -> None:
    rows = [
        {"id": "EXP-001", "provenance_class": "DEMO"},
        {"id": "EXP-REAL-B", "provenance_class": "REAL"},
        {"id": "EXP-REAL-A", "provenance_class": "REAL"},
    ]
    monkeypatch.setattr(public_facade, "list_public_expedient_catalog", lambda: rows)

    assert public_facade.list_published_real_expedient_catalog() == rows[1:]


def test_laboratory_and_published_catalogs_have_distinct_provenance_boundaries() -> None:
    source = Path("reflex_app/features/laboratory/state.py").read_text(encoding="utf-8")
    laboratory_loader = source[source.index("def load_catalog"):source.index("def load_published_catalog")]
    published_loader = source[source.index("def load_published_catalog"):source.index("def load_expedient")]
    assert 'row.get("provenance_class") != "REAL"' in laboratory_loader
    assert "list_published_real_expedient_catalog()" in published_loader


def test_catalog_route_and_explore_link_use_the_public_catalog_boundary() -> None:
    import reflex_app.reflex_app  # noqa: F401

    routes = {kwargs["route"] for _, kwargs in DECORATED_PAGES["reflex_app"]}
    assert "/expedientes" in routes
    assert len(routes) == 23
    search_components = Path("reflex_app/features/search/components.py").read_text(encoding="utf-8")
    assert 'href="/expedientes"' in search_components
    assert 'href="/laboratory"' not in search_components[search_components.index("def guided_discovery_panel"):search_components.index("def public_expedient_card")]


def test_scroll_top_targets_the_document_scrolling_owner_after_hydration() -> None:
    source = inspect.getsource(scroll_top_control)
    assert "document.scrollingElement || document.documentElement" in source
    assert "owner.scrollTo({ top: 0, behavior: 'smooth' })" in source
    assert "scrollOwner.scrollTop" in source
    assert inspect.getsource(shell).count("scroll_top_control()") == 1
    assert "show_built_with_reflex=False" in Path("rxconfig.py").read_text(encoding="utf-8")
