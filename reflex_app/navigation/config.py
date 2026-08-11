from __future__ import annotations

from reflex_app.constants.routes import (
    PAGE_ECOSYSTEM,
    PAGE_HOME,
    PAGE_LABORATORY,
    PAGE_PROJECT,
    PAGE_SEARCH,
)
from reflex_app.navigation.models import NavigationGroup, NavigationItem


PRIMARY_NAVIGATION_GROUPS: tuple[NavigationGroup, ...] = (
    NavigationGroup(
        id="primary",
        label="",
        order=1,
        items=(
            NavigationItem(id="home", label="Inicio", href="/", icon="I", group="primary", order=1, active_page=PAGE_HOME),
            NavigationItem(id="explore", label="Explorar", href="/search", icon="E", group="primary", order=2, active_page=PAGE_SEARCH),
            NavigationItem(id="sources", label="Fuentes", href="/sources", icon="F", group="primary", order=3, active_page=PAGE_ECOSYSTEM),
            NavigationItem(id="laboratory", label="Laboratorio", href="/laboratory", icon="L", group="primary", order=4, active_page=PAGE_LABORATORY),
            NavigationItem(id="about", label="Acerca de", href="/project", icon="A", group="primary", order=5, active_page=PAGE_PROJECT),
        ),
    ),
)

PRIMARY_NAVIGATION_ITEMS: tuple[NavigationItem, ...] = tuple(
    item
    for group in PRIMARY_NAVIGATION_GROUPS
    for item in group.items
)

NAVIGATION_ICON_PREFIXES: tuple[tuple[str, str], ...] = (
    tuple((item.label.lower(), item.icon) for item in PRIMARY_NAVIGATION_ITEMS)
    + (
        ("studio", "S"),
        ("apoyar", "A"),
        ("ayuda", "?"),
    )
)
