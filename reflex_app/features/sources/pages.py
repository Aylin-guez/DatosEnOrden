from __future__ import annotations

import reflex as rx

from reflex_app.components.common.cards import card_grid_or_empty, next_step_card
from reflex_app.components.common.metrics import metric
from reflex_app.constants.routes import PAGE_ECOSYSTEM
from reflex_app.features.sources.components import (
    ecosystem_concept_card,
    ecosystem_roadmap_card,
    ecosystem_source_card,
    real_data_source_card,
)
from reflex_app.features.sources.state import SourcesState
from reflex_app.helpers.routing import _investigation_href
from reflex_app.layouts.page import page_section
from reflex_app.metadata.pages import PUBLIC_OG_IMAGE_URL, _page_meta
from reflex_app.constants.demo import DEMO_INVESTIGATION_TARGET
from reflex_app.layouts.shell import shell


@rx.page(
    route="/ecosystem",
    title="Fuentes - DatosEnOrden Ciudadano",
    description="Catalogo honesto de fuentes conocidas, conectores, datos disponibles y cobertura publica.",
    image=PUBLIC_OG_IMAGE_URL,
    meta=_page_meta(
        "/sources",
        "fuentes oficiales, cobertura documental, datos publicos, trazabilidad, mapa de fuentes",
        "Fuentes - DatosEnOrden Ciudadano",
        "Catalogo honesto de fuentes conocidas, conectores, datos disponibles y cobertura publica.",
    ),
)
def ecosystem() -> rx.Component:
    return shell(
        rx.box(
            rx.text("Fuentes", class_name="title"),
            rx.text(
                "Distingue fuente conocida, conector existente, datos disponibles y cobertura suficiente. Una tarjeta no equivale a integracion activa.",
                class_name="subtitle",
            ),
            class_name="hero",
        ),
        page_section(
            "Resumen del mapa",
            rx.hstack(
                metric("Fuentes activas", SourcesState.ecosystem_active_count),
                metric("En desarrollo", SourcesState.ecosystem_prototype_count),
                metric("Planificadas", SourcesState.ecosystem_planned_count),
                metric("Conceptos", SourcesState.ecosystem_concept_count),
                spacing="3",
                wrap="wrap",
            ),
            subtitle="Cobertura y alcance del mapa de fuentes.",
        ),
        page_section(
            "Catalogo y cobertura",
            rx.text("Fuentes activas", class_name="section-subtitle"),
            card_grid_or_empty(
                SourcesState.ecosystem_active_sources,
                ecosystem_source_card,
                columns="3",
                empty_title="Aún no hay fuentes activas visibles",
                empty_body="Esta publicaci?n todav?a no expone fuentes activas en esta vista.",
                action_label="Volver al inicio",
                href="/",
            ),
            rx.text("Fuentes en desarrollo", class_name="section-subtitle"),
            card_grid_or_empty(
                SourcesState.ecosystem_prototype_sources,
                ecosystem_source_card,
                columns="3",
                empty_title="Sin fuentes en desarrollo para mostrar",
                empty_body="La hoja de ruta pública todavía no expone prototipos adicionales en esta sección.",
                action_label="Ver el proyecto",
                href="/project",
            ),
            rx.text("Fuentes planificadas", class_name="section-subtitle"),
            card_grid_or_empty(
                SourcesState.ecosystem_planned_sources,
                ecosystem_source_card,
                columns="3",
                empty_title="No hay fuentes planificadas publicadas",
                empty_body="Cuando haya nuevas prioridades públicas aparecerán aquí con su estado y alcance.",
                action_label="Explorar fuentes",
                href="/sources",
            ),
            subtitle="Estado actual, en desarrollo y lo que falta por integrar.",
        ),
        page_section(
            "Qué conecta cada fuente",
            card_grid_or_empty(
                SourcesState.ecosystem_concepts,
                ecosystem_concept_card,
                columns="4",
                empty_title="Todav?a no hay conceptos publicados",
                empty_body="Esta superficie necesita fuentes publicadas para mostrar cruces conceptuales ?tiles.",
                action_label="Revisar el proyecto",
                href="/project",
            ),
            subtitle="Conceptos visibles en cada fuente.",
        ),
        page_section(
            "Vista tecnica secundaria",
            rx.hstack(
                metric("Listas", SourcesState.real_data_ready_count),
                metric("Parciales", SourcesState.real_data_partial_count),
                metric("Con demo", SourcesState.real_data_demo_count),
                metric("Sin loader", SourcesState.real_data_without_loader_count),
                spacing="3",
                wrap="wrap",
            ),
            card_grid_or_empty(
                SourcesState.real_data_sources,
                real_data_source_card,
                columns="2",
                empty_title="Sin estado público de fuentes reales",
                empty_body="La cobertura pública todavía no expone fuentes reales adicionales en esta vista.",
                action_label="Ver fuentes",
                href="/sources",
            ),
            subtitle="Cobertura: que fuentes tienen informacion disponible, parcial, demostrativa o pendiente.",
        ),
        page_section(
            "Cómo se cruzan las fuentes",
            rx.text("Cada concepto indica qué fuentes lo alimentan y si su cobertura es activa, parcial o futura.", class_name="muted"),
            card_grid_or_empty(
                SourcesState.ecosystem_roadmap,
                ecosystem_roadmap_card,
                columns="3",
                empty_title="No hay cruces publicados todav?a",
                empty_body="Los cruces aparecen cuando una fuente publicada ya tiene cobertura suficiente para compararse con otra.",
                action_label="Explorar fuentes",
                href="/sources",
            ),
            subtitle="Lectura de cobertura y cruce entre fuentes.",
        ),
        page_section(
            "Catálogo de metadatos",
            card_grid_or_empty(
                SourcesState.ecosystem_sources,
                ecosystem_source_card,
                columns="3",
                empty_title="No hay metadatos publicados",
                empty_body="Esta vista necesita fuentes cargadas para mostrar su detalle y trazabilidad t?cnica.",
                action_label="Volver al inicio",
                href="/",
            ),
            subtitle="Detalle completo y trazabilidad t?cnica bajo demanda.",
        ),
        page_section(
            "Siguientes pasos",
            rx.grid(
            next_step_card("Explorar una pregunta", "Si todavia no sabes que buscar, empieza por una pregunta guiada.", "Ir a Explorar", "/explore"),
                next_step_card("Abrir expediente de ejemplo", "Ver cómo las fuentes se conectan en una entidad concreta.", "Abrir expediente", _investigation_href(DEMO_INVESTIGATION_TARGET)),
                next_step_card("Leer reporte ciudadano", "Ver una lectura menos t?cnica del caso publicado.", "Ir a Informes", "/reports"),
                columns="3",
                spacing="3",
                class_name="responsive-grid",
            ),
            subtitle="Las fuentes son el mapa; el expediente y el reporte muestran el recorrido.",
        ),
        on_mount=SourcesState.load_ecosystem,
        active_page=PAGE_ECOSYSTEM,
    )


@rx.page(
    route="/sources",
    title="Fuentes - DatosEnOrden Ciudadano",
    description="Catalogo honesto de fuentes conocidas, conectores, datos disponibles y cobertura publica.",
    image=PUBLIC_OG_IMAGE_URL,
    meta=_page_meta(
        "/sources",
        "fuentes oficiales, cobertura documental, datos publicos, trazabilidad, mapa de fuentes",
        "Fuentes - DatosEnOrden Ciudadano",
        "Catalogo honesto de fuentes conocidas, conectores, datos disponibles y cobertura publica.",
    ),
)
def sources() -> rx.Component:
    return ecosystem()
