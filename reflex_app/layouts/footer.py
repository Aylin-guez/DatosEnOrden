from __future__ import annotations

import reflex as rx


def footer_text_link(icon: str, label: str, href: str) -> rx.Component:
    return rx.link(
        rx.hstack(
            rx.text(icon, class_name="footer-link-icon"),
            rx.text(label, class_name="footer-link-label"),
            spacing="2",
            align="center",
        ),
        href=href,
        title=label,
        aria_label=label,
        class_name="footer-link footer-column-link",
    )
