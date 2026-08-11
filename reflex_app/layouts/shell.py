from __future__ import annotations

import reflex as rx

from reflex_app.app.state import AppState
from reflex_app.constants.public import STUDIO_CONVERSATION_URL, SUPPORT_SOURCE_SUGGESTION_URL
from reflex_app.layouts.footer import footer_text_link
from reflex_app.layouts.page import _page_class
from reflex_app.layouts.shell_controls import scroll_top_control
from reflex_app.navigation.config import PRIMARY_NAVIGATION_GROUPS
from reflex_app.navigation.sidebar import hamburger_icon, sidebar_nav_item


def app_sidebar(active_page: str) -> rx.Component:
    nav_children = [
        rx.button(
            hamburger_icon(),
            on_click=AppState.toggle_sidebar,
            class_name="sidebar-menu-button",
        )
    ]
    for group_index, group in enumerate(PRIMARY_NAVIGATION_GROUPS):
        if group_index > 0:
            nav_children.append(rx.box(class_name="sidebar-spacer"))
        nav_children.extend(sidebar_nav_item(item, active_page) for item in group.items)

    return rx.box(
        rx.vstack(
            *nav_children,
            spacing="1",
            align="stretch",
            class_name="sidebar-nav",
        ),
        class_name=rx.cond(AppState.sidebar_collapsed, "app-sidebar app-sidebar-collapsed", "app-sidebar"),
    )

def shell(*children: rx.Component, active_page: str, **props) -> rx.Component:
    header_search = rx.box(
        rx.cond(
            AppState.header_search_open,
            rx.hstack(
                rx.input(
                    placeholder="Buscar entidad",
                    value=AppState.header_search_query,
                    on_change=AppState.set_header_search_query,
                    class_name="input header-search-input",
                    aria_label="Buscar entidad",
                ),
                rx.button("Ir", on_click=AppState.submit_header_search, class_name="header-search-submit"),
                spacing="2",
                align="center",
                class_name="header-search-popover header-search-popover-open",
            ),
            rx.button("Buscar", on_click=AppState.toggle_header_search, class_name="header-search-toggle"),
        ),
        class_name="header-search",
    )
    shell_class = rx.cond(
        AppState.sidebar_collapsed,
        f"shell theme-dark sidebar-collapsed {_page_class(active_page)}",
        f"shell theme-dark {_page_class(active_page)}",
    )
    return rx.box(
        app_sidebar(active_page),
        rx.box(
            rx.box(
                rx.hstack(
                    rx.link("DatosEnOrden Ciudadano", href="/", class_name="brand"),
                    header_search,
                    justify="between",
                    align="center",
                    class_name="nav-inner",
                ),
                class_name="shell-header shell-header-sidebar-ready",
            ),
            rx.cond(
                AppState.error_message != "",
                rx.box(
                    rx.text("Esta pagina necesita una segunda carga", class_name="eyebrow"),
                    rx.text(
                        "No pudimos actualizar por completo esta vista con los datos locales disponibles. Puedes reintentar o volver a una ruta estable.",
                        class_name="muted",
                    ),
                    rx.hstack(
                        rx.button("Volver al inicio", on_click=rx.redirect("/"), class_name="button button-secondary"),
                        rx.button("Buscar", on_click=rx.redirect("/search"), class_name="button button-secondary"),
                        spacing="2",
                        wrap="wrap",
                        class_name="shell-alert-actions",
                    ),
                    class_name="card error shell-alert",
                ),
            ),
            rx.vstack(*children, spacing="5", align="stretch", class_name="page"),
            app_footer(),
            class_name="shell-main",
        ),
        scroll_top_control(),
        class_name=shell_class,
        **props,
    )


def app_footer() -> rx.Component:
    return rx.box(
        rx.grid(
            rx.box(
                rx.text("DATOSENORDEN CIUDADANO", class_name="footer-column-title"),
                rx.text("Explorar, leer y verificar información pública con contexto documental.", class_name="footer-copy footer-column-copy"),
                footer_text_link("♥", "Apoyar DatosEnOrden", "/support"),
                footer_text_link("⌕", "Explorar", "/search"),
                footer_text_link("+", "Sugerir una fuente", SUPPORT_SOURCE_SUGGESTION_URL),
                footer_text_link("i", "Acerca de", "/project"),
                class_name="footer-column",
            ),
            rx.box(
                rx.text("DATOSENORDEN STUDIO", class_name="footer-column-title"),
                rx.text("Herramientas para equipos que necesitan expedientes, conectores y evidencia verificable.", class_name="footer-copy footer-column-copy"),
                footer_text_link("", "Studio", "/studio"),
                footer_text_link("✉", "Contacto comercial", STUDIO_CONVERSATION_URL),
                class_name="footer-column",
            ),
            columns="2",
            spacing="4",
            class_name="footer-grid",
        ),
        class_name="site-footer",
    )
