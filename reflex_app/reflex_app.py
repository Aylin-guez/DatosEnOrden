from __future__ import annotations

from urllib.parse import quote_plus

import reflex as rx

from datosenorden.web.app_services import get_cross_dataset_connections
from datosenorden.web.app_services import get_citizen_dashboard
from datosenorden.web.app_services import get_dataset_summary
from datosenorden.web.app_services import get_demo_status
from datosenorden.web.app_services import get_discovery_cases
from datosenorden.web.app_services import get_guided_discovery_options
from datosenorden.web.app_services import get_guided_questions
from datosenorden.web.app_services import get_investigation
from datosenorden.web.app_services import get_entity_comparison
from datosenorden.web.app_services import get_investigation_graph
from datosenorden.web.app_services import get_investigation_markdown
from datosenorden.web.app_services import get_investigation_timeline
from datosenorden.web.app_services import get_institution_profile
from datosenorden.web.app_services import get_source_trace
from datosenorden.web.app_services import get_source_contributions
from datosenorden.web.app_services import get_investigation_story
from datosenorden.web.app_services import export_investigation_report
from datosenorden.web.app_services import get_data_ecosystem
from datosenorden.web.app_services import resolve_canonical_expediente_target
from datosenorden.web.app_services import resolve_investigation_target
from datosenorden.web.app_services import search_workspace
from datosenorden.web.app_services import search_entities
from datosenorden.maintenance.safe_access import _as_list
from datosenorden.maintenance.safe_access import _as_text
from datosenorden.maintenance.safe_access import _field as _safe_field


GRAPH_EXPLANATION = (
    "Esta entidad aparece conectada con compras publicas, roles publicos y registros de lobby. "
    "Cada conexion proviene de una fuente cargada y evidencia asociada. "
    "Esto no implica causalidad ni irregularidad."
)

PAGE_HOME = "home"
PAGE_ECOSYSTEM = "ecosystem"
PAGE_DISCOVER = "discover"
PAGE_SEARCH = "search"
PAGE_INVESTIGATION = "investigation"
PAGE_DASHBOARD = "dashboard"


def _clean(value: object, fallback: str = "Sin dato") -> str:
    text = "" if value is None else str(value).strip()
    return text or fallback

def _human_label(value: object) -> str:
    labels = {
        "outgoing": "salida",
        "incoming": "entrada",
        "CONTRACT": "contrato",
        "ROLE": "rol público",
        "ISSUES_PURCHASE_ORDER": "emite orden de compra",
        "ORGANIZATION_HELD_LOBBY_MEETING": "registró reunión de lobby",
        "ORGANIZATION_HAS_PUBLIC_ROLE": "tiene rol público registrado",
        "ROLE_BELONGS_TO_ORGANIZATION": "rol pertenece al organismo",
    }
    return labels.get(_clean(value), _clean(value))

def _format_procurement_rows(rows: list[dict]) -> list[dict]:
    return [
        {
            "title": _clean(_field(row, "contract_name"), "Orden de compra"),
            "dataset": _clean(_field(row, "dataset"), "ChileCompra"),
            "date": "Sin fecha",
            "explanation": "Registro de compra publica asociado a esta entidad.",
            "evidence": int(_field(row, "evidence_count", 0) or 0),
            "relationship_type": "Compra publica",
            "facts_text": f"Proveedor: {_clean(_field(row, 'supplier'))}",
            "technical_text": f"dataset={_clean(_field(row, 'dataset'), 'ChileCompra')}",
            "detail_text": f"dataset={_clean(_field(row, 'dataset'), 'ChileCompra')}",
        }
        for row in rows
    ]


def _format_lobby_rows(rows: list[dict]) -> list[dict]:
    return [
        {
            "title": "Reunion de lobby registrada",
            "dataset": _clean(_field(row, "dataset"), "Lobby"),
            "date": _clean(_field(row, "date"), "Sin fecha"),
            "explanation": "Registro de lobby asociado a esta entidad y una contraparte.",
            "evidence": int(_field(row, "evidence_count", 0) or 0),
            "relationship_type": "Lobby",
            "facts_text": " | ".join([
                f"Organismo: {_clean(_field(row, 'organization'))}",
                f"Contraparte: {_clean(_field(row, 'counterparty'))}",
                f"Materia: {_clean(_field(row, 'subject'))}",
            ]),
            "technical_text": f"dataset={_clean(_field(row, 'dataset'), 'Lobby')}",
            "detail_text": f"dataset={_clean(_field(row, 'dataset'), 'Lobby')}",
        }
        for row in rows
    ]


def _format_transparency_rows(rows: list[dict]) -> list[dict]:
    return [
        {
            "title": "Cargo publico registrado",
            "dataset": _clean(_field(row, "dataset"), "Transparencia"),
            "date": _clean(_field(row, "period"), "Sin periodo"),
            "explanation": "Registro administrativo de cargo o periodo publico.",
            "evidence": int(_field(row, "evidence_count", 0) or 0),
            "relationship_type": "Rol publico",
            "facts_text": " | ".join([
                f"Titular: {_clean(_field(row, 'holder'))}",
                f"Rol: {_clean(_field(row, 'role_title'))}",
                f"Periodo: {_clean(_field(row, 'period'))}",
            ]),
            "technical_text": f"dataset={_clean(_field(row, 'dataset'), 'Transparencia')}",
            "detail_text": f"dataset={_clean(_field(row, 'dataset'), 'Transparencia')}",
        }
        for row in rows
    ]


def _format_registry_rows(rows: list[dict]) -> list[dict]:
    formatted: list[dict] = []
    for row in rows:
        evidence_links = _field(row, "evidence_links", [])
        relation = _clean(_field(row, "relation"), "Registro")
        company = _clean(_field(row, "company"), "Empresa")
        person = _clean(_field(row, "person"), "Persona")
        status = _clean(_field(row, "status"), "")
        rut = _clean(_field(row, "rut"), "")
        percentage = _clean(_field(row, "ownership_percentage"), "")
        formatted.append(
            {
                "title": f"{relation} de empresa",
                "dataset": _clean(_field(row, "dataset"), "Registro Empresas"),
                "date": "Sin fecha",
                "explanation": "Registro societario de muestra asociado a una empresa.",
                "evidence": int(_field(row, "evidence_count", 0) or 0),
                "relationship_type": relation,
                "facts_text": " | ".join(
                    value
                    for value in [
                        f"Empresa: {company}",
                        f"Persona: {person}",
                        f"RUT: {rut}" if rut else "",
                        f"Estado: {status}" if status else "",
                        f"Participacion: {percentage}" if percentage else "",
                    ]
                    if value
                ),
                "technical_text": "\n".join(
                    [
                        f"dataset={_clean(_field(row, 'dataset'), 'Registro Empresas')}",
                        f"relation={relation}",
                        f"evidence_links={len(evidence_links)}",
                    ]
                ),
                "detail_text": "\n".join(
                    [
                        f"dataset={_clean(_field(row, 'dataset'), 'Registro Empresas')}",
                        f"relation={relation}",
                        f"evidence_links={len(evidence_links)}",
                    ]
                ),
            }
        )
    return formatted


def _format_relationship_rows(rows: list[dict]) -> list[dict]:
    formatted: list[dict] = []
    for row in rows:
        if _field(row, "who", None) is not None:
            technical = _field(row, "technical_details", {})
            formatted.append(
                {
                    "title": _clean(_field(row, "who"), "Entidad conectada"),
                    "dataset": _clean(_field(row, "source_dataset"), "Grafo publico local"),
                    "date": "Sin fecha",
                    "explanation": _clean(_field(row, "relationship_meaning"), "Relacion publica almacenada."),
                    "evidence": 0,
                    "relationship_type": _clean(_field(row, "entity_type"), "Entidad conectada"),
                    "facts_text": f"Quien: {_clean(_field(row, 'who'))}",
                    "technical_text": "\n".join([
                        f"relationship_id={_clean(_field(technical, 'relationship_id'))}",
                        f"relationship_type={_clean(_field(technical, 'relationship_type'))}",
                        f"direction={_clean(_field(technical, 'direction'))}",
                        f"neighbor_id={_clean(_field(technical, 'neighbor_id'))}",
                    ]),
                    "detail_text": "\n".join([
                        f"relationship_id={_clean(_field(technical, 'relationship_id'))}",
                        f"relationship_type={_clean(_field(technical, 'relationship_type'))}",
                        f"direction={_clean(_field(technical, 'direction'))}",
                        f"neighbor_id={_clean(_field(technical, 'neighbor_id'))}",
                    ]),
                }
            )
            continue
        neighbor = _field(row, "neighbor", {})
        formatted.append(
            {
                "title": _clean(_field(neighbor, "name"), "Entidad conectada"),
                "dataset": "Grafo local",
                "date": "Sin fecha",
                "explanation": "Entidad conectada por una relacion publica almacenada.",
                "evidence": 0,
                "relationship_type": _human_label(_field(row, "relationship_type")),
                "detail_text": "\n".join([
                    f"Tipo de entidad: {_human_label(_field(neighbor, 'entity_type'))}",
                    f"Dirección: {_human_label(_field(row, 'direction'))}",
                ]),
            }
        )
    return formatted

def _field(obj: object, name: str, fallback: object = None) -> object:
    return _safe_field(obj, name, fallback)


def _accent_badge_class(status: str) -> str:
    accents = {
        "active": "badge badge-teal",
        "prototype": "badge badge-purple",
        "planned": "badge badge-amber",
        "covered": "badge badge-teal",
        "partial": "badge badge-purple",
        "future": "badge badge-amber",
    }
    return accents.get(status, "badge")


def _flow_accent_class(step: int) -> str:
    return {1: "flow-accent flow-accent-teal", 2: "flow-accent flow-accent-purple"}.get(step, "flow-accent flow-accent-amber")


def _nav_class(active: bool) -> str:
    return "nav-link nav-link-active" if active else "nav-link"


def _category_button_class(category_id: str, active: bool) -> str:
    base = "search-chip explorer-category-button"
    if active:
        return f"{base} explorer-category-button-active"
    _ = category_id
    return base


def _entity_badge_class(entity_type: str) -> str:
    labels = {
        "PUBLIC_ORGANIZATION": "badge badge-teal",
        "MUNICIPALITY": "badge badge-teal",
        "PERSON": "badge badge-purple",
        "ROLE": "badge badge-purple",
        "LOBBY_MEETING": "badge badge-purple",
        "CONTRACT": "badge badge-amber",
        "BUDGET": "badge badge-amber",
        "CONTROL_REPORT": "badge badge-amber",
        "PUBLIC_OBSERVATION": "badge badge-amber",
        "PUBLIC_PROJECT": "badge badge-teal",
        "SPENDING_ITEM": "badge badge-amber",
        "ELECTORAL_PERIOD": "badge badge-purple",
    }
    return labels.get(entity_type, "badge")


def _search_href(query: str) -> str:
    cleaned = query.strip()
    if not cleaned:
        return "/search"
    return f"/search?q={quote_plus(cleaned)}"


def page_section(title: str, *children, subtitle: str | None = None) -> rx.Component:
    body = [rx.text(title, class_name="section-title")]
    if subtitle is not None:
        body.append(rx.text(subtitle, class_name="section-subtitle"))
    body.extend(children)
    return rx.vstack(*body, spacing="3", align="stretch", class_name="page-section")


def _clear_investigation_state(self) -> None:
    self.selected_entity_id = ""
    self.selected_entity_name = ""
    self.entity_name = ""
    self.entity_summary = ""
    self.dataset_badges = []
    self.contracts = 0
    self.suppliers = 0
    self.lobby_meetings = 0
    self.evidence_count = 0
    self.relationship_count = 0
    self.datasets_involved = 0
    self.connected_entities = 0
    self.story_cards = []
    self.connection_summary = ""
    self.procurement_rows = []
    self.lobby_rows = []
    self.transparencia_rows = []
    self.registry_rows = []
    self.relationship_rows = []
    self.evidence_rows = []
    self.technical_details = []
    self.neutral_explanation = ""
    self.story_headline = ""
    self.story_summary = ""
    self.story_key_findings = []
    self.story_important_connections = []
    self.story_timeline_highlights = []
    self.story_questions = []
    self.timeline_rows = []
    self.timeline_overflow_rows = []
    self.primary_dataset_label = ""
    self.primary_entity_label = ""
    self.citizen_narrative = ""
    self.source_trace_sources = []
    self.source_trace_left_rows = []
    self.source_trace_right_rows = []
    self.comparison_summary = ""
    self.comparison_observations = []
    self.comparison_overlap_areas = []
    self.comparison_dataset_rows = []
    self.source_trace_overlap_summary = ""
    self.source_trace_notice = ""
    self.graph_summary = ""
    self.graph_dataset_nodes = []
    self.graph_relationship_nodes = []
    self.graph_evidence_nodes = []
    self.timeline_year_rows = []
    self.timeline_older_year_rows = []
    self.source_contribution_rows = []
    self.report_path = ""
    self.investigation_status_message = ""


def _format_evidence_rows(rows: list[dict]) -> list[dict]:
    formatted: list[dict] = []
    for group in rows:
        dataset = _clean(_field(group, "dataset"), "Fuente")
        links = _field(group, "links", [])
        for link in links:
            formatted.append(
                {
                    "title": _clean(_field(link, "title"), "Evidencia"),
                    "dataset": dataset,
                    "date": _clean(_field(link, "published_at"), "Sin fecha"),
                    "explanation": "Enlace de evidencia asociado a registros cargados.",
                    "evidence": 1,
                    "relationship_type": "Evidencia",
                    "facts_text": f"Publicado: {_clean(_field(link, 'published_at'), 'Sin fecha')}",
                    "technical_text": f"url={_clean(_field(link, 'url'))}",
                    "detail_text": f"url={_clean(_field(link, 'url'))}",
                }
            )
    return formatted


