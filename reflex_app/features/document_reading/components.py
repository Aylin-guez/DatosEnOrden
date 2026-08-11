from __future__ import annotations

import reflex as rx

from reflex_app.components.common.cards import tracking_event_card
from reflex_app.components.common.metrics import document_metric

from reflex_app.features.document_reading.state import DocumentReadingState
from reflex_app.features.public_record.state import PublicRecordState


def support_cta_block() -> rx.Component:
    return rx.box(
        rx.text("¿Te resultó útil esta investigación?", class_name="card-title"),
        rx.text(
            "DatosEnOrden se sostiene con trabajo de producto, infraestructura y apoyo de la comunidad, sin vender conclusiones.",
            class_name="support-copy",
        ),
        rx.hstack(
            rx.button("Apoyar el proyecto", on_click=rx.redirect("/support"), class_name="button button-secondary support-mini-button"),
            rx.cond(
                DocumentReadingState.knowledge_share_url != "",
                rx.link("Compartir lectura", href=DocumentReadingState.knowledge_share_url, class_name="document-inline-link"),
                rx.text("Abre Lectura para compartir", class_name="mini-pill"),
            ),
            spacing="2",
            wrap="wrap",
        ),
        class_name="support-inline-block",
    )

def topic_state_graph_node_card(row: dict) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.text(row["node_type"], class_name="badge badge-teal"),
            rx.text(row["sources_text"], class_name="mini-pill evidence-trust"),
            justify="between",
            align="center",
        ),
        rx.text(row["title"], class_name="context-title"),
        rx.text(f"Evidencia: {row['evidence_text']}", class_name="muted small"),
        class_name="context-item state-graph-topic-node",
    )

def topic_nav() -> rx.Component:
    return rx.hstack(
        rx.link("Documento", href="#topic-document", class_name="document-inline-link"),
        rx.text("|", class_name="muted small"),
        rx.link("Lectura", href="#topic-reading", class_name="document-inline-link"),
        rx.text("|", class_name="muted small"),
        rx.link("Evidencia", href="#topic-evidence", class_name="document-inline-link"),
        spacing="2",
        wrap="wrap",
        class_name="topic-nav",
    )

def topic_rail_link(label: str, href: str) -> rx.Component:
    return rx.link(label, href=href, class_name="topic-rail-link")

def topic_context_rail() -> rx.Component:
    return rx.box(
        rx.text("Ruta", class_name="topic-rail-label"),
        topic_rail_link("Documento", "#topic-document"),
        topic_rail_link("Resumen", "#topic-summary"),
        topic_rail_link("Que propone", "#topic-proposes"),
        topic_rail_link("Que cambia", "#topic-changes"),
        topic_rail_link("Que NO cambia", "#topic-no-change"),
        topic_rail_link("Cronologia", "#topic-timeline"),
        topic_rail_link("Evidencia", "#topic-evidence"),
        topic_rail_link("Expediente", "#topic-investigation"),
        class_name="topic-context-rail",
    )

def topic_answer_card(row: dict) -> rx.Component:
    return rx.box(
        rx.text(row["title"], class_name="card-title"),
        rx.text(row["body"], class_name="muted small"),
        class_name="topic-answer-card topic-card-document",
    )

def topic_status_card(row: dict) -> rx.Component:
    return rx.box(
        rx.text(row["status"], class_name=rx.cond(row["ready"], "badge badge-teal", "badge badge-amber")),
        rx.text(row["label"], class_name="context-title"),
        class_name="card topic-status-card",
    )

def topic_official_document_card(row: dict) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.text(row["source"], class_name="badge badge-teal"),
            rx.text(row["document_type"], class_name="mini-pill mini-pill-purple"),
            spacing="2",
            wrap="wrap",
        ),
        rx.text(row["title"], class_name="card-title"),
        rx.text(row["summary"], class_name="story-summary"),
        rx.text(row["official_url"], class_name="mono id-line"),
        rx.hstack(
            rx.button("Abrir lectura", on_click=rx.redirect("/official-document"), class_name="button"),
            rx.link("Documento original", href=row["official_url"], class_name="button button-secondary"),
            spacing="2",
            wrap="wrap",
        ),
        class_name="card tracking-document-card",
    )

