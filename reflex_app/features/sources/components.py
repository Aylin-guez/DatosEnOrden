from __future__ import annotations

import reflex as rx

from reflex_app.components.common.badges import _accent_badge_class


def ecosystem_source_card(row: dict) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.text(row["name"], class_name="card-title"),
            rx.text(row["presentation_status"], class_name=_accent_badge_class(str(row.get("presentation_status", "")))),
            justify="between",
            align="center",
        ),
        rx.text(row["description"], class_name="muted"),
        rx.hstack(
            rx.text(f"catalogo: {row['catalog_status']}", class_name="mini-pill"),
            rx.text(row["coverage_status_label"], class_name="mini-pill mini-pill-purple"),
            spacing="2",
            wrap="wrap",
        ),
        rx.text(f"que aporta: {row['concepts_text']}", class_name="source-fact"),
        rx.text(f"con que se cruza: {row.get('connects_with_text', '')}", class_name="source-fact"),
        rx.text(row["connector_status_label"], class_name="source-fact"),
        rx.text(row["data_status_label"], class_name="source-fact"),
        rx.cond(
            row["population_label"] != "",
            rx.text(row["population_label"], class_name="source-fact source-population-note"),
        ),
        rx.cond(
            row["connector_label"] != "",
            rx.text(row["connector_label"], class_name="source-fact"),
        ),
        rx.cond(
            row.get("state_graph_contribution_label", "") != "",
            rx.text(row.get("state_graph_contribution_label", ""), class_name="source-fact evidence-trust"),
        ),
        rx.accordion.root(
            rx.accordion.item(
                header="Vista tecnica de metadata",
                content=rx.vstack(
                    rx.text(f"entidades: {row.get('entities_text', '')}", class_name="technical-line"),
                    rx.text(f"relationships: {row['relationships_text']}", class_name="technical-line"),
                    spacing="2",
                    align="stretch",
                ),
                value=f"source-meta-{row['slug']}",
            ),
            type="single",
            collapsible=True,
            variant="ghost",
            class_name="technical-accordion",
        ),
        class_name="card ecosystem-card",
    )


def ecosystem_concept_card(row: dict) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.text(row["name"], class_name="card-title"),
            rx.text(row["coverage"], class_name=_accent_badge_class(str(row.get("coverage", "")))),
            justify="between",
            align="center",
        ),
        rx.text(row["datasets_text"], class_name="source-fact"),
        class_name="card concept-card",
    )


def ecosystem_roadmap_card(row: dict) -> rx.Component:
    return rx.box(
        rx.text(row["title"], class_name="card-title"),
        rx.text(row["sources_text"], class_name="source-fact"),
        rx.text(row.get("note_text", ""), class_name="muted small"),
        class_name="card",
    )


def real_data_source_card(row: dict) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.text(row["display_name"], class_name="card-title"),
            rx.text(row["status"], class_name=_accent_badge_class(str(row.get("status", "")))),
            justify="between",
            align="center",
        ),
        rx.text(row["description"], class_name="muted small"),
        rx.hstack(
            rx.text(f"registros: {row['source_records']}", class_name="mini-pill"),
            rx.text(f"entidades: {row['entities']}", class_name="mini-pill"),
            rx.text(f"relaciones: {row['relationships']}", class_name="mini-pill mini-pill-purple"),
            rx.text(f"REAL: {row.get('official_records', 0)}", class_name="mini-pill evidence-trust"),
            rx.text(f"available: {row.get('available_records', 0)}", class_name="mini-pill evidence-trust"),
            rx.text(f"rejected: {row.get('rejected_records', 0)}", class_name="mini-pill"),
            spacing="2",
            wrap="wrap",
        ),
        rx.text(f"formato: {row['expected_format']}", class_name="source-fact"),
        rx.text(f"loader: {row['loader_script']}", class_name="technical-line"),
        rx.text(f"ultima carga: {row.get('last_loaded', '')}", class_name="technical-line"),
        rx.text(f"cobertura: {row['coverage']}", class_name="muted small"),
        class_name="card ecosystem-card real-data-card",
    )
