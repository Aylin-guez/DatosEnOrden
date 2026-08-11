from __future__ import annotations

import reflex as rx

from reflex_app.components.common.cards import investigation_entry_card, next_step_card
from reflex_app.components.common.cards import help_card, tracking_evidence_card
from reflex_app.constants.routes import PAGE_DOCUMENT, PAGE_KNOWLEDGE, PAGE_LIBRARY, PAGE_TOPIC
from reflex_app.features.document_reading.components import (
    guide_evidence,
    knowledge_claim_card,
    knowledge_connection_card,
    knowledge_document_card,
    knowledge_key_point_card,
    knowledge_question_card,
    document_fragment_panel,
    official_document_pdf_viewer,
    official_document_viewer,
    reading_guide_panel,
    support_cta_block,
    topic_mode_body,
    topic_mode_selector,
)
from reflex_app.features.document_reading.state import DocumentReadingState
from reflex_app.layouts.page import page_section
from reflex_app.layouts.shell import shell
from reflex_app.metadata.pages import PUBLIC_OG_IMAGE_URL, _page_meta


@rx.page(
    route="/topic",
    title="Lectura documentada - Ley de Presupuestos 2013 - DatosEnOrden",
    description="Lectura documentada del documento oficial principal con evidencia visible y navegación al PDF publicado.",
    image=PUBLIC_OG_IMAGE_URL,
    meta=_page_meta(
        "/topic",
        "lectura documentada, ley de presupuestos 2013, documento oficial, evidencia, PDF",
        "Lectura documentada - Ley de Presupuestos 2013 - DatosEnOrden",
        "Lectura documentada del documento oficial principal con evidencia visible y navegación al PDF publicado.",
    ),
)
def topic() -> rx.Component:
    return shell(
        rx.box(
            rx.text("Lectura documentada", class_name="document-kicker"),
            rx.text(DocumentReadingState.topic_title, class_name="document-title"),
            rx.text(
                "Primero el documento. Luego la explicacion ciudadana y la evidencia que permite verificar cada afirmacion.",
                class_name="document-subtitle",
            ),
            rx.hstack(
                rx.text(DocumentReadingState.topic_status, class_name="document-meta-pill"),
                rx.text(DocumentReadingState.topic_read_time, class_name="document-meta-pill"),
                rx.text(DocumentReadingState.topic_updated_at, class_name="document-meta-reference"),
                spacing="2",
                wrap="wrap",
                class_name="document-meta-row",
            ),
            topic_mode_selector(),
            rx.text(DocumentReadingState.topic_organizations_text, class_name="document-meta-reference"),
            class_name="document-hero topic-hero",
        ),
        topic_mode_body(),
        support_cta_block(),
        on_mount=DocumentReadingState.load_topic,
        active_page=PAGE_TOPIC,
    )

