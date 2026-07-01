from __future__ import annotations

import os
from dataclasses import fields, is_dataclass
from datetime import date, datetime
from types import MappingProxyType
from uuid import UUID
from urllib.parse import parse_qs, quote_plus, urlparse

import reflex as rx

from datosenorden.web.app_services import get_cross_dataset_connections
from datosenorden.web.app_services import export_citizen_report_demo
from datosenorden.web.app_services import get_citizen_dashboard
from datosenorden.web.app_services import get_citizen_report_demo
from datosenorden.web.app_services import get_citizen_reports
from datosenorden.web.app_services import get_dataset_summary
from datosenorden.web.app_services import get_demo_status
from datosenorden.web.app_services import get_tracking_demo
from datosenorden.web.app_services import get_tracking_items
from datosenorden.web.app_services import get_knowledge_demo
from datosenorden.web.app_services import get_knowledge_documents
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
PAGE_TRACKING = "tracking"
PAGE_KNOWLEDGE = "knowledge"
PAGE_LIBRARY = "library"
PAGE_REPORTS = "reports"
PAGE_DASHBOARD = "dashboard"
PAGE_DEMO = "demo"
PAGE_PROJECT = "project"
INVESTIGATION_STATUS_IDLE = "idle"
INVESTIGATION_STATUS_LOADING = "loading"
INVESTIGATION_STATUS_LOADED = "loaded"
INVESTIGATION_STATUS_ERROR = "error"
INVESTIGATION_STATUS_EMPTY = "empty"
DEMO_INVESTIGATION_TARGET = "SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO"
DEMO_INVESTIGATION_URL = f"http://localhost:3000/investigation?id={quote_plus(DEMO_INVESTIGATION_TARGET)}"
SOURCE_COVERAGE_TEMPLATE = [
    {"source": "ChileCompra", "status": "activo con datos", "contribution": "Compras publicas, proveedores, contratos y evidencia de adquisiciones."},
    {"source": "DIPRES", "status": "prototipo con datos", "contribution": "Presupuestos, anos fiscales y contexto de gasto publico."},
    {"source": "Lobby", "status": "prototipo con datos", "contribution": "Reuniones, contrapartes, materias declaradas y fechas."},
    {"source": "Transparencia Activa", "status": "prototipo con datos", "contribution": "Cargos, roles administrativos y periodos asociados."},
    {"source": "Contraloria", "status": "prototipo con datos", "contribution": "Informes y observaciones para trazabilidad documental."},
    {"source": "Diario Oficial", "status": "prototipo con datos", "contribution": "Publicaciones oficiales y actos administrativos publicados."},
    {"source": "Registro Empresas", "status": "prototipo con datos", "contribution": "Empresas, representantes y relaciones societarias locales."},
    {"source": "Declaraciones de Intereses", "status": "prototipo con datos", "contribution": "Declaraciones, intereses declarados y posibles entidades mencionadas."},
    {"source": "SERVEL", "status": "prototipo con datos", "contribution": "Autoridades electas y periodos electorales de muestra."},
    {"source": "Municipalidades", "status": "prototipo con datos", "contribution": "Contexto municipal y proyectos locales de muestra."},
    {"source": "Sanciones y Procedimientos", "status": "prototipo sin datos", "contribution": "Procedimientos y resoluciones administrativas de prueba cuando exista carga local."},
]
INVESTIGATION_TOPICS = [
    {"label": "Organismos publicos", "example": "SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO"},
    {"label": "Empresas proveedoras", "example": "Consultora Publica SpA"},
    {"label": "Personas", "example": "Autoridades y representantes en registros locales"},
    {"label": "Autoridades", "example": "Cargos publicos y periodos declarados"},
    {"label": "Presupuestos", "example": "DIPRES budget 2026 Servicio de Salud Arauco"},
    {"label": "Contratos", "example": "Ordenes de compra y contratos ChileCompra"},
    {"label": "Reuniones de Lobby", "example": "Reuniones registradas con contraparte y materia"},
    {"label": "Informes de Contraloria", "example": "Informes y observaciones de muestra"},
    {"label": "Publicaciones del Diario Oficial", "example": "Publicaciones oficiales del caso demo"},
    {"label": "Declaraciones de intereses", "example": "Declaraciones locales de ejemplo"},
    {"label": "Sanciones y procedimientos", "example": "Procedimientos y resoluciones administrativas de prueba"},
]


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
            "trust_label": _evidence_trust_label(_clean(_field(row, "dataset"), "ChileCompra")),
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
            "trust_label": _evidence_trust_label(_clean(_field(row, "dataset"), "Lobby")),
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
            "trust_label": _evidence_trust_label(_clean(_field(row, "dataset"), "Transparencia")),
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
                "trust_label": _evidence_trust_label(_clean(_field(row, "dataset"), "Registro Empresas")),
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
                    "trust_label": "Registro local de demo",
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
                "facts_text": f"Entidad: {_clean(_field(neighbor, 'name'), 'Entidad conectada')}",
                "technical_text": f"relationship_type={_clean(_field(row, 'relationship_type'))}",
                "detail_text": "\n".join([
                    f"Tipo de entidad: {_human_label(_field(neighbor, 'entity_type'))}",
                    f"Dirección: {_human_label(_field(row, 'direction'))}",
                ]),
                "trust_label": "Registro local de demo",
            }
        )
    return formatted

def _field(obj: object, name: str, fallback: object = None) -> object:
    return _safe_field(obj, name, fallback)


def to_json_safe(value: object) -> object:
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, UUID | date | datetime):
        return str(value)
    if is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: to_json_safe(getattr(value, field.name, None))
            for field in fields(value)
        }
    if isinstance(value, MappingProxyType):
        return to_json_safe(dict(value))
    if hasattr(value, "model_dump"):
        try:
            return to_json_safe(value.model_dump())
        except Exception:  # noqa: BLE001
            return str(value)
    if isinstance(value, dict):
        return {str(to_json_safe(key)): to_json_safe(item) for key, item in value.items()}
    if isinstance(value, tuple | list | set | frozenset):
        return [to_json_safe(item) for item in value]
    if hasattr(value, "__dict__"):
        safe_fields = {
            key: item
            for key, item in vars(value).items()
            if not key.startswith("_") and not callable(item)
        }
        if safe_fields:
            return to_json_safe(safe_fields)
    return str(value)


def _json_dict(value: object) -> dict:
    safe = to_json_safe(value)
    return safe if isinstance(safe, dict) else {}


def _json_list(value: object) -> list:
    safe = to_json_safe(value)
    return safe if isinstance(safe, list) else []


def _display_label(value: object) -> str:
    labels = {
        "PUBLIC_ORGANIZATION": "Organismo publico",
        "MUNICIPALITY": "Municipalidad",
        "PERSON": "Persona",
        "ROLE": "Cargo publico",
        "COMPANY": "Empresa",
        "SUPPLIER": "Proveedor",
        "CONTRACT": "Compra publica",
        "TENDER": "Licitacion",
        "BUDGET": "Presupuesto",
        "LOBBY_MEETING": "Reunion registrada",
        "CONTROL_REPORT": "Informe de control",
        "PUBLIC_OBSERVATION": "Observacion publica",
        "PUBLIC_PROJECT": "Proyecto publico",
        "SPENDING_ITEM": "Gasto publico",
        "ELECTORAL_PERIOD": "Periodo electoral",
        "ADMINISTRATIVE_PROCEDURE": "Procedimiento administrativo",
        "ADMINISTRATIVE_RESOLUTION": "Resolucion administrativa",
        "ISSUES_PURCHASE_ORDER": "Compra publica emitida",
        "ORGANIZATION_HELD_LOBBY_MEETING": "Reunion registrada",
        "ORGANIZATION_HAS_PUBLIC_ROLE": "Autoridad publica registrada",
        "ROLE_BELONGS_TO_ORGANIZATION": "Cargo asociado al organismo",
        "PERSON_HOLDS_PUBLIC_ROLE": "Persona con cargo publico",
        "PERSON_REPRESENTS_COMPANY": "Representacion de empresa",
        "PERSON_OWNS_COMPANY": "Participacion en empresa",
        "BUDGET_ALLOCATED_TO": "Presupuesto asignado",
        "AWARDS_CONTRACT": "Contrato adjudicado",
        "RECEIVES_CONTRACT": "Contrato recibido",
    }
    return labels.get(_clean(value), _human_label(value))


def _source_sentence(source: str) -> str:
    source_name = _clean(source, "Fuente local")
    return f"Fuente: {source_name}."


def _why_sentence(kind: str) -> str:
    mapping = {
        "Compra publica": "Ayuda a ver como se conectan compras, organismos y proveedores.",
        "Lobby": "Ayuda a ubicar reuniones registradas junto a otras fuentes del expediente.",
        "Rol publico": "Ayuda a entender que personas o cargos aparecen asociados.",
        "Evidencia": "Permite revisar el respaldo local de los registros mostrados.",
        "Registro": "Conecta empresas, representantes y antecedentes societarios de muestra.",
    }
    return mapping.get(kind, "Ayuda a entender por que esta entidad aparece en el expediente.")


