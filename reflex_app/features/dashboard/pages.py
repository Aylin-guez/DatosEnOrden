from __future__ import annotations

import reflex as rx

from reflex_app.components.common.metrics import metric
from reflex_app.constants.routes import PAGE_DASHBOARD
from reflex_app.features.dashboard.components import dashboard_budget_card, discovery_case_card, search_example_card
from reflex_app.features.dashboard.state import DashboardState
from reflex_app.layouts.page import page_section
from reflex_app.layouts.shell import shell
from reflex_app.metadata.pages import PUBLIC_OG_IMAGE_URL, _page_meta


@rx.page(
    route="/dashboard",
    title="Vista ciudadana - DatosEnOrden",
    description="Vista ciudadana de presupuesto, compras, proveedores y reuniones para explorar datos locales de muestra.",
    image=PUBLIC_OG_IMAGE_URL,
    meta=_page_meta(
        "/dashboard",
        "vista ciudadana, presupuesto, compras públicas, proveedores, reuniones",
        "Vista ciudadana - DatosEnOrden",
        "Vista ciudadana de presupuesto, compras, proveedores y reuniones para explorar datos locales de muestra.",
    ),
    on_load=DashboardState.load_dashboard,
)
def dashboard() -> rx.Component:
    return shell(
        rx.box(
            rx.text("¿Dónde fue mi plata?", class_name="title"),
            rx.text(
                "Una vista ciudadana de muestra que cruza presupuesto, compras, proveedores, reuniones y autoridades visibles.",
                class_name="subtitle",
            ),
            rx.hstack(
                rx.button("Explorar ecosistema", on_click=rx.redirect("/ecosystem"), class_name="button"),
                rx.button("Buscar entidad", on_click=rx.redirect("/search"), class_name="button button-secondary"),
                spacing="3",
                wrap="wrap",
                class_name="hero-actions",
            ),
            class_name="hero",
        ),
        page_section(
            "Resumen ciudadano",
            rx.grid(
                metric("Presupuesto", DashboardState.dashboard_budget_total),
                metric("Contratos", DashboardState.dashboard_contracts),
                metric("Proveedores", DashboardState.dashboard_suppliers),
                metric("Reuniones", DashboardState.dashboard_meetings),
                metric("Autoridades", DashboardState.dashboard_authorities),
                columns="5",
                spacing="3",
                class_name="responsive-grid",
            ),
            subtitle="Indicadores compuestos desde los datos de muestra disponibles.",
        ),
        page_section(
            "Presupuesto de muestra",
            rx.text(f"Moneda de referencia: {DashboardState.dashboard_budget_currency}", class_name="muted small"),
            rx.cond(
                DashboardState.dashboard_budget_rows,
                rx.grid(
                    rx.foreach(DashboardState.dashboard_budget_rows, dashboard_budget_card),
                    columns="2",
                    spacing="3",
                    class_name="responsive-grid",
                ),
                rx.text("No hay registros presupuestarios disponibles.", class_name="muted small"),
            ),
            subtitle="Moneda de referencia en los datos de muestra.",
        ),
        page_section(
            "Expedientes destacados",
            rx.cond(
                DashboardState.dashboard_featured_entities,
                rx.grid(
                    rx.foreach(DashboardState.dashboard_featured_entities, search_example_card),
                    columns="2",
                    spacing="3",
                    class_name="responsive-grid",
                ),
                rx.text("No hay expedientes destacados disponibles.", class_name="muted small"),
            ),
            subtitle="Abre los expedientes con evidencia visible y trazabilidad.",
        ),
        page_section(
            "Casos guiados",
            rx.cond(
                DashboardState.dashboard_discovery_cases,
                rx.grid(
                    rx.foreach(DashboardState.dashboard_discovery_cases, discovery_case_card),
                    columns="2",
                    spacing="3",
                    class_name="responsive-grid",
                ),
                rx.text("No hay casos guiados disponibles.", class_name="muted small"),
            ),
            subtitle="Entradas rápidas para explorar sin saber qué buscar.",
        ),
        on_mount=DashboardState.load_dashboard,
        active_page=PAGE_DASHBOARD,
    )
