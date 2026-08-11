from __future__ import annotations

import reflex as rx

from reflex_app.navigation.config import NAVIGATION_ICON_PREFIXES
from reflex_app.navigation.models import NavigationItem


def _sidebar_nav_class(active: bool) -> str:
    return "sidebar-nav-link sidebar-nav-link-active" if active else "sidebar-nav-link"


def _nav_icon_for_label(label: str) -> str:
    normalized = label.lower()
    for prefix, icon in NAVIGATION_ICON_PREFIXES:
        if normalized.startswith(prefix):
            return icon
    return label[:1].upper() or "•"


def sidebar_nav_link(label: str, href: str, active: bool) -> rx.Component:
    return rx.link(
        rx.text(_nav_icon_for_label(label), class_name="sidebar-initial"),
        rx.text(label, class_name="sidebar-label"),
        href=href,
        class_name=_sidebar_nav_class(active),
    )


def hamburger_icon() -> rx.Component:
    return rx.vstack(
        rx.box(class_name="hamburger-line"),
        rx.box(class_name="hamburger-line"),
        rx.box(class_name="hamburger-line"),
        spacing="1",
        align="center",
        class_name="hamburger-icon",
    )


def sidebar_group_label(label: str) -> rx.Component:
    return rx.text(label, class_name="sidebar-group-label")


def sidebar_nav_item(item: NavigationItem, active_page: str) -> rx.Component:
    return sidebar_nav_link(item.label, item.href, active_page == item.active_page)
