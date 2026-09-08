from __future__ import annotations

import reflex as rx

from reflex_app.components.common.indicators import search_chip
from reflex_app.features.search.state import SearchState
from reflex_app.helpers.public_values import _clean
from reflex_app.layouts.page import page_section


def _human_label(value: object) -> str:
    labels = {
        "outgoing": "salida",
        "incoming": "entrada",
        "CONTRACT": "contrato",
        "ROLE": "rol publico",
        "ISSUES_PURCHASE_ORDER": "emite orden de compra",
        "ORGANIZATION_HELD_LOBBY_MEETING": "registro reunion de lobby",
        "ORGANIZATION_HAS_PUBLIC_ROLE": "tiene rol publico registrado",
        "ROLE_BELONGS_TO_ORGANIZATION": "rol pertenece al organismo",
    }
    return labels.get(_clean(value), _clean(value))


def _entity_badge_class(entity_type: str) -> str:
    normalized = str(entity_type or "").lower()
    if "organization" in normalized or "organismo" in normalized:
        return "badge badge-teal"
    if "supplier" in normalized or "proveedor" in normalized:
        return "badge badge-amber"
    if "person" in normalized or "persona" in normalized:
        return "badge badge-purple"
    return "badge"


def investigation_topic_card(row: dict) -> rx.Component:
    return rx.box(
        rx.text(row["label"], class_name="card-title"),
        rx.text(row["example"], class_name="muted small"),
        rx.text(row.get("count_text", "Sin información incorporada todavía"), class_name="source-fact"),
        rx.cond(row.get("collection_href", "") != "", rx.link("Explorar colección", href=row["collection_href"], class_name="button button-secondary")),
        class_name="card topic-card",
    )


def what_to_investigate_panel() -> rx.Component:
    return page_section(
        "Que puedes investigar",
        rx.grid(
            rx.foreach(SearchState.investigation_topic_rows, investigation_topic_card),
            columns="5",
            spacing="3",
            class_name="responsive-grid topic-grid",
        ),
        subtitle="La interfaz admite multiples objetivos investigables; no esta codificada solo para un caso hospitalario.",
    )


def guided_question_card(row: dict) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.text(row["title"], class_name="card-title"),
            rx.text("Pregunta guiada", class_name="badge badge-purple"),
            justify="between",
            align="center",
        ),
        rx.text(row["description"], class_name="muted small"),
        rx.text(row.get("path_text", "Este recorrido conectara fuentes locales relacionadas."), class_name="source-fact"),
        rx.hstack(
            rx.text(row.get("concepts_text", ""), class_name="search-chip"),
            rx.text(row.get("sources_text", ""), class_name="mini-pill mini-pill-purple"),
            spacing="2",
            wrap="wrap",
        ),
        rx.text(f"Ejemplo: {row['example_query']}", class_name="source-fact"),
        rx.button(
            "Ver recorrido sugerido",
            on_click=SearchState.explore_guided_question(
                row["id"],
                row["title"],
                row["description"],
                row.get("search_query", row.get("example_query", "")),
            ),
            class_name="button button-secondary",
        ),
        class_name="card example-card discovery-card",
    )


def guided_category_button(row: dict) -> rx.Component:
    return rx.cond(
        SearchState.selected_guided_category_id == row["id"],
        rx.button(
            row["title"],
            on_click=SearchState.select_guided_category(row["id"]),
            class_name="search-chip explorer-category-button explorer-category-button-active",
        ),
        rx.button(
            row["title"],
            on_click=SearchState.select_guided_category(row["id"]),
            class_name="search-chip explorer-category-button",
        ),
    )


def guided_option_card(row: dict) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.text(row["record_badge"], class_name="badge badge-teal"),
            rx.text(row["sources_text"], class_name="muted small"),
            justify="between",
            align="center",
        ),
        rx.text(row["title"], class_name="card-title"),
        rx.text(row["why_it_appears"], class_name="muted small"),
        rx.cond(
            row.get("related_text", "") != "",
            rx.text(row["related_text"], class_name="source-fact"),
        ),
        rx.button(
            "Ver informacion disponible",
            on_click=rx.redirect(row["canonical_investigation_href"]),
            class_name="button button-secondary",
        ),
        class_name="card example-card discovery-card",
    )