def _accent_badge_class(status: str) -> str:
    accents = {
        "active": "badge badge-teal",
        "prototype": "badge badge-purple",
        "planned": "badge badge-amber",
        "covered": "badge badge-teal",
        "partial": "badge badge-purple",
        "future": "badge badge-amber",
        "activo con datos": "badge badge-teal",
        "prototipo con datos": "badge badge-purple",
        "prototipo sin datos": "badge badge-amber",
        "planificado": "badge badge-amber",
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
        "ADMINISTRATIVE_PROCEDURE": "badge badge-amber",
        "ADMINISTRATIVE_RESOLUTION": "badge badge-amber",
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


def _investigation_href(target: str) -> str:
    cleaned = str(target or "").strip()
    if not cleaned:
        return "/investigation"
    return f"/investigation?id={quote_plus(cleaned)}"


def _router_query_value(router: object, key: str) -> str:
    url = _shallow_getattr(router, "url", None)
    session = _shallow_getattr(router, "session", None)
    candidates = [router, url, session]

    for candidate in candidates:
        for attr in ("query_parameters", "query_params", "params", "query"):
            value = _query_value_from_mapping(_shallow_getattr(candidate, attr, {}), key)
            if value:
                return value

    for candidate in candidates:
        for attr in ("full_path", "raw_path", "path", "as_path", "url", "href", "route", "pathname", "search", "query_string"):
            value = _query_value_from_text(_shallow_getattr(candidate, attr, ""), key)
            if value:
                return value

    for candidate in candidates:
        for value in _safe_public_values(candidate):
            mapped = _query_value_from_mapping(value, key)
            if mapped:
                return mapped
            parsed = _query_value_from_text(value, key)
            if parsed:
                return parsed
    return ""


def _shallow_getattr(obj: object, key: str, fallback: object = None) -> object:
    if obj is None:
        return fallback
    if isinstance(obj, dict):
        return obj.get(key, fallback)
    try:
        return getattr(obj, key, fallback)
    except Exception:  # noqa: BLE001
        return fallback


def _query_value_from_mapping(value: object, key: str) -> str:
    if not hasattr(value, "get"):
        return ""
    try:
        raw = value.get(key, "")
    except Exception:  # noqa: BLE001
        return ""
    if isinstance(raw, list | tuple):
        raw = raw[0] if raw else ""
    return str(raw).strip() if raw else ""


def _query_value_from_text(raw: object, key: str) -> str:
    if not isinstance(raw, str) or key not in raw:
        return ""
    query = raw[1:] if raw.startswith("?") else raw
    parsed = urlparse(query)
    query = parsed.query or (query.split("?", 1)[1] if "?" in query else query)
    values = parse_qs(query)
    if values.get(key):
        return str(values[key][0]).strip()
    return ""


def _safe_public_values(obj: object) -> list[object]:
    if obj is None:
        return []
    if isinstance(obj, dict):
        return list(obj.values())
    try:
        fields = vars(obj)
    except Exception:  # noqa: BLE001
        return []
    return [
        value
        for name, value in fields.items()
        if not str(name).startswith("_") and isinstance(value, str | dict | list | tuple)
    ]


def page_section(title: str, *children, subtitle: str | None = None, class_name: str = "") -> rx.Component:
    body = [rx.text(title, class_name="section-title")]
    if subtitle is not None:
        body.append(rx.text(subtitle, class_name="section-subtitle"))
    body.extend(children)
    section_class = "page-section" if not class_name else f"page-section {class_name}"
    return rx.vstack(*body, spacing="3", align="stretch", class_name=section_class)


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
    self.source_coverage_rows = []
    self.relationship_journey_rows = []
    self.related_entity_group_rows = []
    self.report_path = ""
    self.citizen_summary = ""
    self.canonical_investigation_link = ""
    self.investigation_status_message = ""
    self.investigation_status = INVESTIGATION_STATUS_IDLE
    self.requested_investigation_target = ""
    self.last_loaded_investigation_target = ""
    self.last_valid_investigation_target = ""
    self.investigation_loaded = False
    self.investigation_loading = False


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
                    "trust_label": _evidence_trust_label(dataset),
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
                "technical_text": f"claim_id={_clean(_field(row, 'claim_id'))}",
                "trust_label": _evidence_trust_label(_clean(_field(row, "dataset"), "Fuente")),
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


def _build_relationship_journey_rows(
    *,
    entity_name: str,
    procurement: list[dict],
    registry: list[dict],
    lobby: list[dict],
    transparency: list[dict],
    timeline: list[dict],
    evidence: list[dict],
) -> list[dict]:
    candidates = [
        *procurement[:2],
        *registry[:2],
        *lobby[:2],
        *transparency[:2],
        *timeline[:2],
        *evidence[:2],
    ]
    rows: list[dict] = []
    for index, row in enumerate(candidates, start=1):
        kind = _clean(_field(row, "relationship_type"), "Registro publico")
        source = _clean(_field(row, "dataset"), "Fuente local")
        title = _clean(_field(row, "title"), f"Paso {index}")
        explanation = _clean(_field(row, "explanation"), "Registro local asociado al expediente.")
        rows.append(
            {
                "step": str(index),
                "title": title,
                "source": source,
                "kind": kind,
                "body": explanation,
                "why": _why_sentence(kind),
                "entity": entity_name,
                "source_sentence": _source_sentence(source),
                "evidence_label": _evidence_trust_label(source),
            }
        )
    return rows


def _evidence_trust_label(source: str) -> str:
    normalized = _clean(source, "").lower()
    if "demo" in normalized or "local" in normalized:
        return "Registro local de demo"
    if any(token in normalized for token in ("chilecompra", "dipres", "lobby", "contraloria", "diario", "transparencia")):
        return "Fuente publica"
    if normalized:
        return "Prototipo local"
    return "No oficial / dato de prueba"


def _build_source_coverage_rows(source_rows: list[dict]) -> list[dict]:
    by_name = {str(_field(row, "dataset", "")).lower(): row for row in source_rows}
    coverage: list[dict] = []
    for template in SOURCE_COVERAGE_TEMPLATE:
        source_name = template["source"]
        loaded = next((row for key, row in by_name.items() if source_name.lower() in key or key in source_name.lower()), {})
        evidence = int(_field(loaded, "evidence_count", 0) or 0)
        relationships = int(_field(loaded, "relationship_count", 0) or 0)
        status = template["status"]
        if evidence or relationships:
            status = "activo con datos" if source_name == "ChileCompra" else "prototipo con datos"
        coverage.append(
            {
                "source": source_name,
                "status": status,
                "contribution": str(_field(loaded, "summary", "") or template["contribution"]),
                "evidence_count": evidence,
                "relationship_count": relationships,
                "trust_label": _evidence_trust_label(source_name),
            }
        )
    return coverage


def _citizen_summary_text(entity_name: str, sources: int, evidence: int, relationships: int, connected: int, dataset_badges: list[str]) -> str:
    source_text = ", ".join(dataset_badges[:6]) if dataset_badges else "fuentes locales de demostracion"
    return (
        f"Este expediente reune {sources} fuentes publicas, {evidence} evidencias, "
        f"{relationships} relaciones y {connected} entidades conectadas sobre {entity_name}. "
        f"Las fuentes visibles incluyen {source_text}. Aportan registros de compras, presupuesto, roles, "
        "reuniones, publicaciones y documentos de respaldo segun la carga local disponible. "
        "Los cruces muestran coincidencias y relaciones documentadas entre entidades y registros; "
        "no implican causalidad, irregularidad ni responsabilidad."
    )


def _debug_investigation(message: str, **values: object) -> None:
    if not os.environ.get("DATOSENORDEN_DEBUG_INVESTIGATION"):
        return
    detail = " ".join(f"{key}={value!r}" for key, value in values.items())
    print(f"[DatosEnOrden investigation] {message} {detail}".rstrip(), flush=True)


def _build_related_entity_group_rows(relationships: list[dict], registry: list[dict], lobby: list[dict], procurement: list[dict]) -> list[dict]:
    groups: dict[str, list[dict]] = {
        "Organismos": [],
        "Empresas y proveedores": [],
        "Personas y autoridades": [],
        "Reuniones y registros": [],
        "Compras y presupuestos": [],
    }
    for row in relationships:
        entity_type = _clean(_field(row, "relationship_type"), "Entidad")
        item = {
            "title": _clean(_field(row, "title"), "Entidad relacionada"),
            "type": _display_label(entity_type),
            "why": _clean(_field(row, "explanation"), "Aparece por una relacion publica registrada."),
            "source": _clean(_field(row, "dataset"), "Grafo local"),
        }
        label = item["type"].lower()
        if "empresa" in label or "proveedor" in label:
            groups["Empresas y proveedores"].append(item)
        elif "persona" in label or "cargo" in label or "autoridad" in label:
            groups["Personas y autoridades"].append(item)
        elif "compra" in label or "presupuesto" in label or "contrato" in label:
            groups["Compras y presupuestos"].append(item)
        elif "reunion" in label:
            groups["Reuniones y registros"].append(item)
        else:
            groups["Organismos"].append(item)
    for row in registry[:4]:
        groups["Empresas y proveedores"].append(
            {
                "title": _clean(_field(row, "title"), "Empresa relacionada"),
                "type": "Registro de empresa",
                "why": _clean(_field(row, "facts_text"), "Aparece en registros societarios locales."),
                "source": _clean(_field(row, "dataset"), "Registro Empresas"),
            }
        )
    for row in lobby[:3]:
        groups["Reuniones y registros"].append(
            {
                "title": _clean(_field(row, "title"), "Reunion registrada"),
                "type": "Lobby",
                "why": _clean(_field(row, "facts_text"), "Aparece por una reunion registrada localmente."),
                "source": _clean(_field(row, "dataset"), "Lobby"),
            }
        )
    for row in procurement[:3]:
        groups["Compras y presupuestos"].append(
            {
                "title": _clean(_field(row, "title"), "Compra publica"),
                "type": "Compra publica",
                "why": _clean(_field(row, "facts_text"), "Aparece por una compra publica local."),
                "source": _clean(_field(row, "dataset"), "ChileCompra"),
            }
        )
    flattened: list[dict] = []
    for group, items in groups.items():
        for item in items[:4]:
            flattened.append({**item, "group": group})
    return flattened


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


def _state_has_investigation_data(state: object) -> bool:
    return bool(str(_field(state, "entity_name", "")).strip()) or any(
        int(_field(state, key, 0) or 0) > 0
        for key in ("datasets_involved", "evidence_count", "relationship_count", "connected_entities")
    )


def _investigation_response_has_data(data: dict) -> bool:
    if not bool(data.get("found", False)):
        return False
    metrics = data.get("key_metrics", {})
    compact_metrics = data.get("compact_metrics", {})
    entity_name = str(_field(_field(data, "entity", {}), "name", "")).strip()
    numeric_values = (
        int(_field(compact_metrics, "datasets_involved", 0) or 0),
        int(_field(compact_metrics, "evidence_count", 0) or 0),
        int(_field(compact_metrics, "relationship_count", 0) or 0),
        int(_field(metrics, "evidence", 0) or 0),
        int(_field(metrics, "relationships", 0) or 0),
    )
    return bool(entity_name) or any(value > 0 for value in numeric_values)


class AppState(rx.State):
    query: str = ""
    results: list[dict] = []
    workspace_matches: list[dict] = []
    guided_search_title: str = ""
    selected_entity_id: str = ""
    selected_entity_name: str = ""
    error_message: str = ""
    theme_dark: bool = True
    header_search_open: bool = False
    header_search_query: str = ""

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
    selected_guided_category_path: str = ""
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
    source_coverage_rows: list[dict] = []
    relationship_journey_rows: list[dict] = []
    related_entity_group_rows: list[dict] = []
    report_path: str = ""
    citizen_summary: str = ""
    canonical_investigation_link: str = DEMO_INVESTIGATION_URL
    demo_sources_ready: bool = False
    demo_investigation_ready: bool = False
    demo_report_ready: bool = False
    demo_report_path: str = ""
    citizen_reports: list[dict] = []
    citizen_report: dict = {}
    citizen_report_title: str = ""
    citizen_report_summary: str = ""
    citizen_report_subject: str = DEMO_INVESTIGATION_TARGET
    citizen_report_status: str = ""
    citizen_report_sources: list[str] = []
    citizen_report_sections: list[dict] = []
    citizen_report_evidence_refs: list[str] = []
    citizen_report_path: str = ""
    citizen_report_error: str = ""
    tracking_items: list[dict] = []
    tracking_item: dict = {}
    tracking_title: str = ""
    tracking_summary: str = ""
    tracking_current_status: str = ""
    tracking_expediente_target: str = DEMO_INVESTIGATION_TARGET
    tracking_events: list[dict] = []
    tracking_documents: list[dict] = []
    tracking_evidence: list[dict] = []
    tracking_follow_targets: list[dict] = []
    tracking_related_sources: list[str] = []
    tracking_status_label: str = ""
    tracking_error: str = ""
    knowledge_documents: list[dict] = []
    knowledge_document: dict = {}
    knowledge_title: str = ""
    knowledge_summary: str = ""
    knowledge_key_points: list[dict] = []
    knowledge_questions: list[dict] = []
    knowledge_claims: list[dict] = []
    knowledge_evidence: list[dict] = []
    knowledge_connections: list[dict] = []
    knowledge_notice: str = ""
    knowledge_expediente_target: str = DEMO_INVESTIGATION_TARGET
    knowledge_error: str = ""
    investigation_status_message: str = ""
    investigation_status: str = INVESTIGATION_STATUS_IDLE
    requested_investigation_target: str = ""
    last_loaded_investigation_target: str = ""
    last_valid_investigation_target: str = ""
    investigation_loaded: bool = False
    investigation_loading: bool = False

    def toggle_theme(self) -> None:
        self.theme_dark = not self.theme_dark

    def toggle_header_search(self) -> None:
        self.header_search_open = not self.header_search_open

    def set_header_search_query(self, value: str) -> None:
        self.header_search_query = value

    def submit_header_search(self):
        query = str(self.header_search_query or self.query or "").strip()
        self.query = query
        return rx.redirect(_search_href(query))

    def submit_main_search(self):
        query = str(self.query or self.header_search_query or "").strip()
        self.query = query
        return rx.redirect(_search_href(query))

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
                    "path_text": "Este recorrido conectara: "
                    + " -> ".join(str(item) for item in row.get("concepts", [])[:6]),
                    "search_href": _search_href(str(row.get("search_query", row.get("example_query", "")))),
                }
                for row in guided_questions.get("questions", [])
            ]
            self.guided_category_rows = [
                {
                    **row,
                    "examples_text": " | ".join(str(item) for item in row.get("examples", [])),
                    "sources_text": " | ".join(str(item) for item in row.get("suggested_sources", [])),
                    "path_text": "Fuentes sugeridas: "
                    + " | ".join(str(item) for item in row.get("suggested_sources", [])),
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
            self.selected_guided_category_path = str(first.get("path_text", ""))
            self.guided_option_rows = _format_guided_options(get_guided_discovery_options(first_id))

    def load_search(self) -> None:
        self.error_message = ""
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
        self.selected_guided_category_path = ""
        self.guided_option_rows = []
        query_value = _router_query_value(self.router, "q")
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
        self.selected_guided_category_path = "Este recorrido mostrara opciones locales antes de abrir el expediente."
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
        self.selected_guided_category_path = str(match.get("path_text", ""))
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

    def load_demo(self) -> None:
        self.error_message = ""
        self.demo_sources_ready = False
        self.demo_investigation_ready = False
        self.demo_report_ready = False
        self.demo_report_path = ""
        try:
            summary = get_dataset_summary()
            totals = _field(summary, "totals", {})
            self.demo_sources_ready = int(_field(totals, "datasets", 0) or 0) > 0 and int(_field(totals, "source_records", 0) or 0) > 0
            investigation = _json_dict(get_investigation(DEMO_INVESTIGATION_TARGET))
            metrics = _field(investigation, "compact_metrics", {})
            self.demo_investigation_ready = bool(_field(investigation, "found", False)) and int(_field(metrics, "evidence_count", 0) or 0) > 0
            resolved = _json_dict(resolve_investigation_target(DEMO_INVESTIGATION_TARGET))
            entity_id = str(_field(resolved, "entity_id", ""))
            if entity_id:
                self.demo_report_path = export_investigation_report(entity_id)
                self.demo_report_ready = bool(self.demo_report_path)
        except Exception as exc:  # noqa: BLE001
            self.error_message = f"{type(exc).__name__}: {exc}"

    def load_tracking(self) -> None:
        self.error_message = ""
        self.tracking_error = ""
        try:
            items = _json_list(get_tracking_items())
            demo = _json_dict(get_tracking_demo())
            item = _json_dict(demo.get("item", {}))
            self.tracking_items = items
            self.tracking_item = item
            self.tracking_title = str(_field(item, "title", ""))
            self.tracking_summary = str(_field(item, "summary", ""))
            self.tracking_current_status = str(_field(item, "current_status", "unknown"))
            self.tracking_expediente_target = str(_field(item, "related_expediente_target", DEMO_INVESTIGATION_TARGET))
            self.tracking_events = _json_list(demo.get("events", []))
            self.tracking_documents = _json_list(demo.get("documents", []))
            self.tracking_evidence = _json_list(demo.get("evidence", []))
            self.tracking_follow_targets = _json_list(demo.get("follow_targets", []))
            self.tracking_related_sources = [str(source) for source in _field(item, "related_sources", [])]
            self.tracking_status_label = _display_label(str(_field(item, "current_status", "unknown")).upper())
        except Exception as exc:  # noqa: BLE001
            self.tracking_items = []
            self.tracking_item = {}
            self.tracking_title = ""
            self.tracking_summary = ""
            self.tracking_current_status = ""
            self.tracking_expediente_target = DEMO_INVESTIGATION_TARGET
            self.tracking_events = []
            self.tracking_documents = []
            self.tracking_evidence = []
            self.tracking_follow_targets = []
            self.tracking_related_sources = []
            self.tracking_status_label = ""
            self.tracking_error = f"{type(exc).__name__}: {exc}"
            self.error_message = self.tracking_error

    def load_knowledge(self) -> None:
        self.error_message = ""
        self.knowledge_error = ""
        try:
            documents = _json_list(get_knowledge_documents())
            demo = _json_dict(get_knowledge_demo())
            document = _json_dict(demo.get("document", {}))
            self.knowledge_documents = documents
            self.knowledge_document = document
            self.knowledge_title = str(_field(document, "title", ""))
            self.knowledge_summary = str(_field(demo, "citizen_summary", ""))
            self.knowledge_key_points = _json_list(demo.get("key_points", []))
            self.knowledge_questions = _json_list(demo.get("citizen_questions", []))
            self.knowledge_claims = [
                {
                    **dict(row),
                    "evidence_text": " | ".join(str(ref) for ref in row.get("evidence_ids", [])),
                }
                for row in _json_list(demo.get("claims", []))
            ]
            self.knowledge_evidence = _json_list(demo.get("evidence", []))
            self.knowledge_connections = [
                {"label": str(key), "value": str(value)}
                for key, value in _json_dict(demo.get("connections", {})).items()
            ]
            self.knowledge_notice = str(_field(demo, "notice", ""))
            self.knowledge_expediente_target = str(_field(document, "related_expediente_target", DEMO_INVESTIGATION_TARGET))
        except Exception as exc:  # noqa: BLE001
            self.knowledge_documents = []
            self.knowledge_document = {}
            self.knowledge_title = ""
            self.knowledge_summary = ""
            self.knowledge_key_points = []
            self.knowledge_questions = []
            self.knowledge_claims = []
            self.knowledge_evidence = []
            self.knowledge_connections = []
            self.knowledge_notice = ""
            self.knowledge_expediente_target = DEMO_INVESTIGATION_TARGET
            self.knowledge_error = f"{type(exc).__name__}: {exc}"
            self.error_message = self.knowledge_error

    def load_reports(self) -> None:
        self.error_message = ""
        self.citizen_report_error = ""
        try:
            reports = _json_list(get_citizen_reports())
            demo = _json_dict(get_citizen_report_demo())
            self.citizen_reports = reports
            self.citizen_report = demo
            self.citizen_report_title = str(_field(demo, "title", ""))
            self.citizen_report_summary = str(_field(demo, "summary", ""))
            self.citizen_report_subject = str(_field(demo, "subject", DEMO_INVESTIGATION_TARGET))
            self.citizen_report_status = str(_field(demo, "current_status", "demo_read_only"))
            self.citizen_report_sources = [str(source) for source in _field(demo, "sources", [])]
            self.citizen_report_sections = [
                {
                    **dict(row),
                    "evidence_text": " | ".join(str(ref) for ref in row.get("evidence_refs", [])),
                }
                for row in _json_list(_field(demo, "sections", []))
            ]
            self.citizen_report_evidence_refs = [str(ref) for ref in _field(demo, "evidence_refs", [])]
            self.citizen_report_path = export_citizen_report_demo()
        except Exception as exc:  # noqa: BLE001
            self.citizen_reports = []
            self.citizen_report = {}
            self.citizen_report_title = ""
            self.citizen_report_summary = ""
            self.citizen_report_subject = DEMO_INVESTIGATION_TARGET
            self.citizen_report_status = ""
            self.citizen_report_sources = []
            self.citizen_report_sections = []
            self.citizen_report_evidence_refs = []
            self.citizen_report_path = ""
            self.citizen_report_error = f"{type(exc).__name__}: {exc}"
            self.error_message = self.citizen_report_error


    def select_result(self, entity_id: str):
        match = next((row for row in self.results if row.get("id") == entity_id), {})
        target = str(match.get("canonical_entity_id", entity_id))
        name = str(match.get("canonical_entity_name", match.get("name", "")))
        return self.open_canonical_investigation(target or name)

    def open_investigation(self, entity_id: str, entity_name: str):
        return self.open_canonical_investigation(entity_id or entity_name)

    def open_tracking_investigation(self):
        return rx.redirect(_investigation_href(self.tracking_expediente_target or DEMO_INVESTIGATION_TARGET))

    def open_knowledge_investigation(self):
        return rx.redirect(_investigation_href(self.knowledge_expediente_target or DEMO_INVESTIGATION_TARGET))

    def open_report_investigation(self):
        return rx.redirect(_investigation_href(self.citizen_report_subject or DEMO_INVESTIGATION_TARGET))

    def open_canonical_investigation(self, target: str):
        canonical = _json_dict(resolve_canonical_expediente_target(target))
        self.selected_entity_id = str(canonical.get("canonical_entity_id", target))
        self.selected_entity_name = str(canonical.get("canonical_entity_name", target))
        stable_target = self.selected_entity_id or self.selected_entity_name or target
        self.last_valid_investigation_target = stable_target
        _debug_investigation("open canonical", received=target, resolved=stable_target)
        return rx.redirect(_investigation_href(stable_target))

    def load_investigation(self) -> None:
        self.error_message = ""
        query_id = _router_query_value(self.router, "id")
        target = query_id
        had_valid_state = bool(_field(self, "investigation_loaded", False)) and _state_has_investigation_data(self)
        _debug_investigation(
            "load start",
            received=query_id,
            chosen=target,
            had_valid_state=had_valid_state,
        )
        if query_id:
            self.requested_investigation_target = query_id
            self.last_valid_investigation_target = query_id
        if not target:
            self.requested_investigation_target = ""
            self.investigation_loading = False
            if had_valid_state:
                self.investigation_status = INVESTIGATION_STATUS_LOADED
                _debug_investigation("preserved previous state", reason="missing target")
                return
            _clear_investigation_state(self)
            self.investigation_status = INVESTIGATION_STATUS_EMPTY
            _debug_investigation("empty state", reason="missing target and no previous state")
            return
        self.investigation_loading = True
        self.investigation_status = INVESTIGATION_STATUS_LOADING
        try:
            resolved = _json_dict(resolve_investigation_target(target))
            if not bool(_field(resolved, "found", False)):
                _clear_investigation_state(self)
                self.requested_investigation_target = target
                self.last_valid_investigation_target = target
                self.investigation_status = INVESTIGATION_STATUS_ERROR
                self.investigation_status_message = str(
                    _field(resolved, "warning", "No se encontro una entidad local para abrir el expediente.")
                )
                self.error_message = self.investigation_status_message
                _debug_investigation("empty state", received=target, reason="target not found")
                return
            resolved_entity_id = str(_field(resolved, "entity_id", target))
            resolved_entity_name = str(_field(resolved, "entity_name", ""))
            _debug_investigation("target resolved", received=target, resolved=resolved_entity_id, name=resolved_entity_name)
            data = _json_dict(get_investigation(resolved_entity_id))
            if not _investigation_response_has_data(data):
                if had_valid_state:
                    self.investigation_loading = False
                    self.investigation_status = INVESTIGATION_STATUS_LOADED
                    self.requested_investigation_target = ""
                    self.investigation_status_message = "La respuesta local no trajo datos suficientes; se conserva el expediente cargado."
                    _debug_investigation("preserved previous state", received=target, resolved=resolved_entity_id, reason="empty response")
                    return
                _clear_investigation_state(self)
                self.requested_investigation_target = target
                self.last_valid_investigation_target = target
                self.investigation_status = INVESTIGATION_STATUS_ERROR
                self.investigation_status_message = "La respuesta local no trajo datos suficientes para este expediente."
                self.error_message = self.investigation_status_message
                _debug_investigation("rejected empty response", received=target, resolved=resolved_entity_id)
                return
            comparison = _json_dict(get_entity_comparison(resolved_entity_id))
            trace = _json_dict(get_source_trace(resolved_entity_id))
            story = _json_dict(get_investigation_story(resolved_entity_id))
            graph = _json_dict(get_investigation_graph(resolved_entity_id))
            timeline = _json_dict(get_investigation_timeline(resolved_entity_id))
            contributions = _json_dict(get_source_contributions(resolved_entity_id))
            report_path = export_investigation_report(resolved_entity_id)
        except Exception as exc:  # noqa: BLE001
            if had_valid_state:
                self.investigation_status = INVESTIGATION_STATUS_LOADED
                self.requested_investigation_target = ""
                self.investigation_status_message = f"No se pudo refrescar el expediente; se conserva la vista cargada. {type(exc).__name__}: {exc}"
                _debug_investigation("preserved previous state", received=target, reason=type(exc).__name__)
                return
            _clear_investigation_state(self)
            self.requested_investigation_target = target
            self.last_valid_investigation_target = target
            self.investigation_status = INVESTIGATION_STATUS_ERROR
            self.error_message = f"{type(exc).__name__}: {exc}"
            self.investigation_status_message = self.error_message
            return
        finally:
            self.investigation_loading = False

        metrics = data.get("key_metrics", {})
        compact_metrics = data.get("compact_metrics", {})
        self.selected_entity_id = resolved_entity_id
        self.selected_entity_name = resolved_entity_name
        self.report_path = report_path
        self.entity_name = str(_field(_field(data, "entity", {}), "name", ""))
        self.selected_entity_name = self.entity_name
        self.entity_summary = str(data.get("narrative_summary") or data.get("summary", ""))
        self.dataset_badges = [str(item) for item in _json_list(data.get("dataset_badges", []))]
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
        self.relationship_journey_rows = _build_relationship_journey_rows(
            entity_name=self.entity_name,
            procurement=self.procurement_rows,
            registry=self.registry_rows,
            lobby=self.lobby_rows,
            transparency=self.transparencia_rows,
            timeline=timeline_rows,
            evidence=self.evidence_rows,
        )
        self.related_entity_group_rows = _build_related_entity_group_rows(
            self.relationship_rows,
            self.registry_rows,
            self.lobby_rows,
            self.procurement_rows,
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
            self.timeline_year_rows.append(row)
        source_counts = {
            str(_field(item, "dataset", "")): {
                "evidence_count": int(_field(item, "evidence_count", 0) or 0),
                "relationship_count": int(_field(item, "relationship_count", 0) or 0),
            }
            for item in self.source_trace_sources
        }
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
                "evidence_count": int(source_counts.get(str(_field(item, "dataset", "")), {}).get("evidence_count", 0)),
                "relationship_count": int(source_counts.get(str(_field(item, "dataset", "")), {}).get("relationship_count", 0)),
                "commands_text": str(_field(item, "commands_text", "")),
            }
            for item in _field(contributions, "sources", [])
        ]
        self.source_coverage_rows = _build_source_coverage_rows(self.source_contribution_rows)
        self.citizen_summary = _citizen_summary_text(
            self.entity_name,
            self.datasets_involved,
            self.evidence_count,
            self.relationship_count,
            self.connected_entities,
            self.dataset_badges,
        )
        self.canonical_investigation_link = f"http://localhost:3000{_investigation_href(self.entity_name or target)}"
        self.last_loaded_investigation_target = self.selected_entity_id
        self.last_valid_investigation_target = target
        self.requested_investigation_target = ""
        self.investigation_loaded = True
        self.investigation_status = INVESTIGATION_STATUS_LOADED
        self.investigation_status_message = ""
        _debug_investigation(
            "load complete",
            received=target,
            resolved=self.selected_entity_id,
            evidence=self.evidence_count,
            relationships=self.relationship_count,
            sources=self.datasets_involved,
        )


def shell(*children: rx.Component, active_page: str, **props) -> rx.Component:
    nav_items = rx.hstack(
        rx.link("Inicio", href="/", class_name=_nav_class(active_page == PAGE_HOME)),
        rx.link("Descubre", href="/discover", class_name=_nav_class(active_page == PAGE_DISCOVER)),
        rx.link("Expediente", href="/investigation", class_name=_nav_class(active_page == PAGE_INVESTIGATION)),
        rx.link("Reportes", href="/reports", class_name=_nav_class(active_page == PAGE_REPORTS)),
        rx.link("Biblioteca", href="/library", class_name=_nav_class(active_page == PAGE_LIBRARY)),
        rx.link("Seguimiento", href="/tracking", class_name=_nav_class(active_page == PAGE_TRACKING)),
        rx.link("Fuentes", href="/ecosystem", class_name=_nav_class(active_page == PAGE_ECOSYSTEM)),
        rx.link("Proyecto", href="/project", class_name=_nav_class(active_page == PAGE_PROJECT)),
        spacing="2",
        align="center",
        class_name="nav-links",
    )
    header_search = rx.hstack(
        rx.button("Buscar", on_click=AppState.toggle_header_search, class_name="header-search-toggle"),
        rx.cond(
            AppState.header_search_open,
            rx.hstack(
                rx.input(
                    placeholder="Buscar entidad",
                    value=AppState.header_search_query,
                    on_change=AppState.set_header_search_query,
                    class_name="input header-search-input",
                ),
                rx.button("Ir", on_click=AppState.submit_header_search, class_name="header-search-submit"),
                spacing="2",
                align="center",
                class_name="header-search-popover",
            ),
        ),
        spacing="2",
        align="center",
        class_name="header-search",
    )
    return rx.box(
        rx.box(
            rx.hstack(
                rx.link("DatosEnOrden", href="/", class_name="brand"),
                nav_items,
                header_search,
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
        app_footer(),
        class_name=rx.cond(AppState.theme_dark, f"shell theme-dark {_page_class(active_page)}", f"shell theme-light {_page_class(active_page)}"),
        **props,
    )


def _page_class(active_page: str) -> str:
    return {
        PAGE_HOME: "page-home",
        PAGE_DISCOVER: "page-discover",
        PAGE_INVESTIGATION: "page-investigation",
        PAGE_LIBRARY: "page-library",
        PAGE_KNOWLEDGE: "page-library",
        PAGE_TRACKING: "page-tracking",
        PAGE_REPORTS: "page-reports",
        PAGE_ECOSYSTEM: "page-ecosystem",
        PAGE_PROJECT: "page-project",
        PAGE_SEARCH: "page-discover",
        PAGE_DEMO: "page-home",
    }.get(active_page, "page-home")


def app_footer() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.text(
                "DatosEnOrden ayuda a convertir informacion publica y documental en evidencia navegable.",
                class_name="footer-copy",
            ),
            rx.hstack(
                rx.link("DatosEnOrden", href="/", class_name="footer-link"),
                rx.link("DatosEnOrden Studio", href="/project", class_name="footer-link"),
                rx.link("Reportes", href="/reports", class_name="footer-link"),
                rx.link("Biblioteca", href="/library", class_name="footer-link"),
                rx.link("Seguimiento", href="/tracking", class_name="footer-link"),
                rx.link("Fuentes", href="/ecosystem", class_name="footer-link"),
                rx.link("Estado del proyecto", href="/project", class_name="footer-link"),
                rx.link("Contacto", href="mailto:datosenorden@gmail.com", class_name="footer-link"),
                spacing="3",
                wrap="wrap",
                justify="center",
            ),
            rx.text("Contacto: datosenorden@gmail.com", class_name="footer-copy"),
            rx.text("Desarrollado por DatosEnOrden Studio.", class_name="footer-copy"),
            spacing="2",
            align="center",
        ),
        class_name="site-footer",
    )

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
            on_click=AppState.open_canonical_investigation(row["organization_id"]),
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
            rx.text(row.get("trust_label", "Registro local de demo"), class_name="mini-pill evidence-trust"),
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


def evidence_card(row: dict) -> rx.Component:
    return story_card(row)


def relationship_badge(label: str) -> rx.Component:
    return rx.text(label, class_name="mini-pill mini-pill-purple")


def journey_node(row: dict) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.text(row["step"], class_name="journey-step"),
            rx.text(row["source"], class_name="badge badge-teal"),
            justify="between",
            align="center",
        ),
        rx.text(row["title"], class_name="card-title"),
        rx.text(row["body"], class_name="muted"),
        rx.text(row["why"], class_name="source-fact"),
        rx.hstack(
            relationship_badge(row["kind"]),
            rx.text(row["source_sentence"], class_name="mini-pill"),
            spacing="2",
            wrap="wrap",
        ),
        class_name="card journey-node",
    )


