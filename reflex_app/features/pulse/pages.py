from __future__ import annotations

import reflex as rx

from reflex_app.constants.routes import PAGE_HOME
from reflex_app.features.pulse.components import home_pulse_card
from reflex_app.features.pulse.state import PulseState
from reflex_app.features.search.state import SearchState
from reflex_app.layouts.page import page_section
from reflex_app.layouts.shell import shell
from reflex_app.metadata.pages import PUBLIC_OG_IMAGE_URL, _page_meta


@rx.page(
    route="/",
    title="DatosEnOrden Ciudadano - Informacion publica conectada",
    description="Busca entidades, normas, proyectos, contratos, documentos y fuentes publicas con trazabilidad visible.",
    image=PUBLIC_OG_IMAGE_URL,
    meta=_page_meta(
        "/",
        "datos publicos, documentos oficiales, evidencia, expedientes, lectura ciudadana, fuentes oficiales",
        "DatosEnOrden Ciudadano - Informacion publica conectada",
        "Busca entidades, normas, proyectos, contratos, documentos y fuentes publicas con trazabilidad visible.",
    ),
)
def home() -> rx.Component:
    return shell(
        rx.box(
            rx.text("DatosEnOrden Ciudadano", class_name="title"),
            rx.text(
                "Transformar informacion publica dispersa en conocimiento conectado, verificable y comprensible.",
                class_name="subtitle",
            ),
            rx.text("Un proyecto de DatosEnOrden Studio", class_name="badge badge-teal launch-notice"),
            rx.box(
                rx.text("Que quieres entender?", class_name="section-title"),
                rx.text(
                    "Busca un organismo, empresa, autoridad, politica, norma, proyecto, contrato, presupuesto, evento o tema publico.",
                    class_name="muted",
                ),
                rx.hstack(
                    rx.input(
                        placeholder="Hospital, ChileCompra, presupuesto, ley, contrato o entidad",
                        value=SearchState.query,
                        on_change=SearchState.set_query,
                        class_name="input search-input",
                        aria_label="Buscar informacion publica",
                    ),
                    rx.button("Explorar", on_click=SearchState.submit_main_search, class_name="button search-button"),
                    spacing="2",
                    wrap="wrap",
                    class_name="search-bar home-search-bar",
                ),
                class_name="card home-search-card",
            ),
            rx.hstack(
                rx.button("Ir a Explorar", on_click=rx.redirect("/search"), class_name="button primary-action"),
                rx.button("Ver fuentes", on_click=rx.redirect("/sources"), class_name="button button-secondary"),
                rx.text("Buscar no crea expedientes: muestra conocimiento ya disponible o lecturas preliminares.", class_name="hero-action-note"),
                spacing="3",
                wrap="wrap",
                class_name="hero-actions",
            ),
            class_name="hero home-pulse-hero",
        ),
        page_section(
            "Cambios recientes",
            rx.cond(
                PulseState.current_topic_rows,
                rx.grid(
                    rx.foreach(PulseState.current_topic_rows, home_pulse_card),
                    columns="3",
                    spacing="3",
                    class_name="responsive-grid home-pulse-grid",
                ),
                rx.text("Todavia no hay eventos publicos recientes para mostrar.", class_name="muted small"),
            ),
            subtitle="Cada tarjeta indica que cambio, que fuente lo sostiene y que entidad, documento o lectura permite abrir.",
        ),
        page_section(
            "Lecturas e investigaciones destacadas",
            rx.grid(
                rx.box(
                    rx.text("EXP-001", class_name="badge badge-teal"),
                    rx.text("Caso hospitalario o infraestructura publica", class_name="card-title"),
                    rx.text("Fixture local para demostrar entidades, documentos, cronologia, relaciones, fuentes, cobertura y preguntas abiertas.", class_name="muted small"),
                    rx.button("Abrir expediente actualizado", on_click=rx.redirect("/investigation"), class_name="button button-secondary"),
                    class_name="card public-demo-card",
                ),
                rx.box(
                    rx.text("Documento", class_name="badge badge-purple"),
                    rx.text("Ficha de documento fuente", class_name="card-title"),
                    rx.text("Lectura contextual con documento original, fragmentos, evidencias y entidades relacionadas cuando el modelo lo permite.", class_name="muted small"),
                    rx.button("Ver documento", on_click=rx.redirect("/official-document"), class_name="button button-secondary"),
                    class_name="card public-demo-card",
                ),
                columns="2",
                spacing="3",
                class_name="responsive-grid",
            ),
            subtitle="EXP-001 es un caso de prueba estable, no el centro del producto.",
        ),
        page_section(
            "Como funciona",
            rx.grid(
                rx.box(rx.text("Fuentes publicas", class_name="card-title"), rx.text("Origen identificable y limitaciones visibles.", class_name="muted small"), class_name="card flow-card"),
                rx.box(rx.text("Entidades conectadas", class_name="card-title"), rx.text("Organismos, personas, empresas, normas, proyectos y eventos relacionados.", class_name="muted small"), class_name="card flow-card"),
                rx.box(rx.text("Documentos verificables", class_name="card-title"), rx.text("Fragmentos, evidencias y enlaces a fuente original.", class_name="muted small"), class_name="card flow-card"),
                rx.box(rx.text("Conocimiento comprensible", class_name="card-title"), rx.text("Resumen primero; detalle investigativo despues.", class_name="muted small"), class_name="card flow-card"),
                columns="4",
                spacing="3",
                class_name="responsive-grid",
            ),
        ),
        on_mount=PulseState.load_home,
        active_page=PAGE_HOME,
    )
