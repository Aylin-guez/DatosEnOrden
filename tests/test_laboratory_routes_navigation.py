from reflex_app.app.registry import registered_page_modules
from reflex_app.navigation.config import PRIMARY_NAVIGATION_GROUPS


def test_laboratory_routes_and_registry():
    modules = registered_page_modules()
    routes = {"/laboratory", "/laboratory/expedient"}
    assert any(m.__name__ == "reflex_app.features.laboratory.pages" for m in modules)
    import reflex_app.reflex_app  # noqa: F401
    from reflex.page import DECORATED_PAGES
    pages = [row for rows in DECORATED_PAGES.values() for row in rows]
    assert len(pages) >= 21
    assert routes <= {str(kwargs["route"]) for _, kwargs in pages}


def test_laboratory_navigation_is_declarative():
    items = [item for group in PRIMARY_NAVIGATION_GROUPS for item in group.items]
    assert any(item.label == "Laboratorio" and item.href == "/laboratory" for item in items)