def citizen_summary_panel() -> rx.Component:
    return investigation_panel(
        "Resumen ciudadano",
        rx.text(AppState.citizen_summary, class_name="story-summary story-summary-dominant"),
        rx.grid(
            summary_metric_card("Fuentes publicas", AppState.datasets_involved),
            summary_metric_card("Evidencias", AppState.evidence_count),
            summary_metric_card("Relaciones", AppState.relationship_count),
            summary_metric_card("Entidades conectadas", AppState.connected_entities),
            columns="4",
            spacing="2",
            class_name="responsive-grid",
        ),
        rx.hstack(
            rx.link("Exportar expediente", href=AppState.report_path, class_name="button"),
            rx.text("Registro local de demo", class_name="mini-pill evidence-trust"),
            spacing="2",
            wrap="wrap",
        ),
        rx.box(
            rx.text("Enlace canonico", class_name="muted small"),
            rx.text(AppState.canonical_investigation_link, class_name="mono id-line"),
            class_name="canonical-link-box",
        ),
        subtitle="Lectura breve para explicar que contiene el expediente sin afirmar causalidad, irregularidad ni responsabilidad.",
    )


def journey_connection() -> rx.Component:
    return rx.text("↓", class_name="journey-connection")


def related_entity_card(row: dict) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.text(row["group"], class_name="badge badge-teal"),
            rx.text(row["source"], class_name="muted small"),
            justify="between",
            align="center",
        ),
        rx.text(row["type"], class_name="mini-pill mini-pill-purple"),
        rx.text(row["title"], class_name="context-title"),
        rx.text(row["why"], class_name="muted small"),
        class_name="context-item related-entity-card",
    )