def topic_fragment_nav_item(row: dict) -> rx.Component:
    return rx.button(
        rx.vstack(
            rx.hstack(
                rx.text(row["label"], class_name="fragment-number"),
                rx.text(f"Página {row['page']}", class_name="mini-pill"),
                justify="between",
                align="center",
                spacing="2",
                wrap="wrap",
            ),
            rx.text(str(row.get("reference_label", "")), class_name="fragment-title"),
            rx.hstack(
                rx.text(str(row.get("type", "fragmento")), class_name="mini-pill mini-pill-purple"),
                rx.text(str(row.get("source", "Documento oficial")), class_name="mini-pill evidence-trust"),
                spacing="2",
                wrap="wrap",
            ),
            spacing="1",
            align="stretch",
        ),
        on_click=DocumentReadingState.select_document_anchor(row["page"], row["fragment_id"]),
        class_name=rx.cond(
            row["fragment_id"] == DocumentReadingState.knowledge_selected_fragment_id,
            "topic-fragment-nav-item topic-fragment-nav-item-active",
            "topic-fragment-nav-item",
        ),
    )

def document_fragment_panel() -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.text("Fragmentos", class_name="document-label"),
            rx.text(DocumentReadingState.knowledge_reference_text, class_name="mini-pill"),
            justify="between",
            align="center",
        ),
        rx.text("Selecciona un fragmento para abrir su página en el documento.", class_name="muted small"),
        rx.cond(
            DocumentReadingState.knowledge_fragment_contexts,
            rx.grid(
                rx.foreach(DocumentReadingState.knowledge_fragment_contexts, topic_fragment_nav_item),
                columns="1",
                spacing="2",
                class_name="fragment-nav-grid",
            ),
            rx.cond(
                DocumentReadingState.knowledge_pages,
                rx.hstack(
                    rx.foreach(DocumentReadingState.knowledge_pages, document_page_button),
                    spacing="2",
                    wrap="wrap",
                    class_name="document-page-nav",
                ),
                rx.text("No hay fragmentos visibles para navegar.", class_name="muted small"),
            ),
        ),
        class_name="document-fragment-panel",
    )

def document_paragraph(row: dict) -> rx.Component:
    return rx.box(
        rx.cond(
            row["marker"] != "",
            rx.text(row["marker"], class_name="document-paragraph-marker"),
        ),
        rx.text(
            row["text"],
            class_name=rx.cond(row["is_heading"], "document-paragraph document-paragraph-heading", "document-paragraph"),
        ),
        id=row["id"],
        class_name=rx.cond(
            row["fragment_id"] == DocumentReadingState.knowledge_selected_fragment_id,
            "document-paragraph-block document-paragraph-block-active",
            "document-paragraph-block",
        ),
    )

def topic_pdf_document_viewer(active_fragment_id: str) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.text("Documento principal", class_name="document-label"),
            rx.link("Abrir PDF en pestaña nueva", href=DocumentReadingState.knowledge_document_pdf_page_href, class_name="document-inline-link"),
            justify="between",
            align="center",
            wrap="wrap",
        ),
        rx.el.iframe(
            src=DocumentReadingState.knowledge_document_pdf_page_href,
            title="Documento oficial PDF",
            loading="lazy",
            class_name="topic-pdf-frame",
        ),
        rx.box(
            rx.text("Marca del fragmento seleccionado", class_name="document-label"),
            rx.text(DocumentReadingState.knowledge_selected_reference_label, class_name="document-page-label"),
            rx.text(DocumentReadingState.knowledge_selected_excerpt, class_name="document-highlight"),
            rx.cond(
                DocumentReadingState.knowledge_selected_page_is_approximate,
                rx.text(DocumentReadingState.knowledge_pdf_location_notice, class_name="document-location-notice"),
            ),
            rx.text(active_fragment_id, class_name="mono id-line"),
            reading_share_actions(),
            class_name="topic-pdf-citation-panel",
        ),
        class_name="topic-pdf-document-viewer",
    )