def _format_timeline_rows(rows: list[dict]) -> list[dict]:
    formatted: list[dict] = []
    for row in rows:
        technical = _field(row, "technical_details", {})
        predicate = _clean(_field(row, "predicate"), "Evento")
        formatted.append(
            {
                "title": _clean(_field(row, "title"), "Evento de la linea de tiempo"),
                "dataset": _clean(_field(row, "dataset"), "Fuente"),
                "date": _clean(_field(row, "date"), "Sin fecha"),
                "explanation": _clean(_field(row, "explanation"), "Hecho publico registrado en la cronologia."),
                "evidence": int(_field(row, "evidence_count", 0) or 0),
                "relationship_type": _human_label(predicate),
                "facts_text": " | ".join([
                    f"Fuente: {_clean(_field(row, 'dataset_name'), _clean(_field(row, 'dataset'), 'Fuente'))}",
                    f"Evidencia: {int(_field(row, 'evidence_count', 0) or 0)}",
                ]),
                "detail_text": "\n".join([
                    f"claim_id={_clean(_field(row, 'claim_id'))}",
                    f"predicate={predicate}",
                    f"source_record_id={_clean(_field(row, 'source_record_id'))}",
                    f"technical={_clean(technical)}",
                ]),
            }
        )
    return formatted


def _build_story_cards(
    *,
    transparency: list[dict],
    lobby: list[dict],
    procurement: list[dict],
    registry: list[dict],
    relationships: list[dict],
    evidence: list[dict],
) -> list[dict]:
    cards: list[dict] = []
    cards.extend(transparency[:2])
    cards.extend(lobby[:2])
    cards.extend(procurement[:2])
    cards.extend(registry[:2])
    cards.extend(relationships[:2])
    cards.extend(evidence[:2])
    return cards


def _format_guided_options(rows: list[dict]) -> list[dict]:
    return [
        {
            **row,
            "sources_text": str(row.get("sources_text") or " | ".join(str(item) for item in row.get("sources", [])) or "Fuentes locales"),
            "canonical_entity_id": str(row.get("canonical_entity_id", row.get("entity_id", ""))),
            "canonical_entity_name": str(row.get("canonical_entity_name", row.get("title", ""))),
            "record_badge": "Registro especifico" if bool(row.get("is_record", False)) else str(row.get("type_label", row.get("type", ""))),
            "related_text": (
                f"Relacionado con: {row.get('canonical_entity_name')}"
                if bool(row.get("is_record", False)) and row.get("canonical_entity_name")
                else ""
            ),
        }
        for row in rows
    ]


