from __future__ import annotations

import reflex as rx


def home_pulse_card(row: dict) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.text("*", class_name="source-card-icon"),
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
            rx.button("Ver lectura o documento", on_click=rx.redirect(row["href"]), class_name="button"),
            class_name="pulse-field",
        ),
        class_name="current-topic-card home-pulse-card topic-card-document",
    )
