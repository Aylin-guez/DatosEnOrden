from __future__ import annotations

import reflex as rx

from reflex_app.components.common.badges import _accent_badge_class
from reflex_app.components.common.cards import help_card, loading_placeholder_card
from reflex_app.components.common.indicators import relationship_badge
from reflex_app.components.common.metrics import summary_metric_card
from reflex_app.constants.demo import DEMO_INVESTIGATION_TARGET
from reflex_app.features.public_record.state import PublicRecordState
from reflex_app.features.public_record.view_models import GRAPH_EXPLANATION
from reflex_app.features.reports.state import ReportsState
from reflex_app.features.search.state import SearchState
from reflex_app.helpers.routing import _investigation_href

def story_card(row: dict) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.text(row["dataset"], class_name=_accent_badge_class(str(row.get("dataset", "")))),
            rx.text(row["date"], class_name="muted small"),
            justify="between",
            align="center",
        ),
        rx.text(row["title"], class_name="story-title"),
        rx.text(row["explanation"], class_name="muted"),
        rx.text(row["facts_text"], class_name="fact-line"),
        rx.hstack(
            rx.text(f"Evidencia: {row['evidence']}", class_name="mini-pill"),
            rx.text(row["relationship_type"], class_name="mini-pill mini-pill-purple"),
            rx.text(row.get("trust_label", "Registro local de muestra"), class_name="mini-pill evidence-trust"),
            spacing="2",
            wrap="wrap",
        ),
        rx.box(
            rx.text("Detalles técnicos / trazabilidad", class_name="muted small"),
            rx.text(row["detail_text"], class_name="detail-line"),
            class_name="technical-inline",
        ),
        class_name="story-card",
    )

def evidence_card(row: dict) -> rx.Component:
    return story_card(row)

def journey_node(row: dict) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.text(row["step"], class_name="journey-step"),
            rx.text(row["source"], class_name="badge badge-teal"),
            justify="between",
            align="center",
        ),
        rx.text(row["title"], class_name="card-title"),
        rx.text(row["body"], class_name="muted"),
        rx.text(row["why"], class_name="source-fact"),
        rx.hstack(
            relationship_badge(row["kind"]),
            rx.text(row["source_sentence"], class_name="mini-pill"),
            spacing="2",
            wrap="wrap",
        ),
        class_name="card journey-node",
    )

def investigation_panel(title: str, *children, subtitle: str | None = None) -> rx.Component:
    subtitle_component = (
        rx.text(subtitle, class_name="section-subtitle investigation-subtitle")
        if subtitle is not None
        else None
    )
    body_children = [rx.text(title, class_name="section-title investigation-section-title")]
    if subtitle_component is not None:
        body_children.append(subtitle_component)
    body_children.extend(children)
    return rx.vstack(*body_children, spacing="2", align="stretch", class_name="card investigation-card")

def investigation_key_point_card(row: dict) -> rx.Component:
    return rx.box(
        rx.text(row["text"], class_name="muted"),
        rx.cond(
            row["evidence_text"] != "",
            rx.text(f"Evidencia: {row['evidence_text']}", class_name="source-fact"),
        ),
        rx.cond(
            row["sources_text"] != "",
            rx.text(f"Fuentes: {row['sources_text']}", class_name="mini-pill"),
        ),
        class_name="knowledge-point",
    )

def state_graph_connection_card(row: dict) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.text(row["node_type"], class_name="badge badge-teal"),
            rx.text(row["confidence_label"], class_name="mini-pill evidence-trust"),
            justify="between",
            align="center",
        ),
        rx.text(row["title"], class_name="context-title"),
        rx.text(row["relation_type"], class_name="mini-pill mini-pill-purple"),
        rx.text(f"Fuente/conector: {row['source_connector']}", class_name="source-fact"),
        rx.text(f"Evidencia: {row['evidence_text']}", class_name="muted small"),
        rx.cond(
            row.get("href", "") != "",
            rx.button(row.get("action_label", "Abrir entidad"), on_click=rx.redirect(row["href"]), class_name="button button-secondary"),
            rx.text(row.get("action_label", "Conexi\u00f3n observada"), class_name="mini-pill"),
        ),
        class_name="context-item state-graph-connection-card",
    )

def state_graph_source_chip(row: dict) -> rx.Component:
    return rx.text(row["summary"], class_name="comparison-chip")

def state_graph_connections_panel() -> rx.Component:
    return investigation_panel(
        "Conexiones del Estado",
        rx.text(
            "Relaciones documentadas que el StateGraph conecta desde fuentes, evidencia y eventos disponibles.",
            class_name="muted small",
        ),
        rx.text(PublicRecordState.state_graph_summary_text, class_name="source-fact"),
        rx.cond(
            PublicRecordState.state_graph_connection_rows,
            rx.grid(
                rx.foreach(PublicRecordState.state_graph_connection_rows, state_graph_connection_card),
                columns="2",
                spacing="2",
                class_name="responsive-grid",
            ),
            rx.text("No hay conexiones observadas para este expediente.", class_name="muted small"),
        ),
        rx.cond(
            PublicRecordState.state_graph_source_rows,
            rx.hstack(
                rx.foreach(PublicRecordState.state_graph_source_rows, state_graph_source_chip),
                spacing="2",
                wrap="wrap",
            ),
        ),
        subtitle="Lenguaje descriptivo: aparece en, vinculado por documento/fuente y relaci\u00f3n documentada.",
    )