class AppState(rx.State):
    query: str = ""
    results: list[dict] = []
    workspace_matches: list[dict] = []
    guided_search_title: str = ""
    selected_entity_id: str = ""
    selected_entity_name: str = ""
    error_message: str = ""
    theme_dark: bool = True

    dataset_rows: list[dict] = []
    ecosystem_sources: list[dict] = []
    ecosystem_active_sources: list[dict] = []
    ecosystem_prototype_sources: list[dict] = []
    ecosystem_planned_sources: list[dict] = []
    ecosystem_concepts: list[dict] = []
    ecosystem_roadmap: list[dict] = []
    ecosystem_active_count: int = 0
    ecosystem_prototype_count: int = 0
    ecosystem_planned_count: int = 0
    ecosystem_concept_count: int = 0
    connection_rows: list[dict] = []
    connection_rows_preview: list[dict] = []
    discovery_case_rows: list[dict] = []
    discovery_case_preview: list[dict] = []
    guided_question_rows: list[dict] = []
    guided_category_rows: list[dict] = []
    selected_guided_category_id: str = ""
    selected_guided_category_title: str = ""
    selected_guided_category_description: str = ""
    selected_guided_category_examples: list[str] = []
    selected_guided_category_sources: list[str] = []
    selected_guided_category_query: str = ""
    selected_guided_category_cta: str = ""
    selected_guided_category_href: str = "/search"
    guided_option_rows: list[dict] = []
    demo_missing: list[str] = []
    total_datasets: int = 0
    active_datasets: int = 0
    total_claims: int = 0
    total_relationships: int = 0
    dashboard_title: str = ""
    dashboard_summary: str = ""
    dashboard_budget_total: int = 0
    dashboard_budget_currency: str = "CLP"
    dashboard_contracts: int = 0
    dashboard_suppliers: int = 0
    dashboard_meetings: int = 0
    dashboard_authorities: int = 0
    dashboard_budget_rows: list[dict] = []
    dashboard_featured_entities: list[dict] = []
    dashboard_discovery_cases: list[dict] = []

    entity_name: str = ""
    entity_summary: str = ""
    dataset_badges: list[str] = []
    contracts: int = 0
    suppliers: int = 0
    lobby_meetings: int = 0
    evidence_count: int = 0
    relationship_count: int = 0
    datasets_involved: int = 0
    connected_entities: int = 0
    story_cards: list[dict] = []
    connection_summary: str = ""
    procurement_rows: list[dict] = []
    lobby_rows: list[dict] = []
    transparencia_rows: list[dict] = []
    registry_rows: list[dict] = []
    relationship_rows: list[dict] = []
    evidence_rows: list[dict] = []
    technical_details: list[dict] = []
    neutral_explanation: str = ""
    story_headline: str = ""
    story_summary: str = ""
    story_key_findings: list[str] = []
    story_important_connections: list[str] = []
    story_timeline_highlights: list[str] = []
    story_questions: list[str] = []
    timeline_rows: list[dict] = []
    timeline_overflow_rows: list[dict] = []
    primary_dataset_label: str = ""
    primary_entity_label: str = ""
    citizen_narrative: str = ""
    source_trace_sources: list[dict] = []
    source_trace_left_rows: list[dict] = []
    source_trace_right_rows: list[dict] = []
    comparison_summary: str = ""
    comparison_observations: list[str] = []
    comparison_overlap_areas: list[str] = []
    comparison_dataset_rows: list[dict] = []
    source_trace_overlap_summary: str = ""
    source_trace_notice: str = ""
    graph_summary: str = ""
    graph_dataset_nodes: list[dict] = []
    graph_relationship_nodes: list[dict] = []
    graph_evidence_nodes: list[dict] = []
    timeline_year_rows: list[dict] = []
    timeline_older_year_rows: list[dict] = []
    source_contribution_rows: list[dict] = []
    report_path: str = ""
    investigation_status_message: str = ""

    def toggle_theme(self) -> None:
        self.theme_dark = not self.theme_dark

    def load_home(self) -> None:
        self.error_message = ""
        if not hasattr(self, "guided_option_rows"):
            self.guided_option_rows = []
        try:
            summary = get_dataset_summary()
            totals = summary.get("totals", {})
            self.dataset_rows = summary.get("datasets", [])
            self.connection_rows = [
                {
                    **row,
                    "datasets_text": " | ".join(row.get("datasets", [])),
                }
                for row in get_cross_dataset_connections()
            ]
            self.connection_rows_preview = self.connection_rows[:6]
            discovery = get_discovery_cases()
            guided_questions = get_guided_questions()
            self.discovery_case_rows = [
                {
                    **row,
                    "id_label": str(row.get("id", "")).replace("_", " "),
                    "concepts_text": " | ".join(str(item) for item in row.get("concepts", [])),
                    "sources_text": " | ".join(str(item) for item in row.get("suggested_sources", [])),
                    "search_href": _search_href(str(row.get("example_query", ""))),
                }
                for row in discovery.get("cases", [])
            ]
            self.discovery_case_preview = self.discovery_case_rows[:3]
            self.guided_question_rows = [
                {
                    **row,
                    "concepts_text": " | ".join(str(item) for item in row.get("concepts", [])),
                    "sources_text": " | ".join(str(item) for item in row.get("suggested_sources", [])),
                    "search_href": _search_href(str(row.get("search_query", row.get("example_query", "")))),
                }
                for row in guided_questions.get("questions", [])
            ]
            self.guided_category_rows = [
                {
                    **row,
                    "examples_text": " | ".join(str(item) for item in row.get("examples", [])),
                    "sources_text": " | ".join(str(item) for item in row.get("suggested_sources", [])),
                    "search_href": _search_href(str(row.get("search_query", ""))),
                }
                for row in guided_questions.get("categories", [])
            ]
            if not self.guided_option_rows and self.guided_category_rows:
                first_category = str(self.guided_category_rows[0].get("id", ""))
                self.guided_option_rows = _format_guided_options(get_guided_discovery_options(first_category))
            demo_status = get_demo_status()
            self.demo_missing = [item.get("label", "") for item in demo_status.get("missing", [])]
            self.total_datasets = int(totals.get("datasets", 0))
            self.active_datasets = int(totals.get("active_datasets", 0))
            self.total_claims = int(totals.get("claims", 0))
            self.total_relationships = int(totals.get("relationships", 0))
        except Exception as exc:  # noqa: BLE001
            self.error_message = f"{type(exc).__name__}: {exc}"

    def load_discover(self) -> None:
        self.load_home()
        if self.guided_category_rows and not self.selected_guided_category_id:
            first = self.guided_category_rows[0]
            first_id = str(first.get("id", ""))
            self.selected_guided_category_id = first_id
            self.selected_guided_category_title = str(first.get("title", ""))
            self.selected_guided_category_description = str(first.get("description", ""))
            self.selected_guided_category_examples = [str(item) for item in first.get("examples", [])]
            self.selected_guided_category_sources = [str(item) for item in first.get("suggested_sources", [])]
            self.selected_guided_category_query = str(first.get("search_query", ""))
            self.selected_guided_category_cta = str(first.get("cta", ""))
            self.selected_guided_category_href = _search_href(self.selected_guided_category_query)
            self.guided_option_rows = _format_guided_options(get_guided_discovery_options(first_id))

    def load_search(self) -> None:
        self.load_home()
        self.results = []
        self.workspace_matches = []
        self.guided_search_title = ""
        self.selected_guided_category_id = ""
        self.selected_guided_category_title = ""
        self.selected_guided_category_description = ""
        self.selected_guided_category_examples = []
        self.selected_guided_category_sources = []
        self.selected_guided_category_query = ""
        self.selected_guided_category_cta = ""
        self.selected_guided_category_href = "/search"
        self.guided_option_rows = []
        query_value = str(self.router.url.query_parameters.get("q", "")).strip()
        if query_value:
            self.query = query_value
            self.guided_search_title = f"Alternativas para explorar: {query_value}"
            self.run_search()
        else:
            self.query = ""

    def load_ecosystem(self) -> None:
        self.error_message = ""
        try:
            ecosystem = get_data_ecosystem()
            sources = [
                {
                    **dict(row),
                    "concepts_text": " | ".join(str(item) for item in row.get("concepts", [])),
                    "relationships_text": " | ".join(str(item) for item in row.get("relationships", [])),
                    "connects_with_text": " | ".join(str(item) for item in row.get("connects_with", [])),
                    "entities_text": " | ".join(str(item) for item in row.get("entities", [])),
                }
                for row in ecosystem.get("sources", [])
            ]
            self.ecosystem_sources = sources
            self.ecosystem_active_sources = [row for row in sources if row.get("status") == "active"]
            self.ecosystem_prototype_sources = [row for row in sources if row.get("status") == "prototype"]
            self.ecosystem_planned_sources = [row for row in sources if row.get("status") == "planned"]
            self.ecosystem_concepts = [
                {
                    **dict(row),
                    "datasets_text": " | ".join(str(item) for item in row.get("datasets", [])),
                }
                for row in ecosystem.get("concepts", [])
            ]
            self.ecosystem_roadmap = [
                {
                    **dict(row),
                    "sources_text": " | ".join(str(item) for item in row.get("sources", [])),
                    "note_text": "Diario Oficial ya figura como prototipo local." if row.get("status") == "prototype" else "",
                }
                for row in ecosystem.get("roadmap", [])
            ]
            self.ecosystem_active_count = len(self.ecosystem_active_sources)
            self.ecosystem_prototype_count = len(self.ecosystem_prototype_sources)
            self.ecosystem_planned_count = len(self.ecosystem_planned_sources)
            self.ecosystem_concept_count = len(self.ecosystem_concepts)
        except Exception as exc:  # noqa: BLE001
            self.error_message = f"{type(exc).__name__}: {exc}"

    def set_query(self, value: str) -> None:
        self.query = value
        self.guided_search_title = ""

    def run_search(self) -> None:
        self.error_message = ""
        try:
            workspace = search_workspace(self.query)
            self.workspace_matches = [
                {
                    **row,
                    "source_hint": (
                        "Registro especifico"
                        if bool(row.get("is_record", False))
                        else "Registros publicos vinculados"
                        if int(row.get("relationship_count", 0)) or int(row.get("evidence_count", 0))
                        else "Entidad encontrada en la base local"
                    ),
                    "datasets_text": " | ".join(row.get("datasets", [])) if row.get("datasets") else "Fuentes disponibles",
                    "canonical_entity_id": str(row.get("canonical_entity_id", row.get("entity_id", ""))),
                    "canonical_entity_name": str(row.get("canonical_entity_name", row.get("entity_name", ""))),
                    "related_label": str(row.get("related_label", "")),
                    "is_record": bool(row.get("is_record", False)),
                }
                for row in workspace.get("matches", [])
            ]
            self.results = self.workspace_matches
        except Exception as exc:  # noqa: BLE001
            self.results = []
            self.workspace_matches = []
            self.error_message = f"{type(exc).__name__}: {exc}"

    def explore_discovery_case(self, case_id: str, example_query: str, title: str):
        query = str(example_query or case_id or "").strip()
        self.query = query
        self.guided_search_title = f"Alternativas para explorar: {title}" if title else "Alternativas para explorar"
        return rx.redirect(_search_href(query))

    def explore_guided_question(self, question_id: str, title: str, description: str, query: str) -> None:
        self.selected_guided_category_id = question_id
        self.selected_guided_category_title = title
        self.selected_guided_category_description = description
        self.selected_guided_category_examples = [query] if query else []
        self.selected_guided_category_sources = []
        self.selected_guided_category_query = query
        self.selected_guided_category_cta = "Buscar"
        self.selected_guided_category_href = _search_href(query)
        self.guided_option_rows = _format_guided_options(get_guided_discovery_options(question_id))
        if query:
            self.query = query

    def select_guided_category(self, category_id: str) -> None:
        self.selected_guided_category_id = category_id
        match = next((row for row in self.guided_category_rows if row.get("id") == category_id), {})
        self.selected_guided_category_title = str(match.get("title", ""))
        self.selected_guided_category_description = str(match.get("description", ""))
        self.selected_guided_category_examples = [str(item) for item in match.get("examples", [])]
        self.selected_guided_category_sources = [str(item) for item in match.get("suggested_sources", [])]
        self.selected_guided_category_query = str(match.get("search_query", ""))
        self.selected_guided_category_cta = str(match.get("cta", ""))
        self.selected_guided_category_href = _search_href(self.selected_guided_category_query)
        self.guided_option_rows = _format_guided_options(get_guided_discovery_options(category_id))
        if self.selected_guided_category_query:
            self.query = self.selected_guided_category_query
            self.guided_search_title = (
                f"Explorando {self.selected_guided_category_title}"
                if self.selected_guided_category_title
                else ""
            )

    def load_dashboard(self) -> None:
        self.error_message = ""
        try:
            data = get_citizen_dashboard()
            metrics = _field(data, "metrics", {})
            self.dashboard_title = str(_field(data, "title", ""))
            self.dashboard_summary = str(_field(data, "summary", ""))
            self.dashboard_budget_total = int(_field(metrics, "budget_total", 0) or 0)
            self.dashboard_budget_currency = str(_field(metrics, "budget_currency", "CLP"))
            self.dashboard_contracts = int(_field(metrics, "contracts", 0) or 0)
            self.dashboard_suppliers = int(_field(metrics, "suppliers", 0) or 0)
            self.dashboard_meetings = int(_field(metrics, "meetings", 0) or 0)
            self.dashboard_authorities = int(_field(metrics, "authorities", 0) or 0)
            self.dashboard_budget_rows = [
                {
                    **dict(row),
                    "years_text": str(row.get("fiscal_year", "")),
                }
                for row in _field(data, "budget_rows", [])
            ]
            self.dashboard_featured_entities = [
                {
                    **dict(row),
                    "datasets_text": " | ".join(str(item) for item in row.get("datasets", [])),
                }
                for row in _field(data, "featured_entities", [])
            ]
            self.dashboard_discovery_cases = [
                {
                    **dict(row),
                    "id_label": str(row.get("id", "")).replace("_", " "),
                    "concepts_text": " | ".join(str(item) for item in row.get("concepts", [])),
                    "sources_text": " | ".join(str(item) for item in row.get("suggested_sources", [])),
                    "search_href": _search_href(str(row.get("search_query", row.get("example_query", "")))),
                }
                for row in _field(data, "discovery_cases", [])
            ]
        except Exception as exc:  # noqa: BLE001
            self.error_message = f"{type(exc).__name__}: {exc}"


    def select_result(self, entity_id: str):
        self.selected_entity_id = entity_id
        match = next((row for row in self.results if row.get("id") == entity_id), {})
        self.selected_entity_name = str(match.get("name", ""))
        return rx.redirect(f"/investigation?id={entity_id}")

    def open_investigation(self, entity_id: str, entity_name: str):
        canonical = resolve_canonical_expediente_target(entity_id or entity_name)
        self.selected_entity_id = str(canonical.get("canonical_entity_id", entity_id))
        self.selected_entity_name = str(canonical.get("canonical_entity_name", entity_name))
        return rx.redirect(f"/investigation?id={self.selected_entity_id}")

    def load_investigation(self) -> None:
        self.error_message = ""
        query_id = str(self.router.url.query_parameters.get("id", "")).strip()
        if not query_id:
            self.load_home()
            _clear_investigation_state(self)
            return
        try:
            resolved = resolve_investigation_target(query_id)
            if not bool(_field(resolved, "found", False)):
                self.load_home()
                _clear_investigation_state(self)
                self.investigation_status_message = str(
                    _field(resolved, "warning", "No se encontro una entidad local para abrir el expediente.")
                )
                self.error_message = self.investigation_status_message
                return
            self.selected_entity_id = str(_field(resolved, "entity_id", query_id))
            self.selected_entity_name = str(_field(resolved, "entity_name", ""))
            data = get_investigation(self.selected_entity_id)
            comparison = get_entity_comparison(self.selected_entity_id)
            trace = get_source_trace(self.selected_entity_id)
            story = get_investigation_story(self.selected_entity_id)
            graph = get_investigation_graph(self.selected_entity_id)
            timeline = get_investigation_timeline(self.selected_entity_id)
            contributions = get_source_contributions(self.selected_entity_id)
            self.report_path = export_investigation_report(self.selected_entity_id)
        except Exception as exc:  # noqa: BLE001
            self.load_home()
            _clear_investigation_state(self)
            self.error_message = f"{type(exc).__name__}: {exc}"
            return
        if not data.get("found", False):
            self.load_home()
            _clear_investigation_state(self)
            self.investigation_status_message = "No se encontraron registros locales para ese expediente."
            self.error_message = self.investigation_status_message
            return

        metrics = data.get("key_metrics", {})
        compact_metrics = data.get("compact_metrics", {})
        self.entity_name = str(_field(_field(data, "entity", {}), "name", ""))
        self.selected_entity_name = self.entity_name
        self.entity_summary = data.get("narrative_summary") or data.get("summary", "")
        self.dataset_badges = data.get("dataset_badges", [])
        self.contracts = int(metrics.get("contracts", 0))
        self.suppliers = int(metrics.get("suppliers", 0))
        self.lobby_meetings = int(metrics.get("lobby_meetings", 0))
        self.evidence_count = int(compact_metrics.get("evidence_count", metrics.get("evidence", 0)))
        self.relationship_count = int(compact_metrics.get("relationship_count", metrics.get("relationships", 0)))
        self.datasets_involved = int(compact_metrics.get("datasets_involved", len(self.dataset_badges)))
        self.connected_entities = int(compact_metrics.get("connected_entities", 0))
        self.connection_summary = data.get("connections", {}).get("summary", "")
        self.procurement_rows = _format_procurement_rows(data.get("contracts_compras", []))
        self.lobby_rows = _format_lobby_rows(data.get("lobby", []))
        self.transparencia_rows = _format_transparency_rows(data.get("transparencia", []))
        self.registry_rows = _format_registry_rows(data.get("registro_empresas", []))
        timeline_rows = _format_timeline_rows(data.get("timeline", []))
        self.timeline_rows = timeline_rows[:5]
        self.timeline_overflow_rows = timeline_rows[5:]
        self.relationship_rows = _format_relationship_rows(
            data.get("connections", {}).get("relationship_cards")
            or data.get("connections", {}).get("direct_neighbors", [])
        )[:5]
        self.evidence_rows = _format_evidence_rows(data.get("evidence", []))
        self.story_cards = _build_story_cards(
            transparency=self.transparencia_rows,
            lobby=self.lobby_rows,
            procurement=self.procurement_rows,
            registry=self.registry_rows,
            relationships=self.relationship_rows,
            evidence=self.evidence_rows,
        )
        self.technical_details = [
            *self.procurement_rows,
            *self.lobby_rows,
            *self.transparencia_rows,
            *self.registry_rows,
            *self.relationship_rows,
            *self.evidence_rows,
        ]
        self.neutral_explanation = data.get("neutral_explanation", "")
        self.story_headline = str(story.get("headline", self.entity_name))
        self.story_summary = str(story.get("summary", self.entity_summary))
        self.story_key_findings = [str(item) for item in story.get("key_findings", [])]
        self.story_important_connections = [str(item) for item in story.get("important_connections", [])]
        self.story_timeline_highlights = [str(item) for item in story.get("timeline_highlights", [])]
        self.story_questions = [str(item) for item in story.get("questions_for_citizens", [])]
        self.source_trace_sources = [
            {
                "dataset": str(_field(item, "dataset", "")),
                "contribution": str(_field(item, "contribution", "")),
                "evidence_count": int(_field(item, "evidence_count", 0) or 0),
                "relationship_count": int(_field(item, "relationship_count", 0) or 0),
                "facts_text": " | ".join(str(fact) for fact in _field(item, "facts", [])),
                "technical_text": " | ".join(str(value) for value in _field(item, "technical", [])),
            }
            for item in _field(trace, "sources", [])
        ]
        midpoint = max(1, len(self.source_trace_sources) // 2) if self.source_trace_sources else 0
        self.source_trace_left_rows = self.source_trace_sources[:midpoint]
        self.source_trace_right_rows = self.source_trace_sources[midpoint:]
        self.comparison_summary = str(comparison.get("coverage_summary", ""))
        self.comparison_observations = [str(item) for item in comparison.get("consistency_observations", [])]
        self.comparison_overlap_areas = [str(item) for item in comparison.get("overlap_areas", [])]
        self.comparison_dataset_rows = [
            {
                "dataset": str(_field(item, "dataset", "")),
                "summary": str(_field(item, "summary", "")),
                "contributes_text": " | ".join(str(value) for value in _field(item, "contributes", [])),
                "category": str(_field(item, "category", "")),
            }
            for item in _field(comparison, "dataset_contributions", [])
        ]
        self.source_trace_overlap_summary = str(_field(trace, "overlap_summary", ""))
        self.source_trace_notice = str(_field(trace, "neutrality_notice", ""))
        self.primary_dataset_label = self.dataset_badges[0] if self.dataset_badges else "Dataset"
        self.primary_entity_label = self.entity_name or "Entity"
        self.citizen_narrative = self.entity_summary or self.connection_summary or self.story_summary
        self.graph_summary = str(_field(graph, "summary", ""))
        graph_nodes = [
            {
                "label": str(_field(item, "label", "")),
                "summary": str(_field(item, "summary", "")),
                "dataset": str(_field(item, "dataset", "")),
                "category": str(_field(item, "category", "")),
            }
            for item in _field(graph, "nodes", [])
        ]
        self.graph_dataset_nodes = [node for node in graph_nodes if node.get("category") == "dataset"]
        self.graph_relationship_nodes = [node for node in graph_nodes if node.get("category") == "relationship"]
        self.graph_evidence_nodes = [node for node in graph_nodes if node.get("category") == "evidence"]
        self.timeline_year_rows = []
        self.timeline_older_year_rows = []
        for index, year in enumerate(_field(timeline, "years", [])):
            items = []
            for category_group in _field(year, "categories", []):
                items.extend(_field(category_group, "items", []))
            item_texts = [
                f"{str(_field(item, 'category', ''))}: {str(_field(item, 'label', ''))} ({str(_field(item, 'dataset', ''))})"
                for item in items
            ]
            row = {
                "year": str(_field(year, "year", "")),
                "items_text": " | ".join(item_texts[:3]),
                "items_overflow_text": " | ".join(item_texts[3:]),
            }
            if index < 2:
                self.timeline_year_rows.append(row)
            else:
                self.timeline_older_year_rows.append(row)
        self.source_contribution_rows = [
            {
                "dataset": str(_field(item, "dataset", "")),
                "summary": str(_field(item, "summary", "")),
                "contributes_text": " | ".join(str(value) for value in _field(item, "contributes", [])),
                "overlap_note": str(_field(item, "overlap_note", "")),
                "category": str(_field(item, "category", "")),
                "status": str(_field(item, "status", "")),
                "concepts_text": str(_field(item, "concepts_text", "")),
                "evidence_types_text": str(_field(item, "evidence_types_text", "")),
                "timeline_contribution": str(_field(item, "timeline_contribution", "")),
            }
            for item in _field(contributions, "sources", [])
        ]


def shell(*children: rx.Component, active_page: str, **props) -> rx.Component:
    nav_items = rx.hstack(
        rx.link("Inicio", href="/", class_name=_nav_class(active_page == PAGE_HOME)),
        rx.link("Ecosistema", href="/ecosystem", class_name=_nav_class(active_page == PAGE_ECOSYSTEM)),
        rx.link("Descubre", href="/discover", class_name=_nav_class(active_page == PAGE_DISCOVER)),
        rx.link("Buscar", href="/search", class_name=_nav_class(active_page == PAGE_SEARCH)),
        rx.link("Expediente", href="/investigation", class_name=_nav_class(active_page == PAGE_INVESTIGATION)),
        spacing="2",
        align="center",
        class_name="nav-links",
    )
    return rx.box(
        rx.box(
            rx.hstack(
                rx.link("DatosEnOrden", href="/", class_name="brand"),
                nav_items,
                rx.button(
                    rx.cond(AppState.theme_dark, "Claro", "Oscuro"),
                    on_click=AppState.toggle_theme,
                    class_name="theme-toggle",
                ),
                justify="between",
                align="center",
                class_name="nav-inner",
            ),
            class_name="shell-header",
        ),
        rx.cond(
            AppState.error_message != "",
            rx.box(
                rx.text("Estado de carga", class_name="eyebrow"),
                rx.text(AppState.error_message, class_name="muted"),
                class_name="card error shell-alert",
            ),
        ),
        rx.vstack(*children, spacing="5", align="stretch", class_name="page"),
        class_name=rx.cond(AppState.theme_dark, "shell theme-dark", "shell theme-light"),
        **props,
    )

def metric(label: str, value) -> rx.Component:  # noqa: ANN001
    return rx.box(
        rx.text(value, class_name="metric-value"),
        rx.text(label, class_name="muted"),
        class_name="metric-card",
    )


def dataset_card(row: dict) -> rx.Component:
    return rx.box(
        rx.text(row["name"], class_name="card-title"),
        rx.text(row["health"], class_name=_accent_badge_class(str(row.get("health", "")))),
        rx.text(f"source records: {row['source_records']}", class_name="muted"),
        rx.text(f"entities: {row['entities']} | claims: {row['claims']}", class_name="muted"),
        rx.text(f"evidence: {row['evidence']} | relationships: {row['relationships']}", class_name="muted"),
        class_name="card",
    )


def ecosystem_source_card(row: dict) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.text(row["name"], class_name="card-title"),
            rx.text(row["status"], class_name=_accent_badge_class(str(row.get("status", "")))),
            justify="between",
            align="center",
        ),
        rx.text(row["description"], class_name="muted"),
        rx.hstack(
            rx.text(f"categoria: {row['category']}", class_name="mini-pill"),
            rx.text(f"cobertura: {row['coverage']}", class_name="mini-pill mini-pill-purple"),
            spacing="2",
            wrap="wrap",
        ),
        rx.text(f"qué aporta: {row['concepts_text']}", class_name="source-fact"),
        rx.text(f"con qué se cruza: {row.get('connects_with_text', '')}", class_name="source-fact"),
        rx.accordion.root(
            rx.accordion.item(
                header="Detalles técnicos de metadata",
                content=rx.vstack(
                    rx.text(f"entidades: {row.get('entities_text', '')}", class_name="technical-line"),
                    rx.text(f"relationships: {row['relationships_text']}", class_name="technical-line"),
                    spacing="2",
                    align="stretch",
                ),
                value=f"source-meta-{row['slug']}",
            ),
            type="single",
            collapsible=True,
            variant="ghost",
            class_name="technical-accordion",
        ),
        class_name="card ecosystem-card",
    )