def guided_category_panel() -> rx.Component:
    return rx.cond(
        SearchState.selected_guided_category_id != "",
        rx.box(
            rx.hstack(
                rx.text(SearchState.selected_guided_category_title, class_name="card-title"),
                rx.text("Panel exploratorio", class_name="badge badge-purple"),
                justify="between",
                align="center",
            ),
            rx.text(SearchState.selected_guided_category_description, class_name="muted"),
            rx.cond(
                SearchState.selected_guided_category_path != "",
                rx.text(SearchState.selected_guided_category_path, class_name="source-fact"),
            ),
            rx.hstack(
                rx.foreach(SearchState.selected_guided_category_examples, search_chip),
                spacing="2",
                wrap="wrap",
            ),
            rx.hstack(
                rx.foreach(SearchState.selected_guided_category_sources, lambda item: rx.text(item, class_name="mini-pill mini-pill-purple")),
                spacing="2",
                wrap="wrap",
            ),
            rx.cond(
                SearchState.guided_option_rows,
                rx.grid(
                    rx.foreach(SearchState.guided_option_rows, guided_option_card),
                    columns="2",
                    spacing="2",
                    class_name="responsive-grid",
                ),
                rx.text("No hay opciones locales cargadas para esta categoria.", class_name="muted small"),
            ),
            rx.hstack(
                rx.button(
                    "Buscar esta categoria",
                    on_click=SearchState.run_search,
                    class_name="button",
                ),
                rx.button(
                    "Ir a Buscar",
                    on_click=rx.redirect(SearchState.selected_guided_category_href),
                    class_name="button button-secondary",
                ),
                spacing="3",
                wrap="wrap",
            ),
            class_name="card explorer-panel",
        ),
        rx.text("Selecciona una categoria para ver ejemplos.", class_name="muted small"),
    )


def guided_discovery_panel() -> rx.Component:
    return rx.vstack(
        page_section(
            "Expedientes disponibles",
            rx.cond(
                SearchState.public_expedient_rows,
                rx.grid(
                    rx.foreach(SearchState.public_expedient_rows, public_expedient_card),
                    columns="2",
                    spacing="3",
                    class_name="responsive-grid",
                ),
                rx.text("No hay expedientes públicos disponibles todavía.", class_name="muted small"),
            ),
            rx.link("Ver todos los expedientes", href="/expedientes", class_name="document-inline-link"),
            subtitle="Una selección acotada; el catálogo público ofrece todos los expedientes publicados con su procedencia visible.",
        ),
        page_section(
            "Preguntas guiadas",
            rx.cond(
                SearchState.guided_question_rows,
                rx.grid(
                    rx.foreach(SearchState.guided_question_rows, guided_question_card),
                    columns="2",
                    spacing="3",
                    class_name="responsive-grid",
                ),
                rx.text("Todavia no hay preguntas guiadas disponibles.", class_name="muted small"),
            ),
            subtitle="Consultas concretas que exploran datos locales.",
        ),
        page_section(
            "Explora por categoria",
            rx.hstack(
                rx.foreach(SearchState.guided_category_rows, guided_category_button),
                spacing="2",
                wrap="wrap",
                class_name="chip-row",
            ),
            guided_category_panel(),
            subtitle="Selecciona una categoria para ver ejemplos sin perder el contexto.",
        ),
        spacing="4",
        align="stretch",
    )


def public_expedient_card(row: dict) -> rx.Component:
    return rx.box(
        rx.text("Expediente público", class_name="badge badge-teal"),
        rx.text(row["title"], class_name="card-title"),
        rx.text(row["question"], class_name="muted small"),
        rx.button(
            "Abrir expediente",
            on_click=rx.redirect(f"/laboratory/expedient?id={row['id']}"),
            class_name="button button-secondary",
        ),
        class_name="card example-card discovery-card",
    )


def search_empty_state() -> rx.Component:
    return rx.vstack(
        page_section(
            "Sin resultados por ahora",
            rx.text("No encontramos coincidencias con ese nombre o identificador en esta base local publicada.", class_name="muted"),
            rx.text(
                "Puede tratarse de otra denominacion oficial, una entidad aun no publicada, una fuente no conectada o cobertura insuficiente para formar una lectura.",
                class_name="muted small",
            ),
            rx.text("Que si puedes hacer: probar una institucion, empresa, autoridad, contrato, documento o fuente ya disponible.", class_name="source-fact"),
            rx.hstack(
                rx.link("Usar entrada guiada", href="/discover", class_name="badge badge-purple"),
                rx.link("Explorar fuentes oficiales", href="/sources", class_name="document-inline-link"),
                rx.link("Volver a Inicio", href="/", class_name="document-inline-link"),
                spacing="3",
                wrap="wrap",
            ),
            subtitle="Prueba con una institucion, empresa, persona o documento usando su nombre oficial mas reconocible.",
        ),
        spacing="4",
        align="stretch",
    )