def citizen_summary_panel() -> rx.Component:
    return investigation_panel(
        "Resumen ciudadano",
        rx.text(PublicRecordState.citizen_summary, class_name="story-summary story-summary-dominant"),
        rx.cond(
            PublicRecordState.investigation_key_points,
            rx.vstack(
                rx.text("Puntos clave", class_name="context-title"),
                rx.grid(
                    rx.foreach(PublicRecordState.investigation_key_points, investigation_key_point_card),
                    columns="2",
                    spacing="2",
                    class_name="responsive-grid",
                ),
                spacing="2",
                align="stretch",
            ),
        ),
        rx.cond(
            PublicRecordState.investigation_questions,
            rx.vstack(
                rx.text("Preguntas sugeridas", class_name="context-title"),
                rx.hstack(
                    rx.foreach(PublicRecordState.investigation_questions, lambda item: rx.text(item, class_name="search-chip")),
                    spacing="2",
                    wrap="wrap",
                ),
                spacing="2",
                align="stretch",
            ),
        ),
        rx.cond(
            PublicRecordState.investigation_limitations,
            rx.vstack(
                rx.text("Limitaciones", class_name="context-title"),
                rx.hstack(
                    rx.foreach(PublicRecordState.investigation_limitations, lambda item: rx.text(item, class_name="mini-pill evidence-trust")),
                    spacing="2",
                    wrap="wrap",
                ),
                spacing="2",
                align="stretch",
            ),
        ),
        rx.cond(
            PublicRecordState.investigation_neutrality_notice != "",
            rx.text(PublicRecordState.investigation_neutrality_notice, class_name="source-fact"),
        ),
        rx.grid(
            summary_metric_card("Fuentes publicas", PublicRecordState.datasets_involved),
            summary_metric_card("Evidencias", PublicRecordState.evidence_count),
            summary_metric_card("Relaciones", PublicRecordState.relationship_count),
            summary_metric_card("Entidades conectadas", PublicRecordState.connected_entities),
            columns="4",
            spacing="2",
            class_name="responsive-grid",
        ),
        rx.hstack(
            rx.text("Exportación disponible solo en operación interna", class_name="muted small"),
            rx.text("Registro local de muestra", class_name="mini-pill evidence-trust"),
            spacing="2",
            wrap="wrap",
        ),
        rx.box(
            rx.text("Enlace canonico", class_name="muted small"),
            rx.text(PublicRecordState.canonical_investigation_link, class_name="mono id-line"),
            class_name="canonical-link-box",
        ),
        subtitle="Lectura breve para explicar que contiene el expediente sin afirmar causalidad, irregularidad ni responsabilidad.",
    )

def related_entity_card(row: dict) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.text(row["group"], class_name="badge badge-teal"),
            rx.text(row["source"], class_name="muted small"),
            justify="between",
            align="center",
        ),
        rx.text(row["type"], class_name="mini-pill mini-pill-purple"),
        rx.text(row["title"], class_name="context-title"),
        rx.text(row["why"], class_name="muted small"),
        rx.cond(
            row.get("target_href", "") != "",
            rx.button(row.get("action_label", "Abrir expediente"), on_click=rx.redirect(row["target_href"]), class_name="button button-secondary"),
            rx.text(row.get("action_label", "Relacionado"), class_name="mini-pill"),
        ),
        class_name="context-item related-entity-card",
    )

def related_entity_group(row: dict) -> rx.Component:
    return related_entity_card(row)

def context_entity_card(row: dict) -> rx.Component:
    return rx.box(
        rx.text(row["title"], class_name="context-title"),
        rx.text(row["relationship_type"], class_name="mini-pill mini-pill-purple"),
        rx.text(row["explanation"], class_name="muted small"),
        rx.cond(
            row.get("target_href", "") != "",
            rx.button(row.get("action_label", "Abrir expediente"), on_click=rx.redirect(row["target_href"]), class_name="button button-secondary"),
            rx.text(row.get("action_label", "Relacionado"), class_name="mini-pill"),
        ),
        class_name="context-item",
    )

def technical_detail_card(row: dict) -> rx.Component:
    return rx.box(
        rx.text(row["title"], class_name="context-title"),
        rx.text(row["technical_text"], class_name="mono id-line"),
        class_name="context-item technical-item",
    )

def source_trace_technical_row(text: str) -> rx.Component:
    return rx.text(text, class_name="technical-line")