def ecosystem_concept_card(row: dict) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.text(row["name"], class_name="card-title"),
            rx.text(row["coverage"], class_name=_accent_badge_class(str(row.get("coverage", "")))),
            justify="between",
            align="center",
        ),
        rx.text(row["datasets_text"], class_name="source-fact"),
        class_name="card concept-card",
    )


def ecosystem_roadmap_card(row: dict) -> rx.Component:
    return rx.box(
        rx.text(row["title"], class_name="card-title"),
        rx.text(row["sources_text"], class_name="source-fact"),
        rx.text(row.get("note_text", ""), class_name="muted small"),
        class_name="card",
    )


def connection_card(row: dict) -> rx.Component:
    return rx.box(
        rx.text(row["organization_name"], class_name="card-title"),
        rx.text(row["datasets_text"], class_name="badge badge-teal"),
        rx.text(f"Contratos: {row['contracts']} | reuniones: {row['lobby_meetings']}", class_name="muted"),
        rx.text(f"Evidencia: {row['evidence']} | relaciones: {row['relationships']}", class_name="muted"),
        rx.button(
            "Abrir expediente",
            on_click=AppState.open_investigation(row["organization_id"], row["organization_name"]),
            class_name="button button-secondary",
        ),
        class_name="card example-card",
    )


def story_card(row: dict) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.text(row["dataset"], class_name=_accent_badge_class(str(row.get("dataset", "")))),
            rx.text(row["date"], class_name="muted small"),
            justify="between",
            align="center",
        ),
        rx.text(row["title"], class_name="story-title"),
        rx.text(row["explanation"], class_name="muted"),
        rx.text(row["facts_text"], class_name="fact-line"),
        rx.hstack(
            rx.text(f"Evidencia: {row['evidence']}", class_name="mini-pill"),
            rx.text(row["relationship_type"], class_name="mini-pill mini-pill-purple"),
            spacing="2",
            wrap="wrap",
        ),
        rx.box(
            rx.text("Detalles técnicos / trazabilidad", class_name="muted small"),
            rx.text(row["detail_text"], class_name="detail-line"),
            class_name="technical-inline",
        ),
        class_name="story-card",
    )


def context_entity_card(row: dict) -> rx.Component:
    return rx.box(
        rx.text(row["title"], class_name="context-title"),
        rx.text(row["relationship_type"], class_name="mini-pill mini-pill-purple"),
        rx.text(row["explanation"], class_name="muted small"),
        class_name="context-item",
    )


def technical_detail_card(row: dict) -> rx.Component:
    return rx.box(
        rx.text(row["title"], class_name="context-title"),
        rx.text(row["technical_text"], class_name="mono id-line"),
        class_name="context-item technical-item",
    )


def source_trace_technical_row(text: str) -> rx.Component:
    return rx.text(text, class_name="technical-line")


def source_trace_card(row: dict) -> rx.Component:
    return rx.box(
        rx.text(row["dataset"], class_name="source-title"),
        rx.text(row["contribution"], class_name="muted small"),
        rx.hstack(
            rx.text(f"Evidencia {row['evidence_count']}", class_name="mini-pill"),
            rx.text(f"Relaciones {row['relationship_count']}", class_name="mini-pill"),
            spacing="2",
            wrap="wrap",
        ),
        rx.text(row["facts_text"], class_name="source-fact"),
        rx.accordion.root(
            rx.accordion.item(
                header="Detalles técnicos / trazabilidad",
                content=rx.text(row["technical_text"], class_name="technical-line"),
                value=f"source-{row['dataset']}",
            ),
            type="single",
            collapsible=True,
            variant="ghost",
            class_name="technical-accordion",
        ),
        class_name="card source-card",
    )


def entity_trace_card() -> rx.Component:
    return rx.box(
        rx.text(AppState.primary_entity_label, class_name="source-title"),
        rx.text(AppState.entity_summary, class_name="muted small"),
        rx.text("Entity", class_name="badge compact-badge"),
        rx.text(AppState.source_trace_overlap_summary, class_name="source-fact"),
        class_name="card source-entity-card",
    )


def source_trace_panel() -> rx.Component:
    return investigation_panel(
        "Source Trace",
        rx.text(
            "Public sources are arranged around the entity to show how records converge.",
            class_name="section-subtitle investigation-subtitle",
        ),
        rx.cond(
            AppState.source_trace_sources,
            rx.box(
                rx.hstack(
                    rx.foreach(AppState.source_trace_left_rows, source_trace_card),
                    rx.text("->", class_name="trace-arrow"),
                    entity_trace_card(),
                    rx.text("<-", class_name="trace-arrow"),
                    rx.foreach(AppState.source_trace_right_rows, source_trace_card),
                    spacing="2",
                    align="stretch",
                    wrap="nowrap",
                    class_name="source-trace-strip",
                ),
                class_name="source-trace-scroll",
            ),
            rx.text("No source trace available.", class_name="muted small"),
        ),
        rx.text(AppState.source_trace_notice, class_name="muted small"),
        subtitle=AppState.source_trace_overlap_summary,
    )


def comparison_panel() -> rx.Component:
    return investigation_panel(
        "Source Comparison",
        rx.text(AppState.comparison_summary, class_name="story-summary"),
        rx.cond(
            AppState.comparison_observations,
            rx.hstack(
                rx.foreach(
                    AppState.comparison_observations,
                    lambda item: rx.text(item, class_name="comparison-chip"),
                ),
                spacing="2",
                wrap="wrap",
            ),
            rx.text("No comparison observations available.", class_name="muted small"),
        ),
        subtitle="Comparison stays neutral and descriptive.",
    )


def source_contribution_card(row: dict) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.text(row["dataset"], class_name="badge"),
            rx.text(row["status"], class_name="mini-pill"),
            justify="between",
            align="center",
        ),
        rx.text(row["summary"], class_name="muted small"),
        rx.text(row["concepts_text"], class_name="source-fact"),
        rx.text(row["evidence_types_text"], class_name="muted small"),
        rx.text(row["timeline_contribution"], class_name="muted small"),
        rx.text(row["contributes_text"], class_name="source-fact"),
        rx.text(row["overlap_note"], class_name="muted small"),
        class_name="card source-card",
    )


def comparison_dataset_card(row: dict) -> rx.Component:
    return rx.box(
        rx.text(row["dataset"], class_name="badge"),
        rx.text(row["summary"], class_name="muted small"),
        rx.text(row["contributes_text"], class_name="source-fact"),
        class_name="card source-card",
    )


def comparison_overlap_card(text: str) -> rx.Component:
    return rx.text(text, class_name="comparison-chip")


def graph_node_card(row: dict) -> rx.Component:
    return rx.box(
        rx.text(row["label"], class_name="context-title"),
        rx.text(row.get("summary", ""), class_name="muted small"),
        rx.text(
            rx.cond(row["dataset"] != "", row["dataset"], row["category"]),
            class_name="badge compact-badge",
        ),
        class_name="context-item",
    )


def graph_entity_card() -> rx.Component:
    return rx.box(
        rx.text(AppState.primary_entity_label, class_name="source-title"),
        rx.text(AppState.entity_summary, class_name="muted small"),
        rx.text(AppState.graph_summary, class_name="source-fact"),
        class_name="card source-entity-card",
    )


def timeline_year_card(row: dict) -> rx.Component:
    return rx.box(
        rx.text(row["year"], class_name="story-headline"),
        rx.text(row.get("items_text", ""), class_name="source-fact"),
        rx.cond(
            row.get("items_overflow_text", ""),
            rx.accordion.root(
                rx.accordion.item(
                            header="Ver entradas anteriores",
                    content=rx.text(row.get("items_overflow_text", ""), class_name="muted small"),
                    value=f"timeline-{row['year']}",
                ),
                type="single",
                collapsible=True,
                variant="ghost",
                class_name="timeline-accordion",
            ),
        ),
        class_name="card story-card",
    )


def workspace_match_card(row: dict) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.text(row.get("entity_type_label", _human_label(row.get("entity_type", ""))), class_name=_entity_badge_class(str(row.get("entity_type", "")))),
            rx.text(row["source_hint"], class_name="muted small"),
            justify="between",
            align="center",
        ),
        rx.text(row["entity_name"], class_name="card-title"),
        rx.cond(
            row.get("is_record", False),
            rx.text("Registro específico", class_name="badge badge-amber"),
        ),
        rx.cond(
            row.get("related_label", "") != "",
            rx.text(row.get("related_label", ""), class_name="muted small"),
        ),
        rx.text(row["datasets_text"], class_name="muted small"),
        rx.hstack(
            rx.text(f"Evidencia: {row['evidence_count']}", class_name="mini-pill"),
            rx.text(f"Relaciones: {row['relationship_count']}", class_name="mini-pill"),
            spacing="2",
            wrap="wrap",
        ),
        rx.hstack(
            rx.button("Abrir expediente", on_click=AppState.open_investigation(row["canonical_entity_id"], row["canonical_entity_name"]), class_name="button button-secondary"),
            rx.cond(
                row.get("is_record", False),
                rx.text("Ver registro: pendiente", class_name="mini-pill"),
            ),
            spacing="2",
            wrap="wrap",
        ),
        class_name="card example-card search-result-card",
    )


def summary_metric_card(label: str, value) -> rx.Component:  # noqa: ANN001
    return rx.box(
        rx.text(label, class_name="summary-label"),
        rx.text(value, class_name="summary-value"),
        class_name="summary-card",
    )


def investigation_panel(title: str, *children, subtitle: str | None = None) -> rx.Component:
    subtitle_component = (
        rx.text(subtitle, class_name="section-subtitle investigation-subtitle")
        if subtitle is not None
        else None
    )
    body_children = [rx.text(title, class_name="section-title investigation-section-title")]
    if subtitle_component is not None:
        body_children.append(subtitle_component)
    body_children.extend(children)
    return rx.vstack(*body_children, spacing="2", align="stretch", class_name="card investigation-card")


def flow_card(step: int, title: str, body: str) -> rx.Component:
    return rx.box(
        rx.text(f"{step:02d}", class_name=_flow_accent_class(step)),
        rx.text(title, class_name="card-title"),
        rx.text(body, class_name="muted small"),
        class_name="card flow-card",
    )


def search_chip(label: str) -> rx.Component:
    return rx.box(rx.text(label, class_name="search-chip-text"), class_name="search-chip")


def guided_question_card(row: dict) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.text(row["title"], class_name="card-title"),
            rx.text(row["id"], class_name="badge badge-purple"),
            justify="between",
            align="center",
        ),
        rx.text(row["description"], class_name="muted small"),
        rx.hstack(
            rx.text(row.get("concepts_text", ""), class_name="search-chip"),
            rx.text(row.get("sources_text", ""), class_name="mini-pill mini-pill-purple"),
            spacing="2",
            wrap="wrap",
        ),
        rx.text(f"Ejemplo: {row['example_query']}", class_name="source-fact"),
        rx.button(
            row.get("cta", "Explorar"),
            on_click=AppState.explore_guided_question(
                row["id"],
                row["title"],
                row["description"],
                row.get("search_query", row.get("example_query", "")),
            ),
            class_name="button button-secondary",
        ),
        class_name="card example-card discovery-card",
    )


def guided_category_button(row: dict) -> rx.Component:
    return rx.cond(
        AppState.selected_guided_category_id == row["id"],
        rx.button(
            row["title"],
            on_click=AppState.select_guided_category(row["id"]),
            class_name="search-chip explorer-category-button explorer-category-button-active",
        ),
        rx.button(
            row["title"],
            on_click=AppState.select_guided_category(row["id"]),
            class_name="search-chip explorer-category-button",
        ),
    )


def guided_option_card(row: dict) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.text(row["record_badge"], class_name="badge badge-teal"),
            rx.text(row["sources_text"], class_name="muted small"),
            justify="between",
            align="center",
        ),
        rx.text(row["title"], class_name="card-title"),
        rx.text(row["why_it_appears"], class_name="muted small"),
        rx.cond(
            row.get("related_text", "") != "",
            rx.text(row["related_text"], class_name="source-fact"),
        ),
        rx.button(
            "Abrir expediente",
            on_click=AppState.open_investigation(row["canonical_entity_id"], row["canonical_entity_name"]),
            class_name="button button-secondary",
        ),
        class_name="card example-card discovery-card",
    )


