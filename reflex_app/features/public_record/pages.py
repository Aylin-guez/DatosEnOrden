from __future__ import annotations

import reflex as rx

from reflex_app.components.common.cards import next_step_card
from reflex_app.components.common.metrics import metric_card
from reflex_app.constants.routes import INVESTIGATION_STATUS_ERROR, INVESTIGATION_STATUS_LOADING, PAGE_INVESTIGATION
from reflex_app.features.public_record.components import (
    investigation_empty_state,
    investigation_error_state,
    investigation_loading_state,
    single_investigation_product_view,
)
from reflex_app.features.public_record.state import PublicRecordState
from reflex_app.layouts.page import page_section
from reflex_app.layouts.shell import shell
from reflex_app.metadata.pages import PUBLIC_OG_IMAGE_URL, _page_meta


@rx.page(
    route="/investigation",
    title="Expediente - DatosEnOrden",
    description="Expediente ciudadano para reunir entidades, relaciones, evidencia y trazabilidad en una sola lectura.",
    image=PUBLIC_OG_IMAGE_URL,
    meta=_page_meta(
        "/investigation",
        "expediente, evidencia, relaciones, trazabilidad, lectura ciudadana",
        "Expediente - DatosEnOrden",
        "Expediente ciudadano para reunir entidades, relaciones, evidencia y trazabilidad en una sola lectura.",
    ),
    on_load=PublicRecordState.load_investigation,
)
def investigation() -> rx.Component:
    return shell(
        rx.cond(
            PublicRecordState.selected_entity_id != "",
            rx.box(
                rx.vstack(
                    rx.box(
                        rx.text(PublicRecordState.entity_name, class_name="title"),
                        rx.text(PublicRecordState.entity_summary, class_name="subtitle"),
                        rx.hstack(
                            rx.foreach(PublicRecordState.dataset_badges, lambda item: rx.text(item, class_name="badge badge-teal")),
                            spacing="2",
                            wrap="wrap",
                        ),
                        class_name="hero",
                    ),
                    rx.hstack(
                        metric_card("Fuentes", PublicRecordState.datasets_involved, "consultadas"),
                        metric_card("Evidencia", PublicRecordState.evidence_count, "registros de respaldo"),
                        metric_card("Relaciones", PublicRecordState.relationship_count, "conexiones publicas"),
                        metric_card("Entidades conectadas", PublicRecordState.connected_entities, "personas, empresas u organismos"),
                        spacing="2",
                        wrap="wrap",
                        class_name="summary-strip",
                    ),
                    single_investigation_product_view(),
                    page_section(
                        "Siguientes pasos",
                        rx.grid(
                            next_step_card("Leer reporte ciudadano", "Ver una explicacion en formato articulo.", "Ir a Informes", "/reports"),
                            next_step_card("Ver documento fuente", "Revisar el documento junto a sus referencias.", "Ver documento", "/official-document"),
                            next_step_card("Seguir proyecto", "Ver la historia en el tiempo y sus hitos.", "Ir a Cronologia", "/tracking"),
                            columns="3",
                            spacing="3",
                            class_name="responsive-grid",
                        ),
                        subtitle="Un expediente ayuda a entrar; las otras vistas ayudan a seguir leyendo.",
                    ),
                    spacing="4",
                    align="stretch",
                    class_name="investigation-shell",
                ),
            ),
            rx.cond(
                PublicRecordState.investigation_status == INVESTIGATION_STATUS_ERROR,
                investigation_error_state(),
                rx.cond(
                    (PublicRecordState.investigation_loading)
                    | (PublicRecordState.investigation_status == INVESTIGATION_STATUS_LOADING),
                    investigation_loading_state(),
                    investigation_empty_state(),
                ),
            ),
        ),
        active_page=PAGE_INVESTIGATION,
    )


investigation_view = investigation