def source_trace_card(row: dict) -> rx.Component:
    return rx.box(
        rx.text(row["dataset"], class_name="source-title"),
        rx.text(row["contribution"], class_name="muted small"),
        rx.hstack(
            rx.text(f"Evidencia {row['evidence_count']}", class_name="mini-pill"),
            rx.text(f"Relaciones {row['relationship_count']}", class_name="mini-pill"),
            spacing="2",
            wrap="wrap",
        ),
        rx.text(row["facts_text"], class_name="source-fact"),
        rx.accordion.root(
            rx.accordion.item(
                header="Detalles técnicos / trazabilidad",
                content=rx.text(row["technical_text"], class_name="technical-line"),
                value=f"source-{row['dataset']}",
            ),
            type="single",
            collapsible=True,
            variant="ghost",
            class_name="technical-accordion",
        ),
        class_name="card source-card",
    )

def entity_trace_card() -> rx.Component:
    return rx.box(
        rx.text(PublicRecordState.primary_entity_label, class_name="source-title"),
        rx.text(PublicRecordState.entity_summary, class_name="muted small"),
        rx.text("Entity", class_name="badge compact-badge"),
        rx.text(PublicRecordState.source_trace_overlap_summary, class_name="source-fact"),
        class_name="card source-entity-card",
    )

def source_trace_panel() -> rx.Component:
    return investigation_panel(
        "Source Trace",
        rx.text(
            "Public sources are arranged around the entity to show how records converge.",
            class_name="section-subtitle investigation-subtitle",
        ),
        rx.cond(
            PublicRecordState.source_trace_sources,
            rx.box(
                rx.hstack(
                    rx.foreach(PublicRecordState.source_trace_left_rows, source_trace_card),
                    rx.text("->", class_name="trace-arrow"),
                    entity_trace_card(),
                    rx.text("<-", class_name="trace-arrow"),
                    rx.foreach(PublicRecordState.source_trace_right_rows, source_trace_card),
                    spacing="2",
                    align="stretch",
                    wrap="nowrap",
                    class_name="source-trace-strip",
                ),
                class_name="source-trace-scroll",
            ),
            rx.text("No source trace available.", class_name="muted small"),
        ),
        rx.text(PublicRecordState.source_trace_notice, class_name="muted small"),
        subtitle=PublicRecordState.source_trace_overlap_summary,
    )

def comparison_panel() -> rx.Component:
    return investigation_panel(
        "Source Comparison",
        rx.text(PublicRecordState.comparison_summary, class_name="story-summary"),
        rx.cond(
            PublicRecordState.comparison_observations,
            rx.hstack(
                rx.foreach(
                    PublicRecordState.comparison_observations,
                    lambda item: rx.text(item, class_name="comparison-chip"),
                ),
                spacing="2",
                wrap="wrap",
            ),
            rx.text("No comparison observations available.", class_name="muted small"),
        ),
        subtitle="Comparison stays neutral and descriptive.",
    )

def source_card(row: dict) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.text("*", class_name="source-card-icon"),
            rx.text(row["dataset"], class_name="badge"),
            rx.text(row["status"], class_name="mini-pill"),
            justify="between",
            align="center",
        ),
        rx.text(row["summary"], class_name="muted small"),
        rx.hstack(
            rx.text(f"Evidencia: {row['evidence_count']}", class_name="mini-pill"),
            rx.text(f"Relaciones: {row['relationship_count']}", class_name="mini-pill mini-pill-purple"),
            spacing="2",
            wrap="wrap",
        ),
        rx.text(f"Conceptos: {row['concepts_text']}", class_name="source-fact"),
        rx.text(f"Aporta: {row['contributes_text']}", class_name="source-fact"),
        rx.text(row["timeline_contribution"], class_name="muted small"),
        class_name="card source-card",
    )

def source_coverage_card(row: dict) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.text(row["source"], class_name="card-title"),
            rx.text(row["status"], class_name=_accent_badge_class(str(row.get("status", "")))),
            justify="between",
            align="center",
        ),
        rx.text(row["contribution"], class_name="muted small"),
        rx.hstack(
            rx.text(f"Evidencia: {row['evidence_count']}", class_name="mini-pill"),
            rx.text(f"Relaciones: {row['relationship_count']}", class_name="mini-pill mini-pill-purple"),
            rx.text(row["trust_label"], class_name="mini-pill evidence-trust"),
            spacing="2",
            wrap="wrap",
        ),
        class_name="card source-card source-coverage-card",
    )

def source_contribution_card(row: dict) -> rx.Component:
    return source_card(row)

def technical_source_card(row: dict) -> rx.Component:
    return rx.box(
        rx.text(row["dataset"], class_name="context-title"),
        rx.text(f"Estado: {row['status']}", class_name="technical-line"),
        rx.text(f"Evidencia: {row['evidence_count']} | Relaciones: {row['relationship_count']}", class_name="technical-line"),
        rx.text(f"Conceptos: {row['concepts_text']}", class_name="technical-line"),
        rx.text(f"Tipos de evidencia: {row['evidence_types_text']}", class_name="technical-line"),
        rx.text(f"Comandos: {row['commands_text']}", class_name="technical-line"),
        rx.text(row["overlap_note"], class_name="muted small"),
        class_name="context-item technical-item",
    )

def comparison_dataset_card(row: dict) -> rx.Component:
    return rx.box(
        rx.text(row["dataset"], class_name="badge"),
        rx.text(row["summary"], class_name="muted small"),
        rx.text(row["contributes_text"], class_name="source-fact"),
        class_name="card source-card",
    )