def guided_category_panel() -> rx.Component:
    return rx.cond(
        AppState.selected_guided_category_id != "",
        rx.box(
            rx.hstack(
                rx.text(AppState.selected_guided_category_title, class_name="card-title"),
                rx.text("Panel exploratorio", class_name="badge badge-purple"),
                justify="between",
                align="center",
            ),
            rx.text(AppState.selected_guided_category_description, class_name="muted"),
            rx.hstack(
                rx.foreach(AppState.selected_guided_category_examples, search_chip),
                spacing="2",
                wrap="wrap",
            ),
            rx.hstack(
                rx.foreach(AppState.selected_guided_category_sources, lambda item: rx.text(item, class_name="mini-pill mini-pill-purple")),
                spacing="2",
                wrap="wrap",
            ),
            rx.cond(
                AppState.guided_option_rows,
                rx.grid(
                    rx.foreach(AppState.guided_option_rows, guided_option_card),
                    columns="2",
                    spacing="2",
                    class_name="responsive-grid",
                ),
                rx.text("No hay opciones locales cargadas para esta categoria.", class_name="muted small"),
            ),
            rx.hstack(
                rx.button(
                    "Buscar esta categoría",
                    on_click=AppState.run_search,
                    class_name="button",
                ),
                rx.button(
                    "Ir a Buscar",
                    on_click=rx.redirect(AppState.selected_guided_category_href),
                    class_name="button button-secondary",
                ),
                spacing="3",
                wrap="wrap",
            ),
            class_name="card explorer-panel",
        ),
        rx.text("Selecciona una categoría para ver ejemplos.", class_name="muted small"),
    )


def guided_discovery_panel() -> rx.Component:
    return rx.vstack(
        page_section(
            "Preguntas guiadas",
            rx.cond(
                AppState.guided_question_rows,
                rx.grid(
                    rx.foreach(AppState.guided_question_rows, guided_question_card),
                    columns="2",
                    spacing="3",
                    class_name="responsive-grid",
                ),
                rx.text("TodavÃ­a no hay preguntas guiadas disponibles.", class_name="muted small"),
            ),
            subtitle="Consultas concretas que exploran datos locales.",
        ),
        page_section(
            "Explora por categorÃ­a",
            rx.hstack(
                rx.foreach(AppState.guided_category_rows, guided_category_button),
                spacing="2",
                wrap="wrap",
                class_name="chip-row",
            ),
            guided_category_panel(),
            subtitle="Selecciona una categorÃ­a para ver ejemplos sin perder el contexto.",
        ),
        spacing="4",
        align="stretch",
    )


def search_example_card(row: dict) -> rx.Component:
    return rx.box(
        rx.text(row["organization_name"], class_name="card-title"),
        rx.text(row["datasets_text"], class_name="badge badge-teal"),
        rx.text(f"Contratos: {row['contracts']} | reuniones: {row['lobby_meetings']}", class_name="muted small"),
        rx.text(f"Evidencia: {row['evidence']} | relaciones: {row['relationships']}", class_name="muted small"),
        rx.button(
            "Abrir expediente",
            on_click=AppState.open_investigation(row["organization_id"], row["organization_name"]),
            class_name="button button-secondary",
        ),
        class_name="card example-card",
    )


def dashboard_budget_card(row: dict) -> rx.Component:
    return rx.box(
        rx.text(row["organization_name"], class_name="card-title"),
        rx.text(f"Año fiscal: {row.get('fiscal_year', '')}", class_name="muted small"),
        rx.text(
            f"Ejecutado: {row.get('executed_budget', 0)} {row.get('currency', 'CLP')}",
            class_name="source-fact",
        ),
        rx.text(
            f"Aprobado: {row.get('approved_budget', 0)} | OC: {row.get('purchase_orders', 0)} | Proveedores: {row.get('suppliers', 0)}",
            class_name="muted small",
        ),
        class_name="card dashboard-card",
    )


def discovery_case_card(row: dict) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.text(row["title"], class_name="card-title"),
            rx.text(row["id_label"], class_name="badge badge-purple"),
            justify="between",
            align="center",
        ),
        rx.text(row["description"], class_name="muted small"),
        rx.hstack(
            rx.text(row.get("concepts_text", ""), class_name="search-chip"),
            rx.text(row.get("sources_text", ""), class_name="mini-pill mini-pill-purple"),
            spacing="2",
            wrap="wrap",
        ),
        rx.text(f"Ejemplo: {row['example_query']}", class_name="source-fact"),
        rx.button(
            row.get("cta", "Explorar"),
            on_click=AppState.explore_discovery_case(row["id"], row["example_query"], row["title"]),
            class_name="button button-secondary",
        ),
        class_name="card example-card discovery-card",
    )


def start_from_ecosystem_card() -> rx.Component:
    return rx.link(
        rx.box(
            rx.text("Empieza por el ecosistema", class_name="card-title"),
            rx.text("Si no sabes qué buscar, explora primero las fuentes disponibles.", class_name="muted small"),
            rx.text("Ir a Ecosistema", class_name="badge badge-amber"),
            class_name="card prompt-card",
        ),
        href="/ecosystem",
        class_name="prompt-link",
    )


def investigation_entry_card(title: str, body: str, button_label: str, href: str, accent_class: str = "button") -> rx.Component:
    return rx.box(
        rx.text(title, class_name="card-title"),
        rx.text(body, class_name="muted small"),
        rx.button(button_label, on_click=rx.redirect(href), class_name=accent_class),
        class_name="card empty-entry-card",
    )


def investigation_empty_state() -> rx.Component:
    return rx.vstack(
        rx.box(
            rx.text("Abre un expediente", class_name="title"),
            rx.text("Un expediente reúne las fuentes públicas disponibles para una entidad.", class_name="subtitle"),
            rx.cond(
                AppState.investigation_status_message != "",
                rx.text(AppState.investigation_status_message, class_name="muted"),
            ),
            class_name="hero",
        ),
        rx.grid(
            investigation_entry_card(
                "Buscar una entidad",
                "Encuentra organismos, proveedores, autoridades o cargos públicos.",
                "Ir a Buscar",
                "/search",
                "button",
            ),
            rx.box(
                rx.text("Ver ejemplos", class_name="card-title"),
                rx.text("Abre un expediente ya conectado por varias fuentes locales.", class_name="muted small"),
                rx.cond(
                    AppState.connection_rows_preview,
                    rx.vstack(
                        rx.foreach(AppState.connection_rows_preview[:1], search_example_card),
                        spacing="2",
                        align="stretch",
                    ),
                    rx.text("Todavía no hay ejemplos disponibles.", class_name="muted small"),
                ),
                class_name="card empty-entry-card empty-entry-card-wide",
            ),
            investigation_entry_card(
                "Entender fuentes",
                "Explora primero el mapa si todavía no sabes qué buscar.",
                "Ver Ecosistema",
                "/ecosystem",
                "button button-secondary",
            ),
            columns="3",
            spacing="3",
            class_name="responsive-grid investigation-empty-grid",
        ),
        spacing="4",
        align="stretch",
    )

def search_empty_state() -> rx.Component:
    return rx.vstack(
        page_section(
            "Prueba con estos ejemplos",
            rx.cond(
                AppState.discovery_case_rows,
                rx.grid(
                    rx.foreach(AppState.discovery_case_rows, discovery_case_card),
                    columns="2",
                    spacing="3",
                    class_name="responsive-grid",
                ),
                rx.text("Todavía no hay sugerencias disponibles.", class_name="muted small"),
            ),
            subtitle="Casos guiados antes de buscar.",
        ),
        page_section(
            "¿Qué puedes buscar?",
            rx.hstack(
                rx.foreach(
                    [
                        "Organismos públicos",
                        "Proveedores",
                        "Autoridades",
                        "Compras",
                        "Presupuestos",
                        "Reuniones",
                        "Cargos públicos",
                    ],
                    search_chip,
                ),
                spacing="2",
                wrap="wrap",
                class_name="chip-row",
            ),
            subtitle="Términos útiles para empezar.",
        ),
        page_section(
            "Ejemplos de expediente",
            rx.cond(
                AppState.connection_rows_preview,
                rx.grid(
                    rx.foreach(AppState.connection_rows_preview, search_example_card),
                    columns="2",
                    spacing="3",
                    class_name="responsive-grid",
                ),
                rx.text("Todavía no hay ejemplos disponibles.", class_name="muted small"),
            ),
            subtitle="Cruces visibles entre fuentes locales.",
        ),
        page_section(
            "Empieza por el ecosistema",
            start_from_ecosystem_card(),
            subtitle="Si no sabes qué buscar, explora primero las fuentes disponibles.",
        ),
        spacing="4",
        align="stretch",
    )


def narrative_item(text: str) -> rx.Component:
    return rx.box(rx.text(text, class_name="narrative-text"), class_name="narrative-item")


def timeline_highlights_panel() -> rx.Component:
    return investigation_panel(
        "Cronología",
        rx.cond(
            AppState.timeline_year_rows,
            rx.vstack(
                rx.foreach(AppState.timeline_year_rows, timeline_year_card),
                rx.cond(
                    AppState.timeline_older_year_rows,
                    rx.accordion.root(
                        rx.accordion.item(
                            header="Ver entradas anteriores",
                            content=rx.vstack(
                                rx.foreach(AppState.timeline_older_year_rows, timeline_year_card),
                                spacing="2",
                                align="stretch",
                            ),
                            value="older-timeline",
                        ),
                        type="single",
                        collapsible=True,
                        variant="ghost",
                        class_name="timeline-accordion",
                    ),
                ),
                spacing="2",
                align="stretch",
            ),
            rx.cond(
                AppState.story_timeline_highlights,
                rx.vstack(
                    rx.foreach(AppState.story_timeline_highlights, narrative_item),
                    spacing="2",
                    align="stretch",
                ),
                rx.text("No hay cronología disponible.", class_name="muted small"),
            ),
        ),
        subtitle="Los años recientes quedan visibles. Las entradas anteriores permanecen colapsadas.",
    )


def investigation_tabs_panel() -> rx.Component:
    return investigation_panel(
        "Recorrido de evidencia",
        rx.tabs.root(
            rx.tabs.list(
                rx.tabs.trigger("Compras", value="procurement"),
                rx.tabs.trigger("Lobby", value="lobby"),
                rx.tabs.trigger("Transparencia", value="transparency"),
                rx.tabs.trigger("Empresas", value="registry"),
                rx.tabs.trigger("Evidencia", value="evidence"),
                class_name="tabs-list",
            ),
            rx.tabs.content(
                rx.cond(
                    AppState.procurement_rows,
                    rx.grid(
                        rx.foreach(AppState.procurement_rows, story_card),
                        columns="2",
                        spacing="2",
                        class_name="tab-grid",
                    ),
                    rx.text("No hay registros de compras disponibles.", class_name="muted small"),
                ),
                value="procurement",
                class_name="tab-content",
            ),
            rx.tabs.content(
                rx.cond(
                    AppState.lobby_rows,
                    rx.grid(
                        rx.foreach(AppState.lobby_rows, story_card),
                        columns="2",
                        spacing="2",
                        class_name="tab-grid",
                    ),
                    rx.text("No hay registros de lobby disponibles.", class_name="muted small"),
                ),
                value="lobby",
                class_name="tab-content",
            ),
            rx.tabs.content(
                rx.cond(
                    AppState.transparencia_rows,
                    rx.grid(
                        rx.foreach(AppState.transparencia_rows, story_card),
                        columns="2",
                        spacing="2",
                        class_name="tab-grid",
                    ),
                    rx.text("No hay registros de transparencia disponibles.", class_name="muted small"),
                ),
                value="transparency",
                class_name="tab-content",
            ),
            rx.tabs.content(
                rx.cond(
                    AppState.registry_rows,
                    rx.grid(
                        rx.foreach(AppState.registry_rows, story_card),
                        columns="2",
                        spacing="2",
                        class_name="tab-grid",
                    ),
                    rx.text("No hay registros de empresas disponibles.", class_name="muted small"),
                ),
                value="registry",
                class_name="tab-content",
            ),
            rx.tabs.content(
                rx.cond(
                    AppState.evidence_rows,
                    rx.grid(
                        rx.foreach(AppState.evidence_rows, story_card),
                        columns="2",
                        spacing="2",
                        class_name="tab-grid",
                    ),
                    rx.text("No hay evidencia disponible.", class_name="muted small"),
                ),
                value="evidence",
                class_name="tab-content",
            ),
            default_value="procurement",
            class_name="tabs-root",
        ),
        subtitle="Cambia de tema en vez de recorrer secciones apiladas.",
    )


def relationship_map_panel() -> rx.Component:
    return rx.box(
        rx.text("Mapa de relaciones", class_name="section-title investigation-section-title"),
        rx.text("Fuente -> Entidad -> Relación -> Evidencia", class_name="section-subtitle investigation-subtitle"),
        rx.hstack(
            rx.hstack(
                rx.foreach(AppState.graph_dataset_nodes, graph_node_card),
                spacing="2",
                wrap="wrap",
            ),
            rx.text("->", class_name="map-arrow"),
            graph_entity_card(),
            rx.text("->", class_name="map-arrow"),
            rx.hstack(
                rx.foreach(AppState.graph_relationship_nodes, graph_node_card),
                spacing="2",
                wrap="wrap",
            ),
            rx.text("->", class_name="map-arrow"),
            rx.hstack(
                rx.foreach(AppState.graph_evidence_nodes, graph_node_card),
                spacing="2",
                wrap="wrap",
            ),
            spacing="2",
            align="stretch",
            wrap="nowrap",
        ),
        rx.text(AppState.graph_summary, class_name="muted small"),
        class_name="card relationship-map",
    )