@rx.page(
    route="/knowledge",
    title="Conocimiento - DatosEnOrden",
    description="Resumen estructurado de documentos oficiales con preguntas, claims y evidencia revisable.",
    image=PUBLIC_OG_IMAGE_URL,
    meta=_page_meta(
        "/knowledge",
        "conocimiento, documento oficial, preguntas ciudadanas, claims, evidencia",
        "Conocimiento - DatosEnOrden",
        "Resumen estructurado de documentos oficiales con preguntas, claims y evidencia revisable.",
    ),
)
def knowledge() -> rx.Component:
    return shell(
        rx.box(
            rx.text("Knowledge Engine", class_name="title"),
            rx.text(
                "Motor local read-only para transformar documentos oficiales o registros publicos de prueba en conocimiento estructurado.",
                class_name="subtitle",
            ),
            rx.hstack(
                rx.button("Abrir expediente", on_click=DocumentReadingState.open_knowledge_investigation, class_name="button"),
                rx.button("Ver cronologia", on_click=rx.redirect("/tracking"), class_name="button button-secondary"),
                rx.button("Ver informes", on_click=rx.redirect("/reports"), class_name="button button-secondary"),
                spacing="3",
                wrap="wrap",
                class_name="hero-actions",
            ),
            class_name="hero",
        ),
        page_section(
            "Documentos disponibles",
            rx.cond(
                DocumentReadingState.knowledge_documents,
                rx.grid(
                    rx.foreach(DocumentReadingState.knowledge_documents, knowledge_document_card),
                    columns="2",
                    spacing="3",
                    class_name="responsive-grid",
                ),
                rx.text("No hay documentos locales disponibles.", class_name="muted small"),
            ),
            subtitle="Solo metadata y secciones locales de prueba; sin scraping, APIs externas ni PDFs pesados.",
        ),
        page_section(
            "Resumen ciudadano",
            rx.text(DocumentReadingState.knowledge_summary, class_name="story-summary"),
            rx.hstack(
                rx.text("Muestra local no oficial", class_name="mini-pill evidence-trust"),
                rx.text(DocumentReadingState.knowledge_title, class_name="badge badge-teal"),
                spacing="2",
                wrap="wrap",
            ),
            subtitle="Resumen rule-based generado desde campos ya presentes en el JSON local.",
        ),
        page_section(
            "Puntos importantes",
            rx.grid(
                rx.foreach(DocumentReadingState.knowledge_key_points, knowledge_key_point_card),
                columns="2",
                spacing="3",
                class_name="responsive-grid",
            ),
            subtitle="Lectura estructurada por secciones, sin inferir culpabilidad ni riesgo.",
        ),
        page_section(
            "Preguntas ciudadanas sugeridas",
            rx.grid(
                rx.foreach(DocumentReadingState.knowledge_questions, knowledge_question_card),
                columns="3",
                spacing="3",
                class_name="responsive-grid",
            ),
            subtitle="Preguntas para orientar revision con la evidencia original.",
        ),
        page_section(
            "Claims verificables",
            rx.grid(
                rx.foreach(DocumentReadingState.knowledge_claims, knowledge_claim_card),
                columns="3",
                spacing="3",
                class_name="responsive-grid",
            ),
            subtitle="Cada afirmacion incluye evidencia asociada y nota de revision.",
        ),
        page_section(
            "Conexiones reutilizables",
            rx.grid(
                rx.foreach(DocumentReadingState.knowledge_connections, knowledge_connection_card),
                columns="2",
                spacing="3",
                class_name="responsive-grid",
            ),
            subtitle="El mismo digest conecta expediente, cronologia, informe ciudadano y fuente publica.",
        ),
        page_section(
            "Evidencia asociada",
            rx.grid(
                rx.foreach(DocumentReadingState.knowledge_evidence, tracking_evidence_card),
                columns="2",
                spacing="3",
                class_name="responsive-grid",
            ),
            rx.text(DocumentReadingState.knowledge_notice, class_name="muted small"),
            subtitle="Revisar siempre el registro original antes de publicar o citar conclusiones.",
        ),
        on_mount=DocumentReadingState.load_knowledge,
        active_page=PAGE_KNOWLEDGE,
    )

