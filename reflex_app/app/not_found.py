from __future__ import annotations

import reflex as rx

from reflex_app.components.common.cards import next_step_card
from reflex_app.constants.routes import PAGE_NOT_FOUND
from reflex_app.features.search.state import SearchState
from reflex_app.layouts.page import page_section
from reflex_app.layouts.shell import shell
from reflex_app.metadata.pages import PUBLIC_OG_IMAGE_URL, _page_meta


def not_found_document_illustration() -> rx.Component:
    return rx.box(
        rx.box(
            rx.box(class_name="not-found-document-tab"),
            rx.box(
                rx.box(class_name="not-found-document-line"),
                rx.box(class_name="not-found-document-line not-found-document-line-medium"),
                rx.box(class_name="not-found-document-line not-found-document-line-short"),
                class_name="not-found-document-body",
            ),
            class_name="not-found-document-card",
        ),
        rx.text("Sin ruta", class_name="not-found-badge"),
        class_name="not-found-illustration",
        role="img",
        aria_label="Ilustracion de documento no encontrado",
    )


@rx.page(
    route="404",
    title="Pagina no encontrada - DatosEnOrden Ciudadano",
    description="No encontramos esta ruta, pero puedes buscar informacion publica conectada.",
    image=PUBLIC_OG_IMAGE_URL,
    meta=_page_meta(
        "/404",
        "404, expediente, documento, evidencia, datosenorden",
        "Pagina no encontrada - DatosEnOrden Ciudadano",
        "No encontramos esta ruta, pero puedes buscar informacion publica conectada.",
    ),
)
def not_found() -> rx.Component:
    return shell(
        rx.box(
            rx.grid(
                rx.vstack(
                    rx.text("No encontramos esta pagina.", class_name="title"),
                    rx.text("Puedes buscar una entidad, documento, fuente o expediente disponible.", class_name="subtitle"),
                    rx.hstack(
                        rx.input(
                            placeholder="Buscar informacion publica",
                            value=SearchState.query,
                            on_change=SearchState.set_query,
                            class_name="input search-input",
                            aria_label="Buscar desde pagina no encontrada",
                        ),
                        rx.button("Explorar", on_click=SearchState.submit_main_search, class_name="button search-button"),
                        spacing="2",
                        wrap="wrap",
                        class_name="search-bar",
                    ),
                    rx.hstack(
                        rx.button("Inicio", on_click=rx.redirect("/"), class_name="button"),
                        rx.button("Explorar", on_click=rx.redirect("/search"), class_name="button button-secondary"),
                        rx.button("Fuentes", on_click=rx.redirect("/sources"), class_name="button button-secondary"),
                        spacing="3",
                        wrap="wrap",
                        class_name="hero-actions",
                    ),
                    spacing="4",
                    align="stretch",
                ),
                not_found_document_illustration(),
                columns="2",
                spacing="4",
                class_name="not-found-hero",
            ),
            class_name="hero",
        ),
        page_section(
            "Rutas utiles",
            rx.grid(
                next_step_card("Abrir una lectura", "Revisar el documento fuente y sus fragmentos verificables.", "Ver documento", "/official-document"),
                next_step_card("Abrir expediente disponible", "Explorar entidades, relaciones, documentos, fuentes y cronologia.", "Abrir expediente", "/investigation"),
                next_step_card("Revisar fuentes", "Distinguir catalogo, conector, datos y cobertura.", "Ir a Fuentes", "/sources"),
                columns="3",
                spacing="3",
                class_name="responsive-grid",
            ),
            subtitle="Las rutas contextuales siguen disponibles aunque no esten en la navegacion principal.",
        ),
        active_page=PAGE_NOT_FOUND,
    )