def comparison_overlap_card(text: str) -> rx.Component:
    return rx.text(text, class_name="comparison-chip")

def graph_node_card(row: dict) -> rx.Component:
    return rx.box(
        rx.text(row["label"], class_name="context-title"),
        rx.text(row.get("summary", ""), class_name="muted small"),
        rx.text(
            rx.cond(row["dataset"] != "", row["dataset"], row["category"]),
            class_name="badge compact-badge",
        ),
        class_name="context-item",
    )

def graph_entity_card() -> rx.Component:
    return rx.box(
        rx.text(PublicRecordState.primary_entity_label, class_name="source-title"),
        rx.text(PublicRecordState.entity_summary, class_name="muted small"),
        rx.text(PublicRecordState.graph_summary, class_name="source-fact"),
        class_name="card source-entity-card",
    )

def timeline_year_card(row: dict) -> rx.Component:
    return rx.box(
        rx.text(row["year"], class_name="story-headline"),
        rx.text(row.get("items_text", ""), class_name="source-fact"),
        rx.cond(
            row.get("items_overflow_text", ""),
            rx.accordion.root(
                rx.accordion.item(
                            header="Ver entradas anteriores",
                    content=rx.text(row.get("items_overflow_text", ""), class_name="muted small"),
                    value=f"timeline-{row['year']}",
                ),
                type="single",
                collapsible=True,
                variant="ghost",
                class_name="timeline-accordion",
            ),
        ),
        class_name="card story-card",
    )

def narrative_item(text: str) -> rx.Component:
    return rx.box(rx.text(text, class_name="narrative-text"), class_name="narrative-item")

def investigation_empty_state() -> rx.Component:
    return rx.vstack(
        rx.box(
            rx.text("¿Qué quieres investigar?", class_name="title"),
            rx.text("Un expediente reúne fuentes, evidencia y relaciones para ayudarte a entender una entidad sin perder el contexto.", class_name="subtitle"),
            rx.hstack(
                rx.input(
                    placeholder="Busca organismo, empresa, persona o proyecto",
                    value=SearchState.query,
                    on_change=SearchState.set_query,
                    class_name="input search-input",
                    aria_label="Buscar entidad",
                ),
                rx.button("Buscar", on_click=SearchState.submit_main_search, class_name="button search-button"),
                spacing="3",
                align="center",
                class_name="search-bar investigation-welcome-search",
            ),
            rx.hstack(
                rx.button("Abrir expediente de ejemplo", on_click=rx.redirect(_investigation_href(DEMO_INVESTIGATION_TARGET)), class_name="button"),
                rx.button("Ver biblioteca", on_click=rx.redirect("/library"), class_name="button button-secondary"),
                rx.button("Ver fuentes oficiales", on_click=rx.redirect("/ecosystem"), class_name="button button-secondary"),
                spacing="3",
                wrap="wrap",
                class_name="hero-actions",
            ),
            class_name="hero investigation-welcome",
        ),
        rx.grid(
            help_card("¿Qué es un expediente?", "Una carpeta de lectura: reúne lo que sabemos, de dónde viene y cómo se conecta."),
            help_card("¿Qué es evidencia?", "Una pista verificable que permite volver a la fuente o al documento original."),
            help_card("¿Qué puedes hacer después?", "Leer un reporte, seguir la historia del proyecto o revisar las fuentes."),
            columns="3",
            spacing="3",
            class_name="responsive-grid investigation-empty-grid",
        ),
        spacing="4",
        align="stretch",
    )

def investigation_loading_state() -> rx.Component:
    return rx.vstack(
        rx.box(
            rx.text("Cargando expediente...", class_name="title"),
            rx.text("Estamos preparando el expediente desde la publicación local y ordenando sus rutas de verificación.", class_name="subtitle"),
            rx.hstack(
                rx.button("Reintentar", on_click=PublicRecordState.load_investigation, class_name="button button-secondary"),
                rx.button("Volver al recorrido", on_click=rx.redirect("/demo"), class_name="button button-secondary"),
                spacing="3",
                wrap="wrap",
                class_name="hero-actions",
            ),
            class_name="hero",
        ),
        rx.grid(
            loading_placeholder_card("Reconstruyendo evidencia", "Ordenamos hechos, relaciones y referencias ya disponibles."),
            loading_placeholder_card("Preparando documento", "Sincronizamos el PDF oficial y el contexto citado."),
            loading_placeholder_card("Abriendo siguientes pasos", "Dejamos lista la navegación a informes, cronología y fuentes."),
            columns="3",
            spacing="3",
            class_name="responsive-grid loading-skeleton-grid",
        ),
        spacing="4",
        align="stretch",
    )