def context_sidebar_panel() -> rx.Component:
    return rx.box(
        rx.text("Detalles técnicos / trazabilidad", class_name="section-title investigation-section-title"),
        rx.text(AppState.connection_summary, class_name="muted"),
        rx.text(GRAPH_EXPLANATION, class_name="muted small"),
        rx.text(AppState.neutral_explanation, class_name="muted small"),
        rx.text("Qué aporta cada fuente", class_name="context-title"),
        rx.hstack(
            rx.foreach(AppState.source_contribution_rows, source_contribution_card),
            spacing="2",
            wrap="nowrap",
            class_name="horizontal-scroll",
        ),
        rx.text("Áreas de cruce", class_name="context-title"),
        rx.cond(
            AppState.comparison_overlap_areas,
            rx.hstack(
                rx.foreach(AppState.comparison_overlap_areas, comparison_overlap_card),
                spacing="2",
                wrap="wrap",
            ),
            rx.text("No hay áreas de cruce disponibles.", class_name="muted small"),
        ),
        rx.text("Detalle de comparación", class_name="context-title"),
        rx.cond(
            AppState.comparison_dataset_rows,
            rx.hstack(
                rx.foreach(AppState.comparison_dataset_rows, comparison_dataset_card),
                spacing="2",
                wrap="nowrap",
                class_name="horizontal-scroll",
            ),
            rx.text("No hay detalle de comparación disponible.", class_name="muted small"),
        ),
        rx.text("Metrics", class_name="context-title"),
        rx.grid(
            summary_metric_card("Fuentes", AppState.datasets_involved),
            summary_metric_card("Evidencia", AppState.evidence_count),
            summary_metric_card("Relaciones", AppState.relationship_count),
            summary_metric_card("Entidades conectadas", AppState.connected_entities),
            columns="2",
            spacing="2",
            class_name="metrics-grid",
        ),
        rx.text("Entidades conectadas", class_name="context-title"),
        rx.cond(
            AppState.relationship_rows,
            rx.vstack(
                rx.foreach(AppState.relationship_rows, context_entity_card),
                spacing="2",
                align="stretch",
            ),
            rx.text("No hay entidades conectadas disponibles.", class_name="muted small"),
        ),
        rx.accordion.root(
            rx.accordion.item(
                header="Detalles técnicos / trazabilidad",
                content=rx.vstack(
                    rx.text(
                        "Aquí se guardan identificadores, URLs, predicados, códigos de relación y referencias internas para trazabilidad.",
                        class_name="muted small",
                    ),
                    rx.cond(
                        AppState.technical_details,
                        rx.vstack(
                            rx.foreach(AppState.technical_details, technical_detail_card),
                            spacing="2",
                            align="stretch",
                        ),
                        rx.text("No hay detalles técnicos disponibles.", class_name="muted small"),
                    ),
                    spacing="2",
                    align="stretch",
                ),
                value="technical-details",
            ),
            type="single",
            collapsible=True,
            variant="ghost",
            class_name="technical-accordion",
        ),
        class_name="card context-panel investigation-sidebar",
    )


def investigation_left_column() -> rx.Component:
    return rx.vstack(
        investigation_panel(
            "Historia del expediente",
            rx.text(AppState.story_headline, class_name="story-headline"),
            rx.text(AppState.story_summary, class_name="story-summary"),
            rx.cond(
                AppState.story_key_findings,
                rx.hstack(
                    rx.foreach(AppState.story_key_findings, lambda item: rx.text(item, class_name="story-chip")),
                    spacing="2",
                    wrap="wrap",
                ),
                rx.text("No hay hallazgos clave disponibles.", class_name="muted small"),
            ),
            subtitle="Primero el resumen; el detalle técnico se mantiene oculto.",
        ),
        investigation_panel(
            "Narrativa ciudadana",
            rx.text(AppState.citizen_narrative, class_name="story-summary story-summary-dominant"),
            rx.cond(
                AppState.story_important_connections,
                rx.vstack(
                    rx.foreach(AppState.story_important_connections, narrative_item),
                    spacing="2",
                    align="stretch",
                ),
                rx.text("No hay narrativa ciudadana disponible.", class_name="muted small"),
            ),
            rx.cond(
                AppState.story_questions,
                rx.hstack(
                    rx.foreach(AppState.story_questions, lambda item: rx.text(item, class_name="prompt-chip")),
                    spacing="2",
                    wrap="wrap",
                ),
                rx.text("No hay sugerencias de recorrido disponibles.", class_name="muted small"),
            ),
            subtitle="Pistas breves y contexto para guiar la exploración.",
        ),
        timeline_highlights_panel(),
        spacing="3",
        align="stretch",
        class_name="story-main investigation-left",
    )


def investigation_center_column() -> rx.Component:
    return rx.vstack(
        relationship_map_panel(),
        investigation_tabs_panel(),
        spacing="3",
        align="stretch",
        class_name="story-main investigation-center",
    )


@rx.page(route="/", title="Inicio - DatosEnOrden")
def home() -> rx.Component:
    return shell(
        rx.box(
            rx.text("Explora cómo se conectan los datos públicos", class_name="title"),
            rx.text(
                "DatosEnOrden conecta fuentes públicas para ayudarte a entender organismos, compras, presupuestos, autoridades y evidencia disponible.",
                class_name="subtitle",
            ),
            rx.hstack(
                rx.button("Explorar ecosistema", on_click=rx.redirect("/ecosystem"), class_name="button"),
                rx.button("Buscar entidad", on_click=rx.redirect("/search"), class_name="button button-secondary"),
                spacing="3",
                wrap="wrap",
                class_name="hero-actions",
            ),
            class_name="hero",
        ),
        page_section(
            "Recorrido",
            rx.grid(
                flow_card(1, "Explora fuentes", "Revisa qué bases existen hoy, cuáles están en desarrollo y cuáles se planean."),
                flow_card(2, "Busca una entidad", "Encuentra organismos, proveedores, autoridades o cargos públicos."),
                flow_card(3, "Abre un expediente", "Cruza fuentes, evidencia y trazabilidad en una sola vista."),
                columns="3",
                spacing="3",
                class_name="responsive-grid",
            ),
            subtitle="Un recorrido simple antes de entrar en la búsqueda.",
        ),
        page_section(
            "Descubre",
            rx.grid(
                rx.foreach(AppState.discovery_case_preview, discovery_case_card),
                columns="3",
                spacing="3",
                class_name="responsive-grid",
            ),
            rx.link("Ver todos los casos", href="/discover", class_name="badge badge-purple"),
            subtitle="Casos guiados para empezar por una pregunta.",
        ),
        rx.box(
            rx.vstack(
                page_section(
                    "Métricas compactas",
                    rx.hstack(
                        metric("Fuentes", AppState.total_datasets),
                        metric("Activas", AppState.active_datasets),
                        metric("Evidencias", AppState.total_claims),
                        metric("Relaciones", AppState.total_relationships),
                        spacing="3",
                        wrap="wrap",
                    ),
                    subtitle="Resumen breve al final del recorrido.",
                ),
                page_section(
                    "Conjuntos de datos",
                    rx.grid(
                        rx.foreach(AppState.dataset_rows, dataset_card),
                        columns="2",
                        spacing="3",
                        class_name="responsive-grid",
                    ),
                    subtitle="Fuentes que ya están disponibles localmente.",
                ),
                spacing="4",
                align="stretch",
            ),
            rx.vstack(
                page_section(
                    "Conexiones destacadas",
                    rx.text("Explora entidades que aparecen en varias fuentes públicas.", class_name="section-subtitle"),
                    rx.grid(
                        rx.foreach(AppState.connection_rows_preview, connection_card),
                        columns="1",
                        spacing="3",
                        class_name="responsive-grid",
                    ),
                    subtitle="Casos de ejemplo para abrir expedientes.",
                ),
                page_section(
                    "Estado de carga",
                    rx.foreach(AppState.demo_missing, lambda item: rx.text(item, class_name="muted")),
                    subtitle="Chequeo local de disponibilidad.",
                ),
                spacing="4",
                align="stretch",
            ),
            class_name="home-lower-layout",
        ),
        on_mount=AppState.load_home,
        active_page=PAGE_HOME,
    )


@rx.page(route="/ecosystem", title="Ecosistema - DatosEnOrden")
def ecosystem() -> rx.Component:
    return shell(
        rx.box(
            rx.text("Ecosistema", class_name="title"),
            rx.text(
                "Mapa conceptual de las fuentes disponibles, las que están en camino y cómo se cruzan entre sí.",
                class_name="subtitle",
            ),
            class_name="hero",
        ),
        page_section(
            "Resumen del mapa",
            rx.hstack(
                metric("Fuentes activas", AppState.ecosystem_active_count),
                metric("En desarrollo", AppState.ecosystem_prototype_count),
                metric("Planificadas", AppState.ecosystem_planned_count),
                metric("Conceptos", AppState.ecosystem_concept_count),
                spacing="3",
                wrap="wrap",
            ),
            subtitle="Cobertura y alcance del mapa de fuentes.",
        ),
        page_section(
            "Fuentes actuales",
            rx.text("Fuentes activas", class_name="section-subtitle"),
            rx.grid(
                rx.foreach(AppState.ecosystem_active_sources, ecosystem_source_card),
                columns="3",
                spacing="3",
                class_name="responsive-grid",
            ),
            rx.text("Fuentes en desarrollo", class_name="section-subtitle"),
            rx.grid(
                rx.foreach(AppState.ecosystem_prototype_sources, ecosystem_source_card),
                columns="3",
                spacing="3",
                class_name="responsive-grid",
            ),
            rx.text("Fuentes planificadas", class_name="section-subtitle"),
            rx.grid(
                rx.foreach(AppState.ecosystem_planned_sources, ecosystem_source_card),
                columns="3",
                spacing="3",
                class_name="responsive-grid",
            ),
            subtitle="Estado actual, en desarrollo y lo que falta por integrar.",
        ),
        page_section(
            "Qué conecta cada fuente",
            rx.grid(
                rx.foreach(AppState.ecosystem_concepts, ecosystem_concept_card),
                columns="4",
                spacing="3",
                class_name="responsive-grid",
            ),
            subtitle="Conceptos visibles en cada fuente.",
        ),
        page_section(
            "Cómo se cruzan las fuentes",
            rx.text("Cada concepto indica qué fuentes lo alimentan y si su cobertura es activa, parcial o futura.", class_name="muted"),
            rx.grid(
                rx.foreach(AppState.ecosystem_roadmap, ecosystem_roadmap_card),
                columns="3",
                spacing="3",
                class_name="responsive-grid",
            ),
            subtitle="Lectura de cobertura y cruce entre fuentes.",
        ),
        page_section(
            "Catálogo de metadatos",
            rx.grid(
                rx.foreach(AppState.ecosystem_sources, ecosystem_source_card),
                columns="3",
                spacing="3",
                class_name="responsive-grid",
            ),
            subtitle="Detalle completo y trazabilidad técnica bajo demanda.",
        ),
        on_mount=AppState.load_ecosystem,
        active_page=PAGE_ECOSYSTEM,
    )


@rx.page(route="/discover", title="Descubre - DatosEnOrden")
def discover() -> rx.Component:
    return shell(
        rx.box(
            rx.text("Descubre qué puedes explorar", class_name="title"),
            rx.text(
                "Elige una pregunta inicial y DatosEnOrden te guía por las fuentes públicas disponibles.",
                class_name="subtitle",
            ),
            class_name="hero",
        ),
        guided_discovery_panel(),
        page_section(
            "Casos guiados",
            rx.grid(
                rx.foreach(AppState.discovery_case_rows, discovery_case_card),
                columns="2",
                spacing="3",
                class_name="responsive-grid",
            ),
            subtitle="Puntos de entrada para empezar antes de buscar.",
        ),
        page_section(
            "Qué puedes probar",
            rx.hstack(
                rx.text("Organismos públicos", class_name="search-chip"),
                rx.text("Proveedores", class_name="search-chip"),
                rx.text("Autoridades", class_name="search-chip"),
                rx.text("Compras", class_name="search-chip"),
                rx.text("Presupuestos", class_name="search-chip"),
                rx.text("Reuniones", class_name="search-chip"),
                rx.text("Cargos públicos", class_name="search-chip"),
                spacing="2",
                wrap="wrap",
            ),
            subtitle="Conceptos para orientar el primer recorrido.",
        ),
        page_section(
            "Desde aquí",
            rx.hstack(
                rx.button("Buscar entidad", on_click=rx.redirect("/search"), class_name="button"),
                rx.button("Ir al ecosistema", on_click=rx.redirect("/ecosystem"), class_name="button button-secondary"),
                spacing="3",
                wrap="wrap",
            ),
            subtitle="Cambia de ruta sin perder el contexto.",
        ),
        on_mount=AppState.load_discover,
        active_page=PAGE_DISCOVER,
    )


def result_card(row: dict) -> rx.Component:
    return workspace_match_card(row)


@rx.page(route="/search", title="Buscar - DatosEnOrden")
def search() -> rx.Component:
    return shell(
        rx.box(
            rx.text("Buscar", class_name="title"),
            rx.text(
                "Busca una entidad para abrir un expediente con fuentes públicas, evidencia y trazabilidad.",
                class_name="subtitle",
            ),
            class_name="hero",
        ),
        page_section(
            "Barra de búsqueda",
            rx.hstack(
                rx.input(
                    placeholder="Busca organismo, proveedor, autoridad o cargo público",
                    value=AppState.query,
                    on_change=AppState.set_query,
                    class_name="input search-input",
                ),
                rx.button("Buscar", on_click=AppState.run_search, class_name="button search-button"),
                spacing="3",
                align="center",
                class_name="search-bar",
            ),
            subtitle="La entrada principal para abrir un expediente.",
        ),
        guided_discovery_panel(),
        rx.cond(
            AppState.results,
            page_section(
                rx.cond(AppState.guided_search_title != "", AppState.guided_search_title, "Resultados"),
                rx.grid(
                    rx.foreach(AppState.results, result_card),
                    columns="3",
                    spacing="3",
                    class_name="responsive-grid",
                ),
                subtitle="Selecciona un resultado para abrir el expediente.",
            ),
            search_empty_state(),
        ),
        on_mount=AppState.load_search,
        active_page=PAGE_SEARCH,
    )


