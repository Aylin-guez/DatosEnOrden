from __future__ import annotations

import reflex as rx


def _flow_accent_class(step: int) -> str:
    return {1: "flow-accent flow-accent-teal", 2: "flow-accent flow-accent-purple"}.get(step, "flow-accent flow-accent-amber")


def flow_card(step: int, title: str, body: str) -> rx.Component:
    return rx.box(
        rx.text(f"{step:02d}", class_name=_flow_accent_class(step)),
        rx.text(title, class_name="card-title"),
        rx.text(body, class_name="muted small"),
        class_name="card flow-card",
    )


def help_card(title: str, body: str) -> rx.Component:
    return rx.box(
        rx.text(title, class_name="context-title"),
        rx.text(body, class_name="muted small"),
        class_name="card help-card",
    )


def support_action_card(title: str, body: str, label: str, href: str) -> rx.Component:
    return rx.box(
        rx.text(title, class_name="card-title"),
        rx.text(body, class_name="muted small"),
        rx.link(label, href=href, class_name="document-inline-link support-action-link"),
        class_name="card support-action-card",
    )


def tracking_evidence_card(row: dict) -> rx.Component:
    return rx.box(
        rx.text(row["source"], class_name="mini-pill"),
        rx.text(row["label"], class_name="context-title"),
        rx.text(row["excerpt"], class_name="muted small"),
        rx.text(row["url"], class_name="mono id-line"),
        class_name="context-item",
    )


def loading_placeholder_card(title: str, body: str) -> rx.Component:
    return rx.box(
        rx.text(title, class_name="card-title"),
        rx.box(class_name="loading-skeleton-line loading-skeleton-line-medium"),
        rx.box(class_name="loading-skeleton-line"),
        rx.box(class_name="loading-skeleton-line loading-skeleton-line-short"),
        rx.text(body, class_name="muted small"),
        class_name="card loading-skeleton-card",
    )


def investigation_entry_card(title: str, body: str, button_label: str, href: str, accent_class: str = "button") -> rx.Component:
    return rx.box(
        rx.text(title, class_name="card-title"),
        rx.text(body, class_name="muted small"),
        rx.button(button_label, on_click=rx.redirect(href), class_name=accent_class),
        class_name="card empty-entry-card",
    )


def card_grid_or_empty(rows, renderer, *, columns: str, empty_title: str, empty_body: str, action_label: str, href: str, class_name: str = "responsive-grid") -> rx.Component:  # noqa: ANN001
    return rx.cond(
        rows,
        rx.grid(
            rx.foreach(rows, renderer),
            columns=columns,
            spacing="3",
            class_name=class_name,
        ),
        investigation_entry_card(empty_title, empty_body, action_label, href, "button button-secondary"),
    )


def next_step_card(title: str, body: str, label: str, href: str) -> rx.Component:
    return rx.box(
        rx.text(title, class_name="card-title"),
        rx.text(body, class_name="muted small"),
        rx.button(label, on_click=rx.redirect(href), class_name="button button-secondary"),
        class_name="card next-step-card",
    )


def tracking_event_card(row: dict) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.text("*", class_name="source-card-icon"),
            rx.text(row["date"], class_name="badge badge-teal"),
            rx.text(row["status"], class_name="mini-pill mini-pill-purple"),
            justify="between",
            align="center",
        ),
        rx.text(row["title"], class_name="card-title"),
        rx.text(row["description"], class_name="muted small"),
        rx.text(f"Fuente: {row['source']}", class_name="source-fact"),
        rx.text(rx.cond(row.get("origin", "") == "demo_manual", "Origen: demo manual", "Origen: timeline derivada"), class_name="mini-pill evidence-trust"),
        class_name="card tracking-event-card",
    )