def investigation_error_state() -> rx.Component:
    return rx.box(
        rx.text("No se pudo abrir el expediente", class_name="title"),
        rx.text(
            rx.cond(
                PublicRecordState.investigation_status_message != "",
                PublicRecordState.investigation_status_message,
                "No pudimos abrir este expediente con la publicación actual. Puedes reintentar o volver al recorrido guiado.",
            ),
            class_name="subtitle",
        ),
        rx.hstack(
            rx.button("Reintentar", on_click=PublicRecordState.load_investigation, class_name="button"),
            rx.button("Volver al recorrido", on_click=rx.redirect("/demo"), class_name="button button-secondary"),
            spacing="3",
            wrap="wrap",
            class_name="hero-actions",
        ),
        class_name="hero investigation-error",
    )

def timeline_highlights_panel() -> rx.Component:
    return investigation_panel(
        "Cronología",
        rx.cond(
            PublicRecordState.timeline_year_rows,
            rx.vstack(
                rx.foreach(PublicRecordState.timeline_year_rows, timeline_year_card),
                rx.cond(
                    PublicRecordState.timeline_older_year_rows,
                    rx.accordion.root(
                        rx.accordion.item(
                            header="Ver entradas anteriores",
                            content=rx.vstack(
                                rx.foreach(PublicRecordState.timeline_older_year_rows, timeline_year_card),
                                spacing="2",
                                align="stretch",
                            ),
                            value="older-timeline",
                        ),
                        type="single",
                        collapsible=True,
                        variant="ghost",
                        class_name="timeline-accordion",
                    ),
                ),
                spacing="2",
                align="stretch",
            ),
            rx.cond(
                PublicRecordState.story_timeline_highlights,
                rx.vstack(
                    rx.foreach(PublicRecordState.story_timeline_highlights, narrative_item),
                    spacing="2",
                    align="stretch",
                ),
                rx.text("No hay cronología disponible.", class_name="muted small"),
            ),
        ),
        subtitle="Eventos agrupados cronologicamente desde todas las fuentes disponibles.",
    )

def investigation_tabs_panel() -> rx.Component:
    return investigation_panel(
        "Recorrido de evidencia",
        rx.tabs.root(
            rx.tabs.list(
                rx.tabs.trigger("Compras", value="procurement"),
                rx.tabs.trigger("Lobby", value="lobby"),
                rx.tabs.trigger("Transparencia", value="transparency"),
                rx.tabs.trigger("Empresas", value="registry"),
                rx.tabs.trigger("Evidencia", value="evidence"),
                class_name="tabs-list",
            ),
            rx.tabs.content(
                rx.cond(
                    PublicRecordState.procurement_rows,
                    rx.grid(
                        rx.foreach(PublicRecordState.procurement_rows, story_card),
                        columns="2",
                        spacing="2",
                        class_name="tab-grid",
                    ),
                    rx.text("No hay registros de compras disponibles.", class_name="muted small"),
                ),
                value="procurement",
                class_name="tab-content",
            ),
            rx.tabs.content(
                rx.cond(
                    PublicRecordState.lobby_rows,
                    rx.grid(
                        rx.foreach(PublicRecordState.lobby_rows, story_card),
                        columns="2",
                        spacing="2",
                        class_name="tab-grid",
                    ),
                    rx.text("No hay registros de lobby disponibles.", class_name="muted small"),
                ),
                value="lobby",
                class_name="tab-content",
            ),
            rx.tabs.content(
                rx.cond(
                    PublicRecordState.transparencia_rows,
                    rx.grid(
                        rx.foreach(PublicRecordState.transparencia_rows, story_card),
                        columns="2",
                        spacing="2",
                        class_name="tab-grid",
                    ),
                    rx.text("No hay registros de transparencia disponibles.", class_name="muted small"),
                ),
                value="transparency",
                class_name="tab-content",
            ),
            rx.tabs.content(
                rx.cond(
                    PublicRecordState.registry_rows,
                    rx.grid(
                        rx.foreach(PublicRecordState.registry_rows, story_card),
                        columns="2",
                        spacing="2",
                        class_name="tab-grid",
                    ),
                    rx.text("No hay registros de empresas disponibles.", class_name="muted small"),
                ),
                value="registry",
                class_name="tab-content",
            ),
            rx.tabs.content(
                rx.cond(
                    PublicRecordState.evidence_rows,
                    rx.grid(
                        rx.foreach(PublicRecordState.evidence_rows, story_card),
                        columns="2",
                        spacing="2",
                        class_name="tab-grid",
                    ),
                    rx.text("No hay evidencia disponible.", class_name="muted small"),
                ),
                value="evidence",
                class_name="tab-content",
            ),
            default_value="procurement",
            class_name="tabs-root",
        ),
        subtitle="Cambia de tema en vez de recorrer secciones apiladas.",
    )

def relationship_map_panel() -> rx.Component:
    return rx.box(
        rx.text("Mapa de relaciones", class_name="section-title investigation-section-title"),
        rx.text("Fuente -> Entidad -> Relación -> Evidencia", class_name="section-subtitle investigation-subtitle"),
        rx.hstack(
            rx.hstack(
                rx.foreach(PublicRecordState.graph_dataset_nodes, graph_node_card),
                spacing="2",
                wrap="wrap",
            ),
            rx.text("->", class_name="map-arrow"),
            graph_entity_card(),
            rx.text("->", class_name="map-arrow"),
            rx.hstack(
                rx.foreach(PublicRecordState.graph_relationship_nodes, graph_node_card),
                spacing="2",
                wrap="wrap",
            ),
            rx.text("->", class_name="map-arrow"),
            rx.hstack(
                rx.foreach(PublicRecordState.graph_evidence_nodes, graph_node_card),
                spacing="2",
                wrap="wrap",
            ),
            spacing="2",
            align="stretch",
            wrap="nowrap",
        ),
        rx.text(PublicRecordState.graph_summary, class_name="muted small"),
        class_name="card relationship-map",
    )