def section(title: str, rows, empty_text: str) -> rx.Component:  # noqa: ANN001
    return rx.box(
        rx.text(title, class_name="section-title"),
        rx.cond(
            rows,
            rx.vstack(
                rx.foreach(rows, story_card),
                spacing="3",
                align="stretch",
            ),
            rx.text(empty_text, class_name="muted"),
        ),
        class_name="card",
    )


@rx.page(route="/investigation", title="Expediente - DatosEnOrden")
def investigation() -> rx.Component:
    return shell(
        rx.cond(
            AppState.selected_entity_id == "",
            investigation_empty_state(),
            rx.box(
                rx.vstack(
                    rx.box(
                        rx.text(AppState.entity_name, class_name="title"),
                        rx.text(AppState.entity_summary, class_name="subtitle"),
                        rx.hstack(
                            rx.foreach(AppState.dataset_badges, lambda item: rx.text(item, class_name="badge badge-teal")),
                            spacing="2",
                            wrap="wrap",
                        ),
                        class_name="hero",
                    ),
                    rx.hstack(
                        summary_metric_card("Fuentes", AppState.datasets_involved),
                        summary_metric_card("Evidencia", AppState.evidence_count),
                        summary_metric_card("Relaciones", AppState.relationship_count),
                        summary_metric_card("Entidades conectadas", AppState.connected_entities),
                        spacing="2",
                        wrap="wrap",
                        class_name="summary-strip",
                    ),
                    rx.box(
                        investigation_left_column(),
                        investigation_center_column(),
                        context_sidebar_panel(),
                        class_name="investigation-layout",
                    ),
                    spacing="4",
                    align="stretch",
                    class_name="investigation-shell",
                ),
            ),
        ),
        on_mount=AppState.load_investigation,
        active_page=PAGE_INVESTIGATION,
    )


@rx.page(route="/dashboard", title="Dashboard - DatosEnOrden")
def dashboard() -> rx.Component:
    return shell(
        rx.box(
            rx.text("¿Dónde fue mi plata?", class_name="title"),
            rx.text(
                "Una vista ciudadana de muestra que cruza presupuesto, compras, proveedores, reuniones y autoridades visibles.",
                class_name="subtitle",
            ),
            rx.hstack(
                rx.button("Explorar ecosistema", on_click=rx.redirect("/ecosystem"), class_name="button"),
                rx.button("Buscar entidad", on_click=rx.redirect("/search"), class_name="button button-secondary"),
                spacing="3",
                wrap="wrap",
                class_name="hero-actions",
            ),
            class_name="hero",
        ),
        page_section(
            "Resumen ciudadano",
            rx.grid(
                metric("Presupuesto", AppState.dashboard_budget_total),
                metric("Contratos", AppState.dashboard_contracts),
                metric("Proveedores", AppState.dashboard_suppliers),
                metric("Reuniones", AppState.dashboard_meetings),
                metric("Autoridades", AppState.dashboard_authorities),
                columns="5",
                spacing="3",
                class_name="responsive-grid",
            ),
            subtitle="Indicadores compuestos desde los datos de muestra disponibles.",
        ),
        page_section(
            "Presupuesto de muestra",
            rx.text(f"Moneda de referencia: {AppState.dashboard_budget_currency}", class_name="muted small"),
            rx.cond(
                AppState.dashboard_budget_rows,
                rx.grid(
                    rx.foreach(AppState.dashboard_budget_rows, dashboard_budget_card),
                    columns="2",
                    spacing="3",
                    class_name="responsive-grid",
                ),
                rx.text("No hay registros presupuestarios disponibles.", class_name="muted small"),
            ),
            subtitle="Moneda de referencia en los datos de muestra.",
        ),
        page_section(
            "Expedientes destacados",
            rx.cond(
                AppState.dashboard_featured_entities,
                rx.grid(
                    rx.foreach(AppState.dashboard_featured_entities, search_example_card),
                    columns="2",
                    spacing="3",
                    class_name="responsive-grid",
                ),
                rx.text("No hay expedientes destacados disponibles.", class_name="muted small"),
            ),
            subtitle="Abre los expedientes con evidencia visible y trazabilidad.",
        ),
        page_section(
            "Casos guiados",
            rx.cond(
                AppState.dashboard_discovery_cases,
                rx.grid(
                    rx.foreach(AppState.dashboard_discovery_cases, discovery_case_card),
                    columns="2",
                    spacing="3",
                    class_name="responsive-grid",
                ),
                rx.text("No hay casos guiados disponibles.", class_name="muted small"),
            ),
            subtitle="Entradas rápidas para explorar sin saber qué buscar.",
        ),
        on_mount=AppState.load_dashboard,
        active_page=PAGE_DASHBOARD,
    )