def workspace_match_card(row: dict) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.text(row["entity_type_label"], class_name=_entity_badge_class("entity")),
            rx.text(row["source_hint"], class_name="muted small"),
            justify="between",
            align="center",
        ),
        rx.text(row["entity_name"], class_name="card-title"),
        rx.cond(
            row["classification"] == "DEMO",
            rx.text("DEMO", class_name="badge badge-amber"),
        ),
        rx.cond(
            row["is_record"],
            rx.text("Registro especifico", class_name="badge badge-amber"),
        ),
        rx.cond(
            row["related_label"] != "",
            rx.text(row["related_label"], class_name="muted small"),
        ),
        rx.text(row["datasets_text"], class_name="muted small"),
        rx.text(row["match_reason"], class_name="source-fact"),
        rx.text(row["coverage_summary"], class_name="muted small"),
        rx.text(row["source_contribution"], class_name="muted small"),
        rx.cond(
            row["state_graph_badges_text"] != "",
            rx.text(row["state_graph_badges_text"], class_name="source-fact evidence-trust"),
        ),
        rx.hstack(
            rx.cond(row["evidence_label"] != "", rx.text(row["evidence_label"], class_name="mini-pill")),
            rx.cond(row["relationship_label"] != "", rx.text(row["relationship_label"], class_name="mini-pill")),
            spacing="2",
            wrap="wrap",
        ),
        rx.hstack(
            rx.cond(
                row["action_href"] != "",
                rx.button(row["action_label"], on_click=rx.redirect(row["action_href"]), class_name="button button-secondary"),
                rx.button(row["action_label"], on_click=rx.redirect(row["canonical_investigation_href"]), class_name="button button-secondary"),
            ),
            rx.cond(
                row["is_record"],
                rx.text("Ver registro: pendiente", class_name="mini-pill"),
            ),
            spacing="2",
            wrap="wrap",
        ),
        class_name="card example-card search-result-card",
    )


def guided_journey_expedient_card(row: dict) -> rx.Component:
    return rx.box(
        rx.text("Expediente disponible", class_name="badge badge-teal"),
        rx.text(row["entity_name"], class_name="card-title"),
        rx.text("Lectura ciudadana disponible.", class_name="muted small"),
        rx.text(row["source_contribution"], class_name="source-fact"),
        rx.button("Abrir expediente", on_click=rx.redirect(row["action_href"]), class_name="button button-secondary"),
        class_name="card example-card discovery-card",
    )


def guided_journey_entity_card(row: dict) -> rx.Component:
    return rx.box(
        rx.text(row["entity_type_label"], class_name="badge badge-purple"),
        rx.text(row["entity_name"], class_name="card-title"),
        rx.text("Aparece en información pública incorporada para responder esta pregunta.", class_name="muted small"),
        rx.text(row["source_contribution"], class_name="source-fact"),
        rx.cond(
            row["related_expedient_count_text"] != "",
            rx.text(row["related_expedient_count_text"], class_name="source-fact evidence-trust"),
        ),
        rx.cond(
            row["canonical_investigation_href"] != "/investigation",
            rx.button("Ver información disponible", on_click=rx.redirect(row["canonical_investigation_href"]), class_name="button button-secondary"),
        ),
        class_name="card example-card discovery-card",
    )


def guided_journey_panel() -> rx.Component:
    return rx.box(
        page_section(
            "Respuesta guiada",
            rx.vstack(
                rx.button("← Volver a Explorar", on_click=SearchState.return_to_explore, class_name="button button-secondary"),
                rx.text(SearchState.guided_journey_title, class_name="title"),
                rx.text(SearchState.guided_journey_description, class_name="subtitle"),
                rx.cond(
                    SearchState.guided_journey_status == "EMPTY",
                    rx.vstack(
                        rx.text(SearchState.guided_journey_summary, class_name="source-fact"),
                        rx.text("Esto no significa que no existan registros; sólo que DatosEnOrden aún no cuenta con información suficiente para responder esta pregunta.", class_name="muted small"),
                        spacing="2",
                        align="stretch",
                    ),
                    rx.vstack(
                        rx.text(SearchState.guided_journey_summary, class_name="muted small"),
                        rx.text(SearchState.guided_journey_count_copy, class_name="source-fact"),
                        rx.text(SearchState.guided_journey_scope_copy, class_name="muted small"),
                        spacing="2",
                        align="stretch",
                    ),
                ),
                rx.cond(
                    SearchState.guided_journey_entity_rows,
                    rx.box(
                        rx.text("Resultados", class_name="section-heading"),
                        rx.grid(
                            rx.foreach(SearchState.guided_journey_entity_rows, guided_journey_entity_card),
                            columns="2",
                            spacing="3",
                            class_name="responsive-grid search-guided-results-grid",
                        ),
                    ),
                ),
                rx.cond(
                    SearchState.guided_journey_expedient_rows,
                    rx.box(
                        rx.text("Expedientes relacionados", class_name="section-heading"),
                        rx.grid(
                            rx.foreach(SearchState.guided_journey_expedient_rows, guided_journey_expedient_card),
                            columns="2",
                            spacing="3",
                            class_name="responsive-grid search-guided-results-grid",
                        ),
                    ),
                ),
                spacing="3",
                align="stretch",
            ),
            subtitle="Los resultados describen información incorporada en DatosEnOrden, no el universo completo de Chile.",
        ),
        id="guided-journey",
    )
