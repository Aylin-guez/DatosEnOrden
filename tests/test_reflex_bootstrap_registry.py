from __future__ import annotations

import reflex as rx
from reflex.page import DECORATED_PAGES

from reflex_app.app.bootstrap import create_app, global_head_components, public_hydrate_fallback
from reflex_app.app.registry import registered_page_modules
from reflex_app.app.styles import style


def test_registry_is_explicit_and_routes_are_not_duplicated() -> None:
    modules = registered_page_modules()
    names = [module.__name__ for module in modules]

    assert names == [
        "reflex_app.app.not_found",
        "reflex_app.features.pulse.pages",
        "reflex_app.features.sources.pages",
        "reflex_app.features.demo.pages",
        "reflex_app.features.document_reading.pages",
        "reflex_app.features.institutional.pages",
        "reflex_app.features.search.pages",
        "reflex_app.features.tracking.pages",
        "reflex_app.features.reports.pages",
        "reflex_app.features.dashboard.pages",
        "reflex_app.features.public_record.pages",
        "reflex_app.features.laboratory.pages",
    ]
    routes = [kwargs["route"] for _, kwargs in DECORATED_PAGES["reflex_app"]]
    assert len(routes) == len(set(routes)) == 21
    assert {"/laboratory", "/laboratory/expedient"} <= set(routes)


def test_bootstrap_creates_reflex_app_with_public_head_components() -> None:
    app = create_app(style=style, head_components=global_head_components, hydrate_fallback=public_hydrate_fallback())

    assert isinstance(app, rx.App)
