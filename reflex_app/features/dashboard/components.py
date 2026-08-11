from __future__ import annotations

import reflex as rx

from reflex_app.features.public_record.state import PublicRecordState


def search_example_card(row: dict) -> rx.Component:
    return rx.box(
        rx.text(row["organization_name"], class_name="card-title"),
        rx.text(row["datasets_text"], class_name="badge badge-teal"),
        rx.text(f"Contratos: {row['contracts']} | reuniones: {row['lobby_meetings']}", class_name="muted small"),
        rx.text(f"Evidencia: {row['evidence']} | relaciones: {row['relationships']}", class_name="muted small"),
        rx.button(
            "Abrir expediente",
            on_click=PublicRecordState.open_canonical_investigation(row["organization_id"]),
            class_name="button button-secondary",
        ),
        class_name="card example-card",
    )

def dashboard_budget_card(row: dict) -> rx.Component:
    return rx.box(
        rx.text(row["organization_name"], class_name="card-title"),
        rx.text(f"Año fiscal: {row.get('fiscal_year', '')}", class_name="muted small"),
        rx.text(
            f"Ejecutado: {row.get('executed_budget', 0)} {row.get('currency', 'CLP')}",
            class_name="source-fact",
        ),
        rx.text(
            f"Aprobado: {row.get('approved_budget', 0)} | OC: {row.get('purchase_orders', 0)} | Proveedores: {row.get('suppliers', 0)}",
            class_name="muted small",
        ),
        class_name="card dashboard-card",
    )

def discovery_case_card(row: dict) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.text(row["title"], class_name="card-title"),
            rx.text(row["id_label"], class_name="badge badge-purple"),
            justify="between",
            align="center",
        ),
        rx.text(row["description"], class_name="muted small"),
        rx.hstack(
            rx.text(row.get("concepts_text", ""), class_name="search-chip"),
            rx.text(row.get("sources_text", ""), class_name="mini-pill mini-pill-purple"),
            spacing="2",
            wrap="wrap",
        ),
        rx.text(f"Ejemplo: {row['example_query']}", class_name="source-fact"),
        rx.button(
            row.get("cta", "Explorar"),
            on_click=rx.redirect(row["search_href"]),
            class_name="button button-secondary",
        ),
        class_name="card example-card discovery-card",
    )
