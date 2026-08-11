from __future__ import annotations

import reflex as rx

from reflex_app.features.laboratory.state import LaboratoryState, REQUIRED_SECTIONS


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
            rx.text(row["id"], class_name="badge badge-teal"),
            section_status(row["status"]),
            justify="between",
            align="center",
        ),
        rx.text(row["title"], class_name="card-title"),
        rx.text(row["summary"], class_name="muted small"),
        rx.text(f"Actualizado: {row['updated_at']}", class_name="source-fact"),
        rx.button(
            "Abrir expediente de laboratorio",
            on_click=rx.redirect(f"/laboratory/expedient?id={row['id']}"),
            class_name="button",
        ),
        class_name="card laboratory-catalog-card",
    )


def expedient_header() -> rx.Component:
    return rx.box(
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
        rx.text("Este expediente organiza una hipotesis publica inicial. Sus datos aun estan en investigacion.", class_name="muted"),
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