def topic_text_document_viewer() -> rx.Component:
    return rx.box(
        rx.box(
            rx.text("Documento oficial", class_name="document-label"),
            rx.text(DocumentReadingState.topic_official_document["title"], class_name="document-sheet-title"),
            class_name="document-sheet-cover",
        ),
        rx.foreach(DocumentReadingState.knowledge_document_paragraphs, document_paragraph),
        class_name="document-page topic-document-page document-sheet",
    )

def topic_source_panel() -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.text("Documento Fuente", class_name="badge badge-teal"),
            rx.text(DocumentReadingState.topic_official_document["source"], class_name="source-fact"),
            spacing="2",
            wrap="wrap",
            class_name="topic-source-header",
        ),
        rx.text(DocumentReadingState.topic_official_document["title"], class_name="card-title"),
        rx.text(
            rx.cond(
                DocumentReadingState.knowledge_document_has_pdf,
                "PDF oficial publicado.",
                rx.cond(
                    DocumentReadingState.knowledge_document_source_is_fallback,
                    "Documento reconstruido desde una lectura publicada de respaldo.",
                    "Documento publicado como texto.",
                ),
            ),
            class_name="topic-source-guidance",
        ),
        rx.cond(
            DocumentReadingState.knowledge_document_has_pdf,
            rx.box(
                topic_pdf_document_viewer(DocumentReadingState.knowledge_selected_fragment_id),
                rx.box(
                    document_fragment_panel(),
                    reading_guide_panel(),
                    class_name="reading-document-side",
                ),
                class_name="reading-document-workspace",
            ),
            topic_text_document_viewer(),
        ),
        rx.box(
            rx.text("Recurso oficial", class_name="document-label"),
            rx.text("Archivo oficial del Senado en formato original (.doc).", class_name="source-fact"),
            rx.link(
                "Abrir recurso oficial del Senado",
                href=DocumentReadingState.topic_original_url,
                class_name="document-inline-link topic-original-link",
            ),
            class_name="topic-official-resource",
        ),
        class_name="topic-source-panel topic-card-document",
        id="topic-document",
    )

def topic_evidence_card(row: dict) -> rx.Component:
    return rx.box(
        rx.text(row["source"], class_name="mini-pill"),
        rx.text(row["label"], class_name="context-title"),
        rx.text(row["excerpt"], class_name="muted small"),
        rx.button(
            "Ver en documento",
            on_click=[
                DocumentReadingState.select_document_anchor(row["page"], row["fragment_id"]),
                rx.call_script("setTimeout(() => (document.querySelector('.topic-pdf-document-viewer') || document.querySelector('.topic-source-panel .document-paragraph-block-active'))?.scrollIntoView({behavior: 'smooth', block: 'center'}), 80)"),
            ],
            class_name="button button-secondary",
        ),
        class_name=rx.cond(
            row["fragment_id"] == DocumentReadingState.knowledge_selected_fragment_id,
            "context-item topic-card-evidence topic-card-evidence-active",
            "context-item topic-card-evidence",
        ),
    )

def topic_change_card(row: dict) -> rx.Component:
    return rx.box(
        rx.text(row["claim"], class_name="guide-title"),
        rx.text(row["review_note"], class_name="guide-copy"),
        reference_button(row),
        class_name="topic-answer-card topic-card-changes",
    )

def topic_no_change_card(row: dict) -> rx.Component:
    return rx.box(
        rx.text(row["claim"], class_name="guide-title"),
        rx.text(row["review_note"], class_name="guide-copy"),
        rx.cond(row.get("fragment_id", "") != "", reference_button(row)),
        class_name="topic-answer-card topic-card-no-change",
    )

