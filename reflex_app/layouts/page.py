from __future__ import annotations

import reflex as rx

from reflex_app.constants.routes import (
    PAGE_DEMO,
    PAGE_DISCOVER,
    PAGE_DOCUMENT,
    PAGE_ECOSYSTEM,
    PAGE_HOME,
    PAGE_INVESTIGATION,
    PAGE_KNOWLEDGE,
    PAGE_LABORATORY,
    PAGE_LABORATORY_EXPEDIENT,
    PAGE_LIBRARY,
    PAGE_NOT_FOUND,
    PAGE_PROJECT,
    PAGE_REPORTS,
    PAGE_SEARCH,
    PAGE_STUDIO,
    PAGE_SUPPORT,
    PAGE_TOPIC,
    PAGE_TRACKING,
)


def page_section(title: str, *children, subtitle: str | None = None, class_name: str = "", element_id: str = "") -> rx.Component:
    title_key = title.lower() if isinstance(title, str) else ""
    section_icon = _section_icon(title_key)
    body = [rx.hstack(rx.text(section_icon, class_name="section-icon"), rx.text(title, class_name="section-title"), spacing="2", align="center")]
    if subtitle is not None:
        body.append(rx.text(subtitle, class_name="section-subtitle"))
    body.extend(children)
    section_class = "page-section" if not class_name else f"page-section {class_name}"
    return rx.vstack(*body, spacing="3", align="stretch", class_name=section_class, id=element_id)


def _section_icon(title_key: str) -> str:
    if "buscar" in title_key or "explorar" in title_key:
        return "?"
    if "fuente" in title_key:
        return "F"
    if "cronolog" in title_key or "seguimiento" in title_key:
        return "C"
    if "document" in title_key or "lectura" in title_key:
        return "D"
    if "proyecto" in title_key or "acerca" in title_key:
        return "A"
    if "studio" in title_key:
        return "S"
    if "informe" in title_key:
        return "I"
    if "evidencia" in title_key:
        return "E"
    if "expediente" in title_key:
        return "X"
    if "laboratorio" in title_key:
        return "L"
    return "*"


def _page_class(active_page: str) -> str:
    return {
        PAGE_HOME: "page-home",
        PAGE_TOPIC: "page-topic",
        PAGE_DISCOVER: "page-discover",
        PAGE_INVESTIGATION: "page-investigation",
        PAGE_LIBRARY: "page-library",
        PAGE_KNOWLEDGE: "page-library",
        PAGE_DOCUMENT: "page-document",
        PAGE_TRACKING: "page-tracking",
        PAGE_REPORTS: "page-reports",
        PAGE_ECOSYSTEM: "page-ecosystem",
        PAGE_PROJECT: "page-project",
        PAGE_SUPPORT: "page-project",
        PAGE_STUDIO: "page-project",
        PAGE_NOT_FOUND: "page-project page-not-found",
        PAGE_SEARCH: "page-discover",
        PAGE_DEMO: "page-home",
        PAGE_LABORATORY: "page-laboratory",
        PAGE_LABORATORY_EXPEDIENT: "page-laboratory",
    }.get(active_page, "page-home")
