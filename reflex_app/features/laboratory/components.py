from __future__ import annotations

import reflex as rx

from reflex_app.features.laboratory.state import LaboratoryState, REQUIRED_SECTIONS
from reflex_app.models.public_money import (
    PublicMoneyActionRow,
    PublicMoneyInstrumentRow,
    PublicMoneyObservationRow,
    PublicMoneyProceedingRow,
    PublicMoneySnapshotRow,
)
from reflex_app.models.citizen_expedient import CitizenPublicSectionRow, CitizenStatementRow


def laboratory_header() -> rx.Component:
    return rx.box(
        rx.text("Laboratorio", class_name="title"),
        rx.text(
            "Hipotesis, investigacion y propuestas en desarrollo a partir de informacion publica.",
            class_name="subtitle",
        ),
        rx.text(
            "Esta superficie no publica una politica aprobada ni informacion oficial; muestra una investigacion en laboratorio.",
            class_name="muted small",
        ),
        class_name="hero laboratory-hero",
    )


def section_status(status: str) -> rx.Component:
    return rx.text(status, class_name="mini-pill laboratory-status")


def expedition_catalog_card(row: dict) -> rx.Component:
    return rx.box(
        rx.hstack(
            section_status(row["status"]),
            justify="between",
            align="center",
        ),
        rx.text(row["title"], class_name="card-title"),
        rx.text(row["summary"], class_name="muted small"),
        rx.text(f"Actualizado: {row['updated_at']}", class_name="source-fact"),
        rx.button(
            "Abrir expediente",
            on_click=rx.redirect(f"/laboratory/expedient?id={row['id']}"),
            class_name="button",
        ),
        rx.text("ID: ", row["id"], class_name="mono id-line"),
        class_name="card laboratory-catalog-card",
    )


def expedient_header() -> rx.Component:
    return rx.box(
        rx.button(
            "← Volver",
            on_click=rx.call_script("if (window.history.length > 1) { window.history.back(); } else { window.location.assign('/laboratory'); }"),
            class_name="button button-secondary",
        ),
        rx.hstack(
            rx.text(LaboratoryState.expedient_id, class_name="badge badge-teal"),
            rx.text(LaboratoryState.expedient_status, class_name="mini-pill"),
            justify="between",
            align="center",
        ),
        rx.text(LaboratoryState.expedient_title, class_name="title"),
        rx.text(LaboratoryState.expedient_summary, class_name="subtitle"),
        rx.text(
            "Alcance: ",
            LaboratoryState.expedient_scope,
            " | Territorio: ",
            LaboratoryState.expedient_territory,
            " | Periodo: ",
            LaboratoryState.expedient_period,
            " | Actualizado: ",
            LaboratoryState.expedient_updated_at,
            class_name="muted small",
        ),
        class_name="hero laboratory-expedient-header",
    )


def section_tabs() -> rx.Component:
    labels = (
        ("Resumen", "summary"),
        ("Problema", "problem"),
        ("Evidencia", "evidence"),
        ("Afirmaciones", "claims"),
        ("Hipotesis", "hypotheses"),
        ("Indicadores", "indicators"),
        ("Fuentes", "sources"),
        ("Relaciones", "relationships"),
        ("Participacion", "participation"),
    )
    return rx.tabs.root(
        rx.tabs.list(
            *(rx.tabs.trigger(label, value=value) for label, value in labels),
            class_name="tabs-list laboratory-tabs-list",
        ),
        rx.box(section_body(), class_name="tab-content laboratory-tab-body"),
        default_value="summary",
        on_change=LaboratoryState.set_active_section,
        class_name="tabs-root laboratory-tabs-root",
    )