def related_entity_group(row: dict) -> rx.Component:
    return related_entity_card(row)


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


def source_card(row: dict) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.text(row["dataset"], class_name="badge"),
            rx.text(row["status"], class_name="mini-pill"),
            justify="between",
            align="center",
        ),
        rx.text(row["summary"], class_name="muted small"),
        rx.hstack(
            rx.text(f"Evidencia: {row['evidence_count']}", class_name="mini-pill"),
            rx.text(f"Relaciones: {row['relationship_count']}", class_name="mini-pill mini-pill-purple"),
            spacing="2",
            wrap="wrap",
        ),
        rx.text(f"Conceptos: {row['concepts_text']}", class_name="source-fact"),
        rx.text(f"Aporta: {row['contributes_text']}", class_name="source-fact"),
        rx.text(row["timeline_contribution"], class_name="muted small"),
        class_name="card source-card",
    )


def source_coverage_card(row: dict) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.text(row["source"], class_name="card-title"),
            rx.text(row["status"], class_name=_accent_badge_class(str(row.get("status", "")))),
            justify="between",
            align="center",
        ),
        rx.text(row["contribution"], class_name="muted small"),
        rx.hstack(
            rx.text(f"Evidencia: {row['evidence_count']}", class_name="mini-pill"),
            rx.text(f"Relaciones: {row['relationship_count']}", class_name="mini-pill mini-pill-purple"),
            rx.text(row["trust_label"], class_name="mini-pill evidence-trust"),
            spacing="2",
            wrap="wrap",
        ),
        class_name="card source-card source-coverage-card",
    )


def source_contribution_card(row: dict) -> rx.Component:
    return source_card(row)


def technical_source_card(row: dict) -> rx.Component:
    return rx.box(
        rx.text(row["dataset"], class_name="context-title"),
        rx.text(f"Estado: {row['status']}", class_name="technical-line"),
        rx.text(f"Evidencia: {row['evidence_count']} | Relaciones: {row['relationship_count']}", class_name="technical-line"),
        rx.text(f"Conceptos: {row['concepts_text']}", class_name="technical-line"),
        rx.text(f"Tipos de evidencia: {row['evidence_types_text']}", class_name="technical-line"),
        rx.text(f"Comandos: {row['commands_text']}", class_name="technical-line"),
        rx.text(row["overlap_note"], class_name="muted small"),
        class_name="context-item technical-item",
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
            rx.button("Abrir expediente", on_click=AppState.open_canonical_investigation(row["canonical_entity_id"]), class_name="button button-secondary"),
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


def help_card(title: str, body: str) -> rx.Component:
    return rx.box(
        rx.text(title, class_name="context-title"),
        rx.text(body, class_name="muted small"),
        class_name="card help-card",
    )


def next_step_card(title: str, body: str, label: str, href: str) -> rx.Component:
    return rx.box(
        rx.text(title, class_name="card-title"),
        rx.text(body, class_name="muted small"),
        rx.button(label, on_click=rx.redirect(href), class_name="button button-secondary"),
        class_name="card next-step-card",
    )


def search_chip(label: str) -> rx.Component:
    return rx.box(rx.text(label, class_name="search-chip-text"), class_name="search-chip")


def investigation_topic_card(row: dict) -> rx.Component:
    return rx.box(
        rx.text(row["label"], class_name="card-title"),
        rx.text(row["example"], class_name="muted small"),
        class_name="card topic-card",
    )


def what_to_investigate_panel() -> rx.Component:
    return page_section(
        "Que puedes investigar",
        rx.grid(
            rx.foreach(INVESTIGATION_TOPICS, investigation_topic_card),
            columns="5",
            spacing="3",
            class_name="responsive-grid topic-grid",
        ),
        subtitle="Categorias del expediente ciudadano con ejemplos disponibles o prototipos locales.",
    )


def guided_question_card(row: dict) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.text(row["title"], class_name="card-title"),
            rx.text("Pregunta guiada", class_name="badge badge-purple"),
            justify="between",
            align="center",
        ),
        rx.text(row["description"], class_name="muted small"),
        rx.text(row.get("path_text", "Este recorrido conectara fuentes locales relacionadas."), class_name="source-fact"),
        rx.hstack(
            rx.text(row.get("concepts_text", ""), class_name="search-chip"),
            rx.text(row.get("sources_text", ""), class_name="mini-pill mini-pill-purple"),
            spacing="2",
            wrap="wrap",
        ),
        rx.text(f"Ejemplo: {row['example_query']}", class_name="source-fact"),
        rx.button(
            "Ver recorrido sugerido",
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
            on_click=AppState.open_canonical_investigation(row["canonical_entity_id"]),
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
            rx.cond(
                AppState.selected_guided_category_path != "",
                rx.text(AppState.selected_guided_category_path, class_name="source-fact"),
            ),
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
            on_click=AppState.open_canonical_investigation(row["organization_id"]),
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


def demo_check_item(label: str, ready) -> rx.Component:  # noqa: ANN001
    return rx.hstack(
        rx.text(rx.cond(ready, "Listo", "Pendiente"), class_name=rx.cond(ready, "badge badge-teal", "badge badge-amber")),
        rx.text(label, class_name="context-title"),
        spacing="2",
        align="center",
        class_name="demo-check-row",
    )


def tracking_item_card(row: dict) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.text(row["item_type"], class_name="badge badge-purple"),
            rx.text(row["current_status"], class_name="badge badge-teal"),
            justify="between",
            align="center",
        ),
        rx.text(row["title"], class_name="card-title"),
        rx.text(row["summary"], class_name="muted small"),
        rx.hstack(
            rx.button("Abrir expediente", on_click=AppState.open_canonical_investigation(row["related_expediente_target"]), class_name="button"),
            rx.button("Ver demo", on_click=rx.redirect("/demo"), class_name="button button-secondary"),
            spacing="2",
            wrap="wrap",
        ),
        class_name="card tracking-card",
    )


def tracking_event_card(row: dict) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.text(row["date"], class_name="badge badge-teal"),
            rx.text(row["status"], class_name="mini-pill mini-pill-purple"),
            justify="between",
            align="center",
        ),
        rx.text(row["title"], class_name="card-title"),
        rx.text(row["description"], class_name="muted small"),
        rx.text(f"Fuente: {row['source']}", class_name="source-fact"),
        class_name="card tracking-event-card",
    )


def tracking_document_card(row: dict) -> rx.Component:
    return rx.box(
        rx.text(row["source"], class_name="badge badge-teal"),
        rx.text(row["title"], class_name="card-title"),
        rx.text(f"{row['document_type']} | {row['published_at']}", class_name="muted small"),
        rx.text(row["summary"], class_name="source-fact"),
        rx.text(row["official_url"], class_name="mono id-line"),
        class_name="card tracking-document-card",
    )


def tracking_evidence_card(row: dict) -> rx.Component:
    return rx.box(
        rx.text(row["source"], class_name="mini-pill"),
        rx.text(row["label"], class_name="context-title"),
        rx.text(row["excerpt"], class_name="muted small"),
        rx.text(row["url"], class_name="mono id-line"),
        class_name="context-item",
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
        rx.button("Abrir expediente", on_click=AppState.open_canonical_investigation(row["related_expediente_target"]), class_name="button"),
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


def citizen_report_card(row: dict) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.text(row["classification"], class_name="badge badge-teal"),
            rx.text(row["current_status"], class_name="mini-pill mini-pill-purple"),
            justify="between",
            align="center",
        ),
        rx.text(row["title"], class_name="card-title"),
        rx.text(row["subtitle"], class_name="muted small"),
        rx.text(f"Materia: {row['subject']}", class_name="source-fact"),
        rx.hstack(
            rx.button("Abrir expediente", on_click=AppState.open_canonical_investigation(row["related_expediente_target"]), class_name="button"),
            rx.link("Abrir version HTML", href=AppState.citizen_report_path, class_name="button button-secondary"),
            spacing="2",
            wrap="wrap",
        ),
        class_name="card report-card",
    )


def citizen_report_section_card(row: dict) -> rx.Component:
    return rx.box(
        rx.text(row["title"], class_name="card-title"),
        rx.text(row["summary"], class_name="muted small"),
        rx.vstack(
            rx.text("Evidencia", class_name="muted small"),
            rx.text(
                rx.cond(row["evidence_text"] != "", row["evidence_text"], "sin referencias"),
                class_name="source-fact",
            ),
            spacing="1",
            align="stretch",
        ),
        class_name="card report-section-card",
    )