@rx.page(
    route="/official-document",
    title="Documento fuente - DatosEnOrden",
    description="Visor del documento oficial con PDF publicado, fragmentos citados y contexto de evidencia.",
    image=PUBLIC_OG_IMAGE_URL,
    meta=_page_meta(
        "/official-document",
        "documento fuente, PDF oficial, fragmentos citados, evidencia, lectura documentada",
        "Documento fuente - DatosEnOrden",
        "Visor del documento oficial con PDF publicado, fragmentos citados y contexto de evidencia.",
    ),
)
def official_document() -> rx.Component:
    return shell(
        rx.box(
            rx.box(
                rx.text("Lectura documentada", class_name="document-kicker"),
                rx.text(DocumentReadingState.knowledge_title, class_name="document-title"),
                rx.text(
                    "Responde: de donde salio esta informacion. El documento queda visible junto a sus referencias.",
                    class_name="document-subtitle",
                ),
                class_name="document-hero-copy",
            ),
            rx.hstack(
                rx.text(DocumentReadingState.knowledge_document["source"], class_name="document-meta-pill"),
                rx.text(DocumentReadingState.knowledge_document["published_at"], class_name="document-meta-pill"),
                rx.text(DocumentReadingState.knowledge_document["official_status"], class_name="document-meta-pill"),
                rx.text(DocumentReadingState.knowledge_document["official_url"], class_name="document-meta-reference"),
                spacing="2",
                wrap="wrap",
                class_name="document-meta-row",
            ),
            class_name="document-hero",
        ),
        rx.box(
            rx.box(
                rx.cond(
                    DocumentReadingState.knowledge_document_has_pdf,
                    official_document_pdf_viewer(
                        DocumentReadingState.knowledge_selected_page,
                        DocumentReadingState.knowledge_selected_fragment_id,
                        DocumentReadingState.knowledge_selected_excerpt,
                    ),
                    official_document_viewer(
                        DocumentReadingState.knowledge_document["id"],
                        DocumentReadingState.knowledge_selected_page,
                        DocumentReadingState.knowledge_selected_fragment_id,
                        DocumentReadingState.knowledge_selected_excerpt,
                    ),
                ),
                class_name="document-main-column",
            ),
            rx.box(
                document_fragment_panel(),
                reading_guide_panel(),
                class_name="document-side-column",
            ),
            class_name="official-document-layout",
        ),
        rx.box(
            rx.text("Evidencia dentro del documento", class_name="section-title"),
            rx.text("Cada referencia conserva pagina, fragmento y extracto verificable del documento fuente.", class_name="section-subtitle"),
            rx.cond(
                DocumentReadingState.knowledge_evidence,
                rx.box(
                    rx.foreach(DocumentReadingState.knowledge_evidence, guide_evidence),
                    class_name="reference-strip",
                ),
                investigation_entry_card(
                    "Aún no hay referencias visibles",
                    "Cuando la publicación tenga evidencia enlazada al documento, aparecerá aqué con su extracto verificable.",
                    "Volver a Lectura",
                    "/topic",
                    "button button-secondary",
                ),
            ),
            class_name="document-reference-section",
        ),
        on_mount=DocumentReadingState.load_knowledge,
        active_page=PAGE_DOCUMENT,
    )

