from __future__ import annotations

import reflex as rx

from reflex_app.components.common.cards import help_card
from reflex_app.constants.demo import DEMO_INVESTIGATION_TARGET
from reflex_app.constants.routes import PAGE_REPORTS
from reflex_app.features.reports.components import citizen_report_card, citizen_report_section_card
from reflex_app.features.reports.state import ReportsState
from reflex_app.components.common.cards import next_step_card
from reflex_app.helpers.routing import _investigation_href
from reflex_app.layouts.page import page_section
from reflex_app.layouts.shell import shell
from reflex_app.metadata.pages import PUBLIC_OG_IMAGE_URL, _page_meta


@rx.page(
    route="/reports",
    title="Informes ciudadanos - DatosEnOrden",
    description="Informes ciudadanos con resumen, evidencia, secciones y exportaci?n local de muestra.",
    image=PUBLIC_OG_IMAGE_URL,
    meta=_page_meta(
        "/reports",
        "informes ciudadanos, evidencia, reporte, expediente",
        "Informes ciudadanos - DatosEnOrden",
        "Informes ciudadanos con resumen, evidencia, secciones y exportaci?n local de muestra.",
    ),
    on_load=ReportsState.load_reports,
)
def reports() -> rx.Component:
    loaded_report = rx.box(
        page_section(
            "Resumen",
            rx.text(ReportsState.citizen_report_summary, class_name="story-summary"),
            rx.hstack(
                rx.text(ReportsState.citizen_report_status, class_name="badge badge-teal"),
                rx.text("Muestra local no oficial", class_name="mini-pill evidence-trust"),
                spacing="2",
                wrap="wrap",
            ),
            subtitle="Lectura inicial para entender el caso sin sacar conclusiones apresuradas.",
            class_name="reports-article-section",
        ),
        page_section(
            "Que cambio",
            rx.grid(
                rx.foreach(ReportsState.citizen_report_sections, citizen_report_section_card),
                columns="3",
                spacing="3",
                class_name="responsive-grid",
            ),
            subtitle="Hitos y conexiones explicadas como lectura ciudadana.",
            class_name="reports-wide-section",
        ),
        page_section(
            "Por que importa",
            rx.grid(
                help_card("Contexto", "Reune piezas que suelen estar separadas: documento, expediente, seguimiento y fuentes."),
                help_card("Revision", "Permite volver a la evidencia antes de compartir o citar una afirmacion."),
                help_card("Continuidad", "Conecta el reporte con una historia que puede seguir cambiando."),
                columns="3",
                spacing="3",
                class_name="responsive-grid",
            ),
            subtitle="El reporte no acusa ni concluye: ayuda a comprender y revisar.",
            class_name="reports-wide-section",
        ),
        page_section(
            "Fuentes",
            rx.hstack(
                rx.foreach(ReportsState.citizen_report_sources, lambda item: rx.text(item, class_name="search-chip")),
                spacing="2",
                wrap="wrap",
            ),
            rx.hstack(
                rx.foreach(ReportsState.citizen_report_evidence_refs, lambda item: rx.text(item, class_name="mini-pill")),
                spacing="2",
                wrap="wrap",
            ),
            subtitle="Referencias livianas: metadata y anclas de evidencia, sin PDFs pesados.",
            class_name="reports-wide-section",
        ),
        page_section(
            "Expedientes relacionados",
            rx.grid(
                next_step_card("Abrir expediente", "Ver contexto, relaciones y evidencia asociada.", "Ir al expediente", _investigation_href(DEMO_INVESTIGATION_TARGET)),
                next_step_card("Ver documento fuente", "Leer el documento junto a sus referencias.", "Ver documento", "/official-document"),
                next_step_card("Seguir proyecto", "Revisar timeline, estados y cambios.", "Ir a Cronologia", "/tracking"),
                columns="3",
                spacing="3",
                class_name="responsive-grid",
            ),
            subtitle="El reporte es una puerta de entrada, no un callejon sin salida.",
        ),
        page_section(
            "Aclaración",
            rx.text(
                "Este reporte usa datos locales de prueba, no oficiales. No afirma causalidad, irregularidad ni responsabilidad.",
                class_name="story-summary",
            ),
            subtitle="Contexto obligatorio para esta publicación pública.",
        ),
        class_name="reports-loaded-content",
    )
    empty_report = page_section(
        "Sin informe seleccionado",
        rx.text(
            "Cuando exista un informe ciudadano local disponible, aparecerá aqué con resumen, fuentes y evidencia relacionada.",
            class_name="story-summary",
        ),
        subtitle="Estado estable: no se muestran fuentes temporales ni contenido que desaparece al cargar.",
        class_name="reports-empty-section",
    )
    return shell(
        rx.box(
            rx.text("Informes ciudadanos", class_name="title"),
            rx.text(
                "Informes locales de lectura pública que conectan expediente, seguimiento, fuentes y evidencia navegable.",
                class_name="subtitle",
            ),
            rx.hstack(
                rx.button("Abrir expediente", on_click=ReportsState.open_report_investigation, class_name="button"),
                rx.button("Ver seguimiento", on_click=rx.redirect("/tracking"), class_name="button button-secondary"),
                rx.button("Ver recorrido", on_click=rx.redirect("/demo"), class_name="button button-secondary"),
                spacing="3",
                wrap="wrap",
                class_name="hero-actions",
            ),
            class_name="hero",
        ),
        page_section(
            "Informes disponibles",
            rx.cond(
                ReportsState.citizen_reports,
                rx.grid(
                    rx.foreach(ReportsState.citizen_reports, citizen_report_card),
                    columns="2",
                    spacing="3",
                    class_name="responsive-grid",
                ),
                rx.text("No hay informes ciudadanos locales disponibles.", class_name="muted small"),
            ),
            subtitle="Prototipos read-only marcados como datos locales de prueba.",
            class_name="reports-catalog-section",
        ),
        rx.cond(ReportsState.citizen_report_title != "", loaded_report, empty_report),
        on_mount=ReportsState.load_reports,
        active_page=PAGE_REPORTS,
    )