def follow_target_card(row: dict) -> rx.Component:
    return rx.box(
        rx.text(row["label"], class_name="card-title"),
        rx.text(row["note"], class_name="muted small"),
        rx.button("Suscribirse a cambios", disabled=True, class_name="button button-disabled"),
        class_name="card tracking-card",
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
            rx.text("¿Qué quieres investigar?", class_name="title"),
            rx.text("Un expediente reúne fuentes, evidencia y relaciones para ayudarte a entender una entidad sin perder el contexto.", class_name="subtitle"),
            rx.hstack(
                rx.input(
                    placeholder="Busca organismo, empresa, persona o proyecto",
                    value=AppState.query,
                    on_change=AppState.set_query,
                    class_name="input search-input",
                ),
                rx.button("Buscar", on_click=AppState.submit_main_search, class_name="button search-button"),
                spacing="3",
                align="center",
                class_name="search-bar investigation-welcome-search",
            ),
            rx.hstack(
                rx.button("Abrir expediente demo", on_click=rx.redirect(_investigation_href(DEMO_INVESTIGATION_TARGET)), class_name="button"),
                rx.button("Ver biblioteca", on_click=rx.redirect("/library"), class_name="button button-secondary"),
                rx.button("Explorar fuentes", on_click=rx.redirect("/ecosystem"), class_name="button button-secondary"),
                spacing="3",
                wrap="wrap",
                class_name="hero-actions",
            ),
            class_name="hero investigation-welcome",
        ),
        rx.grid(
            help_card("¿Qué es un expediente?", "Una carpeta de lectura: reúne lo que sabemos, de dónde viene y cómo se conecta."),
            help_card("¿Qué es evidencia?", "Una pista verificable que permite volver a la fuente o al documento original."),
            help_card("¿Qué puedes hacer después?", "Leer un reporte, seguir la historia del proyecto o revisar las fuentes."),
            columns="3",
            spacing="3",
            class_name="responsive-grid investigation-empty-grid",
        ),
        spacing="4",
        align="stretch",
    )


def investigation_loading_state() -> rx.Component:
    return rx.box(
        rx.text("Cargando expediente...", class_name="title"),
        rx.text("Leyendo el identificador de la URL y reconstruyendo la vista desde la base local.", class_name="subtitle"),
        rx.hstack(
            rx.button("Reintentar", on_click=AppState.load_investigation, class_name="button button-secondary"),
            rx.button("Volver al demo", on_click=rx.redirect("/demo"), class_name="button button-secondary"),
            spacing="3",
            wrap="wrap",
            class_name="hero-actions",
        ),
        class_name="hero",
    )


def investigation_error_state() -> rx.Component:
    return rx.box(
        rx.text("No se pudo abrir el expediente", class_name="title"),
        rx.text(
            rx.cond(
                AppState.investigation_status_message != "",
                AppState.investigation_status_message,
                "La app no pudo cargar este expediente local. Puedes reintentar o volver al recorrido demo.",
            ),
            class_name="subtitle",
        ),
        rx.hstack(
            rx.button("Reintentar", on_click=AppState.load_investigation, class_name="button"),
            rx.button("Volver al demo", on_click=rx.redirect("/demo"), class_name="button button-secondary"),
            spacing="3",
            wrap="wrap",
            class_name="hero-actions",
        ),
        class_name="hero investigation-error",
    )


def _legacy_guided_search_empty_state() -> rx.Component:
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
        what_to_investigate_panel(),
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


def search_empty_state() -> rx.Component:
    return rx.vstack(
        page_section(
            "Sin resultados todavia",
            rx.text("Escribe un nombre o identificador local para buscar expedientes disponibles.", class_name="muted"),
            rx.link("Usar entrada guiada", href="/discover", class_name="badge badge-purple"),
            subtitle="/search es una utilidad directa. Si no sabes que buscar, empieza por Descubre.",
        ),
        spacing="4",
        align="stretch",
    )


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
        subtitle="Eventos agrupados cronologicamente desde todas las fuentes disponibles.",
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


def narrative_panel(title: str, body: str, items: list[str] | None = None) -> rx.Component:
    return investigation_panel(
        title,
        rx.text(body, class_name="story-summary story-summary-dominant"),
        rx.cond(
            items or [],
            rx.vstack(
                rx.foreach(items or [], narrative_item),
                spacing="2",
                align="stretch",
            ),
        ),
    )


def history_panel() -> rx.Component:
    return investigation_panel(
        "Historia",
        rx.text(AppState.story_headline, class_name="story-headline"),
        rx.text(AppState.story_summary, class_name="story-summary"),
        rx.cond(
            AppState.story_key_findings,
            rx.hstack(
                rx.foreach(AppState.story_key_findings, lambda item: rx.text(item, class_name="story-chip")),
                spacing="2",
                wrap="wrap",
            ),
            rx.text("No hay puntos destacados disponibles para este expediente.", class_name="muted small"),
        ),
        subtitle="Una lectura unica del expediente, independiente del punto de entrada.",
    )


def citizen_narrative_panel() -> rx.Component:
    return investigation_panel(
        "Narrativa ciudadana",
        rx.text(AppState.citizen_narrative, class_name="story-summary story-summary-dominant"),
        rx.cond(
            AppState.story_important_connections,
            rx.vstack(
                rx.foreach(AppState.story_important_connections, narrative_item),
                spacing="2",
                align="stretch",
            ),
            rx.text("No hay conexiones destacadas disponibles.", class_name="muted small"),
        ),
        rx.cond(
            AppState.story_questions,
            rx.hstack(
                rx.foreach(AppState.story_questions, lambda item: rx.text(item, class_name="prompt-chip")),
                spacing="2",
                wrap="wrap",
            ),
        ),
        subtitle="Lenguaje descriptivo para entender que muestran los datos locales.",
    )


def relationship_journey_panel() -> rx.Component:
    return investigation_panel(
        "Como se conectan los datos",
        rx.cond(
            AppState.relationship_journey_rows,
            rx.vstack(
                rx.foreach(AppState.relationship_journey_rows, journey_node),
                spacing="2",
                align="stretch",
                class_name="journey-list",
            ),
            rx.text("No hay recorrido de relaciones disponible.", class_name="muted small"),
        ),
        subtitle="Una ruta legible reemplaza el grafo denso. Cada paso indica fuente y motivo.",
    )


def evidence_journey_panel() -> rx.Component:
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
                    rx.grid(rx.foreach(AppState.procurement_rows, evidence_card), columns="2", spacing="2", class_name="tab-grid"),
                    rx.text("No hay compras asociadas en los datos locales.", class_name="muted small"),
                ),
                value="procurement",
                class_name="tab-content",
            ),
            rx.tabs.content(
                rx.cond(
                    AppState.lobby_rows,
                    rx.grid(rx.foreach(AppState.lobby_rows, evidence_card), columns="2", spacing="2", class_name="tab-grid"),
                    rx.text("No hay reuniones asociadas en los datos locales.", class_name="muted small"),
                ),
                value="lobby",
                class_name="tab-content",
            ),
            rx.tabs.content(
                rx.cond(
                    AppState.transparencia_rows,
                    rx.grid(rx.foreach(AppState.transparencia_rows, evidence_card), columns="2", spacing="2", class_name="tab-grid"),
                    rx.text("No hay registros de transparencia asociados.", class_name="muted small"),
                ),
                value="transparency",
                class_name="tab-content",
            ),
            rx.tabs.content(
                rx.cond(
                    AppState.registry_rows,
                    rx.grid(rx.foreach(AppState.registry_rows, evidence_card), columns="2", spacing="2", class_name="tab-grid"),
                    rx.text("No hay registros societarios asociados.", class_name="muted small"),
                ),
                value="registry",
                class_name="tab-content",
            ),
            rx.tabs.content(
                rx.cond(
                    AppState.evidence_rows,
                    rx.grid(rx.foreach(AppState.evidence_rows, evidence_card), columns="2", spacing="2", class_name="tab-grid"),
                    rx.text("No hay evidencia asociada.", class_name="muted small"),
                ),
                value="evidence",
                class_name="tab-content",
            ),
            default_value="procurement",
            class_name="tabs-root",
        ),
        subtitle="Registros organizados por tema, no por estructura tecnica.",
    )


def related_entities_panel() -> rx.Component:
    return investigation_panel(
        "Entidades relacionadas",
        rx.cond(
            AppState.related_entity_group_rows,
            rx.grid(
                rx.foreach(AppState.related_entity_group_rows, related_entity_group),
                columns="2",
                spacing="3",
                class_name="responsive-grid",
            ),
            rx.text("No hay entidades relacionadas disponibles.", class_name="muted small"),
        ),
        subtitle="Cada tarjeta explica por que aparece en este expediente.",
    )


def sources_section_panel() -> rx.Component:
    return investigation_panel(
        "Fuentes consultadas",
        rx.cond(
            AppState.source_contribution_rows,
            rx.grid(
                rx.foreach(AppState.source_contribution_rows, source_card),
                columns="2",
                spacing="3",
                class_name="responsive-grid",
            ),
            rx.text("No hay fuentes consultadas disponibles.", class_name="muted small"),
        ),
        subtitle="Metadata proveniente del registro de fuentes publicas locales.",
    )


def source_coverage_panel() -> rx.Component:
    return investigation_panel(
        "Cobertura de fuentes",
        rx.cond(
            AppState.source_coverage_rows,
            rx.grid(
                rx.foreach(AppState.source_coverage_rows, source_coverage_card),
                columns="2",
                spacing="3",
                class_name="responsive-grid",
            ),
            rx.text("No hay cobertura de fuentes disponible.", class_name="muted small"),
        ),
        subtitle="Estado de cada fuente para el demo local y que aporta al expediente.",
    )


def technical_panel() -> rx.Component:
    return rx.accordion.root(
        rx.accordion.item(
            header="Detalles tecnicos / trazabilidad",
            content=rx.vstack(
                rx.text(
                    "Informacion tecnica colapsada: comandos locales, tipos de evidencia, codigos internos y URLs de respaldo.",
                    class_name="muted small",
                ),
                rx.cond(
                    AppState.source_contribution_rows,
                    rx.vstack(
                        rx.foreach(AppState.source_contribution_rows, technical_source_card),
                        spacing="2",
                        align="stretch",
                    ),
                ),
                rx.cond(
                    AppState.technical_details,
                    rx.vstack(
                        rx.foreach(AppState.technical_details, technical_detail_card),
                        spacing="2",
                        align="stretch",
                    ),
                    rx.text("No hay detalles tecnicos disponibles.", class_name="muted small"),
                ),
                spacing="2",
                align="stretch",
            ),
            value="technical-details",
        ),
        type="single",
        collapsible=True,
        variant="ghost",
        class_name="technical-accordion technical-bottom",
    )


def single_investigation_product_view() -> rx.Component:
    return rx.vstack(
        history_panel(),
        citizen_summary_panel(),
        citizen_narrative_panel(),
        relationship_journey_panel(),
        timeline_highlights_panel(),
        evidence_journey_panel(),
        related_entities_panel(),
        source_coverage_panel(),
        sources_section_panel(),
        technical_panel(),
        spacing="4",
        align="stretch",
        class_name="product-investigation-flow",
    )