def topic_reading_card(row: dict) -> rx.Component:
    return rx.box(
        rx.text(row["title"], class_name="card-title"),
        rx.text(row["summary"], class_name="muted small"),
        rx.text(row["coverage"], class_name="mini-pill"),
        rx.button("Abrir lectura documentada", on_click=rx.redirect(row["href"]), class_name="button button-secondary"),
        class_name="card report-section-card",
    )

def topic_summary_card(title: str, body: rx.Var | str, helper: rx.Var | str = "") -> rx.Component:
    return rx.box(
        rx.text(title, class_name="card-title"),
        rx.text(body, class_name="muted"),
        rx.cond(helper != "", rx.text(helper, class_name="source-fact")),
        class_name="card report-card",
    )

def topic_reading_flow() -> rx.Component:
    return rx.vstack(
        rx.box(
            rx.text("Resumen", class_name="section-title"),
            rx.foreach(DocumentReadingState.topic_hero_answer_rows, topic_answer_card),
            rx.grid(
                rx.foreach(DocumentReadingState.topic_status_rows, topic_status_card),
                columns="2",
                spacing="3",
                class_name="responsive-grid",
            ),
            class_name="topic-reading-section topic-card-document",
            id="topic-summary",
        ),
        rx.box(
            rx.text("Que propone", class_name="section-title"),
            rx.grid(
                rx.foreach(DocumentReadingState.topic_proposes_rows, knowledge_key_point_card),
                columns="1",
                spacing="3",
                class_name="topic-compact-grid",
            ),
            class_name="topic-reading-section topic-card-proposes",
            id="topic-proposes",
        ),
        rx.box(
            rx.text("Que cambia", class_name="section-title"),
            rx.grid(
                rx.foreach(DocumentReadingState.topic_changes_rows, topic_change_card),
                columns="1",
                spacing="3",
                class_name="topic-compact-grid",
            ),
            class_name="topic-reading-section topic-card-changes",
            id="topic-changes",
        ),
        rx.box(
            rx.text("Que NO cambia", class_name="section-title"),
            rx.grid(
                rx.foreach(DocumentReadingState.topic_no_changes_rows, topic_no_change_card),
                columns="1",
                spacing="3",
                class_name="topic-compact-grid",
            ),
            class_name="topic-reading-section topic-card-no-change",
            id="topic-no-change",
        ),
        rx.box(
            rx.text("Cronologia", class_name="section-title"),
            rx.cond(
                DocumentReadingState.topic_timeline_rows,
                rx.grid(
                    rx.foreach(DocumentReadingState.topic_timeline_rows, tracking_event_card),
                    columns="1",
                    spacing="3",
                    class_name="timeline-list",
                ),
                rx.text("No hay hitos de timeline visibles para este tema.", class_name="muted small"),
            ),
            class_name="topic-reading-section topic-card-next",
            id="topic-timeline",
        ),
        rx.box(
            rx.text("Evidencia", class_name="section-title"),
            rx.grid(
                rx.foreach(DocumentReadingState.topic_evidence_rows, topic_evidence_card),
                columns="2",
                spacing="3",
                class_name="responsive-grid topic-evidence-grid",
            ),
            class_name="topic-reading-section topic-card-evidence",
            id="topic-evidence",
        ),
        rx.box(
            rx.text("Expediente", class_name="section-title"),
            topic_summary_card(DocumentReadingState.topic_expediente_title, DocumentReadingState.topic_expediente_summary, DocumentReadingState.topic_expediente_metrics),
            class_name="topic-reading-section",
            id="topic-investigation",
        ),
        spacing="4",
        align="stretch",
        class_name="topic-reading-flow",
    )

def topic_mode_button(label: str, mode: str) -> rx.Component:
    return rx.button(
        label,
        on_click=DocumentReadingState.set_topic_view_mode(mode),
        class_name=rx.cond(DocumentReadingState.topic_view_mode == mode, "topic-mode-button topic-mode-button-active", "topic-mode-button"),
    )

def topic_mode_selector() -> rx.Component:
    return rx.hstack(
        topic_mode_button("Lectura", "lectura"),
        topic_mode_button("Sistema Vivo", "sistema_vivo"),
        topic_mode_button("Evidencia", "evidencia"),
        spacing="2",
        wrap="wrap",
        class_name="topic-mode-selector",
    )

