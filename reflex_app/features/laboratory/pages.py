from __future__ import annotations

import reflex as rx

from reflex_app.constants.routes import PAGE_LABORATORY, PAGE_LABORATORY_EXPEDIENT
from reflex_app.features.laboratory.components import (
    expedient_header,
    expedition_catalog_card,
    laboratory_header,
    participation_gate,
    section_tabs,
)
from reflex_app.features.laboratory.state import LaboratoryState
from reflex_app.layouts.page import page_section
from reflex_app.layouts.shell import shell
from reflex_app.metadata.pages import PUBLIC_OG_IMAGE_URL, _page_meta


@rx.page(
    route="/laboratory",
    title="Laboratorio de Políticas Públicas - DatosEnOrden",
    description="Lectura pública de problemas, hipótesis, evidencia, indicadores y fuentes.",
    image=PUBLIC_OG_IMAGE_URL,
    meta=_page_meta(
        "/laboratory",
        "laboratorio, políticas públicas, problemas, hipótesis, evidencia, indicadores",
        "Laboratorio de Políticas Públicas - DatosEnOrden",
        "Lectura pública de problemas, hipótesis, evidencia, indicadores y fuentes.",
    ),
    on_load=LaboratoryState.load_catalog,
)
def laboratory() -> rx.Component:
    return shell(
        laboratory_header(),
        page_section(
            "Catálogo de Expedientes",
            rx.cond(
                LaboratoryState.catalog_rows,
                rx.grid(rx.foreach(LaboratoryState.catalog_rows, expedition_catalog_card), columns="2", spacing="3", class_name="responsive-grid"),
                rx.cond(
                    LaboratoryState.load_status == "error",
                    rx.text(LaboratoryState.error_message, class_name="muted small"),
                    rx.text("Datos en preparación.", class_name="muted small"),
                ),
            ),
            subtitle="Primera versión pública: un Expediente demostrativo, sin prometer investigación todavía no realizada.",
        ),
        page_section(
            "Qué hace el Laboratorio",
            rx.grid(
                rx.box(rx.text("Estudia problemas", class_name="card-title"), rx.text("Delimita alcance, población, territorio y periodo.", class_name="muted small"), class_name="card"),
                rx.box(rx.text("Compara hipótesis", class_name="card-title"), rx.text("Expone mecanismos, beneficios esperados y riesgos sin cerrar conclusiones.", class_name="muted small"), class_name="card"),
                rx.box(rx.text("Organiza evidencia", class_name="card-title"), rx.text("Conserva fuentes, fragmentos y límites visibles.", class_name="muted small"), class_name="card"),
                columns="3",
                spacing="3",
                class_name="responsive-grid",
            ),
        ),
        page_section(
            "Estado de desarrollo",
            rx.text("Primera versión pública. Los datos todavía están en investigación y la participación aún no está habilitada.", class_name="story-summary"),
        ),
        active_page=PAGE_LABORATORY,
    )


@rx.page(
    route="/laboratory/expedient",
    title="Expediente del Laboratorio - DatosEnOrden",
    description="Ficha pública de un Expediente de políticas públicas.",
    image=PUBLIC_OG_IMAGE_URL,
    meta=_page_meta(
        "/laboratory/expedient",
        "expediente, laboratorio, hipótesis, evidencia, indicadores, fuentes",
        "Expediente del Laboratorio - DatosEnOrden",
        "Ficha pública de un Expediente de políticas públicas.",
    ),
    on_load=LaboratoryState.load_expedient,
)
def laboratory_expedient() -> rx.Component:
    return shell(
        rx.cond(
            LaboratoryState.load_status == "not_found",
            rx.box(
                rx.text("Expediente no encontrado", class_name="title"),
                rx.text("No encontramos un Expediente público con ese identificador.", class_name="subtitle"),
                rx.link("Volver al Laboratorio", href="/laboratory", class_name="button"),
                class_name="hero",
            ),
            rx.cond(
                LaboratoryState.load_status == "error",
                rx.box(
                    rx.text("No pudimos cargar el Expediente", class_name="title"),
                    rx.text(LaboratoryState.error_message, class_name="muted small"),
                    class_name="hero",
                ),
                rx.vstack(
                    expedient_header(),
                    reading_progress_panel(),
                    section_tabs(),
                    spacing="4",
                    align="stretch",
                    class_name="laboratory-expedient-shell",
                ),
            ),
        ),
        active_page=PAGE_LABORATORY_EXPEDIENT,
    )


def reading_progress_panel() -> rx.Component:
    return rx.box(
        rx.text("Lectura obligatoria antes de participar", class_name="context-title"),
        rx.text("Progreso: ", LaboratoryState.reading_progress, "% · secciones visitadas: ", LaboratoryState.visited_sections.length(), " de 8", class_name="muted small"),
        rx.cond(
            LaboratoryState.reading_complete,
            rx.text("Lectura completa. La participación sigue siendo informativa en esta fase.", class_name="badge badge-green"),
            rx.text("Revisa Resumen, Problema, Evidencia, Afirmaciones, Hipótesis, Indicadores, Fuentes y Relaciones.", class_name="muted small"),
        ),
        participation_gate(),
        class_name="card laboratory-progress-panel",
    )