@rx.page(route="/", title="DatosEnOrden - Informacion publica con evidencia")
def home() -> rx.Component:
    return shell(
        rx.box(
            rx.text("Comprende la informacion. Sigue su historia.", class_name="title"),
            rx.text(
                "DatosEnOrden es una plataforma independiente para leer, conectar y seguir informacion publica con evidencia.",
                class_name="subtitle",
            ),
            rx.text(
                "MVP con datos locales de prueba. No representa datos oficiales reales.",
                class_name="badge badge-purple launch-notice",
            ),
            rx.hstack(
                rx.button("Leer un reporte ciudadano", on_click=rx.redirect("/reports"), class_name="button"),
                rx.button("Abrir expediente demo", on_click=rx.redirect(_investigation_href(DEMO_INVESTIGATION_TARGET)), class_name="button button-secondary"),
                rx.button("Revisar documento explicado", on_click=rx.redirect("/library"), class_name="button button-secondary"),
                spacing="3",
                wrap="wrap",
                class_name="hero-actions",
            ),
            class_name="hero",
        ),
        page_section(
            "Entradas principales",
            rx.grid(
                next_step_card("Leer un reporte ciudadano", "Una lectura tipo articulo que resume el caso, sus fuentes y sus siguientes pasos.", "Leer reporte", "/reports"),
                next_step_card("Abrir expediente demo", "Una carpeta navegable con fuentes, evidencia, relaciones y contexto.", "Abrir expediente", _investigation_href(DEMO_INVESTIGATION_TARGET)),
                next_step_card("Revisar documento explicado", "Un documento de prueba convertido en resumen, preguntas y puntos clave.", "Abrir Biblioteca", "/library"),
                columns="3",
                spacing="3",
                class_name="responsive-grid",
            ),
            subtitle="Tres puertas de entrada al mismo recorrido ciudadano de demostracion.",
        ),
        page_section(
            "Que puedes hacer aqui",
            rx.grid(
                help_card("Consultar documentos", "Leer documentos explicados en lenguaje ciudadano."),
                help_card("Comprender proyectos", "Abrir expedientes para ver contexto y relaciones."),
                help_card("Seguir cambios", "Revisar una timeline con hitos y estados."),
                help_card("Revisar fuentes", "Volver a la evidencia antes de compartir conclusiones."),
                columns="4",
                spacing="3",
                class_name="responsive-grid",
            ),
            subtitle="La plataforma ordena informacion publica para leerla con calma, no para emitir acusaciones.",
        ),
        page_section(
            "Demo disponible",
            rx.grid(
                rx.box(
                    rx.text("Servicio de Salud Arauco Hospital de Arauco", class_name="card-title"),
                    rx.text(
                        "Recorrido recomendado con datos locales de prueba: expediente, documento explicado, reporte ciudadano y seguimiento.",
                        class_name="story-summary",
                    ),
                    rx.hstack(
                        rx.button("Empezar por el expediente", on_click=rx.redirect(_investigation_href(DEMO_INVESTIGATION_TARGET)), class_name="button"),
                        rx.button("Leer reporte", on_click=rx.redirect("/reports"), class_name="button button-secondary"),
                        rx.button("Ver seguimiento", on_click=rx.redirect("/tracking"), class_name="button button-secondary"),
                        spacing="2",
                        wrap="wrap",
                    ),
                    class_name="card public-demo-card",
                ),
                columns="1",
                spacing="3",
                class_name="responsive-grid",
            ),
            subtitle="LOCAL_TEST_DATA / NOT_OFFICIAL_DATA. Sirve para mostrar la experiencia, no para afirmar hechos oficiales.",
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
        what_to_investigate_panel(),
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
        page_section(
            "Reportes ciudadanos",
            rx.grid(
                rx.box(
                    rx.text("Reporte demo Servicio de Salud Arauco", class_name="card-title"),
                    rx.text("Resumen ciudadano con expediente, seguimiento, fuentes y evidencia local de prueba.", class_name="muted small"),
                    rx.hstack(
                        rx.button("Ver reportes", on_click=rx.redirect("/reports"), class_name="button"),
                        rx.button("Ver seguimiento", on_click=rx.redirect("/tracking"), class_name="button button-secondary"),
                        spacing="2",
                        wrap="wrap",
                    ),
                    class_name="card report-card",
                ),
                columns="1",
                spacing="3",
                class_name="responsive-grid",
            ),
            subtitle="Reportes reutilizables para lectura publica sin afirmar irregularidades.",
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
        page_section(
            "Siguientes pasos",
            rx.grid(
                next_step_card("Descubrir una pregunta", "Si todavia no sabes que buscar, empieza por una pregunta guiada.", "Ir a Descubre", "/discover"),
                next_step_card("Abrir expediente demo", "Ver como las fuentes se conectan en una entidad concreta.", "Abrir expediente", _investigation_href(DEMO_INVESTIGATION_TARGET)),
                next_step_card("Leer reporte ciudadano", "Ver una lectura menos tecnica del caso demo.", "Ir a Reportes", "/reports"),
                columns="3",
                spacing="3",
                class_name="responsive-grid",
            ),
            subtitle="Las fuentes son el mapa; el expediente y el reporte muestran el recorrido.",
        ),
        on_mount=AppState.load_ecosystem,
        active_page=PAGE_ECOSYSTEM,
    )


@rx.page(route="/demo", title="Demo ciudadana - DatosEnOrden MVP")
def demo() -> rx.Component:
    return shell(
        rx.box(
            rx.text("Demo ciudadana", class_name="title"),
            rx.text(
                "Recorrido publico con datos locales de prueba. No son datos oficiales y no implican causalidad, irregularidad ni responsabilidad.",
                class_name="subtitle",
            ),
            rx.hstack(
                rx.button("Abrir expediente de ejemplo", on_click=rx.redirect(_investigation_href(DEMO_INVESTIGATION_TARGET)), class_name="button"),
                rx.button("Ver ecosistema de fuentes", on_click=rx.redirect("/ecosystem"), class_name="button button-secondary"),
                rx.button("Ver reportes ciudadanos", on_click=rx.redirect("/reports"), class_name="button button-secondary"),
                rx.link("Exportar reporte HTML", href=AppState.demo_report_path, class_name="button button-secondary"),
                spacing="3",
                wrap="wrap",
                class_name="hero-actions",
            ),
            class_name="hero",
        ),
        page_section(
            "Checklist del demo",
            rx.vstack(
                demo_check_item("Fuentes cargadas", AppState.demo_sources_ready),
                demo_check_item("Expediente disponible", AppState.demo_investigation_ready),
                demo_check_item("Reporte HTML exportable", AppState.demo_report_ready),
                spacing="2",
                align="stretch",
                class_name="demo-checklist",
            ),
            subtitle="Estado calculado desde la base local al abrir esta ruta.",
        ),
        page_section(
            "Como presentar este demo",
            rx.grid(
                flow_card(1, "Ver fuentes disponibles", "Abrir Ecosistema para explicar que fuentes locales de prueba estan cargadas."),
                flow_card(2, "Abrir expediente de ejemplo", "Entrar al expediente canonico del Servicio de Salud Arauco Hospital de Arauco."),
                flow_card(3, "Revisar evidencia y trazabilidad", "Mostrar resumen ciudadano, seguimiento, reportes, fuentes consultadas y detalles tecnicos colapsados."),
                columns="3",
                spacing="3",
                class_name="responsive-grid",
            ),
            subtitle="Ruta recomendada para una demo publica minima.",
        ),
        page_section(
            "Aclaracion",
            rx.text(
                "Este recorrido muestra como se veria un expediente ciudadano al cruzar fuentes publicas. "
                "Los registros son datos locales de prueba, no oficiales, y sirven para explicar el producto sin inferir irregularidades.",
                class_name="story-summary",
            ),
            subtitle="Mensaje recomendado antes de mostrar el expediente.",
        ),
        on_mount=AppState.load_demo,
        active_page=PAGE_DEMO,
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
        what_to_investigate_panel(),
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
                rx.button("Abrir expediente demo", on_click=rx.redirect(_investigation_href(DEMO_INVESTIGATION_TARGET)), class_name="button button-secondary"),
                rx.button("Ir a Biblioteca", on_click=rx.redirect("/library"), class_name="button button-secondary"),
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


@rx.page(route="/tracking", title="Seguimiento - DatosEnOrden")
def tracking() -> rx.Component:
    return shell(
        rx.box(
            rx.text("Sigue la historia de una propuesta publica", class_name="title"),
            rx.text(
                "Seguimiento local de documentos, propuestas, estados, evidencia, expedientes relacionados y cambios historicos.",
                class_name="subtitle",
            ),
            rx.hstack(
                rx.button("Abrir expediente", on_click=AppState.open_tracking_investigation, class_name="button"),
                rx.button("Ver demo", on_click=rx.redirect("/demo"), class_name="button button-secondary"),
                spacing="3",
                wrap="wrap",
                class_name="hero-actions",
            ),
            class_name="hero",
        ),
        page_section(
            "Que significa seguimiento",
            rx.grid(
                help_card("Estado", "Indica en que punto esta una historia documental segun los datos disponibles."),
                help_card("Evento", "Es un hito con fecha que ayuda a entender que paso antes y despues."),
                help_card("Timeline", "Ordena eventos para leer una historia completa, no solo datos sueltos."),
                columns="3",
                spacing="3",
                class_name="responsive-grid",
            ),
            subtitle="Una forma simple de seguir cambios en el tiempo.",
        ),
        page_section(
            "Seguimientos disponibles",
            rx.cond(
                AppState.tracking_items,
                rx.grid(
                    rx.foreach(AppState.tracking_items, tracking_item_card),
                    columns="2",
                    spacing="3",
                    class_name="responsive-grid",
                ),
                rx.text("No hay seguimientos locales disponibles.", class_name="muted small"),
            ),
            subtitle="Prototipos locales marcados como datos de prueba, sin APIs externas ni PDFs pesados.",
        ),
        page_section(
            "Timeline de seguimiento",
            rx.text(AppState.tracking_summary, class_name="story-summary"),
            rx.hstack(
                rx.text(AppState.tracking_current_status, class_name="badge badge-teal"),
                rx.text("LOCAL_TEST_DATA / NOT_OFFICIAL_DATA", class_name="mini-pill evidence-trust"),
                spacing="2",
                wrap="wrap",
            ),
            rx.grid(
                rx.foreach(AppState.tracking_events, tracking_event_card),
                columns="1",
                spacing="4",
                class_name="timeline-list",
            ),
            subtitle="Propuesta -> documento oficial -> presupuesto -> compra publica -> proveedor -> publicacion/cargo -> control -> expediente relacionado.",
        ),
        page_section(
            "Documentos oficiales relacionados",
            rx.grid(
                rx.foreach(AppState.tracking_documents, tracking_document_card),
                columns="2",
                spacing="3",
                class_name="responsive-grid",
            ),
            subtitle="Estrategia liviana: metadata, URL, hash opcional, resumen y fuente.",
        ),
        page_section(
            "Expedientes relacionados",
            rx.box(
                rx.text(AppState.tracking_expediente_target, class_name="card-title"),
                rx.text("Expediente ciudadano conectado al seguimiento por evidencia local.", class_name="muted small"),
                rx.button("Abrir expediente", on_click=AppState.open_tracking_investigation, class_name="button"),
                class_name="card",
            ),
            subtitle="El seguimiento no reemplaza el expediente: lo conecta con historia documental.",
        ),
        page_section(
            "Evidencia y fuentes consultadas",
            rx.grid(
                rx.foreach(AppState.tracking_evidence, tracking_evidence_card),
                columns="2",
                spacing="3",
                class_name="responsive-grid",
            ),
            rx.hstack(
                rx.foreach(AppState.tracking_related_sources, lambda item: rx.text(item, class_name="search-chip")),
                spacing="2",
                wrap="wrap",
            ),
            subtitle="Referencias locales descriptivas; no afirman causalidad, irregularidad ni responsabilidad.",
        ),
        page_section(
            "Siguientes pasos",
            rx.grid(
                next_step_card("Abrir expediente", "Ver la entidad, relaciones y evidencia asociada.", "Ir al expediente", _investigation_href(DEMO_INVESTIGATION_TARGET)),
                next_step_card("Leer reporte ciudadano", "Ver una lectura tipo articulo del caso.", "Ir a Reportes", "/reports"),
                next_step_card("Ver documento oficial", "Abrir la Biblioteca para revisar preguntas y puntos clave.", "Ir a Biblioteca", "/library"),
                columns="3",
                spacing="3",
                class_name="responsive-grid",
            ),
            subtitle="Por ahora no hay suscripciones reales; el seguimiento es local y read-only.",
        ),
        on_mount=AppState.load_tracking,
        active_page=PAGE_TRACKING,
    )


@rx.page(route="/knowledge", title="Conocimiento - DatosEnOrden")
def knowledge() -> rx.Component:
    return shell(
        rx.box(
            rx.text("Knowledge Engine", class_name="title"),
            rx.text(
                "Motor local read-only para transformar documentos oficiales o registros publicos de prueba en conocimiento estructurado.",
                class_name="subtitle",
            ),
            rx.hstack(
                rx.button("Abrir expediente", on_click=AppState.open_knowledge_investigation, class_name="button"),
                rx.button("Ver seguimiento", on_click=rx.redirect("/tracking"), class_name="button button-secondary"),
                rx.button("Ver reportes", on_click=rx.redirect("/reports"), class_name="button button-secondary"),
                spacing="3",
                wrap="wrap",
                class_name="hero-actions",
            ),
            class_name="hero",
        ),
        page_section(
            "Documentos disponibles",
            rx.cond(
                AppState.knowledge_documents,
                rx.grid(
                    rx.foreach(AppState.knowledge_documents, knowledge_document_card),
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
            rx.text(AppState.knowledge_summary, class_name="story-summary"),
            rx.hstack(
                rx.text("LOCAL_TEST_DATA / NOT_OFFICIAL_DATA", class_name="mini-pill evidence-trust"),
                rx.text(AppState.knowledge_title, class_name="badge badge-teal"),
                spacing="2",
                wrap="wrap",
            ),
            subtitle="Resumen rule-based generado desde campos ya presentes en el JSON local.",
        ),
        page_section(
            "Puntos importantes",
            rx.grid(
                rx.foreach(AppState.knowledge_key_points, knowledge_key_point_card),
                columns="2",
                spacing="3",
                class_name="responsive-grid",
            ),
            subtitle="Lectura estructurada por secciones, sin inferir culpabilidad ni riesgo.",
        ),
        page_section(
            "Preguntas ciudadanas sugeridas",
            rx.grid(
                rx.foreach(AppState.knowledge_questions, knowledge_question_card),
                columns="3",
                spacing="3",
                class_name="responsive-grid",
            ),
            subtitle="Preguntas para orientar revision con la evidencia original.",
        ),
        page_section(
            "Claims verificables",
            rx.grid(
                rx.foreach(AppState.knowledge_claims, knowledge_claim_card),
                columns="3",
                spacing="3",
                class_name="responsive-grid",
            ),
            subtitle="Cada afirmacion incluye evidencia asociada y nota de revision.",
        ),
        page_section(
            "Conexiones reutilizables",
            rx.grid(
                rx.foreach(AppState.knowledge_connections, knowledge_connection_card),
                columns="2",
                spacing="3",
                class_name="responsive-grid",
            ),
            subtitle="El mismo digest conecta expediente, seguimiento, reporte ciudadano y fuente publica.",
        ),
        page_section(
            "Evidencia asociada",
            rx.grid(
                rx.foreach(AppState.knowledge_evidence, tracking_evidence_card),
                columns="2",
                spacing="3",
                class_name="responsive-grid",
            ),
            rx.text(AppState.knowledge_notice, class_name="muted small"),
            subtitle="Revisar siempre el registro original antes de publicar o citar conclusiones.",
        ),
        on_mount=AppState.load_knowledge,
        active_page=PAGE_KNOWLEDGE,
    )


@rx.page(route="/library", title="Biblioteca Oficial - DatosEnOrden")
def library() -> rx.Component:
    return shell(
        rx.box(
            rx.text("Biblioteca Oficial", class_name="title"),
            rx.text(
                "Documentos explicados en lenguaje ciudadano, con preguntas, puntos clave y evidencia para revisar.",
                class_name="subtitle",
            ),
            rx.text("MVP con documentos locales de prueba. No representa documentos oficiales reales.", class_name="badge badge-purple launch-notice"),
            rx.hstack(
                rx.button("Abrir expediente", on_click=AppState.open_knowledge_investigation, class_name="button"),
                rx.button("Leer reporte", on_click=rx.redirect("/reports"), class_name="button button-secondary"),
                rx.button("Ver seguimiento", on_click=rx.redirect("/tracking"), class_name="button button-secondary"),
                spacing="3",
                wrap="wrap",
                class_name="hero-actions",
            ),
            class_name="hero",
        ),
        page_section(
            "Como leer la Biblioteca",
            rx.grid(
                help_card("Documento", "Es la pieza de informacion que se quiere entender. En esta fase usamos documentos demo."),
                help_card("Resumen ciudadano", "Una explicacion breve para saber de que trata antes de revisar detalles."),
                help_card("Evidencia", "La pista que permite volver a la fuente o seccion original y comprobar una afirmacion."),
                columns="3",
                spacing="3",
                class_name="responsive-grid",
            ),
            subtitle="La Biblioteca prepara el lugar donde podran vivir miles de documentos explicados.",
        ),
        page_section(
            "Listado",
            rx.cond(
                AppState.knowledge_documents,
                rx.grid(
                    rx.foreach(AppState.knowledge_documents, knowledge_document_card),
                    columns="2",
                    spacing="3",
                    class_name="responsive-grid",
                ),
                rx.text("Todavia no hay documentos disponibles.", class_name="muted small"),
            ),
            subtitle="Primera version visible, alimentada por Knowledge Engine.",
        ),
        page_section(
            "Documento demo",
            rx.text(AppState.knowledge_title, class_name="card-title"),
            rx.text(AppState.knowledge_summary, class_name="story-summary"),
            rx.hstack(
                rx.text("LOCAL_TEST_DATA / NOT_OFFICIAL_DATA", class_name="mini-pill evidence-trust"),
                rx.button("Abrir expediente", on_click=AppState.open_knowledge_investigation, class_name="button"),
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
                rx.foreach(AppState.knowledge_questions, knowledge_question_card),
                columns="3",
                spacing="3",
                class_name="responsive-grid",
            ),
            subtitle="Preguntas para revisar el documento sin depender solo del resumen.",
        ),
        page_section(
            "Puntos clave",
            rx.grid(
                rx.foreach(AppState.knowledge_key_points, knowledge_key_point_card),
                columns="2",
                spacing="3",
                class_name="responsive-grid",
            ),
            subtitle="Ideas principales vinculadas a evidencia.",
        ),
        page_section(
            "Siguientes pasos",
            rx.grid(
                next_step_card("Leer el reporte", "Ver la lectura completa en formato articulo.", "Ir a Reportes", "/reports"),
                next_step_card("Seguir la historia", "Revisar eventos, fechas y cambios asociados.", "Ir a Seguimiento", "/tracking"),
                next_step_card("Explorar fuentes", "Entender de donde vienen los datos del demo.", "Ir a Fuentes", "/ecosystem"),
                columns="3",
                spacing="3",
                class_name="responsive-grid",
            ),
            subtitle="La Biblioteca no es un final: conecta con el resto del recorrido.",
        ),
        on_mount=AppState.load_knowledge,
        active_page=PAGE_LIBRARY,
    )


@rx.page(route="/reports", title="Reportes ciudadanos - DatosEnOrden")
def reports() -> rx.Component:
    return shell(
        rx.box(
            rx.text("Reportes ciudadanos", class_name="title"),
            rx.text(
                "Reportes locales de lectura publica que conectan expediente, seguimiento, fuentes y evidencia navegable.",
                class_name="subtitle",
            ),
            rx.hstack(
                rx.button("Abrir expediente", on_click=AppState.open_report_investigation, class_name="button"),
                rx.button("Ver seguimiento", on_click=rx.redirect("/tracking"), class_name="button button-secondary"),
                rx.button("Ver demo", on_click=rx.redirect("/demo"), class_name="button button-secondary"),
                spacing="3",
                wrap="wrap",
                class_name="hero-actions",
            ),
            class_name="hero",
        ),
        page_section(
            "Reportes disponibles",
            rx.cond(
                AppState.citizen_reports,
                rx.grid(
                    rx.foreach(AppState.citizen_reports, citizen_report_card),
                    columns="2",
                    spacing="3",
                    class_name="responsive-grid",
                ),
                rx.text("No hay reportes ciudadanos locales disponibles.", class_name="muted small"),
            ),
            subtitle="Prototipos read-only marcados como datos locales de prueba.",
            class_name="reports-catalog-section",
        ),
        page_section(
            "Resumen",
            rx.text(AppState.citizen_report_summary, class_name="story-summary"),
            rx.hstack(
                rx.text(AppState.citizen_report_status, class_name="badge badge-teal"),
                rx.text("LOCAL_TEST_DATA / NOT_OFFICIAL_DATA", class_name="mini-pill evidence-trust"),
                spacing="2",
                wrap="wrap",
            ),
            subtitle="Lectura inicial para entender el caso sin sacar conclusiones apresuradas.",
            class_name="reports-article-section",
        ),
        page_section(
            "Que cambio",
            rx.grid(
                rx.foreach(AppState.citizen_report_sections, citizen_report_section_card),
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
                rx.foreach(AppState.citizen_report_sources, lambda item: rx.text(item, class_name="search-chip")),
                spacing="2",
                wrap="wrap",
            ),
            rx.hstack(
                rx.foreach(AppState.citizen_report_evidence_refs, lambda item: rx.text(item, class_name="mini-pill")),
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
                next_step_card("Ver documento oficial", "Leer el resumen ciudadano en la Biblioteca.", "Ir a Biblioteca", "/library"),
                next_step_card("Seguir proyecto", "Revisar timeline, estados y cambios.", "Ir a Seguimiento", "/tracking"),
                columns="3",
                spacing="3",
                class_name="responsive-grid",
            ),
            subtitle="El reporte es una puerta de entrada, no un callejon sin salida.",
        ),
        page_section(
            "Aclaracion",
            rx.text(
                "Este reporte usa datos locales de prueba, no oficiales. No afirma causalidad, irregularidad ni responsabilidad.",
                class_name="story-summary",
            ),
            rx.link("Abrir version HTML local", href=AppState.citizen_report_path, class_name="button button-secondary"),
            subtitle="Mensaje obligatorio para el demo publico.",
        ),
        on_mount=AppState.load_reports,
        active_page=PAGE_REPORTS,
    )


@rx.page(route="/project", title="Estado del proyecto - DatosEnOrden")
def project() -> rx.Component:
    return shell(
        rx.box(
            rx.text("Estado del proyecto", class_name="title"),
            rx.text(
                "DatosEnOrden esta en fase MVP: una version publica de demostracion para probar el recorrido ciudadano completo.",
                class_name="subtitle",
            ),
            rx.text("MVP con datos locales de prueba. No representa datos oficiales reales.", class_name="badge badge-purple launch-notice"),
            rx.hstack(
                rx.button("Volver al inicio", on_click=rx.redirect("/"), class_name="button"),
                rx.button("Abrir demo", on_click=rx.redirect(_investigation_href(DEMO_INVESTIGATION_TARGET)), class_name="button button-secondary"),
                spacing="3",
                wrap="wrap",
                class_name="hero-actions",
            ),
            class_name="hero",
        ),
        page_section(
            "Que es DatosEnOrden",
            rx.grid(
                help_card("Plataforma independiente", "Ayuda a leer, conectar y seguir informacion publica con evidencia."),
                help_card("Experiencia ciudadana", "Organiza documentos, reportes, expedientes, seguimiento y fuentes en un recorrido unico."),
                help_card("Motores reutilizables", "La tecnologia interna esta pensada para adaptarse a distintos dominios en el tiempo."),
                columns="3",
                spacing="3",
                class_name="responsive-grid",
            ),
            subtitle="La version publica muestra el potencial del producto con datos locales de prueba.",
        ),
        page_section(
            "DatosEnOrden Studio",
            rx.text(
                "DatosEnOrden ciudadano es la primera aplicacion publica del ecosistema. DatosEnOrden Studio prepara soluciones para organizaciones que necesitan ordenar, conectar y seguir su propia informacion documental sin perder evidencia.",
                class_name="story-summary",
            ),
            rx.grid(
                help_card("Seguimiento / TraceFlow", "Capacidad para seguir estados, hitos, responsables, documentos y cambios en el tiempo."),
                help_card("Knowledge Engine", "Capacidad para transformar documentos y registros en resumenes, preguntas, claims y evidencia revisable."),
                help_card("Reportes y documentacion", "Capacidad para convertir conocimiento estructurado en reportes, publicaciones y materiales para distintas audiencias."),
                help_card("Platform Core configurable", "Capacidad para adaptar vocabulario, workflows, templates y audiencias sin hardcodear el negocio."),
                columns="4",
                spacing="3",
                class_name="responsive-grid",
            ),
            subtitle="Presentado como capacidades de producto, no como detalle interno de implementacion.",
        ),
        page_section(
            "Que significa MVP",
            rx.text(
                "MVP significa producto minimo viable: una version suficientemente completa para probar si el recorrido se entiende, si las conexiones son utiles y si la experiencia ayuda a revisar informacion con evidencia.",
                class_name="story-summary",
            ),
            subtitle="No es la version final ni contiene todavia fuentes reales conectadas de forma continua.",
        ),
        page_section(
            "Que partes usan datos demo",
            rx.grid(
                help_card("Expediente demo", "Usa datos locales de prueba para mostrar como se conectarian fuentes y evidencia."),
                help_card("Biblioteca demo", "Usa documentos simulados para mostrar resumenes, preguntas y puntos clave."),
                help_card("Reportes y seguimiento", "Usan contenido local marcado como LOCAL_TEST_DATA / NOT_OFFICIAL_DATA."),
                columns="3",
                spacing="3",
                class_name="responsive-grid",
            ),
            subtitle="La plataforma esta preparada para fuentes reales, pero esta publicacion no debe confundirse con datos oficiales.",
        ),
        page_section(
            "Roadmap resumido",
            rx.grid(
                flow_card(1, "Primeras fuentes reales", "Integrar fuentes verificadas y mantener avisos claros de cobertura."),
                flow_card(2, "Dominio y despliegue", "Publicar con SSL, monitoreo y backups."),
                flow_card(3, "Feedback ciudadano", "Recoger problemas de lectura, navegacion y confianza."),
                flow_card(4, "Newsletter y redes", "Compartir reportes y documentos explicados con tono neutral."),
                columns="4",
                spacing="3",
                class_name="responsive-grid",
            ),
            subtitle="Solo producto publico; sin prometer login, pagos ni automatizaciones aun no construidas.",
        ),
        page_section(
            "Como apoyar reportando errores",
            rx.text(
                "Si encuentras un texto confuso, una pantalla vacia, un enlace que no ayuda o una afirmacion que necesita mejor evidencia, reportalo con la ruta de la pagina y una breve descripcion.",
                class_name="story-summary",
            ),
            rx.text(
                "Quieres reportar un error, sugerir una fuente o conversar sobre una implementacion para tu organizacion? Escribe a datosenorden@gmail.com.",
                class_name="story-summary",
            ),
            rx.hstack(
                rx.button("Revisar Biblioteca", on_click=rx.redirect("/library"), class_name="button"),
                rx.button("Leer Reportes", on_click=rx.redirect("/reports"), class_name="button button-secondary"),
                rx.button("Explorar Fuentes", on_click=rx.redirect("/ecosystem"), class_name="button button-secondary"),
                spacing="3",
                wrap="wrap",
            ),
            subtitle="Por ahora no se piden donaciones ni pagos.",
        ),
        active_page=PAGE_PROJECT,
    )


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


@rx.page(route="/investigation", title="Expediente - DatosEnOrden", on_load=AppState.load_investigation)
def investigation() -> rx.Component:
    return shell(
        rx.cond(
            AppState.selected_entity_id != "",
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
                        metric_card("Fuentes", AppState.datasets_involved, "consultadas"),
                        metric_card("Evidencia", AppState.evidence_count, "registros de respaldo"),
                        metric_card("Relaciones", AppState.relationship_count, "conexiones publicas"),
                        metric_card("Entidades conectadas", AppState.connected_entities, "personas, empresas u organismos"),
                        spacing="2",
                        wrap="wrap",
                        class_name="summary-strip",
                    ),
                    single_investigation_product_view(),
                    page_section(
                        "Siguientes pasos",
                        rx.grid(
                            next_step_card("Leer reporte ciudadano", "Ver una explicacion en formato articulo.", "Ir a Reportes", "/reports"),
                            next_step_card("Ver documento oficial", "Revisar el resumen ciudadano y preguntas clave.", "Ir a Biblioteca", "/library"),
                            next_step_card("Seguir proyecto", "Ver la historia en el tiempo y sus hitos.", "Ir a Seguimiento", "/tracking"),
                            columns="3",
                            spacing="3",
                            class_name="responsive-grid",
                        ),
                        subtitle="Un expediente ayuda a entrar; las otras vistas ayudan a seguir leyendo.",
                    ),
                    spacing="4",
                    align="stretch",
                    class_name="investigation-shell",
                ),
            ),
            rx.cond(
                AppState.investigation_status == INVESTIGATION_STATUS_ERROR,
                investigation_error_state(),
                rx.cond(
                    (AppState.investigation_loading)
                    | (AppState.investigation_status == INVESTIGATION_STATUS_LOADING),
                    investigation_loading_state(),
                    investigation_empty_state(),
                ),
            ),
        ),
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
    ".site-footer": {
        "width": "min(calc(100% - 48px), 1760px)",
        "max_width": "1760px",
        "margin": "28px auto 0",
        "padding": "22px 0 0",
        "border_top": "1px solid rgba(161, 161, 170, 0.18)",
    },
    ".footer-copy": {"font_size": "13px", "color": "#a1a1aa", "text_align": "center"},
    ".footer-link": {"font_size": "13px", "color": "#d4d4d8", "font_weight": "600"},
    ".shell.theme-light .footer-copy": {"color": "#71717a"},
    ".shell.theme-light .footer-link": {"color": "#374151"},
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
    ".header-search": {"position": "relative", "flex_wrap": "wrap", "justify_content": "flex-end"},
    ".header-search-toggle": {
        "border_radius": "999px",
        "padding": "8px 14px",
        "border": "1px solid rgba(45, 212, 191, 0.28)",
        "background": "rgba(45, 212, 191, 0.12)",
        "color": "#ccfbf1",
        "font_weight": "700",
    },
    ".header-search-popover": {
        "padding": "6px",
        "border": "1px solid rgba(161, 161, 170, 0.22)",
        "border_radius": "8px",
        "background": "rgba(24, 24, 27, 0.96)",
    },
    ".header-search-input": {"width": "220px", "min_height": "36px", "font_size": "14px"},
    ".header-search-submit": {
        "border_radius": "6px",
        "padding": "8px 12px",
        "background": "#2dd4bf",
        "color": "#042f2e",
        "font_weight": "800",
    },
    ".shell.theme-light .header-search-toggle": {
        "background": "rgba(13, 148, 136, 0.12)",
        "color": "#0f766e",
    },
    ".shell.theme-light .header-search-popover": {
        "background": "rgba(255, 255, 255, 0.98)",
        "border": "1px solid rgba(113, 113, 122, 0.24)",
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
    ".page-home .hero": {
        "padding": "46px 34px",
        "border_left": "4px solid rgba(228, 228, 231, 0.34)",
        "background": "linear-gradient(180deg, rgba(31, 31, 36, 0.96), rgba(18, 18, 22, 0.94))",
    },
    ".page-investigation .hero": {"border_left": "4px solid rgba(45, 212, 191, 0.55)"},
    ".page-library .hero": {"border_left": "4px solid rgba(167, 139, 250, 0.58)"},
    ".page-tracking .hero": {"border_left": "4px solid rgba(74, 222, 128, 0.56)"},
    ".page-reports .hero": {"border_left": "4px solid rgba(251, 146, 60, 0.58)"},
    ".page-ecosystem .hero": {"border_left": "4px solid rgba(96, 165, 250, 0.58)"},
    ".page-project .hero": {"border_left": "4px solid rgba(161, 161, 170, 0.62)"},
    ".page-home .title": {"color": "#f4f4f5"},
    ".page-investigation .title": {"color": "#ccfbf1"},
    ".page-library .title": {"color": "#ddd6fe"},
    ".page-tracking .title": {"color": "#bbf7d0"},
    ".page-reports .title": {"color": "#fed7aa"},
    ".page-ecosystem .title": {"color": "#bfdbfe"},
    ".page-project .title": {"color": "#e4e4e7"},
    ".shell.theme-light .hero": {
        "background": "linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(247, 247, 248, 0.98))",
        "border_color": "rgba(113, 113, 122, 0.18)",
    },
    ".title": {"font_size": "34px", "font_weight": "800", "line_height": "1.1"},
    ".subtitle": {"color": "#a1a1aa", "max_width": "820px", "line_height": "1.55"},
    ".shell.theme-light .subtitle": {"color": "#71717a"},
    ".section-title": {"font_size": "20px", "font_weight": "700", "margin_bottom": "12px", "color": "#f4f4f5"},
    ".page-reports .section-title": {"font_size": "24px", "font_weight": "800", "color": "#fed7aa"},
    ".page-library .section-title": {"color": "#ddd6fe"},
    ".page-tracking .section-title": {"color": "#bbf7d0"},
    ".page-investigation .section-title": {"color": "#ccfbf1"},
    ".page-ecosystem .section-title": {"color": "#bfdbfe"},
    ".page-project .section-title": {"color": "#e4e4e7"},
    ".shell.theme-light .section-title": {"color": "#18181b"},
    ".section-subtitle": {"color": "#a1a1aa", "margin_bottom": "14px"},
    ".shell.theme-light .section-subtitle": {"color": "#71717a"},
    ".page-section": {
        "display": "grid",
        "gap": "14px",
        "padding": "4px 0 10px",
    },
    ".page-home .page-section": {"padding": "12px 0 18px"},
    ".page-reports .page-section": {
        "width": "100%",
        "max_width": "1180px",
        "margin": "0 auto",
        "padding": "24px 0",
        "border_top": "1px solid rgba(251, 146, 60, 0.16)",
    },
    ".page-reports .reports-article-section": {"max_width": "980px"},
    ".page-reports .reports-catalog-section, .page-reports .reports-wide-section": {"max_width": "1180px"},
    ".page-library .page-section": {
        "padding": "22px 0",
        "border_top": "1px solid rgba(167, 139, 250, 0.14)",
    },
    ".page-tracking .page-section": {
        "padding": "20px 0",
        "border_top": "1px solid rgba(74, 222, 128, 0.14)",
    },
    ".page-ecosystem .page-section": {
        "padding": "20px 0",
        "border_top": "1px solid rgba(96, 165, 250, 0.14)",
    },
    ".page-project .page-section": {
        "padding": "20px 0",
        "border_top": "1px solid rgba(161, 161, 170, 0.14)",
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
    ".launch-notice": {"width": "fit-content", "margin_top": "6px"},
    ".badge-amber": {"background": "rgba(250, 204, 21, 0.14)", "color": "#facc15", "border_color": "rgba(250, 204, 21, 0.28)"},
    ".page-tracking .badge-teal": {"background": "rgba(74, 222, 128, 0.12)", "color": "#86efac", "border_color": "rgba(74, 222, 128, 0.28)"},
    ".page-reports .badge-teal": {"background": "rgba(251, 146, 60, 0.12)", "color": "#fdba74", "border_color": "rgba(251, 146, 60, 0.28)"},
    ".page-ecosystem .badge-teal": {"background": "rgba(96, 165, 250, 0.12)", "color": "#93c5fd", "border_color": "rgba(96, 165, 250, 0.28)"},
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
    ".evidence-trust": {"background": "rgba(250, 204, 21, 0.1)", "border_color": "rgba(250, 204, 21, 0.22)"},
    ".canonical-link-box": {
        "border": "1px solid rgba(161, 161, 170, 0.18)",
        "border_radius": "8px",
        "padding": "10px",
        "background": "#1f1f24",
        "overflow_wrap": "anywhere",
    },
    ".topic-card": {"min_height": "130px", "display": "grid", "gap": "8px", "align_content": "start"},
    ".topic-grid": {"align_items": "stretch"},
    ".source-coverage-card": {"max_width": "none", "width": "100%"},
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
    ".investigation-shell": {"display": "grid", "gap": "14px", "width": "min(95vw, 1600px)", "margin": "0 auto"},
    ".product-investigation-flow": {
        "display": "grid",
        "gap": "18px",
        "width": "100%",
        "max_width": "1600px",
        "margin": "0 auto",
    },
    ".product-metric-card": {
        "min_width": "190px",
        "flex": "1 1 190px",
    },
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
    ".technical-bottom": {
        "border": "1px solid rgba(161, 161, 170, 0.18)",
        "border_radius": "16px",
        "padding": "10px 14px",
        "background": "#18181b",
    },
    ".shell.theme-light .technical-bottom": {
        "background": "#ffffff",
        "border_color": "rgba(113, 113, 122, 0.18)",
    },
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
    ".journey-list": {"max_width": "920px", "margin": "0 auto", "width": "100%"},
    ".journey-node": {
        "position": "relative",
        "display": "grid",
        "gap": "8px",
        "padding": "16px",
        "overflow": "hidden",
    },
    ".journey-node + .journey-node": {"margin_top": "8px"},
    ".journey-step": {
        "display": "inline-flex",
        "align_items": "center",
        "justify_content": "center",
        "width": "32px",
        "height": "32px",
        "border_radius": "999px",
        "background": "rgba(45, 212, 191, 0.14)",
        "color": "#2dd4bf",
        "font_weight": "900",
    },
    ".journey-connection": {
        "text_align": "center",
        "font_size": "28px",
        "font_weight": "900",
        "color": "#2dd4bf",
    },
    ".related-entity-group": {"display": "grid", "gap": "10px", "min_width": "0"},
    ".related-entity-card": {"min_width": "0"},
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
    ".tracking-card": {"min_height": "220px", "display": "grid", "gap": "10px", "align_content": "start"},
    ".tracking-event-card": {
        "min_height": "210px",
        "border_left": "3px solid rgba(74, 222, 128, 0.62)",
        "background": "linear-gradient(90deg, rgba(74, 222, 128, 0.06), #18181b 34%)",
    },
    ".timeline-list": {
        "position": "relative",
        "max_width": "980px",
    },
    ".page-tracking .timeline-list": {
        "padding_left": "18px",
        "border_left": "1px solid rgba(74, 222, 128, 0.28)",
    },
    ".page-tracking .tracking-event-card": {
        "min_height": "auto",
        "padding": "18px 20px",
        "border_left": "3px solid rgba(74, 222, 128, 0.72)",
        "border_radius": "0 8px 8px 0",
    },
    ".tracking-document-card": {"min_height": "230px"},
    ".report-card": {"min_height": "210px", "display": "grid", "gap": "10px", "align_content": "start"},
    ".report-section-card": {"min_height": "190px", "display": "grid", "gap": "8px", "align_content": "start"},
    ".help-card": {"min_height": "150px", "display": "grid", "gap": "8px", "align_content": "start"},
    ".next-step-card": {"min_height": "185px", "display": "grid", "gap": "10px", "align_content": "start"},
    ".button-disabled": {"opacity": "0.55", "cursor": "not-allowed"},
    ".page-investigation .investigation-card": {"border_left": "3px solid rgba(45, 212, 191, 0.38)"},
    ".page-investigation .summary-card": {"border_top": "2px solid rgba(45, 212, 191, 0.32)"},
    ".page-library .tracking-document-card": {
        "border_left": "3px solid rgba(167, 139, 250, 0.58)",
        "background": "linear-gradient(90deg, rgba(167, 139, 250, 0.06), #18181b 34%)",
    },
    ".page-library .report-section-card": {"border_top": "2px solid rgba(167, 139, 250, 0.32)"},
    ".page-reports .report-card": {
        "background": "transparent",
        "border_left": "3px solid rgba(251, 146, 60, 0.46)",
        "border_top": "0",
        "border_right": "0",
        "border_bottom": "0",
        "border_radius": "0",
        "padding": "8px 0 8px 18px",
    },
    ".page-reports .report-section-card": {
        "background": "transparent",
        "border_top": "0",
        "border_right": "0",
        "border_bottom": "0",
        "border_left": "3px solid rgba(251, 146, 60, 0.34)",
        "border_radius": "0",
        "padding": "6px 0 6px 18px",
    },
    ".page-reports .story-summary": {"font_size": "17px", "line_height": "1.75", "max_width": "900px"},
    ".page-ecosystem .source-card, .page-ecosystem .card": {"border_left": "3px solid rgba(96, 165, 250, 0.34)"},
    ".page-project .flow-card, .page-project .help-card": {"border_left": "3px solid rgba(161, 161, 170, 0.42)"},
    ".investigation-welcome": {"padding": "42px 34px"},
    ".investigation-welcome-search": {"max_width": "860px", "margin_top": "22px"},
    ".investigation-error": {"border_left": "4px solid rgba(251, 113, 133, 0.56)"},
    ".public-demo-card": {
        "border_left": "3px solid rgba(45, 212, 191, 0.38)",
        "background": "linear-gradient(90deg, rgba(45, 212, 191, 0.05), #18181b 32%)",
    },
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
    ".shell.theme-light .evidence-trust": {"background": "rgba(250, 204, 21, 0.1)", "color": "#92400e", "border_color": "rgba(250, 204, 21, 0.24)"},
    ".shell.theme-light .canonical-link-box": {"background": "#ffffff", "border_color": "rgba(113, 113, 122, 0.18)"},
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