def topic_reading_mode() -> rx.Component:
    return rx.box(
        topic_source_panel(),
        topic_context_rail(),
        rx.box(topic_reading_flow(), class_name="topic-reading-column", id="topic-reading"),
        class_name="topic-document-first-layout topic-mode-shell topic-mode-reading",
    )

def topic_live_stage(label: str, state: str, body: str) -> rx.Component:
    return rx.box(
        rx.text(state, class_name="live-stage-state"),
        rx.text(label, class_name="live-stage-title"),
        rx.text(body, class_name="live-stage-body"),
        class_name="live-stage-card",
    )

def topic_system_mode() -> rx.Component:
    return rx.box(
        rx.box(
            rx.text("Sistema Vivo", class_name="section-title"),
            rx.text(
                "Vista macroscopica del mismo tema: continuidad, eventos observados y pendientes documentales. No reemplaza la lectura ni el documento.",
                class_name="muted",
            ),
            class_name="live-system-heading",
        ),
        rx.grid(
            topic_live_stage("Estado actual", DocumentReadingState.topic_status, "Situación del tema según la lectura documentada disponible."),
            topic_live_stage("Eventos del tema", DocumentReadingState.topic_document_count, "Documentos y eventos disponibles para sostener la cronologia."),
            topic_live_stage("Cronología viva", DocumentReadingState.topic_updated_at, "Ultima fecha registrada en el recorrido documental."),
            columns="3",
            spacing="3",
            class_name="responsive-grid live-stage-grid",
        ),
        rx.box(
            rx.text("Mapa de conexiones", class_name="card-title"),
            rx.text("Nodos principales alrededor del tema actual, conectados solo por evidencia disponible.", class_name="muted small"),
            rx.cond(
                DocumentReadingState.topic_state_graph_rows,
                rx.grid(
                    rx.foreach(DocumentReadingState.topic_state_graph_rows, topic_state_graph_node_card),
                    columns="3",
                    spacing="2",
                    class_name="responsive-grid",
                ),
                rx.text("No hay conexiones visibles para este tema todav\u00eda.", class_name="muted small"),
            ),
            class_name="topic-reading-section topic-card-next live-connections-panel",
        ),
        rx.box(
            rx.text("Eventos del tema", class_name="card-title"),
            rx.cond(
                DocumentReadingState.topic_timeline_rows,
                rx.hstack(
                    rx.foreach(DocumentReadingState.topic_timeline_rows, tracking_event_card),
                    spacing="3",
                    align="stretch",
                    class_name="live-timeline-strip",
                ),
                rx.text("No hay eventos visibles para este tema todavía.", class_name="muted small"),
            ),
            class_name="topic-reading-section topic-card-next live-timeline-panel",
        ),
        rx.grid(
            rx.box(
                rx.text("Qué cambió", class_name="card-title"),
                rx.grid(
                    rx.foreach(DocumentReadingState.topic_changes_rows, topic_change_card),
                    columns="1",
                    spacing="3",
                    class_name="topic-compact-grid",
                ),
                class_name="topic-reading-section topic-card-changes",
            ),
            rx.box(
                rx.text("Qué falta", class_name="card-title"),
                rx.grid(
                    rx.foreach(DocumentReadingState.topic_no_changes_rows, topic_no_change_card),
                    columns="1",
                    spacing="3",
                    class_name="topic-compact-grid",
                ),
                class_name="topic-reading-section topic-card-no-change",
            ),
            columns="2",
            spacing="3",
            class_name="responsive-grid",
        ),
        class_name="topic-system-placeholder topic-mode-shell",
    )