def section_body() -> rx.Component:
    return rx.cond(
        LaboratoryState.active_section == "summary",
        summary_panel(),
        rx.cond(
            LaboratoryState.active_section == "problem",
            problem_panel(),
            rx.cond(
                LaboratoryState.active_section == "evidence",
                evidence_panel(),
                rx.cond(
                    LaboratoryState.active_section == "claims",
                    claims_panel(),
                    rx.cond(
                        LaboratoryState.active_section == "hypotheses",
                        hypotheses_panel(),
                        rx.cond(
                            LaboratoryState.active_section == "indicators",
                            indicators_panel(),
                            rx.cond(
                                LaboratoryState.active_section == "sources",
                                sources_panel(),
                                rx.cond(
                                    LaboratoryState.active_section == "relationships",
                                    relationships_panel(),
                                    participation_gate(),
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )


def summary_panel() -> rx.Component:
    return rx.vstack(
        rx.text("Lectura inicial", class_name="section-title"),
        rx.cond(
            LaboratoryState.expedient_provenance_class == "REAL",
            rx.text(
                "Este expediente organiza referencias públicas verificadas y no atribuye irregularidad, causalidad ni responsabilidad.",
                class_name="muted",
            ),
            rx.text("Este expediente organiza una hipotesis publica inicial. Sus datos aun estan en investigacion.", class_name="muted"),
        ),
        rx.text("Preguntas abiertas: ", LaboratoryState.open_questions_summary, class_name="story-summary"),
        reading_progress(),
        class_name="laboratory-panel",
    )


def problem_panel() -> rx.Component:
    return rx.vstack(
        rx.text(LaboratoryState.problem_title, class_name="section-title"),
        rx.text(LaboratoryState.problem_description, class_name="story-summary"),
        rx.text("Alcance: ", LaboratoryState.problem_scope, class_name="source-fact"),
        rx.text("Poblacion afectada: ", LaboratoryState.problem_affected_population, class_name="source-fact"),
        rx.text("Territorio: ", LaboratoryState.problem_territory, " | Periodo: ", LaboratoryState.problem_period, class_name="source-fact"),
        section_status(LaboratoryState.problem_status),
        class_name="laboratory-panel",
    )


def evidence_panel() -> rx.Component:
    return rx.vstack(
        rx.cond(
            LaboratoryState.evidence_items,
            rx.grid(rx.foreach(LaboratoryState.evidence_items, evidence_card), columns="2", spacing="3", class_name="responsive-grid"),
            empty_section_notice("Evidencia", "Datos en preparacion. Falta conectar fuentes verificadas."),
        ),
        class_name="laboratory-panel",
    )


def claims_panel() -> rx.Component:
    return rx.vstack(
        rx.cond(
            LaboratoryState.claims,
            rx.grid(rx.foreach(LaboratoryState.claims, claim_card), columns="1", spacing="3", class_name="responsive-grid"),
            empty_section_notice("Afirmaciones", "Pendiente de investigacion y respaldo documental."),
        ),
        class_name="laboratory-panel",
    )


def hypotheses_panel() -> rx.Component:
    return rx.vstack(
        rx.cond(
            LaboratoryState.hypotheses,
            rx.grid(rx.foreach(LaboratoryState.hypotheses, hypothesis_card), columns="1", spacing="3", class_name="responsive-grid"),
            empty_section_notice("Hipotesis", "Pendiente de investigacion."),
        ),
        class_name="laboratory-panel",
    )


def indicators_panel() -> rx.Component:
    return rx.vstack(
        rx.text("No hay valores cargados. Los nombres son indicadores previstos, no estadisticas.", class_name="muted small"),
        rx.grid(rx.foreach(LaboratoryState.indicators, indicator_card), columns="2", spacing="3", class_name="responsive-grid"),
        class_name="laboratory-panel",
    )


def sources_panel() -> rx.Component:
    return rx.vstack(
        rx.cond(
            LaboratoryState.sources,
            rx.grid(rx.foreach(LaboratoryState.sources, source_card), columns="2", spacing="3", class_name="responsive-grid"),
            empty_section_notice("Fuentes", "Datos en preparacion. Falta seleccionar fuentes publicas verificables."),
        ),
        class_name="laboratory-panel",
    )


def relationships_panel() -> rx.Component:
    return rx.vstack(
        rx.cond(
            LaboratoryState.relationships,
            rx.grid(rx.foreach(LaboratoryState.relationships, relationship_card), columns="1", spacing="3", class_name="responsive-grid"),
            empty_section_notice("Relaciones", "Datos en preparacion."),
        ),
        rx.text("No se infieren relaciones automaticamente en esta fase.", class_name="muted small"),
        class_name="laboratory-panel",
    )


def evidence_card(row: dict) -> rx.Component:
    return rx.box(
        rx.text(row["id"], class_name="badge badge-purple"),
        rx.text(row["title"], class_name="card-title"),
        rx.text(row["type"], class_name="mini-pill"),
        rx.text("Fuente: ", row["source"], class_name="source-fact"),
        rx.text("Referencia: ", row["fragment_reference"], class_name="muted small"),
        rx.text(row["limitations"], class_name="muted small"),
        section_status(row["status"]),
        class_name="card laboratory-entity-card",
    )


def claim_card(row: dict) -> rx.Component:
    return rx.box(
        rx.text(row["id"], class_name="badge badge-blue"),
        rx.text(row["text"], class_name="card-title"),
        rx.text(row["type"], class_name="mini-pill"),
        rx.text("Certeza: ", row["certainty"], class_name="muted small"),
        section_status(row["status"]),
        class_name="card laboratory-entity-card",
    )


def hypothesis_card(row: dict) -> rx.Component:
    return rx.box(
        rx.hstack(rx.text(row["id"], class_name="badge badge-teal"), section_status(row["status"]), justify="between"),
        rx.text(row["title"], class_name="card-title"),
        rx.text(row["summary"], class_name="story-summary"),
        rx.text("Mecanismo: ", row["mechanism"], class_name="muted small"),
        rx.text("Beneficios esperados: ", row["expected_benefits"], class_name="muted small"),
        rx.text("Riesgos: ", row["risks"], class_name="muted small"),
        rx.text(row["public_origin_type"], class_name="source-fact"),
        class_name="card laboratory-hypothesis-card",
    )


def indicator_card(row: dict) -> rx.Component:
    return rx.box(
        rx.text(row["id"], class_name="badge badge-purple"),
        rx.text(row["name"], class_name="card-title"),
        rx.text(row["description"], class_name="muted small"),
        rx.text("Valor actual: pendiente de datos", class_name="source-fact"),
        rx.text("Advertencia: ", row["methodological_warning"], class_name="muted small"),
        section_status(row["status"]),
        class_name="card laboratory-entity-card",
    )


def source_card(row: dict) -> rx.Component:
    return rx.box(
        rx.text(row["id"], class_name="badge badge-blue"),
        rx.text(row["name"], class_name="card-title"),
        rx.text("Tipo: ", row["type"], class_name="muted small"),
        rx.text("Emisor: ", row["issuer"], class_name="muted small"),
        rx.text(row["warning"], class_name="muted small"),
        section_status(row["status"]),
        class_name="card laboratory-entity-card",
    )


def relationship_card(row: dict) -> rx.Component:
    return rx.box(
        rx.text(row["id"], class_name="badge badge-teal"),
        rx.text(row["source_entity"], " -> ", row["target_entity"], class_name="card-title"),
        rx.text(row["relation_type"], class_name="mini-pill"),
        rx.text(row["context"], class_name="muted small"),
        section_status(row["status"]),
        class_name="card laboratory-entity-card",
    )


def reading_progress() -> rx.Component:
    return rx.box(
        rx.text("Progreso de lectura: ", LaboratoryState.reading_progress, "%", class_name="context-title"),
        rx.text("Secciones obligatorias visitadas: ", LaboratoryState.visited_sections.length(), " de ", len(REQUIRED_SECTIONS), class_name="muted small"),
        class_name="laboratory-progress",
    )


def participation_gate() -> rx.Component:
    return rx.cond(
        LaboratoryState.reading_complete,
        rx.box(
            rx.text("Participacion proximamente", class_name="card-title"),
            rx.text("La lectura esta completa. Aportar, cuestionar, seguir y comentar todavia no esta habilitado.", class_name="muted small"),
            class_name="card laboratory-participation-gate laboratory-participation-ready",
        ),
        rx.box(
            rx.text("Participacion bloqueada", class_name="card-title"),
            rx.text("Para aportar, cuestionar o seguir este expediente, primero revisa todas sus secciones.", class_name="muted small"),
            class_name="card laboratory-participation-gate",
        ),
    )


def empty_section_notice(title: str, message: str) -> rx.Component:
    return rx.box(
        rx.text(title, class_name="card-title"),
        rx.text(message, class_name="muted small"),
        class_name="card laboratory-empty-notice",
    )


def _citizen_statement(row: CitizenStatementRow) -> rx.Component:
    return rx.box(
        _epistemic_badge(row),
        rx.text(row["statement"], class_name="story-summary"),
        rx.cond(row["support_text"] != "", rx.text(row["support_text"], class_name="source-fact")),
        class_name="card laboratory-entity-card",
    )


def _citizen_document(row: dict) -> rx.Component:
    return rx.box(
        rx.text("Evidencia documental", class_name="badge epistemic-evidence"),
        rx.text(row["title"], class_name="card-title"),
        rx.text(row["institution"], " · ", row["type"], " · ", row["stage"], class_name="source-fact"),
        rx.cond(row["date"] != "", rx.text(row["date"], class_name="muted small")),
        rx.cond(row["official_url"] != "", rx.link("Ver documento oficial", href=row["official_url"], is_external=True, target="_blank", rel="noopener noreferrer", class_name="button button-secondary")),
        class_name="card laboratory-entity-card",
    )


def _public_money_observation(row: PublicMoneyObservationRow) -> rx.Component:
    return rx.box(
        rx.text(row["metric_label"], class_name="source-fact"),
        rx.text(row["display_amount"], class_name="card-title"),
        rx.cond(row["as_of_date"] != "", rx.text("Corte: ", row["as_of_date"], class_name="muted small")),
        rx.text("Fuente: ", row["authority"], class_name="muted small"),
        rx.cond(row["note"] != "", rx.text(row["note"], class_name="muted small")),
        class_name="card public-money-observation",
    )


def _public_money_instrument(row: PublicMoneyInstrumentRow) -> rx.Component:
    return rx.box(
        rx.text(row["identifier"], class_name="badge badge-teal"),
        rx.text(row["title"], class_name="card-title"),
        rx.cond(row["purpose"] != "", rx.text(row["purpose"], class_name="muted small")),
        rx.foreach(row["observations"], _public_money_observation),
        class_name="card public-money-instrument",
    )


def _public_money_snapshot(row: PublicMoneySnapshotRow) -> rx.Component:
    return rx.box(
        rx.text(row["title"], class_name="badge badge-purple"),
        rx.text("Corte informado por ", row["authority"], " al ", row["cutoff_label"], ".", class_name="card-title"),
        rx.text(row["universe"], class_name="muted small"),
        rx.grid(rx.foreach(row["observations"], _public_money_observation), columns="2", spacing="3", class_name="responsive-grid"),
        rx.cond(row["note"] != "", rx.text(row["note"], class_name="muted small")),
        class_name="card public-money-snapshot",
    )


def _public_money_action(row: PublicMoneyActionRow) -> rx.Component:
    return rx.box(
        rx.text(row["title"], class_name="badge badge-amber"),
        rx.grid(rx.foreach(row["observations"], _public_money_observation), columns="2", spacing="3", class_name="responsive-grid"),
        rx.cond(row["note"] != "", rx.text(row["note"], class_name="muted small")),
        class_name="card public-money-action",
    )


def _public_money_proceeding(row: PublicMoneyProceedingRow) -> rx.Component:
    return rx.box(
        rx.text(row["kind"], class_name="badge badge-blue"),
        rx.text(row["title"], class_name="card-title"),
        rx.text(row["text"], class_name="muted small"),
        class_name="card public-money-proceeding",
    )


def public_money_summary() -> rx.Component:
    """Generic renderer for a projection; it has no expedient-specific branch."""
    return citizen_section(
        LaboratoryState.citizen_public_money_title,
        rx.vstack(
            rx.box(
                rx.text(LaboratoryState.citizen_public_money_universe["display_amount"], class_name="public-money-total"),
                rx.text(LaboratoryState.citizen_public_money_universe["metric_label"], class_name="card-title"),
                rx.text(LaboratoryState.citizen_public_money_universe["universe"], class_name="muted small"),
                class_name="card public-money-universe",
            ),
            rx.text(LaboratoryState.citizen_public_money_notice, class_name="muted small public-money-notice"),
            rx.cond(LaboratoryState.citizen_public_money_instruments, rx.box(rx.text("Convenios e instrumentos", class_name="context-title"), rx.grid(rx.foreach(LaboratoryState.citizen_public_money_instruments, _public_money_instrument), columns="3", spacing="3", class_name="responsive-grid"))),
            rx.foreach(LaboratoryState.citizen_public_money_snapshots, _public_money_snapshot),
            rx.cond(LaboratoryState.citizen_public_money_actions, rx.box(rx.text("Actuaciones posteriores", class_name="context-title"), rx.vstack(rx.foreach(LaboratoryState.citizen_public_money_actions, _public_money_action), spacing="3"))),
            rx.cond(LaboratoryState.citizen_public_money_oversight, rx.box(rx.text("Fiscalización", class_name="context-title"), rx.vstack(rx.foreach(LaboratoryState.citizen_public_money_oversight, _public_money_proceeding), spacing="3"))),
            rx.cond(LaboratoryState.citizen_public_money_proceedings, rx.box(rx.text("Proceso", class_name="context-title"), rx.vstack(rx.foreach(LaboratoryState.citizen_public_money_proceedings, _public_money_proceeding), spacing="3"))),
            rx.cond(LaboratoryState.citizen_public_money_limitations, rx.box(rx.text("Límites de esta lectura", class_name="context-title"), rx.foreach(LaboratoryState.citizen_public_money_limitations, lambda item: rx.text(item, class_name="muted small")))),
            spacing="3",
            align="stretch",
        ),
    )


def citizen_expedient_view() -> rx.Component:
    """Narrative UI for any CitizenExpedientProjection; it knows no expedient ID."""
    return rx.vstack(
        rx.box(
            rx.button(
                "← Volver",
                on_click=rx.call_script("if (window.history.length > 1) { window.history.back(); } else { window.location.assign('/laboratory'); }"),
                class_name="button button-secondary",
            ),
            rx.text(LaboratoryState.citizen_type, class_name="badge badge-teal"),
            rx.text(LaboratoryState.expedient_title, class_name="title"),
            rx.cond(
                LaboratoryState.citizen_official_title != "",
                rx.text(
                    "Nombre oficial: ",
                    LaboratoryState.citizen_official_title,
                    class_name="muted small",
                ),
            ),
            rx.box(
                rx.text("Pregunta que organiza este expediente", class_name="expedient-question-label"),
                rx.hstack(
                    rx.text("?", class_name="expedient-question-mark"),
                    rx.text(LaboratoryState.citizen_question, class_name="expedient-question-text"),
                    spacing="3",
                    align="start",
                ),
                class_name="expedient-question-panel",
            ),
            rx.text(LaboratoryState.expedient_summary, class_name="subtitle"),
            rx.cond(
                LaboratoryState.citizen_cutoff_substantive != "",
                rx.box(
                    rx.text("Información sustantiva verificada hasta: ", LaboratoryState.citizen_cutoff_substantive, class_name="source-fact"),
                    rx.cond(LaboratoryState.citizen_cutoff_administrative != "", rx.text("Última actuación administrativa incorporada: ", LaboratoryState.citizen_cutoff_administrative, class_name="source-fact")),
                    rx.text(LaboratoryState.citizen_cutoff_explanation, class_name="muted small"),
                    class_name="card laboratory-progress-panel",
                ),
            ),
            class_name="hero laboratory-expedient-header",
        ),
        citizen_section("Qué pasó", rx.text(LaboratoryState.expedient_summary, class_name="story-summary")),
        rx.cond(LaboratoryState.citizen_public_money_ready, public_money_summary()),
        rx.cond(LaboratoryState.citizen_topics, citizen_section("Materias del proyecto", rx.flex(rx.foreach(LaboratoryState.citizen_topics, lambda item: rx.text(item, class_name="badge badge-blue")), wrap="wrap", spacing="2"))),
        rx.cond(LaboratoryState.citizen_missing_knowledge, citizen_section("Qué falta incorporar", rx.vstack(rx.text("Estas piezas no están incorporadas al corpus actual; no permiten inferir su resultado jurídico.", class_name="muted"), rx.foreach(LaboratoryState.citizen_missing_knowledge, lambda item: rx.text(item, class_name="source-fact")), spacing="2"))),
        rx.cond(LaboratoryState.citizen_facts, citizen_section("Qué sabemos", rx.vstack(rx.foreach(LaboratoryState.citizen_facts, _citizen_statement), spacing="3"))),
        rx.foreach(LaboratoryState.citizen_public_sections, _citizen_public_section),
        rx.cond(
            LaboratoryState.citizen_bank_stages,
            citizen_section("Qué pasó con el secreto bancario", rx.vstack(
                rx.text("Propuesta original → primer trámite → Cámara revisora → retorno al Senado → Comisión Mixta", class_name="source-fact"),
                rx.foreach(LaboratoryState.citizen_bank_stages, _citizen_statement),
                rx.box("No puede afirmarse con la evidencia incorporada que el Senado haya rechazado la regla bancaria identificada en el texto de Cámara.", class_name="card laboratory-empty-notice"), spacing="3")),
        ),
        rx.cond(
            LaboratoryState.citizen_divergences,
            citizen_section("Por qué terminó en Comisión Mixta", rx.vstack(
                rx.text("El Senado aceptó la mayor parte de las modificaciones de Cámara, pero rechazó cuatro.", class_name="story-summary"),
                rx.foreach(LaboratoryState.citizen_divergences, _citizen_statement), spacing="3")),
        ),
        rx.cond(LaboratoryState.citizen_unknowns, citizen_section("Qué todavía no sabemos", rx.vstack(rx.text("No está acreditado con las fuentes incorporadas.", class_name="muted"), rx.foreach(LaboratoryState.citizen_unknowns, _citizen_statement), spacing="3"))),
        rx.cond(LaboratoryState.citizen_limitations, citizen_section("Qué no podemos concluir", rx.vstack(rx.foreach(LaboratoryState.citizen_limitations, _citizen_statement), spacing="3"))),
        rx.cond(LaboratoryState.citizen_chronology, citizen_section("Cronología", rx.vstack(rx.foreach(LaboratoryState.citizen_chronology, lambda row: rx.box(rx.text(row["date"], " · ", row["kind_label"], class_name="source-fact"), rx.text(row["text"], class_name="story-summary"), class_name="card laboratory-entity-card")), spacing="2"))),
        rx.cond(LaboratoryState.citizen_actors, citizen_section("Actores", rx.flex(rx.foreach(LaboratoryState.citizen_actors, lambda item: rx.text(item, class_name="badge badge-blue")), wrap="wrap", spacing="2"))),
        rx.cond(LaboratoryState.citizen_documents, citizen_section("Documentos", rx.grid(rx.foreach(LaboratoryState.citizen_documents, _citizen_document), columns="2", spacing="3", class_name="responsive-grid"))),
        rx.cond(LaboratoryState.citizen_sources, citizen_section("Fuentes", rx.flex(rx.foreach(LaboratoryState.citizen_sources, lambda item: rx.text(item, class_name="badge badge-purple")), wrap="wrap", spacing="2"))),
        rx.cond(LaboratoryState.citizen_questions, citizen_section("Preguntas ciudadanas", rx.vstack(rx.foreach(LaboratoryState.citizen_questions, lambda row: rx.box(rx.text("Pregunta", class_name="badge epistemic-question"), rx.text(row["question"], class_name="card-title"), rx.text(row["answer"], class_name="story-summary"), class_name="card laboratory-entity-card")), spacing="3"))),
        spacing="4", align="stretch", class_name="laboratory-expedient-shell",
    )


def citizen_section(title: str, content: rx.Component) -> rx.Component:
    return rx.box(rx.text(title, class_name="section-title"), content, class_name="laboratory-panel")


def _citizen_public_section(section: CitizenPublicSectionRow) -> rx.Component:
    """Render context-approved sections without coupling the UI to an expedient."""
    return citizen_section(
        section["title"],
        rx.vstack(rx.foreach(section["items"], _citizen_statement), spacing="3"),
    )


def _epistemic_badge(row: dict) -> rx.Component:
    return rx.cond(
        row["section"] == "limitations",
        rx.text("Límite de la evidencia", class_name="badge epistemic-limitation"),
        rx.cond(
        row["epistemic_class"] == "FACT",
        rx.text("Hecho verificado", class_name="badge epistemic-fact"),
        rx.cond(
            row["epistemic_class"] == "OPEN_QUESTION",
            rx.text("Pregunta abierta", class_name="badge epistemic-question"),
            rx.cond(
                row["epistemic_class"] == "UNKNOWN",
                rx.text("Conocimiento pendiente", class_name="badge epistemic-unknown"),
                rx.text("Límite de la evidencia", class_name="badge epistemic-limitation"),
            ),
        ),
        ),
    )