@rx.page(
    route="/library",
    title="Más lecturas - DatosEnOrden",
    description="Lecturas relacionadas para ampliar el contexto del documento principal y conectar con expediente, informe y cronología.",
    image=PUBLIC_OG_IMAGE_URL,
    meta=_page_meta(
        "/library",
        "más lecturas, contexto documental, expediente, cronología, informe ciudadano",
        "Más lecturas - DatosEnOrden",
        "Lecturas relacionadas para ampliar el contexto del documento principal y conectar con expediente, informe y cronología.",
    ),
)
def library() -> rx.Component:
    return shell(
        rx.box(
            rx.text("Más lecturas", class_name="title"),
            rx.text(
                "Documentos explicados en lenguaje ciudadano, con preguntas, puntos clave y evidencia para revisar.",
                class_name="subtitle",
            ),
            rx.text("Muestra pública con documentos locales de prueba. No representa documentos oficiales reales.", class_name="badge badge-purple launch-notice"),
            rx.hstack(
                rx.button("Abrir expediente", on_click=DocumentReadingState.open_knowledge_investigation, class_name="button"),
                rx.button("Leer reporte", on_click=rx.redirect("/reports"), class_name="button button-secondary"),
                rx.button("Ver seguimiento", on_click=rx.redirect("/tracking"), class_name="button button-secondary"),
                spacing="3",
                wrap="wrap",
                class_name="hero-actions",
            ),
            class_name="hero",
        ),
        page_section(
            "Cómo usar Más lecturas",
            rx.grid(
                help_card("Documento", "Es la pieza de información que se quiere entender. En esta fase usamos documentos de ejemplo."),
                help_card("Resumen ciudadano", "Una explicacion breve para saber de que trata antes de revisar detalles."),
                help_card("Evidencia", "La pista que permite volver a la fuente o seccion original y comprobar una afirmacion."),
                columns="3",
                spacing="3",
                class_name="responsive-grid",
            ),
            subtitle="Más lecturas responde: qué otros documentos ayudan a entender este tema.",
        ),
        page_section(
            "Listado",
            rx.cond(
                DocumentReadingState.knowledge_documents,
                rx.grid(
                    rx.foreach(DocumentReadingState.knowledge_documents, knowledge_document_card),
                    columns="2",
                    spacing="3",
                    class_name="responsive-grid",
                ),
                rx.text("Todavía no hay documentos disponibles.", class_name="muted small"),
            ),
            subtitle="Primera version visible, alimentada por Knowledge Engine.",
        ),
        page_section(
            "Documento de ejemplo",
            rx.text(DocumentReadingState.knowledge_title, class_name="card-title"),
            rx.text(DocumentReadingState.knowledge_summary, class_name="story-summary"),
            rx.hstack(
                rx.text("Muestra local no oficial", class_name="mini-pill evidence-trust"),
                rx.button("Abrir expediente", on_click=DocumentReadingState.open_knowledge_investigation, class_name="button"),
                rx.button("Leer reporte", on_click=rx.redirect("/reports"), class_name="button button-secondary"),
                rx.button("Seguir proyecto", on_click=rx.redirect("/tracking"), class_name="button button-secondary"),
                spacing="2",
                wrap="wrap",
            ),
            subtitle="Resumen ciudadano generado desde datos locales de prueba.",
        ),
        page_section(
            "Preguntas importantes",
            rx.grid(
                rx.foreach(DocumentReadingState.knowledge_questions, knowledge_question_card),
                columns="3",
                spacing="3",
                class_name="responsive-grid",
            ),
            subtitle="Preguntas para revisar el documento sin depender solo del resumen.",
        ),
        page_section(
            "Puntos clave",
            rx.grid(
                rx.foreach(DocumentReadingState.knowledge_key_points, knowledge_key_point_card),
                columns="2",
                spacing="3",
                class_name="responsive-grid",
            ),
            subtitle="Ideas principales vinculadas a evidencia.",
        ),
        page_section(
            "Anclas y evidencia",
            rx.cond(
                DocumentReadingState.knowledge_evidence,
                rx.grid(
                    rx.foreach(DocumentReadingState.knowledge_evidence, tracking_evidence_card),
                    columns="2",
                    spacing="3",
                    class_name="responsive-grid",
                ),
                rx.text("Todavía no hay anclas de evidencia disponibles.", class_name="muted small"),
            ),
            rx.text(DocumentReadingState.knowledge_notice, class_name="muted small"),
            subtitle="Cada resumen debe poder revisarse contra una referencia original o local.",
        ),
        page_section(
            "Siguientes pasos",
            rx.grid(
                next_step_card("Leer el reporte", "Ver la lectura completa en formato articulo.", "Ir a Informes", "/reports"),
                next_step_card("Seguir la historia", "Revisar eventos, fechas y cambios asociados.", "Ir a Cronología", "/tracking"),
                next_step_card("Ver fuentes oficiales", "Entender de dónde vienen los datos de esta muestra.", "Ir a Fuentes", "/ecosystem"),
                columns="3",
                spacing="3",
                class_name="responsive-grid",
            ),
            subtitle="Más lecturas no es un final: conecta con documento fuente, cronología y expediente.",
        ),
        on_mount=DocumentReadingState.load_knowledge,
        active_page=PAGE_LIBRARY,
    )



topic_view = topic
knowledge_view = knowledge
official_document_view = official_document
library_view = library