def topic_evidence_mode() -> rx.Component:
    return rx.box(
        topic_source_panel(),
        rx.box(
            rx.text("Evidencia", class_name="section-title"),
            rx.text("Cada accion mueve el documento al fragmento citado sin salir de la lectura.", class_name="muted small"),
            rx.grid(
                rx.foreach(DocumentReadingState.topic_evidence_rows, topic_evidence_card),
                columns="1",
                spacing="3",
                class_name="topic-evidence-grid",
            ),
            class_name="topic-reading-section topic-card-evidence topic-evidence-mode-panel",
        ),
        class_name="topic-document-first-layout topic-mode-shell topic-mode-evidence",
    )

def topic_mode_body() -> rx.Component:
    return rx.cond(
        DocumentReadingState.topic_view_mode == "sistema_vivo",
        topic_system_mode(),
        rx.cond(
            DocumentReadingState.topic_view_mode == "evidencia",
            topic_evidence_mode(),
            topic_reading_mode(),
        ),
    )

def reference_button(row: dict) -> rx.Component:
    return rx.button(
        row["reference_label"],
        on_click=[
            DocumentReadingState.select_document_anchor(row["page"], row["fragment_id"]),
            rx.call_script("setTimeout(() => (document.querySelector('.topic-pdf-document-viewer') || document.querySelector('.topic-source-panel .document-paragraph-block-active'))?.scrollIntoView({behavior: 'smooth', block: 'center'}), 80)"),
        ],
        class_name="reference-button",
    )

def reading_context_bar() -> rx.Component:
    return rx.box(
        rx.text("Cobertura documental", class_name="document-reading-status"),
        rx.box(
            rx.text(DocumentReadingState.knowledge_coverage_text, class_name="document-metric-value"),
            rx.text(DocumentReadingState.knowledge_reference_text, class_name="document-metric-label"),
            class_name="document-metric",
        ),
        document_metric("preguntas respondidas", DocumentReadingState.knowledge_question_count),
        document_metric("afirmaciones verificables", DocumentReadingState.knowledge_claim_count),
        document_metric("referencias documentales", DocumentReadingState.knowledge_reference_count),
        class_name="reading-context-bar",
    )

def reading_share_actions() -> rx.Component:
    return rx.hstack(
        rx.text("Compartir lectura", class_name="document-label"),
        rx.button("Copiar enlace", on_click=rx.call_script(DocumentReadingState.knowledge_share_copy_script), class_name="button button-secondary"),
        rx.link("WhatsApp", href=DocumentReadingState.knowledge_share_whatsapp_url, class_name="badge badge-teal share-pill"),
        rx.link("LinkedIn", href=DocumentReadingState.knowledge_share_linkedin_url, class_name="badge badge-blue share-pill"),
        rx.link("X", href=DocumentReadingState.knowledge_share_x_url, class_name="badge badge-purple share-pill"),
        spacing="2",
        wrap="wrap",
        class_name="reading-share-actions",
    )

def document_fragment_card(row: dict) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.text(f"Pagina {row['page']}", class_name="document-page-marker"),
            rx.text(row["section_title"], class_name="document-section-title"),
            justify="between",
            align="start",
            wrap="wrap",
        ),
        rx.text(row["text"], class_name="document-fragment-text"),
        on_click=DocumentReadingState.select_document_anchor(row["page"], row["id"]),
        id=row["id"],
        class_name=rx.cond(
            row["id"] == DocumentReadingState.knowledge_selected_fragment_id,
            "document-fragment document-fragment-active",
            "document-fragment",
        ),
    )

def document_page_button(row: dict) -> rx.Component:
    return rx.button(
        row["label"],
        on_click=DocumentReadingState.select_document_anchor(row["page"], ""),
        title=f"Ir a {row['label']}",
        class_name=rx.cond(
            row["page"] == DocumentReadingState.knowledge_selected_page,
            "page-chip page-chip-active",
            "page-chip",
        ),
    )

