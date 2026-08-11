from __future__ import annotations

import reflex as rx


def relationship_badge(label: str) -> rx.Component:
    return rx.text(label, class_name="mini-pill mini-pill-purple")


def journey_connection() -> rx.Component:
    return rx.text("↓", class_name="journey-connection")


def search_chip(label: str) -> rx.Component:
    return rx.box(rx.text(label, class_name="search-chip-text"), class_name="search-chip")


def demo_check_item(label: str, ready) -> rx.Component:  # noqa: ANN001
    return rx.hstack(
        rx.text(rx.cond(ready, "Listo", "Pendiente"), class_name=rx.cond(ready, "badge badge-teal", "badge badge-amber")),
        rx.text(label, class_name="context-title"),
        spacing="2",
        align="center",
        class_name="demo-check-row",
    )
