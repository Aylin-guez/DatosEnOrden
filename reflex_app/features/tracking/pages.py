from __future__ import annotations

import reflex as rx

from reflex_app.components.common.cards import help_card, tracking_evidence_card
from reflex_app.constants.demo import DEMO_INVESTIGATION_TARGET
from reflex_app.constants.routes import PAGE_TRACKING
from reflex_app.components.common.cards import card_grid_or_empty, next_step_card, tracking_event_card
from reflex_app.features.tracking.components import tracking_document_card, tracking_item_card
from reflex_app.features.tracking.state import TrackingState
from reflex_app.helpers.routing import _investigation_href
from reflex_app.layouts.page import page_section
from reflex_app.layouts.shell import shell
from reflex_app.metadata.pages import PUBLIC_OG_IMAGE_URL, _page_meta


@rx.page(
    route="/tracking",
    title="Cronología - DatosEnOrden",
    description="Cronología local de documentos, propuestas, estados, evidencia, expedientes relacionados y cambios históricos.",
    image=PUBLIC_OG_IMAGE_URL,
    meta=_page_meta(
        "/tracking",
        "cronología, seguimiento, documentos, evidencia, cambios",
        "Cronología - DatosEnOrden",
        "Cronología local de documentos, propuestas, estados, evidencia, expedientes relacionados y cambios históricos.",
    ),
    on_load=TrackingState.load_tracking,
)
def tracking() -> rx.Component:
    return shell(
        rx.box(
            rx.text("Sigue la historia de una propuesta pública", class_name="title"),
            rx.text(
                "Cronología local de documentos, propuestas, estados, evidencia, expedientes relacionados y cambios históricos.",
                class_name="subtitle",
            ),
            rx.hstack(
                rx.button("Abrir expediente", on_click=TrackingState.open_tracking_investigation, class_name="button"),
                rx.button("Ver recorrido", on_click=rx.redirect("/demo"), class_name="button button-secondary"),
                spacing="3",
                wrap="wrap",
                class_name="hero-actions",
            ),
            class_name="hero",
        ),
        page_section(
            "Qué significa cronología",
            rx.grid(
                help_card("Estado", "Indica en qué punto está una historia documental según los datos disponibles."),
                help_card("Evento", "Es un hito con fecha que ayuda a entender qué pasó antes y después."),
                help_card("Timeline", "Ordena eventos para leer una historia completa, no solo datos sueltos."),
                columns="3",
                spacing="3",
                class_name="responsive-grid",
            ),
            subtitle="Una forma simple de seguir cambios en el tiempo.",
        ),
        page_section(
            "Seguimientos disponibles",
            rx.cond(
                TrackingState.tracking_items,
                rx.grid(
                    rx.foreach(TrackingState.tracking_items, tracking_item_card),
                    columns="2",
                    spacing="3",
                    class_name="responsive-grid",
                ),
                rx.text("No hay seguimientos locales disponibles.", class_name="muted small"),
            ),
            subtitle="Seguimientos locales marcados como datos de prueba, sin APIs externas ni PDFs pesados.",
        ),
        page_section(
            "Timeline de seguimiento",
            rx.text(TrackingState.tracking_summary, class_name="story-summary"),
            rx.hstack(
                rx.text(TrackingState.tracking_current_status, class_name="badge badge-teal"),
                rx.text("Muestra local no oficial", class_name="mini-pill evidence-trust"),
                spacing="2",
                wrap="wrap",
            ),
            rx.grid(
                rx.foreach(TrackingState.tracking_events, tracking_event_card),
                columns="1",
                spacing="4",
                class_name="timeline-list",
            ),
            subtitle="Propuesta -> documento oficial -> presupuesto -> compra pública -> proveedor -> publicación/cargo -> control -> expediente relacionado.",
        ),
        page_section(
            "Documentos oficiales relacionados",
            card_grid_or_empty(
                TrackingState.tracking_documents,
                tracking_document_card,
                columns="2",
                empty_title="Todavía no hay documentos relacionados publicados",
                empty_body="Este seguimiento aún no expone documentos oficiales adicionales en la publicación actual.",
                action_label="Ver documento fuente",
                href="/official-document",
            ),
            subtitle="Estrategia liviana: metadata, URL, hash opcional, resumen y fuente.",
        ),
        page_section(
            "Expedientes relacionados",
            rx.box(
                rx.text(TrackingState.tracking_expediente_target, class_name="card-title"),
                rx.text("Expediente ciudadano conectado al seguimiento por evidencia local.", class_name="muted small"),
                rx.button("Abrir expediente", on_click=TrackingState.open_tracking_investigation, class_name="button"),
                class_name="card",
            ),
            subtitle="La cronología no reemplaza el expediente: lo conecta con historia documental.",
        ),
        page_section(
            "Evidencia y fuentes consultadas",
            card_grid_or_empty(
                TrackingState.tracking_evidence,
                tracking_evidence_card,
                columns="2",
                empty_title="Sin evidencia publicada en esta cronología",
                empty_body="Cuando el seguimiento tenga referencias visibles, aparecerán aqué con su contexto de lectura.",
                action_label="Explorar fuentes",
                href="/sources",
            ),
            rx.cond(
                TrackingState.tracking_related_sources,
                rx.hstack(
                    rx.foreach(TrackingState.tracking_related_sources, lambda item: rx.text(item, class_name="search-chip")),
                    spacing="2",
                    wrap="wrap",
                ),
                rx.text("Todavía no hay fuentes relacionadas publicadas para este seguimiento.", class_name="muted small"),
            ),
            subtitle="Referencias locales descriptivas; no afirman causalidad, irregularidad ni responsabilidad.",
        ),
        page_section(
            "Siguientes pasos",
            rx.grid(
                next_step_card("Abrir expediente", "Ver la entidad, relaciones y evidencia asociada.", "Ir al expediente", _investigation_href(DEMO_INVESTIGATION_TARGET)),
                next_step_card("Leer reporte ciudadano", "Ver una lectura tipo articulo del caso.", "Ir a Informes", "/reports"),
                next_step_card("Ver documento fuente", "Abrir el visor para revisar paginas y fragmentos.", "Ver documento", "/official-document"),
                columns="3",
                spacing="3",
                class_name="responsive-grid",
            ),
            subtitle="Por ahora no hay suscripciones reales; el seguimiento es local y read-only.",
        ),
        on_mount=TrackingState.load_tracking,
        active_page=PAGE_TRACKING,
    )

@rx.page(
    route="/chronology",
    title="Cronología - DatosEnOrden",
    description="Alias público de la cronología ciudadana de DatosEnOrden.",
    image=PUBLIC_OG_IMAGE_URL,
    meta=_page_meta(
        "/chronology",
        "cronología, seguimiento, documentos, evidencia, cambios",
        "Cronología - DatosEnOrden",
        "Alias público de la cronología ciudadana de DatosEnOrden.",
    ),
    on_load=TrackingState.load_tracking,
)
def chronology() -> rx.Component:
    return tracking()