def official_document_pdf_viewer(page: int, fragment_id: str, highlight: str) -> rx.Component:
    return rx.box(
        reading_context_bar(),
        rx.box(
            rx.hstack(
                rx.text("Documento principal", class_name="document-label"),
                rx.link("Abrir PDF en pestaña nueva", href=DocumentReadingState.knowledge_document_pdf_page_href, class_name="document-inline-link"),
                justify="between",
                align="center",
                wrap="wrap",
            ),
            rx.el.iframe(
                src=DocumentReadingState.knowledge_document_pdf_page_href,
                title="Documento oficial PDF",
                loading="lazy",
                class_name="official-document-pdf-frame",
            ),
            rx.box(
                rx.text("Marca del fragmento seleccionado", class_name="document-label"),
                rx.text(f"Página {page}", class_name="document-page-label"),
                rx.text(highlight, class_name="document-highlight"),
                rx.cond(
                    DocumentReadingState.knowledge_selected_page_is_approximate,
                    rx.text(DocumentReadingState.knowledge_pdf_location_notice, class_name="document-location-notice"),
                ),
                rx.text(fragment_id, class_name="mono id-line"),
                reading_share_actions(),
                class_name="document-current-anchor",
            ),
            class_name="document-paper official-document-pdf-paper",
        ),
        class_name="official-document-viewer official-document-pdf-viewer",
    )

def official_document_viewer(document_id: str, page: int, fragment_id: str, highlight: str) -> rx.Component:
    return rx.box(
        reading_context_bar(),
        rx.box(
            rx.hstack(
                rx.text("Documento", class_name="document-label"),
                rx.text(document_id, class_name="mono id-line"),
                justify="between",
                align="center",
                wrap="wrap",
            ),
            rx.box(
                rx.text("Fragmento citado", class_name="document-label"),
                rx.text(f"Página {page}", class_name="document-page-label"),
                rx.text(highlight, class_name="document-highlight"),
                rx.cond(
                    DocumentReadingState.knowledge_selected_page_is_approximate,
                    rx.text(DocumentReadingState.knowledge_pdf_location_notice, class_name="document-location-notice"),
                ),
                rx.text(fragment_id, class_name="mono id-line"),
                reading_share_actions(),
                class_name="document-current-anchor",
            ),
            rx.box(
                rx.foreach(DocumentReadingState.knowledge_document_paragraphs, document_paragraph),
                class_name="document-page",
            ),
            class_name="document-paper",
        ),
        class_name="official-document-viewer",
    )

def guide_point(row: dict) -> rx.Component:
    return rx.box(
        rx.text(row["title"], class_name="guide-title"),
        rx.text(row["detail"], class_name="guide-copy"),
        reference_button(row),
        on_click=DocumentReadingState.select_document_anchor(row["page"], row["fragment_id"]),
        class_name="guide-entry",
    )

def guide_question(row: dict) -> rx.Component:
    return rx.box(
        rx.text(row["display_question"], class_name="guide-title"),
        rx.text(row["why_it_matters"], class_name="guide-copy"),
        reference_button(row),
        on_click=DocumentReadingState.select_document_anchor(row["page"], row["fragment_id"]),
        class_name="guide-entry",
    )

def guide_claim(row: dict) -> rx.Component:
    return rx.box(
        rx.text(row["claim"], class_name="guide-title"),
        rx.text(row["review_note"], class_name="guide-copy"),
        reference_button(row),
        on_click=DocumentReadingState.select_document_anchor(row["page"], row["fragment_id"]),
        class_name="guide-entry",
    )

def guide_evidence(row: dict) -> rx.Component:
    return rx.box(
        rx.text(row["label"], class_name="guide-title"),
        rx.text(row["quoted_text"], class_name="guide-copy"),
        rx.text(row["url"], class_name="mono id-line"),
        class_name="guide-evidence",
    )

def reading_connection(row: dict) -> rx.Component:
    return rx.link(row["label"], href=row["href"], class_name="document-inline-link")

