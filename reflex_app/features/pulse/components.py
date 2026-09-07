from __future__ import annotations

import reflex as rx


def home_pulse_card(row: dict) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.text(row["status"], class_name="badge badge-teal"),
            rx.text(row["updated_at"], class_name="mini-pill mini-pill-purple"),
            spacing="2",
            wrap="wrap",
        ),
        rx.text(row["title"], class_name="card-title"),
        rx.box(
            rx.text("Que cambio", class_name="pulse-field-label"),
            rx.text(row["summary"], class_name="muted small"),
            class_name="pulse-field",
        ),
        rx.box(
            rx.text("Fuente que lo sostiene", class_name="pulse-field-label"),
            rx.text(row["organization"], class_name="source-fact"),
            class_name="pulse-field",
        ),
        rx.box(
            rx.text("Abrir contexto", class_name="pulse-field-label"),
            rx.cond(
                row["actionable"],
                rx.link("Ver lectura o documento", href=row["href"], class_name="button"),
                rx.text(row["action_notice"], class_name="muted small"),
            ),
            class_name="pulse-field",
        ),
        class_name="current-topic-card home-pulse-card topic-card-document",
    )


def featured_expedient_card(row: dict) -> rx.Component:
    return rx.box(
        rx.text("Expediente público", class_name="badge badge-teal"),
        rx.text(row["title"], class_name="card-title"),
        rx.text(row["question"], class_name="muted small"),
        rx.button(
            "Abrir expediente",
            on_click=rx.redirect(f"/laboratory/expedient?id={row['id']}"),
            class_name="button button-secondary",
        ),
        class_name="card public-demo-card",
    )