def context_sidebar_panel() -> rx.Component:
    return rx.box(
        rx.text("Detalles técnicos / trazabilidad", class_name="section-title investigation-section-title"),
        rx.text(PublicRecordState.connection_summary, class_name="muted"),
        rx.text(GRAPH_EXPLANATION, class_name="muted small"),
        rx.text(PublicRecordState.neutral_explanation, class_name="muted small"),
        rx.text("Qué aporta cada fuente", class_name="context-title"),
        rx.hstack(
            rx.foreach(PublicRecordState.source_contribution_rows, source_contribution_card),
            spacing="2",
            wrap="nowrap",
            class_name="horizontal-scroll",
        ),
        rx.text("reas de cruce", class_name="context-title"),
        rx.cond(
            PublicRecordState.comparison_overlap_areas,
            rx.hstack(
                rx.foreach(PublicRecordState.comparison_overlap_areas, comparison_overlap_card),
                spacing="2",
                wrap="wrap",
            ),
            rx.text("No hay reas de cruce disponibles.", class_name="muted small"),
        ),
        rx.text("Detalle de comparación", class_name="context-title"),
        rx.cond(
            PublicRecordState.comparison_dataset_rows,
            rx.hstack(
                rx.foreach(PublicRecordState.comparison_dataset_rows, comparison_dataset_card),
                spacing="2",
                wrap="nowrap",
                class_name="horizontal-scroll",
            ),
            rx.text("No hay detalle de comparación disponible.", class_name="muted small"),
        ),
        rx.text("Metrics", class_name="context-title"),
        rx.grid(
            summary_metric_card("Fuentes", PublicRecordState.datasets_involved),
            summary_metric_card("Evidencia", PublicRecordState.evidence_count),
            summary_metric_card("Relaciones", PublicRecordState.relationship_count),
            summary_metric_card("Entidades conectadas", PublicRecordState.connected_entities),
            columns="2",
            spacing="2",
            class_name="metrics-grid",
        ),
        rx.text("Entidades conectadas", class_name="context-title"),
        rx.cond(
            PublicRecordState.relationship_rows,
            rx.vstack(
                rx.foreach(PublicRecordState.relationship_rows, context_entity_card),
                spacing="2",
                align="stretch",
            ),
            rx.text("No hay entidades conectadas disponibles.", class_name="muted small"),
        ),
        rx.accordion.root(
            rx.accordion.item(
                header="Detalles técnicos / trazabilidad",
                content=rx.vstack(
                    rx.text(
                        "Aquí se guardan identificadores, URLs, predicados, códigos de relación y referencias internas para trazabilidad.",
                        class_name="muted small",
                    ),
                    rx.cond(
                        PublicRecordState.technical_details,
                        rx.vstack(
                            rx.foreach(PublicRecordState.technical_details, technical_detail_card),
                            spacing="2",
                            align="stretch",
                        ),
                        rx.text("No hay detalles técnicos disponibles.", class_name="muted small"),
                    ),
                    spacing="2",
                    align="stretch",
                ),
                value="technical-details",
            ),
            type="single",
            collapsible=True,
            variant="ghost",
            class_name="technical-accordion",
        ),
        class_name="card context-panel investigation-sidebar",
    )

def investigation_left_column() -> rx.Component:
    return rx.vstack(
        investigation_panel(
            "Historia del expediente",
            rx.text(PublicRecordState.story_headline, class_name="story-headline"),
            rx.text(PublicRecordState.story_summary, class_name="story-summary"),
            rx.cond(
                PublicRecordState.story_key_findings,
                rx.hstack(
                    rx.foreach(PublicRecordState.story_key_findings, lambda item: rx.text(item, class_name="story-chip")),
                    spacing="2",
                    wrap="wrap",
                ),
                rx.text("No hay hallazgos clave disponibles.", class_name="muted small"),
            ),
            subtitle="Primero el resumen; el detalle técnico se mantiene oculto.",
        ),
        investigation_panel(
            "Narrativa ciudadana",
            rx.text(PublicRecordState.citizen_narrative, class_name="story-summary story-summary-dominant"),
            rx.cond(
                PublicRecordState.story_important_connections,
                rx.vstack(
                    rx.foreach(PublicRecordState.story_important_connections, narrative_item),
                    spacing="2",
                    align="stretch",
                ),
                rx.text("No hay narrativa ciudadana disponible.", class_name="muted small"),
            ),
            rx.cond(
                PublicRecordState.story_questions,
                rx.hstack(
                    rx.foreach(PublicRecordState.story_questions, lambda item: rx.text(item, class_name="prompt-chip")),
                    spacing="2",
                    wrap="wrap",
                ),
                rx.text("No hay sugerencias de recorrido disponibles.", class_name="muted small"),
            ),
            subtitle="Pistas breves y contexto para guiar la exploración.",
        ),
        timeline_highlights_panel(),
        spacing="3",
        align="stretch",
        class_name="story-main investigation-left",
    )