def reading_guide_panel() -> rx.Component:
    return rx.box(
        rx.text(DocumentReadingState.knowledge_selected_reference_label, class_name="document-page-marker"),
        rx.text("Lectura documentada", class_name="reading-guide-title"),
        rx.text(DocumentReadingState.knowledge_selected_excerpt, class_name="reading-guide-summary"),
        rx.box(
            rx.text("Punto documentado", class_name="reading-guide-heading"),
            rx.cond(
                DocumentReadingState.knowledge_selected_summary,
                rx.foreach(DocumentReadingState.knowledge_selected_summary, guide_point),
                rx.text("Este fragmento no tiene un punto destacado.", class_name="muted small"),
            ),
            class_name="reading-guide-section",
        ),
        rx.box(
            rx.text("Pregunta derivada del texto", class_name="reading-guide-heading"),
            rx.cond(
                DocumentReadingState.knowledge_selected_questions,
                rx.foreach(DocumentReadingState.knowledge_selected_questions, guide_question),
                rx.text("No hay pregunta derivada de este fragmento.", class_name="muted small"),
            ),
            class_name="reading-guide-section",
        ),
        rx.box(
            rx.text("Afirmacion trazable", class_name="reading-guide-heading"),
            rx.cond(
                DocumentReadingState.knowledge_selected_claims,
                rx.foreach(DocumentReadingState.knowledge_selected_claims, guide_claim),
                rx.text("No hay afirmacion trazable para este fragmento.", class_name="muted small"),
            ),
            class_name="reading-guide-section",
        ),
        rx.box(
            rx.text("Evidencia utilizada", class_name="reading-guide-heading"),
            rx.cond(
                DocumentReadingState.knowledge_selected_evidence,
                rx.foreach(DocumentReadingState.knowledge_selected_evidence, guide_evidence),
                rx.text("No hay evidencia seleccionada para este fragmento.", class_name="muted small"),
            ),
            class_name="reading-guide-section",
        ),
        rx.box(
            rx.text("Navegacion relacionada", class_name="reading-guide-heading"),
            rx.hstack(rx.foreach(DocumentReadingState.knowledge_selected_connections, reading_connection), spacing="2", wrap="wrap"),
            class_name="reading-guide-section",
        ),
        class_name="reading-guide-panel",
    )

def knowledge_document_card(row: dict) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.text(row["classification"], class_name="badge badge-teal"),
            rx.text(row["official_status"], class_name="mini-pill mini-pill-purple"),
            justify="between",
            align="center",
        ),
        rx.text(row["title"], class_name="card-title"),
        rx.text(f"{row['source']} | {row['document_type']} | {row['published_at']}", class_name="muted small"),
        rx.text(row["summary"], class_name="source-fact"),
        rx.text(row["official_url"], class_name="mono id-line"),
        rx.hstack(
            rx.button("Ver documento", on_click=rx.redirect("/official-document"), class_name="button"),
            rx.button("Abrir expediente", on_click=PublicRecordState.open_canonical_investigation(row["related_expediente_target"]), class_name="button button-secondary"),
            spacing="2",
            wrap="wrap",
        ),
        class_name="card tracking-document-card",
    )

def knowledge_key_point_card(row: dict) -> rx.Component:
    return rx.box(
        rx.text(row["title"], class_name="card-title"),
        rx.text(row["detail"], class_name="muted small"),
        rx.text(f"Evidencia: {row['evidence_id']}", class_name="mono id-line"),
        class_name="card report-section-card",
    )

def knowledge_question_card(row: dict) -> rx.Component:
    return rx.box(
        rx.text(row["question"], class_name="card-title"),
        rx.text(row["why_it_matters"], class_name="muted small"),
        rx.text(f"Evidencia: {row['evidence_id']}", class_name="mono id-line"),
        class_name="card report-section-card",
    )

def knowledge_claim_card(row: dict) -> rx.Component:
    return rx.box(
        rx.text(row["claim"], class_name="card-title"),
        rx.text(row["review_note"], class_name="muted small"),
        rx.text(f"Evidencia: {row['evidence_text']}", class_name="source-fact"),
        class_name="card report-section-card",
    )

def knowledge_connection_card(row: dict) -> rx.Component:
    return rx.box(
        rx.text(row["label"], class_name="mini-pill"),
        rx.text(row["value"], class_name="card-title"),
        class_name="context-item",
    )
