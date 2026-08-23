from __future__ import annotations

import reflex as rx

from reflex_app.constants.routes import PAGE_SEARCH
from reflex_app.features.search.components import (
    guided_discovery_panel,
    search_empty_state,
    what_to_investigate_panel,
    workspace_match_card,
)
from reflex_app.features.search.state import SearchState
from reflex_app.layouts.page import page_section
from reflex_app.layouts.shell import shell
from reflex_app.metadata.pages import PUBLIC_OG_IMAGE_URL, _page_meta


@rx.page(
    route="/search",
    title="Explorar - DatosEnOrden Ciudadano",
    description="Busqueda compatible para explorar expedientes, entidades y documentos en DatosEnOrden.",
    image=PUBLIC_OG_IMAGE_URL,
    meta=_page_meta(
        "/search",
        "buscar, expedientes, entidades, documentos oficiales, entrada guiada",
        "Explorar - DatosEnOrden Ciudadano",
        "Busqueda compatible para explorar expedientes, entidades y documentos en DatosEnOrden.",
    ),
    on_load=SearchState.load_search,
)
def search() -> rx.Component:
    return _search_view(SearchState.load_search)


def _search_view(on_mount) -> rx.Component:  # noqa: ANN001
    return shell(
        rx.box(
            rx.text("Explorar", class_name="title"),
            rx.text(
                "Empieza por una entidad, politica, norma, proyecto, contrato, presupuesto, evento, documento o pregunta comprensible.",
                class_name="subtitle",
            ),
            rx.hstack(
                rx.input(
                    placeholder="Busca informacion publica conectada",
                    value=SearchState.query,
                    on_change=SearchState.set_query,
                    class_name="input search-input",
                    aria_label="Buscar en conocimiento publico disponible",
                ),
                rx.button("Buscar", on_click=SearchState.submit_main_search, class_name="button search-button"),
                spacing="2",
                wrap="wrap",
                class_name="search-bar",
            ),
            rx.text("La busqueda consulta conocimiento local ya disponible. No crea expedientes persistentes ni ejecuta generacion pesada.", class_name="source-fact"),
            class_name="hero",
        ),
        rx.cond(
            SearchState.guided_question_active,
            rx.vstack(
                _search_results(),
                page_section(
                    "Explorar otra pregunta",
                    rx.button(
                        "← Explorar otra pregunta",
                        on_click=SearchState.explore_another_question,
                        class_name="button button-secondary",
                    ),
                    guided_discovery_panel(),
                    subtitle="Puedes volver a una pregunta guiada sin perder una búsqueda manual ya escrita.",
                ),
                spacing="4",
                align="stretch",
            ),
            rx.vstack(
                guided_discovery_panel(),
                what_to_investigate_panel(),
                _search_results(),
                spacing="4",
                align="stretch",
            ),
        ),
        on_mount=on_mount,
        active_page=PAGE_SEARCH,
    )


def _search_results() -> rx.Component:
    return rx.cond(
        SearchState.results,
        rx.box(
            page_section(
                rx.cond(SearchState.guided_search_title != "", SearchState.guided_search_title, "Resultados agrupados por cobertura"),
                rx.grid(
                    rx.foreach(SearchState.results, workspace_match_card),
                    columns="3",
                    spacing="3",
                    class_name="responsive-grid",
                ),
                subtitle="Cada resultado explica que es, por que coincide, que fuentes contribuyen y que accion corresponde.",
            ),
            id="search-results",
        ),
        rx.cond(SearchState.query != "", search_empty_state()),
    )


@rx.page(
    route="/discover",
    title="Explorar - DatosEnOrden Ciudadano",
    description="Entrada guiada compatible para explorar expedientes, entidades y documentos en DatosEnOrden.",
    image=PUBLIC_OG_IMAGE_URL,
    meta=_page_meta(
        "/search",
        "buscar, expedientes, entidades, documentos oficiales, entrada guiada",
        "Explorar - DatosEnOrden Ciudadano",
        "Entrada guiada compatible para explorar expedientes, entidades y documentos en DatosEnOrden.",
    ),
    on_load=SearchState.load_discover,
)
def discover() -> rx.Component:
    return _search_view(SearchState.load_discover)