def investigation_center_column() -> rx.Component:
    return rx.vstack(
        state_graph_connections_panel(),
        relationship_map_panel(),
        investigation_tabs_panel(),
        spacing="3",
        align="stretch",
        class_name="story-main investigation-center",
    )

def narrative_panel(title: str, body: str, items: list[str] | None = None) -> rx.Component:
    return investigation_panel(
        title,
        rx.text(body, class_name="story-summary story-summary-dominant"),
        rx.cond(
            items or [],
            rx.vstack(
                rx.foreach(items or [], narrative_item),
                spacing="2",
                align="stretch",
            ),
        ),
    )

def history_panel() -> rx.Component:
    return investigation_panel(
        "Historia",
        rx.text(PublicRecordState.story_headline, class_name="story-headline"),
        rx.text(PublicRecordState.story_summary, class_name="story-summary"),
        rx.cond(
            PublicRecordState.story_key_findings,
            rx.hstack(
                rx.foreach(PublicRecordState.story_key_findings, lambda item: rx.text(item, class_name="story-chip")),
                spacing="2",
                wrap="wrap",
            ),
            rx.text("No hay puntos destacados disponibles para este expediente.", class_name="muted small"),
        ),
        subtitle="Una lectura unica del expediente, independiente del punto de entrada.",
    )

def citizen_narrative_panel() -> rx.Component:
    return investigation_panel(
        "Narrativa ciudadana",
        rx.text(PublicRecordState.citizen_narrative, class_name="story-summary story-summary-dominant"),
        rx.cond(
            PublicRecordState.story_important_connections,
            rx.vstack(
                rx.foreach(PublicRecordState.story_important_connections, narrative_item),
                spacing="2",
                align="stretch",
            ),
            rx.text("No hay conexiones destacadas disponibles.", class_name="muted small"),
        ),
        rx.cond(
            PublicRecordState.story_questions,
            rx.hstack(
                rx.foreach(PublicRecordState.story_questions, lambda item: rx.text(item, class_name="prompt-chip")),
                spacing="2",
                wrap="wrap",
            ),
        ),
        subtitle="Lenguaje descriptivo para entender que muestran los datos locales.",
    )

def relationship_journey_panel() -> rx.Component:
    return investigation_panel(
        "Como se conectan los datos",
        rx.cond(
            PublicRecordState.relationship_journey_rows,
            rx.vstack(
                rx.foreach(PublicRecordState.relationship_journey_rows, journey_node),
                spacing="2",
                align="stretch",
                class_name="journey-list",
            ),
            rx.text("No hay recorrido de relaciones disponible.", class_name="muted small"),
        ),
        subtitle="Una ruta legible reemplaza el grafo denso. Cada paso indica fuente y motivo.",
    )

def evidence_journey_panel() -> rx.Component:
    return investigation_panel(
        "Recorrido de evidencia",
        rx.tabs.root(
            rx.tabs.list(
                rx.tabs.trigger("Compras", value="procurement"),
                rx.tabs.trigger("Lobby", value="lobby"),
                rx.tabs.trigger("Transparencia", value="transparency"),
                rx.tabs.trigger("Empresas", value="registry"),
                rx.tabs.trigger("Evidencia", value="evidence"),
                class_name="tabs-list",
            ),
            rx.tabs.content(
                rx.cond(
                    PublicRecordState.procurement_rows,
                    rx.grid(rx.foreach(PublicRecordState.procurement_rows, evidence_card), columns="2", spacing="2", class_name="tab-grid"),
                    rx.text("No hay compras asociadas en los datos locales.", class_name="muted small"),
                ),
                value="procurement",
                class_name="tab-content",
            ),
            rx.tabs.content(
                rx.cond(
                    PublicRecordState.lobby_rows,
                    rx.grid(rx.foreach(PublicRecordState.lobby_rows, evidence_card), columns="2", spacing="2", class_name="tab-grid"),
                    rx.text("No hay reuniones asociadas en los datos locales.", class_name="muted small"),
                ),
                value="lobby",
                class_name="tab-content",
            ),
            rx.tabs.content(
                rx.cond(
                    PublicRecordState.transparencia_rows,
                    rx.grid(rx.foreach(PublicRecordState.transparencia_rows, evidence_card), columns="2", spacing="2", class_name="tab-grid"),
                    rx.text("No hay registros de transparencia asociados.", class_name="muted small"),
                ),
                value="transparency",
                class_name="tab-content",
            ),
            rx.tabs.content(
                rx.cond(
                    PublicRecordState.registry_rows,
                    rx.grid(rx.foreach(PublicRecordState.registry_rows, evidence_card), columns="2", spacing="2", class_name="tab-grid"),
                    rx.text("No hay registros societarios asociados.", class_name="muted small"),
                ),
                value="registry",
                class_name="tab-content",
            ),
            rx.tabs.content(
                rx.cond(
                    PublicRecordState.evidence_rows,
                    rx.grid(rx.foreach(PublicRecordState.evidence_rows, evidence_card), columns="2", spacing="2", class_name="tab-grid"),
                    rx.text("No hay evidencia asociada.", class_name="muted small"),
                ),
                value="evidence",
                class_name="tab-content",
            ),
            default_value="procurement",
            class_name="tabs-root",
        ),
        subtitle="Registros organizados por tema, no por estructura tecnica.",
    )

