from __future__ import annotations

from collections.abc import Callable

import reflex as rx

from reflex_app.components.common.cards import loading_placeholder_card
from reflex_app.constants.public import (
    PUBLIC_MANIFEST_PATH,
    PUBLIC_SITE_NAME,
    PUBLIC_THEME_COLOR,
)


def public_hydrate_fallback() -> rx.Component:
    return rx.box(
        rx.box(
            rx.hstack(
                rx.text(PUBLIC_SITE_NAME, class_name="brand"),
                rx.text("Cargando una lectura verificable...", class_name="muted small"),
                justify="between",
                align="center",
                class_name="nav-inner",
            ),
            class_name="shell-header",
        ),
        rx.vstack(
            rx.box(
                rx.box(class_name="loading-skeleton-line loading-skeleton-line-short"),
                rx.box(class_name="loading-skeleton-line loading-skeleton-line-medium"),
                rx.box(class_name="loading-skeleton-line"),
                class_name="hero loading-skeleton-hero",
            ),
            rx.grid(
                loading_placeholder_card("Preparando documento", "Montamos la lectura principal y sus enlaces publicos."),
                loading_placeholder_card("Sincronizando evidencia", "Organizamos fragmentos, referencias y contexto ciudadano."),
                loading_placeholder_card("Abriendo rutas utiles", "Dejamos lista la navegacion a busqueda, fuentes e informes."),
                columns="3",
                spacing="3",
                class_name="responsive-grid loading-skeleton-grid",
            ),
            spacing="5",
            align="stretch",
            class_name="page",
        ),
        class_name="shell theme-dark loading-shell",
    )


def global_head_components() -> list[rx.Component]:
    return [
        rx.el.link(rel="icon", href="/favicon.ico"),
        rx.el.link(rel="apple-touch-icon", href="/apple-touch-icon.png"),
        rx.el.link(rel="manifest", href=PUBLIC_MANIFEST_PATH),
        rx.el.meta(name="application-name", content=PUBLIC_SITE_NAME),
        rx.el.meta(name="apple-mobile-web-app-title", content=PUBLIC_SITE_NAME),
        rx.el.meta(name="theme-color", content=PUBLIC_THEME_COLOR),
    ]


def create_app(style: dict, head_components: Callable[[], list[rx.Component]], hydrate_fallback: rx.Component) -> rx.App:
    return rx.App(
        style=style,
        head_components=head_components(),
        html_lang="es",
        hydrate_fallback=hydrate_fallback,
    )
