from __future__ import annotations

import reflex as rx

from reflex_app.components.common.cards import flow_card
from reflex_app.components.common.indicators import demo_check_item
from reflex_app.constants.demo import DEMO_INVESTIGATION_TARGET
from reflex_app.constants.routes import PAGE_DEMO
from reflex_app.features.demo.state import DemoState
from reflex_app.helpers.routing import _investigation_href
from reflex_app.layouts.page import page_section
from reflex_app.layouts.shell import shell
from reflex_app.metadata.pages import PUBLIC_OG_IMAGE_URL, _page_meta


@rx.page(
    route="/demo",
    title="Recorrido guiado - DatosEnOrden",
    description="Recorrido público de ejemplo para entender cómo DatosEnOrden conecta fuentes, expedientes y evidencia.",
    image=PUBLIC_OG_IMAGE_URL,
    meta=_page_meta(
        "/demo",
        "muestra pública, evidencia, expedientes, fuentes públicas, datosenorden",
        "Recorrido guiado - DatosEnOrden",
        "Recorrido público de ejemplo para entender cómo DatosEnOrden conecta fuentes, expedientes y evidencia.",
    ),
)
def demo() -> rx.Component:
    return shell(
        rx.box(
            rx.text("Recorrido guiado", class_name="title"),
            rx.text(
                "Recorrido público con datos locales de prueba. No son datos oficiales y no implican causalidad, irregularidad ni responsabilidad.",
                class_name="subtitle",
            ),
            rx.hstack(
                rx.button("Abrir expediente de ejemplo", on_click=rx.redirect(_investigation_href(DEMO_INVESTIGATION_TARGET)), class_name="button"),
                rx.button("Ver ecosistema de fuentes", on_click=rx.redirect("/ecosystem"), class_name="button button-secondary"),
                rx.button("Ver reportes ciudadanos", on_click=rx.redirect("/reports"), class_name="button button-secondary"),
                spacing="3",
                wrap="wrap",
                class_name="hero-actions",
            ),
            class_name="hero",
        ),
        page_section(
            "Checklist del recorrido",
            rx.vstack(
                demo_check_item("Fuentes cargadas", DemoState.demo_sources_ready),
                demo_check_item("Expediente disponible", DemoState.demo_investigation_ready),
                demo_check_item("Reporte generado para revisión interna", DemoState.demo_report_ready),
                spacing="2",
                align="stretch",
                class_name="demo-checklist",
            ),
            subtitle="Estado calculado desde la base local al abrir esta ruta.",
        ),
        page_section(
            "Cómo recorrer esta publicación",
            rx.grid(
                flow_card(1, "Ver fuentes disponibles", "Abrir Fuentes para explicar qué datos locales de prueba están cargados."),
                flow_card(2, "Abrir expediente de ejemplo", "Entrar al expediente canonico del Servicio de Salud Arauco Hospital de Arauco."),
                flow_card(3, "Revisar evidencia y trazabilidad", "Mostrar resumen ciudadano, seguimiento, reportes, fuentes consultadas y detalles tecnicos colapsados."),
                columns="3",
                spacing="3",
                class_name="responsive-grid",
            ),
            subtitle="Ruta recomendada para una primera lectura pública.",
        ),
        page_section(
            "Aclaración",
            rx.text(
                "Este recorrido muestra cómo se vería un expediente ciudadano al cruzar fuentes públicas. "
                "Los registros son datos locales de prueba, no oficiales, y sirven para explicar el producto sin inferir irregularidades.",
                class_name="story-summary",
            ),
            subtitle="Contexto recomendado antes de mostrar el expediente.",
        ),
        on_mount=DemoState.load_demo,
        active_page=PAGE_DEMO,
    )
