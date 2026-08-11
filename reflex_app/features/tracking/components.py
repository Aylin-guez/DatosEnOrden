from __future__ import annotations

import reflex as rx

from reflex_app.features.public_record.state import PublicRecordState


def tracking_item_card(row: dict) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.text(row["item_type"], class_name="badge badge-purple"),
            rx.text(row["current_status"], class_name="badge badge-teal"),
            justify="between",
            align="center",
        ),
        rx.text(row["title"], class_name="card-title"),
        rx.text(row["summary"], class_name="muted small"),
        rx.hstack(
            rx.button("Abrir expediente", on_click=PublicRecordState.open_canonical_investigation(row["related_expediente_target"]), class_name="button"),
            rx.button("Ver recorrido", on_click=rx.redirect("/demo"), class_name="button button-secondary"),
            spacing="2",
            wrap="wrap",
        ),
        class_name="card tracking-card",
    )

def tracking_document_card(row: dict) -> rx.Component:
    return rx.box(
        rx.text(row["source"], class_name="badge badge-teal"),
        rx.text(row["title"], class_name="card-title"),
        rx.text(f"{row['document_type']} | {row['published_at']}", class_name="muted small"),
        rx.text(row["summary"], class_name="source-fact"),
        rx.text(row["official_url"], class_name="mono id-line"),
        class_name="card tracking-document-card",
    )