def related_entities_panel() -> rx.Component:
    return investigation_panel(
        "Entidades relacionadas",
        rx.cond(
            PublicRecordState.related_entity_group_rows,
            rx.grid(
                rx.foreach(PublicRecordState.related_entity_group_rows, related_entity_group),
                columns="2",
                spacing="3",
                class_name="responsive-grid",
            ),
            rx.text("No hay entidades relacionadas disponibles.", class_name="muted small"),
        ),
        subtitle="Cada tarjeta explica por que aparece en este expediente.",
    )

def sources_section_panel() -> rx.Component:
    return investigation_panel(
        "Fuentes consultadas",
        rx.cond(
            PublicRecordState.source_contribution_rows,
            rx.grid(
                rx.foreach(PublicRecordState.source_contribution_rows, source_card),
                columns="2",
                spacing="3",
                class_name="responsive-grid",
            ),
            rx.text("No hay fuentes consultadas disponibles.", class_name="muted small"),
        ),
        subtitle="Metadata proveniente del registro de fuentes publicas locales.",
    )

def source_coverage_panel() -> rx.Component:
    return investigation_panel(
        "Cobertura de fuentes",
        rx.cond(
            PublicRecordState.source_coverage_rows,
            rx.grid(
                rx.foreach(PublicRecordState.source_coverage_rows, source_coverage_card),
                columns="2",
                spacing="3",
                class_name="responsive-grid",
            ),
            rx.text("No hay cobertura de fuentes disponible.", class_name="muted small"),
        ),
        subtitle="Estado de cada fuente en la publicación actual y qué aporta al expediente.",
    )

def technical_panel() -> rx.Component:
    return rx.accordion.root(
        rx.accordion.item(
            header="Detalles tecnicos / trazabilidad",
            content=rx.vstack(
                rx.text(
                    "Informacion tecnica colapsada: comandos locales, tipos de evidencia, codigos internos y URLs de respaldo.",
                    class_name="muted small",
                ),
                rx.cond(
                    PublicRecordState.source_contribution_rows,
                    rx.vstack(
                        rx.foreach(PublicRecordState.source_contribution_rows, technical_source_card),
                        spacing="2",
                        align="stretch",
                    ),
                ),
                rx.cond(
                    PublicRecordState.technical_details,
                    rx.vstack(
                        rx.foreach(PublicRecordState.technical_details, technical_detail_card),
                        spacing="2",
                        align="stretch",
                    ),
                    rx.text("No hay detalles tecnicos disponibles.", class_name="muted small"),
                ),
                spacing="2",
                align="stretch",
            ),
            value="technical-details",
        ),
        type="single",
        collapsible=True,
        variant="ghost",
        class_name="technical-accordion technical-bottom",
    )

def single_investigation_product_view() -> rx.Component:
    return rx.vstack(
        history_panel(),
        citizen_summary_panel(),
        citizen_narrative_panel(),
        relationship_journey_panel(),
        timeline_highlights_panel(),
        evidence_journey_panel(),
        related_entities_panel(),
        source_coverage_panel(),
        sources_section_panel(),
        technical_panel(),
        spacing="4",
        align="stretch",
        class_name="product-investigation-flow",
    )

def citizen_report_card(row: dict) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.text(row["classification"], class_name="badge badge-teal"),
            rx.text(row["current_status"], class_name="mini-pill mini-pill-purple"),
            justify="between",
            align="center",
        ),
        rx.text(row["title"], class_name="card-title"),
        rx.text(row["subtitle"], class_name="muted small"),
        rx.text(f"Materia: {row['subject']}", class_name="source-fact"),
        rx.hstack(
            rx.button("Abrir expediente", on_click=PublicRecordState.open_canonical_investigation(row["related_expediente_target"]), class_name="button"),
            rx.text("Versión HTML disponible solo en operación interna", class_name="muted small"),
            spacing="2",
            wrap="wrap",
        ),
        class_name="card report-card",
    )

def citizen_report_section_card(row: dict) -> rx.Component:
    return rx.box(
        rx.text(row["title"], class_name="card-title"),
        rx.text(row["summary"], class_name="muted small"),
        rx.vstack(
            rx.text("Evidencia", class_name="muted small"),
            rx.text(
                rx.cond(row["evidence_text"] != "", row["evidence_text"], "sin referencias"),
                class_name="source-fact",
            ),
            spacing="1",
            align="stretch",
        ),
        class_name="card report-section-card",
    )