style = {
    "body": {
        "background": "#0f0f12",
        "color": "#f4f4f5",
        "font_family": "IBM Plex Sans, Inter, Segoe UI, sans-serif",
    },
    ".shell": {"min_height": "100vh", "padding": "0 0 28px"},
    ".shell.theme-dark": {"background": "#0f0f12", "color": "#f4f4f5"},
    ".shell.theme-light": {"background": "#f4f4f5", "color": "#18181b"},
    ".shell-header": {
        "width": "100%",
        "border_bottom": "1px solid rgba(161, 161, 170, 0.18)",
        "background": "rgba(24, 24, 27, 0.88)",
        "backdrop_filter": "blur(18px)",
    },
    ".shell.theme-light .shell-header": {
        "background": "rgba(255, 255, 255, 0.88)",
        "border_bottom": "1px solid rgba(113, 113, 122, 0.18)",
    },
    ".nav-inner": {
        "max_width": "1760px",
        "margin": "0 auto",
        "width": "min(calc(100% - 48px), 1760px)",
        "padding": "16px 0",
        "gap": "16px",
    },
    ".page": {"max_width": "1760px", "margin": "0 auto", "width": "min(calc(100% - 48px), 1760px)"},
    ".brand": {"font_size": "20px", "font_weight": "800", "letter_spacing": "0.02em", "color": "#f4f4f5"},
    ".shell.theme-light .brand": {"color": "#18181b"},
    ".nav-links": {"flex_wrap": "wrap", "gap": "22px", "justify_content": "center"},
    ".nav-link": {
        "display": "inline-flex",
        "align_items": "center",
        "justify_content": "center",
        "padding": "8px 2px 10px",
        "border_bottom": "2px solid transparent",
        "background": "transparent",
        "color": "#d4d4d8",
        "font_weight": "600",
    },
    ".nav-link-active": {
        "border_bottom": "2px solid #2dd4bf",
        "color": "#f4f4f5",
    },
    ".shell.theme-light .nav-link": {
        "background": "transparent",
        "color": "#18181b",
    },
    ".shell.theme-light .nav-link-active": {
        "border_bottom": "2px solid #c084fc",
        "color": "#18181b",
    },
    ".theme-toggle": {
        "border_radius": "999px",
        "padding": "8px 14px",
        "border": "1px solid rgba(167, 139, 250, 0.25)",
        "background": "rgba(167, 139, 250, 0.16)",
        "color": "#f4f4f5",
        "font_weight": "700",
    },
    ".shell.theme-light .theme-toggle": {
        "background": "rgba(167, 139, 250, 0.12)",
        "color": "#18181b",
    },
    ".shell-alert": {"width": "min(calc(100% - 48px), 1760px)", "max_width": "1760px", "margin": "16px auto 0"},
    ".hero": {
        "border": "1px solid rgba(161, 161, 170, 0.14)",
        "border_radius": "18px",
        "padding": "28px",
        "background": "linear-gradient(180deg, rgba(31, 31, 36, 0.92), rgba(24, 24, 27, 0.92))",
    },
    ".shell.theme-light .hero": {
        "background": "linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(247, 247, 248, 0.98))",
        "border_color": "rgba(113, 113, 122, 0.18)",
    },
    ".title": {"font_size": "34px", "font_weight": "800", "line_height": "1.1"},
    ".subtitle": {"color": "#a1a1aa", "max_width": "820px", "line_height": "1.55"},
    ".shell.theme-light .subtitle": {"color": "#71717a"},
    ".section-title": {"font_size": "20px", "font_weight": "700", "margin_bottom": "12px", "color": "#f4f4f5"},
    ".shell.theme-light .section-title": {"color": "#18181b"},
    ".section-subtitle": {"color": "#a1a1aa", "margin_bottom": "14px"},
    ".shell.theme-light .section-subtitle": {"color": "#71717a"},
    ".page-section": {
        "display": "grid",
        "gap": "14px",
        "padding": "4px 0 10px",
    },
    ".card": {
        "border": "1px solid rgba(161, 161, 170, 0.16)",
        "border_radius": "16px",
        "padding": "16px",
        "background": "#18181b",
    },
    ".shell.theme-light .card": {"background": "#ffffff", "border_color": "rgba(113, 113, 122, 0.18)", "color": "#18181b"},
    ".error": {"border_color": "rgba(248, 113, 113, 0.55)"},
    ".metric-card": {
        "min_width": "160px",
        "border": "1px solid rgba(161, 161, 170, 0.18)",
        "border_radius": "16px",
        "padding": "14px",
        "background": "#1f1f24",
    },
    ".shell.theme-light .metric-card": {"background": "#ffffff", "border_color": "rgba(113, 113, 122, 0.18)"},
    ".metric-value": {"font_size": "26px", "font_weight": "800", "color": "#2dd4bf"},
    ".summary-card": {
        "min_width": "150px",
        "border": "1px solid rgba(161, 161, 170, 0.18)",
        "border_radius": "16px",
        "padding": "12px",
        "background": "#1f1f24",
        "display": "grid",
        "gap": "4px",
    },
    ".shell.theme-light .summary-card": {"background": "#ffffff", "border_color": "rgba(113, 113, 122, 0.18)"},
    ".summary-label": {"font_size": "12px", "color": "#a1a1aa", "text_transform": "uppercase", "letter_spacing": "0.04em"},
    ".shell.theme-light .summary-label": {"color": "#71717a"},
    ".summary-value": {"font_size": "22px", "font_weight": "800", "color": "#2dd4bf"},
    ".card-title": {"font_weight": "800", "font_size": "18px"},
    ".muted": {"color": "#a1a1aa"},
    ".shell.theme-light .muted": {"color": "#71717a"},
    ".small": {"font_size": "13px"},
    ".badge": {
        "display": "inline-flex",
        "border_radius": "999px",
        "padding": "4px 9px",
        "border": "1px solid rgba(45, 212, 191, 0.22)",
        "background": "rgba(45, 212, 191, 0.12)",
        "color": "#2dd4bf",
        "font_size": "13px",
        "font_weight": "700",
    },
    ".badge-teal": {"background": "rgba(45, 212, 191, 0.14)", "color": "#2dd4bf", "border_color": "rgba(45, 212, 191, 0.3)"},
    ".badge-purple": {"background": "rgba(167, 139, 250, 0.14)", "color": "#a78bfa", "border_color": "rgba(167, 139, 250, 0.3)"},
    ".badge-amber": {"background": "rgba(250, 204, 21, 0.14)", "color": "#facc15", "border_color": "rgba(250, 204, 21, 0.28)"},
    ".mini-pill": {
        "border": "1px solid rgba(45, 212, 191, 0.22)",
        "border_radius": "999px",
        "padding": "3px 8px",
        "background": "rgba(45, 212, 191, 0.1)",
        "color": "#d4d4d8",
        "font_size": "12px",
    },
    ".mini-pill-purple": {"background": "rgba(167, 139, 250, 0.12)", "border_color": "rgba(167, 139, 250, 0.24)", "color": "#e4e4e7"},
    ".story-chip": {
        "border": "1px solid rgba(167, 139, 250, 0.24)",
        "border_radius": "999px",
        "padding": "3px 8px",
        "background": "rgba(167, 139, 250, 0.12)",
        "color": "#e4e4e7",
        "font_size": "12px",
    },
    ".prompt-chip": {
        "border": "1px solid rgba(45, 212, 191, 0.22)",
        "border_radius": "999px",
        "padding": "3px 8px",
        "background": "rgba(45, 212, 191, 0.1)",
        "color": "#e4e4e7",
        "font_size": "12px",
    },
    ".comparison-chip": {
        "border": "1px solid rgba(45, 212, 191, 0.22)",
        "border_radius": "999px",
        "padding": "3px 8px",
        "background": "rgba(45, 212, 191, 0.1)",
        "color": "#d4d4d8",
        "font_size": "12px",
    },
    ".search-chip": {
        "border": "1px solid rgba(113, 113, 122, 0.2)",
        "border_radius": "999px",
        "padding": "8px 12px",
        "background": "#1f1f24",
        "color": "#f4f4f5",
    },
    ".search-chip-text": {"font_size": "13px", "font_weight": "600"},
    ".flow-card": {
        "display": "grid",
        "gap": "8px",
        "border": "1px solid rgba(161, 161, 170, 0.18)",
        "background": "#1f1f24",
    },
    ".flow-accent": {"font_size": "12px", "font_weight": "800", "letter_spacing": "0.08em"},
    ".flow-accent-teal": {"color": "#2dd4bf"},
    ".flow-accent-purple": {"color": "#a78bfa"},
    ".flow-accent-amber": {"color": "#facc15"},
    ".example-card": {"display": "grid", "gap": "8px"},
    ".prompt-card": {"display": "grid", "gap": "8px"},
    ".button": {
        "background": "#2dd4bf",
        "color": "#0b0b0f",
        "border_radius": "12px",
        "font_weight": "700",
    },
    ".button-secondary": {
        "background": "rgba(167, 139, 250, 0.14)",
        "color": "#f4f4f5",
        "border": "1px solid rgba(167, 139, 250, 0.28)",
    },
    ".shell.theme-light .button": {"color": "#18181b"},
    ".shell.theme-light .button-secondary": {"color": "#18181b"},
    ".input": {
        "background": "#18181b",
        "border": "1px solid rgba(161, 161, 170, 0.22)",
        "color": "#f4f4f5",
    },
    ".shell.theme-light .input": {
        "background": "#ffffff",
        "border_color": "rgba(113, 113, 122, 0.24)",
        "color": "#18181b",
    },
    ".search-bar": {"width": "100%", "align_items": "center"},
    ".search-input": {"min_width": "520px", "width": "100%", "font_size": "16px", "padding": "14px 16px"},
    ".search-button": {"padding": "12px 18px"},
    ".hero-actions": {"margin_top": "18px"},
    ".investigation-layout": {
        "display": "grid",
        "grid_template_columns": "minmax(0, 0.95fr) minmax(0, 1.35fr) minmax(280px, 0.8fr)",
        "gap": "16px",
        "align_items": "start",
        "width": "100%",
        "overflow": "visible",
    },
    ".investigation-shell": {"display": "grid", "gap": "14px"},
    ".story-main": {"min_width": "0"},
    ".investigation-left": {"display": "grid", "gap": "12px", "min_width": "0"},
    ".investigation-center": {"display": "grid", "gap": "12px", "min_width": "0"},
    ".investigation-sidebar": {"max_height": "none", "overflow_y": "visible", "min_width": "0"},
    ".context-panel": {"position": "static", "top": "auto", "display": "grid", "gap": "12px", "min_width": "0", "align_self": "start"},
    ".investigation-card": {"padding": "12px", "gap": "8px"},
    ".investigation-section-title": {"margin_bottom": "4px", "font_size": "18px"},
    ".investigation-subtitle": {"margin_bottom": "4px", "font_size": "13px"},
    ".timeline-accordion": {"margin_top": "6px"},
    ".story-card": {
        "border": "1px solid rgba(161, 161, 170, 0.18)",
        "border_radius": "14px",
        "padding": "10px",
        "background": "#1f1f24",
        "display": "grid",
        "gap": "6px",
    },
    ".shell.theme-light .story-card": {"background": "#ffffff", "border_color": "rgba(113, 113, 122, 0.18)"},
    ".story-title": {"font_size": "15px", "font_weight": "800"},
    ".story-headline": {"font_size": "22px", "font_weight": "800"},
    ".story-summary": {"color": "#e4e4e7", "line_height": "1.55"},
    ".story-summary-dominant": {"font_size": "15px"},
    ".narrative-item": {
        "border": "1px solid rgba(161, 161, 170, 0.12)",
        "border_radius": "14px",
        "padding": "8px",
        "background": "#1f1f24",
    },
    ".shell.theme-light .narrative-item": {"background": "#ffffff", "border_color": "rgba(113, 113, 122, 0.16)"},
    ".narrative-text": {"font_size": "13px", "color": "#e4e4e7", "line_height": "1.45"},
    ".detail-line": {
        "border_top": "1px solid rgba(161, 161, 170, 0.14)",
        "padding_top": "7px",
        "color": "#e4e4e7",
    },
    ".shell.theme-light .detail-line": {"color": "#374151", "border_top": "1px solid rgba(113, 113, 122, 0.18)"},
    ".technical-inline": {"display": "none"},
    ".technical-accordion": {"margin_top": "4px"},
    ".technical-item": {"padding": "8px"},
    ".fact-line": {"white_space": "pre-wrap", "color": "#e4e4e7", "line_height": "1.4"},
    ".context-title": {"font_weight": "800", "color": "#f4f4f5"},
    ".shell.theme-light .context-title": {"color": "#18181b"},
    ".context-item": {
        "border": "1px solid rgba(161, 161, 170, 0.18)",
        "border_radius": "14px",
        "padding": "8px",
        "display": "grid",
        "gap": "4px",
        "background": "#1f1f24",
    },
    ".shell.theme-light .context-item": {"background": "#ffffff", "border_color": "rgba(113, 113, 122, 0.18)"},
    ".context-block": {"display": "grid", "gap": "8px"},
    ".context-number": {"font_weight": "800", "color": "#2dd4bf"},
    ".mono": {"font_family": "Consolas, monospace", "font_size": "12px", "white_space": "pre-wrap"},
    ".id-line": {"color": "#a1a1aa", "overflow_wrap": "anywhere"},
    ".shell.theme-light .id-line": {"color": "#71717a"},
    ".relationship-map": {
        "border": "1px solid rgba(161, 161, 170, 0.18)",
        "border_radius": "14px",
        "padding": "12px",
        "display": "grid",
        "gap": "8px",
        "background": "#1f1f24",
        "overflow_x": "auto",
        "max_width": "100%",
    },
    ".shell.theme-light .relationship-map": {"background": "#ffffff", "border_color": "rgba(113, 113, 122, 0.18)"},
    ".map-node": {
        "border": "1px solid rgba(161, 161, 170, 0.18)",
        "border_radius": "14px",
        "padding": "8px",
        "min_width": "110px",
        "background": "#18181b",
        "display": "grid",
        "gap": "2px",
    },
    ".shell.theme-light .map-node": {"background": "#f8fafc", "border_color": "rgba(113, 113, 122, 0.18)"},
    ".map-node-title": {"font_weight": "800", "color": "#f4f4f5"},
    ".shell.theme-light .map-node-title": {"color": "#18181b"},
    ".map-arrow": {"font_size": "22px", "color": "#2dd4bf"},
    ".trace-arrow": {"font_size": "20px", "font_weight": "800", "color": "#2dd4bf"},
    ".tabs-root": {"width": "100%"},
    ".tabs-list": {"margin_bottom": "10px"},
    ".tab-content": {"padding_top": "6px"},
    ".tab-grid": {"width": "100%"},
    ".metrics-grid": {"width": "100%"},
    ".responsive-grid": {"width": "100%"},
    ".horizontal-scroll": {"overflow_x": "auto", "width": "100%"},
    ".source-trace-scroll": {"overflow_x": "auto"},
    ".source-trace-strip": {"min_width": "fit-content"},
    ".source-card": {
        "min_width": "260px",
        "max_width": "320px",
        "display": "grid",
        "gap": "6px",
        "padding": "12px",
        "background": "#1f1f24",
    },
    ".shell.theme-light .source-card": {"background": "#ffffff", "border_color": "rgba(113, 113, 122, 0.18)"},
    ".source-entity-card": {
        "min_width": "240px",
        "display": "grid",
        "gap": "6px",
        "padding": "12px",
        "align_self": "center",
        "background": "#1f1f24",
    },
    ".shell.theme-light .source-entity-card": {"background": "#ffffff", "border_color": "rgba(113, 113, 122, 0.18)"},
    ".source-title": {"font_size": "16px", "font_weight": "800"},
    ".source-fact": {"font_size": "13px", "color": "#e4e4e7", "line_height": "1.4"},
    ".shell.theme-light .source-fact": {"color": "#374151"},
    ".source-fact-list": {"display": "grid", "gap": "4px"},
    ".technical-line": {
        "font_family": "Consolas, monospace",
        "font_size": "12px",
        "color": "#a1a1aa",
        "overflow_wrap": "anywhere",
    },
    ".shell.theme-light .technical-line": {"color": "#71717a"},
    ".comparison-chip": {
        "border": "1px solid rgba(45, 212, 191, 0.22)",
        "border_radius": "999px",
        "padding": "3px 8px",
        "background": "rgba(45, 212, 191, 0.1)",
        "color": "#d4d4d8",
        "font_size": "12px",
    },
    ".flow-card": {
        "display": "grid",
        "gap": "8px",
        "min_width": "0",
    },
    ".flow-accent": {"font_size": "12px", "font_weight": "800", "letter_spacing": "0.08em"},
    ".flow-accent-teal": {"color": "#2dd4bf"},
    ".flow-accent-purple": {"color": "#a78bfa"},
    ".flow-accent-amber": {"color": "#facc15"},
    ".example-card": {"display": "grid", "gap": "8px"},
    ".prompt-card": {"display": "grid", "gap": "8px"},
    ".prompt-link": {"text_decoration": "none"},
    ".button": {
        "background": "#2dd4bf",
        "color": "#0b0b0f",
        "border_radius": "12px",
        "font_weight": "700",
    },
    ".button-secondary": {
        "background": "rgba(167, 139, 250, 0.14)",
        "color": "#f4f4f5",
        "border": "1px solid rgba(167, 139, 250, 0.28)",
    },
    ".shell.theme-light .button": {"color": "#18181b"},
    ".shell.theme-light .button-secondary": {"color": "#18181b"},
    ".input": {
        "background": "#18181b",
        "border": "1px solid rgba(161, 161, 170, 0.22)",
        "color": "#f4f4f5",
    },
    ".shell.theme-light .input": {
        "background": "#ffffff",
        "border_color": "rgba(113, 113, 122, 0.24)",
        "color": "#18181b",
    },
    ".search-bar": {"width": "100%", "align_items": "center", "gap": "12px"},
    ".search-input": {
        "min_width": "0",
        "flex": "1 1 auto",
        "width": "100%",
        "font_size": "16px",
        "padding": "14px 16px",
        "height": "52px",
    },
    ".search-input::placeholder": {"color": "#71717a"},
    ".search-input:focus": {
        "border_color": "#2dd4bf",
        "box_shadow": "0 0 0 3px rgba(45, 212, 191, 0.18)",
    },
    ".search-button": {"padding": "14px 18px", "height": "52px"},
    ".search-result-card": {"min_height": "200px"},
    ".discovery-card": {"min_height": "220px"},
    ".explorer-panel": {
        "border": "1px solid rgba(161, 161, 170, 0.16)",
        "border_radius": "16px",
        "padding": "16px",
        "background": "#18181b",
        "display": "grid",
        "gap": "12px",
    },
    ".shell.theme-light .explorer-panel": {"background": "#ffffff", "border_color": "rgba(113, 113, 122, 0.18)"},
    ".explorer-category-button": {
        "border": "1px solid rgba(113, 113, 122, 0.22)",
        "background": "#1f1f24",
        "color": "#f4f4f5",
        "padding": "8px 12px",
        "height": "40px",
        "font_weight": "700",
    },
    ".explorer-category-button-active": {
        "border_color": "#a78bfa",
        "background": "rgba(167, 139, 250, 0.16)",
        "color": "#f4f4f5",
        "box_shadow": "0 0 0 1px rgba(167, 139, 250, 0.18)",
    },
    ".shell.theme-light .explorer-category-button": {"background": "#ffffff", "color": "#18181b"},
    ".shell.theme-light .explorer-category-button-active": {"background": "rgba(167, 139, 250, 0.12)", "color": "#18181b"},
    ".search-chip": {
        "border": "1px solid rgba(113, 113, 122, 0.2)",
        "border_radius": "999px",
        "padding": "8px 12px",
        "background": "#1f1f24",
        "color": "#f4f4f5",
    },
    ".search-chip-text": {"font_size": "13px", "font_weight": "600"},
    ".shell.theme-light .search-chip": {"background": "#ffffff"},
    ".shell.theme-light .search-chip-text": {"color": "#18181b"},
    ".shell.theme-light .badge": {"background": "rgba(45, 212, 191, 0.12)", "color": "#0f766e", "border_color": "rgba(45, 212, 191, 0.24)"},
    ".shell.theme-light .badge-teal": {"background": "rgba(45, 212, 191, 0.12)", "color": "#0f766e", "border_color": "rgba(45, 212, 191, 0.24)"},
    ".shell.theme-light .badge-purple": {"background": "rgba(167, 139, 250, 0.12)", "color": "#6d28d9", "border_color": "rgba(167, 139, 250, 0.24)"},
    ".shell.theme-light .badge-amber": {"background": "rgba(250, 204, 21, 0.12)", "color": "#b45309", "border_color": "rgba(250, 204, 21, 0.24)"},
    ".shell.theme-light .mini-pill": {"background": "rgba(45, 212, 191, 0.08)", "color": "#0f766e", "border_color": "rgba(45, 212, 191, 0.18)"},
    ".shell.theme-light .mini-pill-purple": {"background": "rgba(167, 139, 250, 0.08)", "color": "#6d28d9", "border_color": "rgba(167, 139, 250, 0.18)"},
    ".shell.theme-light .story-chip": {"background": "rgba(167, 139, 250, 0.08)", "color": "#6d28d9", "border_color": "rgba(167, 139, 250, 0.18)"},
    ".shell.theme-light .prompt-chip": {"background": "rgba(45, 212, 191, 0.08)", "color": "#0f766e", "border_color": "rgba(45, 212, 191, 0.18)"},
    ".shell.theme-light .comparison-chip": {"background": "rgba(45, 212, 191, 0.08)", "color": "#0f766e", "border_color": "rgba(45, 212, 191, 0.18)"},
    ".shell.theme-light .flow-card": {"background": "#ffffff", "border_color": "rgba(113, 113, 122, 0.18)"},
    ".shell.theme-light .flow-accent-teal": {"color": "#0f766e"},
    ".shell.theme-light .flow-accent-purple": {"color": "#6d28d9"},
    ".shell.theme-light .flow-accent-amber": {"color": "#b45309"},
    ".empty-entry-card": {"min_height": "220px", "display": "grid", "gap": "10px", "align_content": "start"},
    ".empty-entry-card .example-card": {"padding": "10px", "min_height": "auto"},
    ".investigation-empty-grid": {"align_items": "stretch"},
    ".home-lower-layout": {
        "display": "grid",
        "grid_template_columns": "minmax(0, 1.35fr) minmax(340px, 0.85fr)",
        "gap": "24px",
        "align_items": "start",
    },
    ".home-lower-layout .page-section": {
        "min_width": "0",
    },
    "@media (max-width: 900px)": {
        ".nav-inner": {"flex_wrap": "wrap"},
        ".nav-links": {"justify_content": "flex-start"},
        ".investigation-layout": {"grid_template_columns": "1fr"},
        ".context-panel": {"position": "static"},
        ".investigation-sidebar": {"max_height": "none"},
        ".search-input": {"min_width": "0"},
        ".search-bar": {"flex_direction": "column", "align_items": "stretch"},
        ".search-button": {"width": "100%"},
        ".home-lower-layout": {"grid_template_columns": "1fr"},
    },
}


app = rx.App(style=style)
