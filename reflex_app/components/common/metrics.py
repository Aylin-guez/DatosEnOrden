from __future__ import annotations

import reflex as rx


def metric(label: str, value) -> rx.Component:  # noqa: ANN001
    return rx.box(
        rx.text(value, class_name="metric-value"),
        rx.text(label, class_name="muted"),
        class_name="metric-card",
    )


def metric_card(label: str, value, helper: str = "") -> rx.Component:  # noqa: ANN001
    return rx.box(
        rx.text(value, class_name="summary-value"),
        rx.text(label, class_name="summary-label"),
        rx.cond(helper != "", rx.text(helper, class_name="muted small")),
        class_name="summary-card product-metric-card",
    )


def document_metric(label: str, value: rx.Var | int) -> rx.Component:
    return rx.box(
        rx.text(value, class_name="document-metric-value"),
        rx.text(label, class_name="document-metric-label"),
        class_name="document-metric",
    )

def summary_metric_card(label: str, value) -> rx.Component:  # noqa: ANN001
    return rx.box(
        rx.text(label, class_name="summary-label"),
        rx.text(value, class_name="summary-value"),
        class_name="summary-card",
    )
