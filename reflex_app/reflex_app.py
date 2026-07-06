from __future__ import annotations

import json
import os
from pathlib import Path
from dataclasses import dataclass, fields, is_dataclass
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
from datosenorden.web.app_services import get_current_topics
from datosenorden.web.app_services import get_knowledge_documents
from datosenorden.web.app_services import get_discovery_cases
from datosenorden.web.app_services import get_guided_discovery_options
from datosenorden.web.app_services import get_guided_questions
from datosenorden.web.app_services import get_investigation
from datosenorden.web.app_services import get_investigation_knowledge
from datosenorden.web.app_services import get_real_data_readiness
from datosenorden.web.app_services import get_entity_comparison
from datosenorden.web.app_services import get_investigation_graph
from datosenorden.web.app_services import get_investigation_timeline
from datosenorden.web.app_services import get_source_trace
from datosenorden.web.app_services import get_source_contributions
from datosenorden.web.app_services import get_investigation_story
from datosenorden.web.app_services import export_investigation_report
from datosenorden.web.app_services import get_data_ecosystem
from datosenorden.web.app_services import resolve_canonical_expediente_target
from datosenorden.web.app_services import resolve_investigation_target
from datosenorden.web.app_services import search_workspace
from datosenorden.web.entity_engine import build_state_graph
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
PAGE_TOPIC = "topic"
PAGE_DOCUMENT = "official_document"
PAGE_REPORTS = "reports"
PAGE_DASHBOARD = "dashboard"
PAGE_DEMO = "demo"
PAGE_PROJECT = "project"
PAGE_SUPPORT = "support"
PAGE_STUDIO = "studio"
PAGE_NOT_FOUND = "not_found"
INVESTIGATION_STATUS_IDLE = "idle"
INVESTIGATION_STATUS_LOADING = "loading"
INVESTIGATION_STATUS_LOADED = "loaded"
INVESTIGATION_STATUS_ERROR = "error"
INVESTIGATION_STATUS_EMPTY = "empty"
DEMO_INVESTIGATION_TARGET = "SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO"
DEMO_INVESTIGATION_URL = f"{os.getenv('DATOSENORDEN_PUBLIC_BASE_URL', 'https://datosenorden.cl').rstrip('/')}/investigation?id={quote_plus(DEMO_INVESTIGATION_TARGET)}"
PDF_LOCATION_APPROXIMATE_NOTICE = "Ubicación aproximada por fragmento; el documento original no entregó coordenadas."

PUBLIC_SITE_URL = os.getenv("DATOSENORDEN_PUBLIC_BASE_URL", "https://datosenorden.cl").rstrip("/")
PUBLIC_SITE_NAME = "DatosEnOrden"
PUBLIC_SITE_AUTHOR = "DatosEnOrden"
PUBLIC_THEME_COLOR = "#0f766e"
PUBLIC_OG_IMAGE_PATH = "/og-image.png"
PUBLIC_MANIFEST_PATH = "/site.webmanifest"
PUBLIC_OG_IMAGE_ALT = "DatosEnOrden: documentos oficiales, evidencia y cronologías en un solo lugar."


@dataclass(frozen=True)
class PDFHighlightTarget:
    fragment_id: str
    page: int
    text_snippet: str
    coordinates: None = None

    def to_dict(self) -> dict:
        return {
            "fragment_id": self.fragment_id,
            "page": self.page,
            "text_snippet": self.text_snippet,
            "coordinates": self.coordinates,
        }
SUPPORT_DONATION_URL = os.getenv("DATOSENORDEN_SUPPORT_URL", "https://link.mercadopago.cl/datosenorden")
SUPPORT_SOURCE_SUGGESTION_URL = "mailto:datosenorden@gmail.comásubject=Sugerir%20fuente%20oficial"
STUDIO_CONVERSATION_URL = "mailto:datosenorden@gmail.comásubject=DatosEnOrden%20Studio"
STUDIO_CONTACT_EMAIL = "datosenorden@gmail.com"
TOPIC_BUDGET_2013_TITLE = "Ley de Presupuestos del Sector Público 2013"
TOPIC_BUDGET_2013_TARGET = "cl-congreso-boletin-8575-05"
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
    {"source": "Sanciones y Procedimientos", "status": "prototipo con datos", "contribution": "Procedimientos y resoluciones administrativas de prueba con trazabilidad local."},
]
PUBLISHED_DOCUMENT_VIEW_PATH = Path("data") / "official_documents" / "published" / "senado-docto-9000-mensaje_mocion" / "document_view.json"
PUBLISHED_DOCUMENT_READING_PATH = Path("data") / "official_documents" / "published" / "senado-docto-9000-mensaje_mocion" / "reading.json"
PUBLISHED_DOCUMENT_PDF_PATH = Path("data") / "official_documents" / "published" / "senado-docto-9000-mensaje_mocion" / "document.pdf"
PUBLISHED_DOCUMENT_PDF_ASSET_PATH = Path("assets") / "official_documents" / "senado-docto-9000-mensaje_mocion" / "document.pdf"
PUBLISHED_DOCUMENT_PDF_PUBLIC_HREF = "/official_documents/senado-docto-9000-mensaje_mocion/document.pdf"
PROCESSING_DOCUMENT_FRAGMENTS_PATH = Path("data") / "official_documents" / "processing" / "senado-docto-9000-mensaje_mocion" / "fragments.json"

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
            neighbor_id = _clean(_field(technical, "neighbor_id"), "")
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
                        f"neighbor_id={neighbor_id}",
                    ]),
                    "detail_text": "\n".join([
                        f"relationship_id={_clean(_field(technical, 'relationship_id'))}",
                        f"relationship_type={_clean(_field(technical, 'relationship_type'))}",
                        f"direction={_clean(_field(technical, 'direction'))}",
                        f"neighbor_id={neighbor_id}",
                    ]),
                    "trust_label": "Registro local de muestra",
                    "target_href": _investigation_href(neighbor_id) if neighbor_id else "",
                    "action_label": "Abrir expediente" if neighbor_id else "Relacionado",
                }
            )
            continue
        neighbor = _field(row, "neighbor", {})
        neighbor_id = _clean(_field(neighbor, "id"), "")
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
                "trust_label": "Registro local de muestra",
                "target_href": _investigation_href(neighbor_id) if neighbor_id else "",
                "action_label": "Abrir expediente" if neighbor_id else "Relacionado",
            }
        )
    return formatted


def _state_graph_display_type(value: object) -> str:
    mapping = {
        "Organismo": "organismo",
        "Persona": "persona",
        "Empresa": "empresa",
        "Documento": "documento",
        "Ley": "ley",
        "Compra": "compra",
        "Contrato": "contrato",
        "Reunion": "reuni\u00f3n",
        "Publicacion": "publicaci\u00f3n",
        "Evento": "evento",
        "Fuente": "fuente",
        "Cargo": "cargo",
    }
    text = _clean(value, "entidad")
    return mapping.get(text, text.lower())


def _state_graph_relation_label(value: object) -> str:
    labels = {
        "COMPANY_APPEARS_IN_PURCHASES": "aparece en compras",
        "PERSON_APPEARS_IN_LOBBY_MEETING": "aparece en reuni\u00f3n de lobby",
        "SOURCE_CONTRIBUTES_TO_ENTITY": "fuente aporta evidencia",
        "PUBLICATION_REFERENCES_ROLE": "publicaci\u00f3n menciona cargo",
        "ROLE_BELONGS_TO_ORGANIZATION": "cargo vinculado al organismo",
        "DOCUMENT_CITES_LAW": "documento cita ley",
        "EVENT_BELONGS_TO_DOSSIER": "evento pertenece al expediente",
    }
    text = _clean(value, "relaci\u00f3n documentada")
    return labels.get(text, _human_label(text))


def _state_graph_evidence_text(evidence: object) -> str:
    rows = _json_list(evidence)
    if not rows:
        return "Evidencia registrada por fuente o conector."
    labels: list[str] = []
    for row in rows[:2]:
        label = (
            _clean(_field(row, "title"), "")
            or _clean(_field(row, "id"), "")
            or _clean(_field(row, "source_record_id"), "")
            or _clean(_field(row, "source"), "")
        )
        if label:
            labels.append(label)
    return " | ".join(labels) if labels else "Evidencia asociada disponible."


def _format_state_graph_connection_rows(graph: object, *, limit: int = 8) -> list[dict]:
    payload = _json_dict(graph)
    entity_id = str(payload.get("entity_id", ""))
    nodes = {str(_field(node, "id", "")): _json_dict(node) for node in _json_list(payload.get("nodes", []))}
    rows: list[dict] = []
    for edge in _json_list(payload.get("edges", [])):
        source_id = str(_field(edge, "source", ""))
        target_id = str(_field(edge, "target", ""))
        source = nodes.get(source_id, {})
        target = nodes.get(target_id, {})
        related = target if source_id == entity_id else source if target_id == entity_id else target or source
        related_id = str(related.get("id", ""))
        related_label = str(related.get("label") or "Entidad conectada")
        node_type = str(related.get("node_type") or "")
        connector = str(_field(edge, "source_connector", "")) or "conector local"
        confidence = float(_field(edge, "confidence", 0.0) or 0.0)
        href = _investigation_href(related_label) if node_type not in {"Documento", "Evento", "Fuente", "Ley"} and related_label else ""
        rows.append(
            {
                "title": related_label,
                "node_type": _state_graph_display_type(node_type),
                "relation_type": _state_graph_relation_label(_field(edge, "edge_type", "")),
                "source_connector": connector,
                "evidence_text": _state_graph_evidence_text(_field(edge, "evidence", [])),
                "confidence_label": f"confianza {confidence:.0%}" if confidence else "confianza no informada",
                "href": href,
                "action_label": "Abrir entidad" if href else "Conexi\u00f3n observada",
                "technical_id": related_id,
            }
        )
    return rows[:limit]


def _format_state_graph_source_rows(graph: object) -> list[dict]:
    payload = _json_dict(graph)
    source_counts: dict[str, int] = {}
    for edge in _json_list(payload.get("edges", [])):
        connector = str(_field(edge, "source_connector", "") or "").strip() or "conector local"
        source_counts[connector] = source_counts.get(connector, 0) + 1
    return [
        {
            "source": source,
            "connections": count,
            "summary": f"Aporta {count} conexiones documentadas al StateGraph.",
        }
        for source, count in sorted(source_counts.items())
    ]


def _format_state_graph_topic_rows(graph: object, *, limit: int = 6) -> list[dict]:
    payload = _json_dict(graph)
    rows = []
    for node in _json_list(payload.get("nodes", [])):
        node_type = _state_graph_display_type(_field(node, "node_type", ""))
        if node_type in {"fuente", "cargo"}:
            continue
        rows.append(
            {
                "title": str(_field(node, "label", "Nodo relacionado")),
                "node_type": node_type,
                "sources_text": " | ".join(str(item) for item in _json_list(_field(node, "sources", []))) or "fuente local",
                "evidence_text": _state_graph_evidence_text(_field(node, "evidence", [])),
            }
        )
    return rows[:limit]


def _state_graph_badges_for_match(row: dict) -> str:
    datasets = " ".join(str(item) for item in _json_list(row.get("datasets", []))).lower()
    entity_type = str(row.get("entity_type", "") or row.get("entity_type_label", "")).lower()
    labels: list[str] = []
    if "chilecompra" in datasets or "compra" in entity_type:
        labels.append("compras")
    if "lobby" in datasets or "reunion" in entity_type or "reuni\u00f3n" in entity_type:
        labels.append("reuniones")
    if "diario" in datasets or "publicacion" in entity_type or "publicaci\u00f3n" in entity_type:
        labels.append("publicaciones")
    if "document" in entity_type or "documento" in entity_type:
        labels.append("documentos")
    if int(row.get("relationship_count", 0) or 0) or int(row.get("evidence_count", 0) or 0):
        labels.append("eventos")
    unique = list(dict.fromkeys(labels))
    return "Conexiones disponibles: " + " | ".join(unique) if unique else ""

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



def _processed_fragment_order(row: dict, fallback: int) -> int:
    raw_order = _field(row, "order", fallback)
    try:
        return int(raw_order or fallback)
    except (TypeError, ValueError):
        return fallback


def _document_blocks(text: str) -> list[str]:
    normalized = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    blocks = [block.strip() for block in normalized.split("\n\n")]
    return [block for block in blocks if block]


def _looks_like_document_heading(text: str) -> bool:
    clean = str(text or "").strip()
    if not clean or len(clean) > 140:
        return False
    return clean.isupper() or clean.startswith(("MENSAJE", "PROYECTO DE LEY", "ANTECEDENTES", "I.", "II.", "III."))


def _load_document_view_blocks(path: Path) -> list[dict]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return []
    blocks = []
    for index, row in enumerate(_json_list(_field(payload, "blocks", [])), start=1):
        text = _clean(_field(row, "text"), "")
        if not text:
            continue
        fragment_id = _clean(_field(row, "source_fragment_id", _field(row, "fragment_id", f"document-view-{index}")), f"document-view-{index}")
        blocks.append(
            {
                "id": _clean(_field(row, "id"), f"{fragment_id}-p{index}"),
                "fragment_id": fragment_id,
                "marker": _clean(_field(row, "marker"), ""),
                "text": text,
                "is_heading": bool(_field(row, "is_heading", False)),
            }
        )
    return blocks

def _load_document_fragments_from_file(path: Path) -> list[dict]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return []
    return _json_list(_field(payload, "fragments", []))


def _load_document_fragments_with_source(fallback_fragments: list[dict]) -> tuple[list[dict], str, bool]:
    view_blocks = _load_document_view_blocks(PUBLISHED_DOCUMENT_VIEW_PATH)
    if view_blocks:
        return view_blocks, str(PUBLISHED_DOCUMENT_VIEW_PATH), False
    for path, is_fallback in (
        (PUBLISHED_DOCUMENT_READING_PATH, False),
        (PROCESSING_DOCUMENT_FRAGMENTS_PATH, True),
    ):
        fragments = _load_document_fragments_from_file(path)
        if fragments:
            return fragments, str(path), is_fallback
    if fallback_fragments:
        return fallback_fragments, "knowledge_demo_payload", True
    return [], "", False


def _document_paragraphs_from_fragments(fragments: list[dict]) -> list[dict]:
    sorted_fragments = sorted(
        _json_list(fragments),
        key=lambda row: _processed_fragment_order(row, 9999),
    )
    paragraphs: list[dict] = []
    for fragment_index, fragment in enumerate(sorted_fragments, start=1):
        fragment_id = _clean(_field(fragment, "fragment_id", _field(fragment, "id", f"fragment-{fragment_index}")), f"fragment-{fragment_index}")
        text = _clean(_field(fragment, "text"), "")
        for paragraph_index, paragraph in enumerate(_document_blocks(text), start=1):
            paragraphs.append(
                {
                    "id": f"{fragment_id}-p{paragraph_index}",
                    "fragment_id": fragment_id,
                    "marker": f"Fragmento {fragment_index:02d}" if paragraph_index == 1 else "",
                    "text": paragraph,
                    "is_heading": _looks_like_document_heading(paragraph),
                }
            )
    return paragraphs


def _load_document_paragraphs(fallback_fragments: list[dict]) -> list[dict]:
    fragments, _, _ = _load_document_fragments_with_source(fallback_fragments)
    return _document_paragraphs_from_fragments(fragments)


def _topic_read_time(fragments: list[dict]) -> str:
    words = sum(len(str(_field(row, "text", "")).split()) for row in fragments)
    minutes = max(1, round(words / 220)) if words else 1
    return f"{minutes} min"


def _format_chilean_date(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        parsed = date.fromisoformat(text[:10])
    except ValueError:
        return text
    return parsed.strftime("%d-%m-%Y")


def _topic_latest_record_date(source_records: list[dict]) -> str:
    dates = sorted(str(_field(row, "retrieved_at", ""))[:10] for row in source_records if str(_field(row, "retrieved_at", "")))
    return _format_chilean_date(dates[-1]) if dates else ""


def _topic_organizations(
    document: dict,
    source_records: list[dict],
    investigation: dict,
) -> list[str]:
    values = [
        str(_field(document, "source", "")),
        str(_field(investigation, "official_source", "")),
    ]
    values.extend(str(_field(row, "source", "")) for row in source_records[:3])
    seen: list[str] = []
    for value in values:
        cleaned = value.strip()
        if cleaned and cleaned not in seen:
            seen.append(cleaned)
    return seen


def _topic_no_change_rows(claims: list[dict], notice: str) -> list[dict]:
    rows: list[dict] = []
    if notice:
        rows.append(
            {
                "claim": f"No cambia el alcance de la lectura: {notice}",
                "review_note": "Aviso de lectura documentada",
                "fragment_id": "",
                "page": 1,
                "reference_label": "Lectura documentada",
            }
        )
    rows.append(
        {
            "claim": "No hay informacion suficiente en la lectura existente para afirmar efectos fuera del documento procesado.",
            "review_note": "Limitacion editorial: no se agregan antecedentes externos.",
            "fragment_id": str(_field(claims[0], "fragment_id", "")) if claims else "",
            "page": int(_field(claims[0], "page", 1) or 1) if claims else 1,
            "reference_label": str(_field(claims[0], "reference_label", "Lectura documentada")) if claims else "Lectura documentada",
        }
    )
    return rows


def _topic_change_rows(claims: list[dict]) -> list[dict]:
    if not claims:
        return [
            {
                "claim": "No hay informacion suficiente en Knowledge para resumir cambios concretos.",
                "review_note": "La lectura mantiene trazabilidad, pero no clasifica cambios normativos.",
                "fragment_id": "",
                "page": 1,
                "reference_label": "Lectura documentada",
            }
        ]
    return [
        {
            **dict(row),
            "claim": str(_field(row, "claim", "")) or "Afirmacion documentada sin texto disponible.",
            "review_note": str(_field(row, "review_note", "")) or "Revisar el fragmento citado antes de interpretar efectos.",
        }
        for row in claims[:3]
    ]


def _topic_evidence_rows(rows: list[dict]) -> list[dict]:
    return [
        {
            **dict(row),
            "href": _official_document_fragment_href(
                str(_field(row, "fragment_id", "")),
                int(_field(row, "page", 1) or 1),
            ),
        }
        for row in rows[:6]
    ]


def _official_document_fragment_href(fragment_id: str, page: int = 1) -> str:
    query_parts = []
    if fragment_id:
        query_parts.append(f"fragment_id={quote_plus(fragment_id)}")
    if page:
        query_parts.append(f"page={int(page)}")
    return "/official-document" if not query_parts else "/official-document?" + "&".join(query_parts)


def _document_pdf_href(href: str = PUBLISHED_DOCUMENT_PDF_PUBLIC_HREF, page: int = 1) -> str:
    safe_page = max(int(page or 1), 1)
    return f"{href}#page={safe_page}"



def _pdf_page_value(value: object) -> int | None:
    try:
        page = int(value or 0)
    except (TypeError, ValueError):
        return None
    return page if page > 0 else None


def _fragment_order_page(contexts: list[dict], fragment_id: str) -> int:
    selected = str(fragment_id or "")
    for index, row in enumerate(_json_list(contexts), start=1):
        if str(row.get("fragment_id", "")) == selected:
            return max(_processed_fragment_order(row, index), 1)
    return 1


def _pdf_highlight_target(fragment_id: str, page: int, text_snippet: str) -> dict:
    return PDFHighlightTarget(
        fragment_id=str(fragment_id or ""),
        page=max(int(page or 1), 1),
        text_snippet=str(text_snippet or ""),
        coordinates=None,
    ).to_dict()

def _topic_timeline_rows(rows: list[dict]) -> list[dict]:
    grouped: dict[tuple[str, str, str], dict] = {}
    for row in rows:
        date = str(_field(row, "event_date", ""))
        title = str(_field(row, "title", ""))
        source = str(_field(row, "dataset_name", _field(row, "dataset", "")))
        key = (date, title, source)
        if key not in grouped:
            grouped[key] = {
                "date": _format_chilean_date(date),
                "sort_date": date,
                "status": str(_field(row, "dataset", "")),
                "title": title,
                "description": str(_field(row, "explanation", "")),
                "source": source,
                "origin": "timeline",
                "count": 0,
            }
        grouped[key]["count"] = int(grouped[key]["count"]) + 1
    formatted: list[dict] = []
    for row in sorted(grouped.values(), key=lambda item: (str(item.get("sort_date", "")), str(item.get("title", ""))))[:5]:
        count = int(row.get("count", 0) or 0)
        title = str(row.get("title", ""))
        formatted.append(
            {
                **{key: value for key, value in row.items() if key != "sort_date"},
                "title": f"{title} ({count} registros agrupados)" if count > 1 else title,
                "origin": "timeline",
            }
        )
    return formatted


def _topic_vote_summary(vote_count: int, timeline_rows: list[dict], source: str) -> str:
    grouped_count = len(timeline_rows)
    if grouped_count:
        return f"{vote_count} votaciones registradas en {source}, agrupadas en {grouped_count} hitos visibles."
    return f"{vote_count} votaciones registradas en {source}."


def _topic_status_rows(
    *,
    document_available: bool,
    expediente_available: bool,
    votes_available: bool,
    text_processed: bool,
) -> list[dict]:
    return [
        {"label": "Documento fuente disponible", "status": "Disponible" if document_available else "No disponible", "ready": document_available},
        {"label": "Expediente disponible", "status": "Disponible" if expediente_available else "No disponible", "ready": expediente_available},
        {"label": "Votaciones disponibles", "status": "Disponible" if votes_available else "No disponible", "ready": votes_available},
        {"label": "Texto completo procesado", "status": "Disponible" if text_processed else "No disponible", "ready": text_processed},
    ]


def _topic_hero_answer_rows(title: str, document_count: int, vote_count: int, evidence_count: int) -> list[dict]:
    return [
        {
            "title": "Qué es",
            "body": f"Un tema público sobre {title}, armado desde la lectura documentada y el expediente cargado.",
            "class_name": "topic-answer-card topic-card-document",
        },
        {
            "title": "Por qué importa",
            "body": "Permite revisar el presupuesto, sus hitos y sus respaldos sin saltar entre pantallas desconectadas.",
            "class_name": "topic-answer-card topic-card-proposes",
        },
        {
            "title": "Qué hay aquí",
            "body": f"{document_count} documento, {evidence_count} evidencias de expediente y {vote_count} votaciones disponibles.",
            "class_name": "topic-answer-card topic-card-evidence",
        },
    ]


def _topic_tracking_summary(rows: list[dict], investigation: dict) -> str:
    if rows:
        first = rows[0]
        return f"Primer hito visible: {first.get('date', '')} - {first.get('title', '')}"
    return str(investigation.get("summary", ""))



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


def page_section(title: str, *children, subtitle: str | None = None, class_name: str = "", element_id: str = "") -> rx.Component:
    title_key = title.lower() if isinstance(title, str) else ""
    section_icon = "?"
    if "buscar" in title_key:
        section_icon = "?"
    elif "fuente" in title_key:
        section_icon = "?"
    elif "cronolog" in title_key or "seguimiento" in title_key:
        section_icon = "?"
    elif "document" in title_key or "lectura" in title_key:
        section_icon = "?"
    elif "proyecto" in title_key:
        section_icon = "?"
    elif "studio" in title_key:
        section_icon = "?"
    elif "informe" in title_key:
        section_icon = "?"
    body = [rx.hstack(rx.text(section_icon, class_name="section-icon"), rx.text(title, class_name="section-title"), spacing="2", align="center")]
    if subtitle is not None:
        body.append(rx.text(subtitle, class_name="section-subtitle"))
    body.extend(children)
    section_class = "page-section" if not class_name else f"page-section {class_name}"
    return rx.vstack(*body, spacing="3", align="stretch", class_name=section_class, id=element_id)


def _public_url(path: str) -> str:
    normalized = path if path.startswith("/") else f"/{path}"
    return f"{PUBLIC_SITE_URL}{normalized}"


PUBLIC_OG_IMAGE_URL = _public_url(PUBLIC_OG_IMAGE_PATH)


def _page_meta(path: str, keywords: str, title: str, description: str, *, og_type: str = "website") -> list[dict | rx.Component]:
    canonical_url = _public_url(path)
    return [
        {"name": "keywords", "content": keywords},
        {"name": "author", "content": PUBLIC_SITE_AUTHOR},
        {"name": "theme-color", "content": PUBLIC_THEME_COLOR},
        {"property": "og:type", "content": og_type},
        {"property": "og:site_name", "content": PUBLIC_SITE_NAME},
        {"property": "og:locale", "content": "es_CL"},
        {"property": "og:url", "content": canonical_url},
        {"property": "og:title", "content": title},
        {"property": "og:description", "content": description},
        {"property": "og:image", "content": PUBLIC_OG_IMAGE_URL},
        {"property": "og:image:alt", "content": PUBLIC_OG_IMAGE_ALT},
        {"name": "twitter:card", "content": "summary_large_image"},
        {"name": "twitter:title", "content": title},
        {"name": "twitter:description", "content": description},
        {"name": "twitter:image", "content": PUBLIC_OG_IMAGE_URL},
        rx.el.link(rel="canonical", href=canonical_url),
    ]


def _public_error_message(action: str, *, next_step: str = "Puedes recargar, volver al inicio o seguir con una ruta estable.") -> str:
    return f"No pudimos {action}. {next_step}"


def loading_placeholder_card(title: str, body: str) -> rx.Component:
    return rx.box(
        rx.text(title, class_name="card-title"),
        rx.box(class_name="loading-skeleton-line loading-skeleton-line-medium"),
        rx.box(class_name="loading-skeleton-line"),
        rx.box(class_name="loading-skeleton-line loading-skeleton-line-short"),
        rx.text(body, class_name="muted small"),
        class_name="card loading-skeleton-card",
    )


def public_hydrate_fallback() -> rx.Component:
    return rx.box(
        rx.box(
            rx.hstack(
                rx.text(PUBLIC_SITE_NAME, class_name="brand"),
                rx.text("Cargando una lectura verificable...", class_name="muted small"),
                justify="between",
                align="center",
                class_name="nav-inner",
            ),
            class_name="shell-header",
        ),
        rx.vstack(
            rx.box(
                rx.box(class_name="loading-skeleton-line loading-skeleton-line-short"),
                rx.box(class_name="loading-skeleton-line loading-skeleton-line-medium"),
                rx.box(class_name="loading-skeleton-line"),
                class_name="hero loading-skeleton-hero",
            ),
            rx.grid(
                loading_placeholder_card("Preparando documento", "Montamos la lectura principal y sus enlaces públicos."),
                loading_placeholder_card("Sincronizando evidencia", "Organizamos fragmentos, referencias y contexto ciudadano."),
                loading_placeholder_card("Abriendo rutas útiles", "Dejamos lista la navegación a búsqueda, fuentes e informes."),
                columns="3",
                spacing="3",
                class_name="responsive-grid loading-skeleton-grid",
            ),
            spacing="5",
            align="stretch",
            class_name="page",
        ),
        class_name="shell theme-dark loading-shell",
    )


def card_grid_or_empty(rows, renderer, *, columns: str, empty_title: str, empty_body: str, action_label: str, href: str, class_name: str = "responsive-grid") -> rx.Component:  # noqa: ANN001
    return rx.cond(
        rows,
        rx.grid(
            rx.foreach(rows, renderer),
            columns=columns,
            spacing="3",
            class_name=class_name,
        ),
        investigation_entry_card(empty_title, empty_body, action_label, href, "button button-secondary"),
    )


def not_found_document_illustration() -> rx.Component:
    return rx.box(
        rx.box(
            rx.box(class_name="not-found-document-tab"),
            rx.box(
                rx.box(class_name="not-found-document-line"),
                rx.box(class_name="not-found-document-line not-found-document-line-medium"),
                rx.box(class_name="not-found-document-line not-found-document-line-short"),
                class_name="not-found-document-body",
            ),
            class_name="not-found-document-card",
        ),
        rx.text("Sin evidencia", class_name="not-found-badge"),
        class_name="not-found-illustration",
        role="img",
        aria_label="Ilustración de expediente sin evidencia",
    )


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
    self.state_graph_connection_rows = []
    self.state_graph_source_rows = []
    self.state_graph_summary_text = ""
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
    self.investigation_key_points = []
    self.investigation_questions = []
    self.investigation_limitations = []
    self.investigation_neutrality_notice = ""
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
        return "Registro local de muestra"
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
    source_text = ", ".join(dataset_badges[:6]) if dataset_badges else "fuentes locales disponibles"
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
            "target_href": _clean(_field(row, "target_href"), ""),
            "action_label": _clean(_field(row, "action_label"), "Relacionado"),
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
                "target_href": "",
                "action_label": "Relacionado",
            }
        )
    for row in lobby[:3]:
        groups["Reuniones y registros"].append(
            {
                "title": _clean(_field(row, "title"), "Reunion registrada"),
                "type": "Lobby",
                "why": _clean(_field(row, "facts_text"), "Aparece por una reunion registrada localmente."),
                "source": _clean(_field(row, "dataset"), "Lobby"),
                "target_href": "",
                "action_label": "Relacionado",
            }
        )
    for row in procurement[:3]:
        groups["Compras y presupuestos"].append(
            {
                "title": _clean(_field(row, "title"), "Compra publica"),
                "type": "Compra publica",
                "why": _clean(_field(row, "facts_text"), "Aparece por una compra publica local."),
                "source": _clean(_field(row, "dataset"), "ChileCompra"),
                "target_href": "",
                "action_label": "Relacionado",
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
    header_search_open: bool = False
    header_search_query: str = ""
    sidebar_collapsed: bool = True
    advanced_nav_open: bool = False
    topic_view_mode: str = "lectura"

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
    real_data_sources: list[dict] = []
    real_data_ready_count: int = 0
    real_data_partial_count: int = 0
    real_data_demo_count: int = 0
    real_data_without_loader_count: int = 0
    connection_rows: list[dict] = []
    connection_rows_preview: list[dict] = []
    discovery_case_rows: list[dict] = []
    discovery_case_preview: list[dict] = []
    current_topic_rows: list[dict] = []
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
    state_graph_connection_rows: list[dict] = []
    state_graph_source_rows: list[dict] = []
    state_graph_summary_text: str = ""
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
    investigation_key_points: list[dict] = []
    investigation_questions: list[str] = []
    investigation_limitations: list[str] = []
    investigation_neutrality_notice: str = ""
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
    knowledge_pages: list[dict] = []
    knowledge_fragments: list[dict] = []
    knowledge_document_paragraphs: list[dict] = []
    knowledge_document_source_path: str = ""
    knowledge_document_source_is_fallback: bool = False
    knowledge_document_has_pdf: bool = False
    knowledge_document_pdf_path: str = ""
    knowledge_document_pdf_href: str = ""
    knowledge_document_pdf_page_href: str = ""
    knowledge_citations: list[dict] = []
    knowledge_connections: list[dict] = []
    knowledge_notice: str = ""
    knowledge_expediente_target: str = DEMO_INVESTIGATION_TARGET
    knowledge_selected_page: int = 18
    knowledge_selected_fragment_id: str = ""
    knowledge_selected_reference_label: str = "Pagina 18"
    knowledge_selected_excerpt: str = ""
    knowledge_selected_summary: list[dict] = []
    knowledge_selected_questions: list[dict] = []
    knowledge_selected_claims: list[dict] = []
    knowledge_selected_evidence: list[dict] = []
    knowledge_selected_connections: list[dict] = []
    knowledge_pdf_highlight_target: dict = {}
    knowledge_selected_page_is_approximate: bool = False
    knowledge_pdf_location_notice: str = ""
    knowledge_fragment_contexts: list[dict] = []
    knowledge_fragment_count: int = 0
    knowledge_total_fragment_count: int = 0
    knowledge_question_count: int = 0
    knowledge_claim_count: int = 0
    knowledge_reference_count: int = 0
    knowledge_coverage_text: str = ""
    knowledge_reference_text: str = ""
    knowledge_share_path: str = ""
    knowledge_share_url: str = ""
    knowledge_share_title: str = ""
    knowledge_share_x_url: str = ""
    knowledge_share_whatsapp_url: str = ""
    knowledge_share_linkedin_url: str = ""
    knowledge_share_copy_script: str = ""
    knowledge_error: str = ""
    topic_title: str = TOPIC_BUDGET_2013_TITLE
    topic_status: str = ""
    topic_read_time: str = ""
    topic_document_count: int = 0
    topic_updated_at: str = ""
    topic_organizations_text: str = ""
    topic_official_document: dict = {}
    topic_proposes_rows: list[dict] = []
    topic_changes_rows: list[dict] = []
    topic_no_changes_rows: list[dict] = []
    topic_timeline_rows: list[dict] = []
    topic_evidence_rows: list[dict] = []
    topic_state_graph_rows: list[dict] = []
    topic_reading_rows: list[dict] = []
    topic_expediente_title: str = ""
    topic_expediente_summary: str = ""
    topic_expediente_metrics: str = ""
    topic_tracking_summary: str = ""
    topic_vote_summary: str = ""
    topic_vote_count: int = 0
    topic_status_rows: list[dict] = []
    topic_hero_answer_rows: list[dict] = []
    topic_original_url: str = ""
    investigation_status_message: str = ""
    investigation_status: str = INVESTIGATION_STATUS_IDLE
    requested_investigation_target: str = ""
    last_loaded_investigation_target: str = ""
    last_valid_investigation_target: str = ""
    investigation_loaded: bool = False
    investigation_loading: bool = False

    def toggle_header_search(self) -> None:
        self.header_search_open = not self.header_search_open
        if not self.header_search_open:
            self.header_search_query = ""

    def toggle_sidebar(self) -> None:
        self.sidebar_collapsed = not self.sidebar_collapsed

    def toggle_advanced_nav(self) -> None:
        self.advanced_nav_open = not self.advanced_nav_open

    def set_topic_view_mode(self, mode: str) -> None:
        self.topic_view_mode = mode

    def set_header_search_query(self, value: str) -> None:
        self.header_search_query = value

    def submit_header_search(self):
        query = str(self.header_search_query or self.query or "").strip()
        if not query:
            self.header_search_open = False
            self.header_search_query = ""
            return None
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
            self.current_topic_rows = [
                {
                    **row,
                    "updated_at": _format_chilean_date(row.get("updated_at", "")),
                }
                for row in _json_list(get_current_topics(limit=3))
            ]
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
                    "population_records": int(row.get("population_records", 0) or 0),
                    "population_summary": str(row.get("population_summary", "")),
                    "population_status_label": str(row.get("population_status_label", "")),
                    "population_label": (
                        f"poblacion minima: {row.get('population_status_label', '')} ({int(row.get('population_records', 0) or 0)} registro). {row.get('population_summary', '')}"
                        if int(row.get("population_records", 0) or 0)
                        else ""
                    ),
                    "connector_label": (
                        f"connector: {row.get('connector_status', '')} | entidades {int(row.get('connector_entities', 0) or 0)} | relaciones {int(row.get('connector_relationships', 0) or 0)} | eventos {int(row.get('connector_events', 0) or 0)}"
                        if str(row.get("connector_status", ""))
                        else ""
                    ),
                    "state_graph_contribution_label": (
                        f"Aporta conexiones al StateGraph: {int(row.get('connector_relationships', 0) or 0)} relaciones documentadas."
                        if int(row.get("connector_relationships", 0) or 0)
                        else ""
                    ),
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
            readiness = _json_dict(get_real_data_readiness())
            self.real_data_sources = [
                {
                    **dict(row),
                    "entity_types_text": " | ".join(str(item) for item in row.get("entity_types", [])),
                    "last_loaded_text": str(row.get("last_loaded", "from_database")),
                    "official_url_text": str(row.get("official_url", "")) or "Pendiente",
                }
                for row in _json_list(readiness.get("entries", []))
            ]
            totals = _json_dict(readiness.get("totals", {}))
            self.real_data_ready_count = int(totals.get("ready", 0) or 0)
            self.real_data_partial_count = int(totals.get("partial", 0) or 0)
            self.real_data_demo_count = int(totals.get("demo", 0) or 0)
            self.real_data_without_loader_count = int(totals.get("without_loader", 0) or 0)
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
                    "state_graph_badges_text": _state_graph_badges_for_match(row),
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
            self.knowledge_pages = _json_list(demo.get("pages", []))
            self.knowledge_citations = _json_list(demo.get("citations", []))
            self.knowledge_key_points = _json_list(demo.get("key_points", []))
            self.knowledge_questions = _json_list(demo.get("citizen_questions", demo.get("questions", [])))
            self.knowledge_claims = _json_list(demo.get("claims", []))
            self.knowledge_evidence = _json_list(demo.get("references", demo.get("evidence", [])))
            self.knowledge_fragments = _json_list(demo.get("fragments", []))
            document_fragments, document_source_path, document_source_is_fallback = _load_document_fragments_with_source(self.knowledge_fragments)
            self.knowledge_document_paragraphs = _document_paragraphs_from_fragments(document_fragments)
            self.knowledge_document_source_path = document_source_path
            self.knowledge_document_source_is_fallback = document_source_is_fallback
            self.knowledge_document_has_pdf = PUBLISHED_DOCUMENT_PDF_ASSET_PATH.exists()
            self.knowledge_document_pdf_path = str(PUBLISHED_DOCUMENT_PDF_PATH) if self.knowledge_document_has_pdf else ""
            self.knowledge_document_pdf_href = _document_pdf_href(PUBLISHED_DOCUMENT_PDF_PUBLIC_HREF, 1) if self.knowledge_document_has_pdf else ""
            self.knowledge_document_pdf_page_href = self.knowledge_document_pdf_href
            self.knowledge_fragment_contexts = _json_list(demo.get("fragment_contexts", []))
            selected_context = _json_dict(demo.get("selected_context", {}))
            requested_fragment_id = _router_query_value(self.router, "fragment_id")
            if requested_fragment_id:
                selected_context = next(
                    (
                        row
                        for row in _json_list(demo.get("fragment_contexts", []))
                        if str(row.get("fragment_id", "")) == requested_fragment_id
                    ),
                    selected_context,
                )
            requested_page = _pdf_page_value(_router_query_value(self.router, "page"))
            context_page = _pdf_page_value(selected_context.get("page"))
            self.knowledge_selected_fragment_id = str(selected_context.get("fragment_id", demo.get("default_fragment_id", "")))
            self.knowledge_selected_page_is_approximate = context_page is None and requested_page is None
            self.knowledge_selected_page = context_page or requested_page or _fragment_order_page(self.knowledge_fragment_contexts, self.knowledge_selected_fragment_id)
            self.knowledge_pdf_location_notice = PDF_LOCATION_APPROXIMATE_NOTICE if self.knowledge_selected_page_is_approximate else ""
            self.knowledge_selected_reference_label = str(selected_context.get("reference_label", "")) or f"Pagina {self.knowledge_selected_page}"
            self.knowledge_selected_excerpt = str(selected_context.get("excerpt", ""))
            self.knowledge_selected_summary = _json_list(selected_context.get("summary", []))
            self.knowledge_selected_questions = _json_list(selected_context.get("questions", []))
            self.knowledge_selected_claims = _json_list(selected_context.get("claims", []))
            self.knowledge_selected_evidence = _json_list(selected_context.get("evidence", []))
            self.knowledge_selected_connections = _json_list(selected_context.get("connections", []))
            self.knowledge_pdf_highlight_target = _pdf_highlight_target(self.knowledge_selected_fragment_id, self.knowledge_selected_page, self.knowledge_selected_excerpt)
            self.knowledge_document_pdf_href = _document_pdf_href(PUBLISHED_DOCUMENT_PDF_PUBLIC_HREF, 1) if self.knowledge_document_has_pdf else ""
            self.knowledge_document_pdf_page_href = _document_pdf_href(PUBLISHED_DOCUMENT_PDF_PUBLIC_HREF, self.knowledge_selected_page) if self.knowledge_document_has_pdf else ""
            self.knowledge_connections = [
                {"label": str(key), "value": str(value)}
                for key, value in _json_dict(demo.get("connections", {})).items()
            ]
            self.knowledge_notice = str(_field(demo, "notice", ""))
            self.knowledge_expediente_target = str(_field(demo, "related_expediente", _field(document, "related_expediente_target", DEMO_INVESTIGATION_TARGET)))
            metrics = {str(row.get("id", "")): int(row.get("value", 0) or 0) for row in _json_list(demo.get("metrics", []))}
            coverage = _json_dict(demo.get("document_coverage", {}))
            self.knowledge_fragment_count = metrics.get("fragments", 0)
            self.knowledge_total_fragment_count = int(coverage.get("total_fragments", len(self.knowledge_fragments)) or len(self.knowledge_fragments))
            self.knowledge_question_count = metrics.get("questions", 0)
            self.knowledge_claim_count = metrics.get("claims", 0)
            self.knowledge_reference_count = metrics.get("references", 0)
            self.knowledge_coverage_text = str(coverage.get("label", "")) or f"Fragmentos utilizados: {self.knowledge_fragment_count} de {self.knowledge_total_fragment_count}"
            self.knowledge_reference_text = str(coverage.get("references_label", "")) or f"Referencias: {self.knowledge_reference_count}"
            if hasattr(self, "_set_document_share_links"):
                self._set_document_share_links()
        except Exception as exc:  # noqa: BLE001
            self.knowledge_documents = []
            self.knowledge_document = {}
            self.knowledge_title = ""
            self.knowledge_summary = ""
            self.knowledge_key_points = []
            self.knowledge_questions = []
            self.knowledge_claims = []
            self.knowledge_evidence = []
            self.knowledge_pages = []
            self.knowledge_fragments = []
            self.knowledge_document_paragraphs = []
            self.knowledge_document_source_path = ""
            self.knowledge_document_source_is_fallback = False
            self.knowledge_document_has_pdf = False
            self.knowledge_document_pdf_path = ""
            self.knowledge_document_pdf_href = ""
            self.knowledge_document_pdf_page_href = ""
            self.knowledge_citations = []
            self.knowledge_connections = []
            self.knowledge_notice = ""
            self.knowledge_expediente_target = DEMO_INVESTIGATION_TARGET
            self.knowledge_selected_page = 18
            self.knowledge_selected_fragment_id = ""
            self.knowledge_selected_reference_label = "Pagina 18"
            self.knowledge_selected_excerpt = ""
            self.knowledge_selected_summary = []
            self.knowledge_selected_questions = []
            self.knowledge_selected_claims = []
            self.knowledge_selected_evidence = []
            self.knowledge_selected_connections = []
            self.knowledge_fragment_contexts = []
            self.knowledge_fragment_count = 0
            self.knowledge_total_fragment_count = 0
            self.knowledge_question_count = 0
            self.knowledge_claim_count = 0
            self.knowledge_reference_count = 0
            self.knowledge_coverage_text = ""
            self.knowledge_reference_text = ""
            self.knowledge_share_path = ""
            self.knowledge_share_url = ""
            self.knowledge_share_title = ""
            self.knowledge_share_x_url = ""
            self.knowledge_share_whatsapp_url = ""
            self.knowledge_share_linkedin_url = ""
            self.knowledge_share_copy_script = ""
            self.knowledge_error = f"{type(exc).__name__}: {exc}"
            self.error_message = self.knowledge_error

    def load_topic(self) -> None:
        self.error_message = ""
        self.load_knowledge()
        document = _json_dict(self.knowledge_document)
        investigation = _json_dict(get_investigation(TOPIC_BUDGET_2013_TARGET))
        legislative = _json_dict(investigation.get("legislative", {}))
        compact_metrics = _json_dict(investigation.get("compact_metrics", {}))
        source_records = _json_list(legislative.get("source_records", []))
        organizations = _topic_organizations(document, source_records, investigation)
        timeline_rows = _json_list(investigation.get("timeline", []))
        self.topic_title = TOPIC_BUDGET_2013_TITLE
        self.topic_status = str(document.get("official_status", "")) or str(investigation.get("official_status", ""))
        self.topic_read_time = _topic_read_time(self.knowledge_fragments)
        self.topic_document_count = 1 if document else 0
        self.topic_updated_at = _format_chilean_date(document.get("published_at", "")) or _topic_latest_record_date(source_records)
        self.topic_organizations_text = " | ".join(organizations)
        self.topic_official_document = {
            "title": str(document.get("title", self.topic_title)),
            "source": str(document.get("source", "")),
            "document_type": str(document.get("document_type", "")),
            "published_at": _format_chilean_date(document.get("published_at", "")),
            "summary": str(self.knowledge_summary),
            "official_url": str(document.get("official_url", "")),
        }
        self.topic_proposes_rows = self.knowledge_key_points[:3]
        self.topic_changes_rows = _topic_change_rows(self.knowledge_claims)
        self.topic_no_changes_rows = _topic_no_change_rows(self.knowledge_claims, self.knowledge_notice)
        self.topic_timeline_rows = _topic_timeline_rows(timeline_rows)
        self.topic_evidence_rows = _topic_evidence_rows(self.knowledge_evidence)
        self.topic_reading_rows = [
            {
                "title": self.knowledge_title or self.topic_title,
                "summary": self.knowledge_summary,
                "href": "/official-document",
                "coverage": self.knowledge_coverage_text,
            }
        ]
        self.topic_expediente_title = str(_field(investigation.get("entity", {}), "name", "Boletin 8575-05"))
        self.topic_expediente_summary = str(investigation.get("narrative_summary", investigation.get("summary", "")))
        self.topic_expediente_metrics = (
            f"Evidencia: {int(compact_metrics.get('evidence_count', 0) or 0)} | "
            f"Relaciones: {int(compact_metrics.get('relationship_count', 0) or 0)}"
        )
        self.topic_tracking_summary = _topic_tracking_summary(self.topic_timeline_rows, investigation)
        self.topic_vote_count = int(legislative.get("votes_found", 0) or 0)
        self.topic_vote_summary = (
            _topic_vote_summary(self.topic_vote_count, self.topic_timeline_rows, str(legislative.get("source", "Datos Abiertos Legislativos")))
            if self.topic_vote_count
            else "La vista de expediente no expone votaciones para este tema."
        )
        self.topic_status_rows = _topic_status_rows(
            document_available=bool(document),
            expediente_available=bool(investigation.get("found", False)),
            votes_available=self.topic_vote_count > 0,
            text_processed=bool(self.knowledge_fragments),
        )
        self.topic_hero_answer_rows = _topic_hero_answer_rows(
            title=self.topic_title,
            document_count=self.topic_document_count,
            vote_count=self.topic_vote_count,
            evidence_count=int(compact_metrics.get("evidence_count", 0) or 0),
        )
        self.topic_original_url = str(document.get("official_url", ""))
        try:
            topic_graph = build_state_graph(TOPIC_BUDGET_2013_TARGET).to_dict()
        except Exception:
            topic_graph = {}
        self.topic_state_graph_rows = _format_state_graph_topic_rows(topic_graph)

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

    def select_document_anchor(self, page: int, fragment_id: str) -> None:
        requested_page = _pdf_page_value(page)
        if requested_page is not None:
            self.knowledge_selected_page = requested_page
        selected_fragment = str(fragment_id or "")
        if not selected_fragment and requested_page is not None:
            page_context = next((row for row in self.knowledge_fragment_contexts if _pdf_page_value(row.get("page")) == requested_page), {})
            selected_fragment = str(page_context.get("fragment_id", ""))
        self._set_document_reading_context(selected_fragment, requested_page)

    def _set_document_reading_context(self, fragment_id: str, requested_page: int | None = None) -> None:
        selected = str(fragment_id or "")
        context = next((row for row in self.knowledge_fragment_contexts if str(row.get("fragment_id", "")) == selected), {})
        if not context:
            context = self.knowledge_fragment_contexts[0] if self.knowledge_fragment_contexts else {}
        self.knowledge_selected_fragment_id = str(context.get("fragment_id", selected))
        context_page = _pdf_page_value(context.get("page"))
        self.knowledge_selected_page_is_approximate = context_page is None and requested_page is None
        self.knowledge_selected_page = context_page or requested_page or _fragment_order_page(self.knowledge_fragment_contexts, self.knowledge_selected_fragment_id)
        self.knowledge_pdf_location_notice = PDF_LOCATION_APPROXIMATE_NOTICE if self.knowledge_selected_page_is_approximate else ""
        self.knowledge_selected_reference_label = str(context.get("reference_label", "")) or f"Pagina {self.knowledge_selected_page}"
        self.knowledge_selected_excerpt = str(context.get("excerpt", ""))
        self.knowledge_selected_summary = _json_list(context.get("summary", []))
        self.knowledge_selected_questions = _json_list(context.get("questions", []))
        self.knowledge_selected_claims = _json_list(context.get("claims", []))
        self.knowledge_selected_evidence = _json_list(context.get("evidence", []))
        self.knowledge_selected_connections = _json_list(context.get("connections", []))
        self.knowledge_pdf_highlight_target = _pdf_highlight_target(self.knowledge_selected_fragment_id, self.knowledge_selected_page, self.knowledge_selected_excerpt)
        self.knowledge_document_pdf_page_href = _document_pdf_href(PUBLISHED_DOCUMENT_PDF_PUBLIC_HREF, self.knowledge_selected_page) if getattr(self, "knowledge_document_has_pdf", False) else ""
        if hasattr(self, "_set_document_share_links"):
            self._set_document_share_links()

    def _set_document_share_links(self) -> None:
        share_path = _official_document_fragment_href(self.knowledge_selected_fragment_id, self.knowledge_selected_page)
        self.knowledge_share_path = share_path
        self.knowledge_share_url = _public_url(share_path)
        self.knowledge_share_title = f"{self.knowledge_selected_reference_label} - DatosEnOrden"
        encoded_url = quote_plus(self.knowledge_share_url)
        encoded_title = quote_plus(self.knowledge_share_title)
        self.knowledge_share_x_url = f"https://twitter.com/intent/tweet?url={encoded_url}&text={encoded_title}"
        self.knowledge_share_whatsapp_url = f"https://wa.me/?text={quote_plus(self.knowledge_share_title + ' ' + self.knowledge_share_url)}"
        self.knowledge_share_linkedin_url = f"https://www.linkedin.com/sharing/share-offsite/?url={encoded_url}"
        self.knowledge_share_copy_script = f"navigator.clipboard.writeText({json.dumps(self.knowledge_share_url)})"

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
            try:
                state_graph = build_state_graph(resolved_entity_id).to_dict()
            except Exception:
                state_graph = {}
        except Exception as exc:  # noqa: BLE001
            if had_valid_state:
                self.investigation_status = INVESTIGATION_STATUS_LOADED
                self.requested_investigation_target = ""
                self.investigation_status_message = "No se pudo refrescar el expediente ahora mismo; se conserva la vista ya cargada."
                _debug_investigation("preserved previous state", received=target, reason=type(exc).__name__)
                return
            _clear_investigation_state(self)
            self.requested_investigation_target = target
            self.last_valid_investigation_target = target
            self.investigation_status = INVESTIGATION_STATUS_ERROR
            self.error_message = _public_error_message("abrir el expediente")
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
        self.state_graph_connection_rows = _format_state_graph_connection_rows(state_graph)
        self.state_graph_source_rows = _format_state_graph_source_rows(state_graph)
        state_summary = _json_dict(state_graph.get("summary", {}))
        self.state_graph_summary_text = (
            f"{int(state_summary.get('nodes', 0) or 0)} nodos y {int(state_summary.get('edges', 0) or 0)} conexiones observadas desde evidencia disponible."
            if state_summary
            else "Conexiones observadas desde evidencia disponible."
        )
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
        knowledge = _json_dict(data.get("knowledge") or get_investigation_knowledge(data))
        self.citizen_summary = str(
            _field(knowledge, "citizen_summary", "")
            or _citizen_summary_text(
                self.entity_name,
                self.datasets_involved,
                self.evidence_count,
                self.relationship_count,
                self.connected_entities,
                self.dataset_badges,
            )
        )
        self.investigation_key_points = [
            {
                "text": str(_field(item, "text", "")),
                "sources_text": " | ".join(str(value) for value in _field(item, "source_ids", [])),
                "evidence_text": " | ".join(str(value) for value in _field(item, "evidence_ids", [])),
            }
            for item in _json_list(_field(knowledge, "key_points", []))
        ]
        self.investigation_questions = [str(item) for item in _field(knowledge, "suggested_questions", [])]
        self.investigation_limitations = [str(item) for item in _field(knowledge, "limitations", [])]
        self.investigation_neutrality_notice = str(_field(knowledge, "neutrality_notice", ""))
        self.canonical_investigation_link = f"{PUBLIC_SITE_URL}{_investigation_href(self.entity_name or target)}"
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


def _sidebar_nav_class(active: bool) -> str:
    return "sidebar-nav-link sidebar-nav-link-active" if active else "sidebar-nav-link"


def _nav_icon_for_label(label: str) -> str:
    normalized = label.lower()
    if normalized.startswith("pulso"):
        return "?"
    if normalized.startswith("lectura"):
        return "?"
    if normalized.startswith("buscar"):
        return "?"
    if normalized.startswith("fuentes"):
        return "?"
    if normalized.startswith("proyecto"):
        return "?"
    if normalized.startswith("expediente"):
        return "?"
    if normalized.startswith("informes"):
        return "?"
    if normalized.startswith("cronologia"):
        return "?"
    return label[:1].upper() or "?"


def sidebar_nav_link(label: str, href: str, active: bool) -> rx.Component:
    return rx.link(
        rx.text(_nav_icon_for_label(label), class_name="sidebar-initial"),
        rx.text(label, class_name="sidebar-label"),
        href=href,
        class_name=_sidebar_nav_class(active),
    )


def hamburger_icon() -> rx.Component:
    return rx.vstack(
        rx.box(class_name="hamburger-line"),
        rx.box(class_name="hamburger-line"),
        rx.box(class_name="hamburger-line"),
        spacing="1",
        align="center",
        class_name="hamburger-icon",
    )


def sidebar_group_label(label: str) -> rx.Component:
    return rx.text(label, class_name="sidebar-group-label")


def app_sidebar(active_page: str) -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.button(
                hamburger_icon(),
                on_click=AppState.toggle_sidebar,
                class_name="sidebar-menu-button",
            ),
            sidebar_nav_link("Pulso", "/", active_page == PAGE_HOME),
            sidebar_nav_link("Lectura", "/topic", active_page == PAGE_TOPIC),
            sidebar_nav_link("Buscar", "/search", active_page == PAGE_SEARCH),
            sidebar_nav_link("Fuentes", "/ecosystem", active_page == PAGE_ECOSYSTEM),
            sidebar_nav_link("Proyecto", "/project", active_page == PAGE_PROJECT),
            rx.box(class_name="sidebar-spacer"),
            sidebar_nav_link("Expediente", "/investigation", active_page == PAGE_INVESTIGATION),
            sidebar_nav_link("Informes", "/reports", active_page == PAGE_REPORTS),
            sidebar_nav_link("Cronologia", "/tracking", active_page == PAGE_TRACKING),
            spacing="1",
            align="stretch",
            class_name="sidebar-nav",
        ),
        class_name=rx.cond(AppState.sidebar_collapsed, "app-sidebar app-sidebar-collapsed", "app-sidebar"),
    )

def scroll_top_control() -> rx.Component:
    return rx.box(
        rx.script(
            """
            (() => {
              if (window.__deoScrollTopReady) return;
              window.__deoScrollTopReady = true;
              const updateScrollTopButton = () => {
                const button = document.getElementById('scroll-top-button');
                if (!button) return;
                button.classList.toggle('scroll-top-visible', window.scrollY > window.innerHeight * 0.9);
              };
              window.addEventListener('scroll', updateScrollTopButton, { passive: true });
              window.addEventListener('resize', updateScrollTopButton);
              setTimeout(updateScrollTopButton, 80);
            })();
            """
        ),
        rx.button(
            "Volver arriba",
            id="scroll-top-button",
            on_click=rx.call_script("window.scrollTo({ top: 0, behavior: 'smooth' })"),
            class_name="scroll-top-button",
        ),
    )


def shell(*children: rx.Component, active_page: str, **props) -> rx.Component:
    header_search = rx.box(
        rx.cond(
            AppState.header_search_open,
            rx.hstack(
                rx.input(
                    placeholder="Buscar entidad",
                    value=AppState.header_search_query,
                    on_change=AppState.set_header_search_query,
                    class_name="input header-search-input",
                    aria_label="Buscar entidad",
                ),
                rx.button("Ir", on_click=AppState.submit_header_search, class_name="header-search-submit"),
                spacing="2",
                align="center",
                class_name="header-search-popover header-search-popover-open",
            ),
            rx.button("Buscar", on_click=AppState.toggle_header_search, class_name="header-search-toggle"),
        ),
        class_name="header-search",
    )
    shell_class = rx.cond(
        AppState.sidebar_collapsed,
        f"shell theme-dark sidebar-collapsed {_page_class(active_page)}",
        f"shell theme-dark {_page_class(active_page)}",
    )
    return rx.box(
        app_sidebar(active_page),
        rx.box(
            rx.box(
                rx.hstack(
                    rx.link("DatosEnOrden", href="/", class_name="brand"),
                    header_search,
                    justify="between",
                    align="center",
                    class_name="nav-inner",
                ),
                class_name="shell-header shell-header-sidebar-ready",
            ),
            rx.cond(
                AppState.error_message != "",
                rx.box(
                    rx.text("Esta pagina necesita una segunda carga", class_name="eyebrow"),
                    rx.text(
                        "No pudimos actualizar por completo esta vista con los datos locales disponibles. Puedes reintentar o volver a una ruta estable.",
                        class_name="muted",
                    ),
                    rx.hstack(
                        rx.button("Volver al inicio", on_click=rx.redirect("/"), class_name="button button-secondary"),
                        rx.button("Buscar", on_click=rx.redirect("/search"), class_name="button button-secondary"),
                        spacing="2",
                        wrap="wrap",
                        class_name="shell-alert-actions",
                    ),
                    class_name="card error shell-alert",
                ),
            ),
            rx.vstack(*children, spacing="5", align="stretch", class_name="page"),
            app_footer(),
            class_name="shell-main",
        ),
        scroll_top_control(),
        class_name=shell_class,
        **props,
    )


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
    }.get(active_page, "page-home")


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


def app_footer() -> rx.Component:
    return rx.box(
        rx.grid(
            rx.box(
                rx.text("PARA CIUDADANOS", class_name="footer-column-title"),
                rx.text("Explorar, leer y verificar información pública sin perder el contexto documental.", class_name="footer-copy footer-column-copy"),
                footer_text_link("♥", "Apoyar DatosEnOrden", "/support"),
                footer_text_link("⌕", "Buscar en el sitio", "/search"),
                footer_text_link("+", "Sugerir una fuente", SUPPORT_SOURCE_SUGGESTION_URL),
                footer_text_link("i", "Sobre el proyecto", "/project"),
                class_name="footer-column",
            ),
            rx.box(
                rx.text("DATOSENORDEN STUDIO", class_name="footer-column-title"),
                rx.text("DATOSENORDEN STUDIO", class_name="footer-column-title"),
                rx.text("Puerta para organizaciones que necesitan expedientes, conectores y evidencia verificable.", class_name="footer-copy footer-column-copy"),
                footer_text_link("✉", "Contacto comercial", STUDIO_CONVERSATION_URL),
                footer_text_link("☁", "Studio", "/studio"),
                footer_text_link("▣", "Ver lectura", "/topic"),
                footer_text_link("↳", "Seguir cronología", "/tracking"),
            ),
            columns="2",
            spacing="4",
            class_name="footer-grid",
        ),
        rx.text("DatosEnOrden trabaja con datos locales de prueba y evidencia trazable, nunca con humo ni conclusiones automáticas.", class_name="footer-copy footer-bottom-copy"),
        class_name="site-footer",
    )


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
                AppState.knowledge_share_url != "",
                rx.link("Compartir lectura", href=AppState.knowledge_share_url, class_name="document-inline-link"),
                rx.text("Abre Lectura para compartir", class_name="mini-pill"),
            ),
            spacing="2",
            wrap="wrap",
        ),
        class_name="support-inline-block",
    )


def support_action_card(title: str, body: str, label: str, href: str) -> rx.Component:
    return rx.box(
        rx.text(title, class_name="card-title"),
        rx.text(body, class_name="muted small"),
        rx.link(label, href=href, class_name="document-inline-link support-action-link"),
        class_name="card support-action-card",
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
        rx.cond(
            row["population_label"] != "",
            rx.text(row["population_label"], class_name="source-fact source-population-note"),
        ),
        rx.cond(
            row["connector_label"] != "",
            rx.text(row["connector_label"], class_name="source-fact"),
        ),
        rx.cond(
            row.get("state_graph_contribution_label", "") != "",
            rx.text(row.get("state_graph_contribution_label", ""), class_name="source-fact evidence-trust"),
        ),
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


def real_data_source_card(row: dict) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.text(row["display_name"], class_name="card-title"),
            rx.text(row["status"], class_name=_accent_badge_class(str(row.get("status", "")))),
            justify="between",
            align="center",
        ),
        rx.text(row["description"], class_name="muted small"),
        rx.hstack(
            rx.text(f"registros: {row['source_records']}", class_name="mini-pill"),
            rx.text(f"entidades: {row['entities']}", class_name="mini-pill"),
            rx.text(f"relaciones: {row['relationships']}", class_name="mini-pill mini-pill-purple"),
            rx.text(f"oficiales: {row.get('official_records', 0)}", class_name="mini-pill evidence-trust"),
            rx.text(f"test/local: {row.get('test_records', 0)}", class_name="mini-pill"),
            spacing="2",
            wrap="wrap",
        ),
        rx.text(f"formato: {row['expected_format']}", class_name="source-fact"),
        rx.text(f"loader: {row['loader_script']}", class_name="technical-line"),
        rx.text(f"ultima carga: {row.get('last_loaded', '')}", class_name="technical-line"),
        rx.text(f"cobertura: {row['coverage']}", class_name="muted small"),
        class_name="card ecosystem-card real-data-card",
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
            rx.text(row.get("trust_label", "Registro local de muestra"), class_name="mini-pill evidence-trust"),
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


def investigation_key_point_card(row: dict) -> rx.Component:
    return rx.box(
        rx.text(row["text"], class_name="muted"),
        rx.cond(
            row["evidence_text"] != "",
            rx.text(f"Evidencia: {row['evidence_text']}", class_name="source-fact"),
        ),
        rx.cond(
            row["sources_text"] != "",
            rx.text(f"Fuentes: {row['sources_text']}", class_name="mini-pill"),
        ),
        class_name="knowledge-point",
    )



def state_graph_connection_card(row: dict) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.text(row["node_type"], class_name="badge badge-teal"),
            rx.text(row["confidence_label"], class_name="mini-pill evidence-trust"),
            justify="between",
            align="center",
        ),
        rx.text(row["title"], class_name="context-title"),
        rx.text(row["relation_type"], class_name="mini-pill mini-pill-purple"),
        rx.text(f"Fuente/conector: {row['source_connector']}", class_name="source-fact"),
        rx.text(f"Evidencia: {row['evidence_text']}", class_name="muted small"),
        rx.cond(
            row.get("href", "") != "",
            rx.button(row.get("action_label", "Abrir entidad"), on_click=rx.redirect(row["href"]), class_name="button button-secondary"),
            rx.text(row.get("action_label", "Conexi\u00f3n observada"), class_name="mini-pill"),
        ),
        class_name="context-item state-graph-connection-card",
    )


def state_graph_source_chip(row: dict) -> rx.Component:
    return rx.text(row["summary"], class_name="comparison-chip")


def state_graph_connections_panel() -> rx.Component:
    return investigation_panel(
        "Conexiones del Estado",
        rx.text(
            "Relaciones documentadas que el StateGraph conecta desde fuentes, evidencia y eventos disponibles.",
            class_name="muted small",
        ),
        rx.text(AppState.state_graph_summary_text, class_name="source-fact"),
        rx.cond(
            AppState.state_graph_connection_rows,
            rx.grid(
                rx.foreach(AppState.state_graph_connection_rows, state_graph_connection_card),
                columns="2",
                spacing="2",
                class_name="responsive-grid",
            ),
            rx.text("No hay conexiones observadas para este expediente.", class_name="muted small"),
        ),
        rx.cond(
            AppState.state_graph_source_rows,
            rx.hstack(
                rx.foreach(AppState.state_graph_source_rows, state_graph_source_chip),
                spacing="2",
                wrap="wrap",
            ),
        ),
        subtitle="Lenguaje descriptivo: aparece en, vinculado por documento/fuente y relaci\u00f3n documentada.",
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

def citizen_summary_panel() -> rx.Component:
    return investigation_panel(
        "Resumen ciudadano",
        rx.text(AppState.citizen_summary, class_name="story-summary story-summary-dominant"),
        rx.cond(
            AppState.investigation_key_points,
            rx.vstack(
                rx.text("Puntos clave", class_name="context-title"),
                rx.grid(
                    rx.foreach(AppState.investigation_key_points, investigation_key_point_card),
                    columns="2",
                    spacing="2",
                    class_name="responsive-grid",
                ),
                spacing="2",
                align="stretch",
            ),
        ),
        rx.cond(
            AppState.investigation_questions,
            rx.vstack(
                rx.text("Preguntas sugeridas", class_name="context-title"),
                rx.hstack(
                    rx.foreach(AppState.investigation_questions, lambda item: rx.text(item, class_name="search-chip")),
                    spacing="2",
                    wrap="wrap",
                ),
                spacing="2",
                align="stretch",
            ),
        ),
        rx.cond(
            AppState.investigation_limitations,
            rx.vstack(
                rx.text("Limitaciones", class_name="context-title"),
                rx.hstack(
                    rx.foreach(AppState.investigation_limitations, lambda item: rx.text(item, class_name="mini-pill evidence-trust")),
                    spacing="2",
                    wrap="wrap",
                ),
                spacing="2",
                align="stretch",
            ),
        ),
        rx.cond(
            AppState.investigation_neutrality_notice != "",
            rx.text(AppState.investigation_neutrality_notice, class_name="source-fact"),
        ),
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
            rx.text("Registro local de muestra", class_name="mini-pill evidence-trust"),
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
        rx.cond(
            row.get("target_href", "") != "",
            rx.button(row.get("action_label", "Abrir expediente"), on_click=rx.redirect(row["target_href"]), class_name="button button-secondary"),
            rx.text(row.get("action_label", "Relacionado"), class_name="mini-pill"),
        ),
        class_name="context-item related-entity-card",
    )


def related_entity_group(row: dict) -> rx.Component:
    return related_entity_card(row)


def context_entity_card(row: dict) -> rx.Component:
    return rx.box(
        rx.text(row["title"], class_name="context-title"),
        rx.text(row["relationship_type"], class_name="mini-pill mini-pill-purple"),
        rx.text(row["explanation"], class_name="muted small"),
        rx.cond(
            row.get("target_href", "") != "",
            rx.button(row.get("action_label", "Abrir expediente"), on_click=rx.redirect(row["target_href"]), class_name="button button-secondary"),
            rx.text(row.get("action_label", "Relacionado"), class_name="mini-pill"),
        ),
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
            rx.text("?", class_name="source-card-icon"),
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
            rx.text("?", class_name="source-card-icon"),
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
        rx.cond(
            row.get("state_graph_badges_text", "") != "",
            rx.text(row.get("state_graph_badges_text", ""), class_name="source-fact evidence-trust"),
        ),
        rx.hstack(
            rx.text(f"Evidencia: {row['evidence_count']}", class_name="mini-pill"),
            rx.text(f"Relaciones: {row['relationship_count']}", class_name="mini-pill"),
            spacing="2",
            wrap="wrap",
        ),
        rx.hstack(
            rx.cond(
                row.get("action_href", "") != "",
                rx.button(row.get("action_label", "Abrir"), on_click=rx.redirect(row["action_href"]), class_name="button button-secondary"),
                rx.button("Abrir expediente", on_click=AppState.open_canonical_investigation(row["canonical_entity_id"]), class_name="button button-secondary"),
            ),
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


def current_topic_card(row: dict) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.text(row["status"], class_name="badge badge-teal"),
            rx.text("Documento oficial", class_name="mini-pill evidence-trust"),
            spacing="2",
            wrap="wrap",
        ),
        rx.text(row["title"], class_name="card-title"),
        rx.text(row["subtitle"], class_name="muted small"),
        rx.text(row["summary"], class_name="source-fact"),
        rx.hstack(
            rx.text(row["organization"], class_name="mini-pill"),
            rx.text(f"Ultima actualizacion: {row['updated_at']}", class_name="mini-pill mini-pill-purple"),
            spacing="2",
            wrap="wrap",
        ),
        rx.button("Ver lectura documentada", on_click=rx.redirect(row["href"]), class_name="button"),
        class_name="current-topic-card",
    )



def home_pulse_card(row: dict) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.text("?", class_name="source-card-icon"),
            rx.text(row["status"], class_name="badge badge-teal"),
            rx.text(row["updated_at"], class_name="mini-pill mini-pill-purple"),
            spacing="2",
            wrap="wrap",
        ),
        rx.text(row["title"], class_name="card-title"),
        rx.box(
            rx.text("Qué cambió", class_name="pulse-field-label"),
            rx.text(row["summary"], class_name="muted small"),
            class_name="pulse-field",
        ),
        rx.box(
            rx.text("Fuente que lo sostiene", class_name="pulse-field-label"),
            rx.text(row["organization"], class_name="source-fact"),
            class_name="pulse-field",
        ),
        rx.box(
            rx.text("Lectura", class_name="pulse-field-label"),
            rx.button("Leer con documento", on_click=rx.redirect(row["href"]), class_name="button"),
            class_name="pulse-field",
        ),
        class_name="current-topic-card home-pulse-card topic-card-document",
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
                rx.text(row["label"], class_name="context-title"),
                rx.text(f"Página {row['page']}", class_name="mini-pill"),
                spacing="2",
                wrap="wrap",
            ),
            rx.text(str(row.get("source", "Documento oficial")), class_name="source-fact"),
            rx.text(row["excerpt"], class_name="muted small"),
            rx.hstack(
                rx.text(str(row.get("type", "fragmento")), class_name="mini-pill mini-pill-purple"),
                rx.text(str(row.get("reference_label", "")), class_name="mini-pill evidence-trust"),
                spacing="2",
                wrap="wrap",
            ),
            spacing="1",
            align="stretch",
        ),
        on_click=AppState.select_document_anchor(row["page"], row["fragment_id"]),
        class_name=rx.cond(
            row["fragment_id"] == AppState.knowledge_selected_fragment_id,
            "topic-fragment-nav-item topic-fragment-nav-item-active",
            "topic-fragment-nav-item",
        ),
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
            row["fragment_id"] == AppState.knowledge_selected_fragment_id,
            "document-paragraph-block document-paragraph-block-active",
            "document-paragraph-block",
        ),
    )

def topic_pdf_document_viewer(active_fragment_id: str) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.text("Documento oficial PDF", class_name="document-label"),
            rx.link("Abrir PDF", href=AppState.knowledge_document_pdf_page_href, class_name="document-inline-link"),
            justify="between",
            align="center",
            wrap="wrap",
        ),
        rx.cond(
            AppState.knowledge_fragment_contexts,
            rx.grid(
                rx.foreach(AppState.knowledge_fragment_contexts, topic_fragment_nav_item),
                columns="1",
                spacing="2",
                class_name="fragment-nav-grid",
            ),
            rx.cond(
                AppState.knowledge_pages,
                rx.hstack(
                    rx.foreach(AppState.knowledge_pages, document_page_button),
                    spacing="2",
                    wrap="wrap",
                    class_name="document-page-nav",
                ),
                rx.text("No hay marcadores de página visibles; usamos la referencia activa del fragmento.", class_name="muted small"),
            ),
        ),
        rx.el.iframe(
            src=AppState.knowledge_document_pdf_page_href,
            title="Documento oficial PDF",
            loading="lazy",
            class_name="topic-pdf-frame",
        ),
        rx.box(
            rx.text("Fragmento citado", class_name="document-label"),
            rx.text(AppState.knowledge_selected_reference_label, class_name="document-page-label"),
            rx.text(AppState.knowledge_selected_excerpt, class_name="document-highlight"),
            rx.cond(
                AppState.knowledge_selected_page_is_approximate,
                rx.text(AppState.knowledge_pdf_location_notice, class_name="document-location-notice"),
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
            rx.text(AppState.topic_official_document["title"], class_name="document-sheet-title"),
            class_name="document-sheet-cover",
        ),
        rx.foreach(AppState.knowledge_document_paragraphs, document_paragraph),
        class_name="document-page topic-document-page document-sheet",
    )


def topic_source_panel() -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.text("Documento Fuente", class_name="badge badge-teal"),
            rx.text(AppState.topic_official_document["source"], class_name="source-fact"),
            spacing="2",
            wrap="wrap",
            class_name="topic-source-header",
        ),
        rx.text(AppState.topic_official_document["title"], class_name="card-title"),
        rx.text(
            rx.cond(
                AppState.knowledge_document_has_pdf,
                "PDF oficial publicado. Fuente: " + AppState.knowledge_document_pdf_path,
                rx.cond(
                    AppState.knowledge_document_source_is_fallback,
                    "Documento reconstruido desde fallback local. Fuente: " + AppState.knowledge_document_source_path,
                    "Documento publicado como texto. Fuente: " + AppState.knowledge_document_source_path,
                ),
            ),
            class_name="topic-source-guidance",
        ),
        rx.cond(
            AppState.knowledge_document_has_pdf,
            topic_pdf_document_viewer(AppState.knowledge_selected_fragment_id),
            topic_text_document_viewer(),
        ),
        rx.box(
            rx.text("Recurso oficial", class_name="document-label"),
            rx.text("Archivo oficial del Senado en formato original (.doc).", class_name="source-fact"),
            rx.link(
                "Abrir recurso oficial del Senado",
                href=AppState.topic_original_url,
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
                AppState.select_document_anchor(row["page"], row["fragment_id"]),
                rx.call_script("setTimeout(() => (document.querySelector('.topic-pdf-document-viewer') || document.querySelector('.topic-source-panel .document-paragraph-block-active'))?.scrollIntoView({behavior: 'smooth', block: 'center'}), 80)"),
            ],
            class_name="button button-secondary",
        ),
        class_name=rx.cond(
            row["fragment_id"] == AppState.knowledge_selected_fragment_id,
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
            rx.foreach(AppState.topic_hero_answer_rows, topic_answer_card),
            rx.grid(
                rx.foreach(AppState.topic_status_rows, topic_status_card),
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
                rx.foreach(AppState.topic_proposes_rows, knowledge_key_point_card),
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
                rx.foreach(AppState.topic_changes_rows, topic_change_card),
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
                rx.foreach(AppState.topic_no_changes_rows, topic_no_change_card),
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
                AppState.topic_timeline_rows,
                rx.grid(
                    rx.foreach(AppState.topic_timeline_rows, tracking_event_card),
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
                rx.foreach(AppState.topic_evidence_rows, topic_evidence_card),
                columns="2",
                spacing="3",
                class_name="responsive-grid topic-evidence-grid",
            ),
            class_name="topic-reading-section topic-card-evidence",
            id="topic-evidence",
        ),
        rx.box(
            rx.text("Expediente", class_name="section-title"),
            topic_summary_card(AppState.topic_expediente_title, AppState.topic_expediente_summary, AppState.topic_expediente_metrics),
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
        on_click=AppState.set_topic_view_mode(mode),
        class_name=rx.cond(AppState.topic_view_mode == mode, "topic-mode-button topic-mode-button-active", "topic-mode-button"),
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
            topic_live_stage("Estado actual", AppState.topic_status, "Situacion del tema según la lectura documentada disponible."),
            topic_live_stage("Eventos del tema", AppState.topic_document_count, "Documentos y eventos disponibles para sostener la cronologia."),
            topic_live_stage("Cronología viva", AppState.topic_updated_at, "Ultima fecha registrada en el recorrido documental."),
            columns="3",
            spacing="3",
            class_name="responsive-grid live-stage-grid",
        ),
        rx.box(
            rx.text("Mapa de conexiones", class_name="card-title"),
            rx.text("Nodos principales alrededor del tema actual, conectados solo por evidencia disponible.", class_name="muted small"),
            rx.cond(
                AppState.topic_state_graph_rows,
                rx.grid(
                    rx.foreach(AppState.topic_state_graph_rows, topic_state_graph_node_card),
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
                AppState.topic_timeline_rows,
                rx.hstack(
                    rx.foreach(AppState.topic_timeline_rows, tracking_event_card),
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
                    rx.foreach(AppState.topic_changes_rows, topic_change_card),
                    columns="1",
                    spacing="3",
                    class_name="topic-compact-grid",
                ),
                class_name="topic-reading-section topic-card-changes",
            ),
            rx.box(
                rx.text("Qué falta", class_name="card-title"),
                rx.grid(
                    rx.foreach(AppState.topic_no_changes_rows, topic_no_change_card),
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
                rx.foreach(AppState.topic_evidence_rows, topic_evidence_card),
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
        AppState.topic_view_mode == "sistema_vivo",
        topic_system_mode(),
        rx.cond(
            AppState.topic_view_mode == "evidencia",
            topic_evidence_mode(),
            topic_reading_mode(),
        ),
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
                rx.text("Todavia no hay preguntas guiadas disponibles.", class_name="muted small"),
            ),
            subtitle="Consultas concretas que exploran datos locales.",
        ),
        page_section(
            "Explora por categoria",
            rx.hstack(
                rx.foreach(AppState.guided_category_rows, guided_category_button),
                spacing="2",
                wrap="wrap",
                class_name="chip-row",
            ),
            guided_category_panel(),
            subtitle="Selecciona una categoria para ver ejemplos sin perder el contexto.",
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
            rx.button("Ver recorrido", on_click=rx.redirect("/demo"), class_name="button button-secondary"),
            spacing="2",
            wrap="wrap",
        ),
        class_name="card tracking-card",
    )


def tracking_event_card(row: dict) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.text("?", class_name="source-card-icon"),
            rx.text(row["date"], class_name="badge badge-teal"),
            rx.text(row["status"], class_name="mini-pill mini-pill-purple"),
            justify="between",
            align="center",
        ),
        rx.text(row["title"], class_name="card-title"),
        rx.text(row["description"], class_name="muted small"),
        rx.text(f"Fuente: {row['source']}", class_name="source-fact"),
        rx.text(rx.cond(row.get("origin", "") == "demo_manual", "Origen: demo manual", "Origen: timeline derivada"), class_name="mini-pill evidence-trust"),
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



def reference_button(row: dict) -> rx.Component:
    return rx.button(
        row["reference_label"],
        on_click=[
            AppState.select_document_anchor(row["page"], row["fragment_id"]),
            rx.call_script("setTimeout(() => (document.querySelector('.topic-pdf-document-viewer') || document.querySelector('.topic-source-panel .document-paragraph-block-active'))?.scrollIntoView({behavior: 'smooth', block: 'center'}), 80)"),
        ],
        class_name="reference-button",
    )


def document_metric(label: str, value: rx.Var | int) -> rx.Component:
    return rx.box(
        rx.text(value, class_name="document-metric-value"),
        rx.text(label, class_name="document-metric-label"),
        class_name="document-metric",
    )


def reading_context_bar() -> rx.Component:
    return rx.box(
        rx.text("Cobertura documental", class_name="document-reading-status"),
        rx.box(
            rx.text(AppState.knowledge_coverage_text, class_name="document-metric-value"),
            rx.text(AppState.knowledge_reference_text, class_name="document-metric-label"),
            class_name="document-metric",
        ),
        document_metric("preguntas respondidas", AppState.knowledge_question_count),
        document_metric("afirmaciones verificables", AppState.knowledge_claim_count),
        document_metric("referencias documentales", AppState.knowledge_reference_count),
        class_name="reading-context-bar",
    )


def reading_share_actions() -> rx.Component:
    return rx.hstack(
        rx.text("Compartir lectura", class_name="document-label"),
        rx.link("X", href=AppState.knowledge_share_x_url, class_name="badge badge-purple share-pill"),
        rx.link("WhatsApp", href=AppState.knowledge_share_whatsapp_url, class_name="badge badge-teal share-pill"),
        rx.link("LinkedIn", href=AppState.knowledge_share_linkedin_url, class_name="badge badge-blue share-pill"),
        rx.button("Copiar enlace", on_click=rx.call_script(AppState.knowledge_share_copy_script), class_name="button button-secondary"),
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
        on_click=AppState.select_document_anchor(row["page"], row["id"]),
        id=row["id"],
        class_name=rx.cond(
            row["id"] == AppState.knowledge_selected_fragment_id,
            "document-fragment document-fragment-active",
            "document-fragment",
        ),
    )


def document_page_button(row: dict) -> rx.Component:
    return rx.button(
        row["label"],
        on_click=AppState.select_document_anchor(row["page"], ""),
        title=f"Ir a {row['label']}",
        class_name=rx.cond(
            row["page"] == AppState.knowledge_selected_page,
            "page-chip page-chip-active",
            "page-chip",
        ),
    )




def official_document_pdf_viewer(page: int, fragment_id: str, highlight: str) -> rx.Component:
    return rx.box(
        reading_context_bar(),
        rx.box(
            rx.hstack(
                rx.text("Documento oficial PDF", class_name="document-label"),
                rx.link("Abrir PDF", href=AppState.knowledge_document_pdf_page_href, class_name="document-inline-link"),
                justify="between",
                align="center",
                wrap="wrap",
            ),
            rx.cond(
                AppState.knowledge_fragment_contexts,
                rx.grid(
                    rx.foreach(AppState.knowledge_fragment_contexts, topic_fragment_nav_item),
                    columns="1",
                    spacing="2",
                    class_name="fragment-nav-grid",
                ),
                rx.cond(
                    AppState.knowledge_pages,
                    rx.hstack(
                        rx.foreach(AppState.knowledge_pages, document_page_button),
                        spacing="2",
                        wrap="wrap",
                        class_name="document-page-nav",
                    ),
                    rx.text("No hay marcadores de página visibles; usamos la referencia activa del fragmento.", class_name="muted small"),
                ),
            ),
            rx.el.iframe(
                src=AppState.knowledge_document_pdf_page_href,
                title="Documento oficial PDF",
                loading="lazy",
                class_name="official-document-pdf-frame",
            ),
            rx.box(
                rx.text("Fragmento citado", class_name="document-label"),
                rx.text(f"Página {page}", class_name="document-page-label"),
                rx.text(highlight, class_name="document-highlight"),
                rx.cond(
                    AppState.knowledge_selected_page_is_approximate,
                    rx.text(AppState.knowledge_pdf_location_notice, class_name="document-location-notice"),
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
            rx.cond(
                AppState.knowledge_fragment_contexts,
                rx.grid(
                    rx.foreach(AppState.knowledge_fragment_contexts, topic_fragment_nav_item),
                    columns="1",
                    spacing="2",
                    class_name="fragment-nav-grid",
                ),
                rx.hstack(
                    rx.foreach(AppState.knowledge_pages, document_page_button),
                    spacing="2",
                    wrap="wrap",
                    class_name="document-page-nav",
                ),
            ),
            rx.box(
                rx.text("Fragmento citado", class_name="document-label"),
                rx.text(f"Página {page}", class_name="document-page-label"),
                rx.text(highlight, class_name="document-highlight"),
                rx.cond(
                    AppState.knowledge_selected_page_is_approximate,
                    rx.text(AppState.knowledge_pdf_location_notice, class_name="document-location-notice"),
                ),
                rx.text(fragment_id, class_name="mono id-line"),
                reading_share_actions(),
                class_name="document-current-anchor",
            ),
            rx.box(
                rx.foreach(AppState.knowledge_document_paragraphs, document_paragraph),
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
        on_click=AppState.select_document_anchor(row["page"], row["fragment_id"]),
        class_name="guide-entry",
    )


def guide_question(row: dict) -> rx.Component:
    return rx.box(
        rx.text(row["display_question"], class_name="guide-title"),
        rx.text(row["why_it_matters"], class_name="guide-copy"),
        reference_button(row),
        on_click=AppState.select_document_anchor(row["page"], row["fragment_id"]),
        class_name="guide-entry",
    )


def guide_claim(row: dict) -> rx.Component:
    return rx.box(
        rx.text(row["claim"], class_name="guide-title"),
        rx.text(row["review_note"], class_name="guide-copy"),
        reference_button(row),
        on_click=AppState.select_document_anchor(row["page"], row["fragment_id"]),
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
        rx.text(AppState.knowledge_selected_reference_label, class_name="document-page-marker"),
        rx.text("Lectura documentada", class_name="reading-guide-title"),
        rx.text(AppState.knowledge_selected_excerpt, class_name="reading-guide-summary"),
        rx.box(
            rx.text("Punto documentado", class_name="reading-guide-heading"),
            rx.cond(
                AppState.knowledge_selected_summary,
                rx.foreach(AppState.knowledge_selected_summary, guide_point),
                rx.text("Este fragmento no tiene un punto destacado.", class_name="muted small"),
            ),
            class_name="reading-guide-section",
        ),
        rx.box(
            rx.text("Pregunta derivada del texto", class_name="reading-guide-heading"),
            rx.cond(
                AppState.knowledge_selected_questions,
                rx.foreach(AppState.knowledge_selected_questions, guide_question),
                rx.text("No hay pregunta derivada de este fragmento.", class_name="muted small"),
            ),
            class_name="reading-guide-section",
        ),
        rx.box(
            rx.text("Afirmacion trazable", class_name="reading-guide-heading"),
            rx.cond(
                AppState.knowledge_selected_claims,
                rx.foreach(AppState.knowledge_selected_claims, guide_claim),
                rx.text("No hay afirmacion trazable para este fragmento.", class_name="muted small"),
            ),
            class_name="reading-guide-section",
        ),
        rx.box(
            rx.text("Evidencia utilizada", class_name="reading-guide-heading"),
            rx.cond(
                AppState.knowledge_selected_evidence,
                rx.foreach(AppState.knowledge_selected_evidence, guide_evidence),
                rx.text("No hay evidencia seleccionada para este fragmento.", class_name="muted small"),
            ),
            class_name="reading-guide-section",
        ),
        rx.box(
            rx.text("Navegacion relacionada", class_name="reading-guide-heading"),
            rx.hstack(rx.foreach(AppState.knowledge_selected_connections, reading_connection), spacing="2", wrap="wrap"),
            class_name="reading-guide-section",
        ),
        class_name="reading-guide-panel",
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
        rx.text(row["official_url"], class_name="mono id-line"),
        rx.hstack(
            rx.button("Ver documento", on_click=rx.redirect("/official-document"), class_name="button"),
            rx.button("Abrir expediente", on_click=AppState.open_canonical_investigation(row["related_expediente_target"]), class_name="button button-secondary"),
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
                    aria_label="Buscar entidad",
                ),
                rx.button("Buscar", on_click=AppState.submit_main_search, class_name="button search-button"),
                spacing="3",
                align="center",
                class_name="search-bar investigation-welcome-search",
            ),
            rx.hstack(
                rx.button("Abrir expediente de ejemplo", on_click=rx.redirect(_investigation_href(DEMO_INVESTIGATION_TARGET)), class_name="button"),
                rx.button("Ver biblioteca", on_click=rx.redirect("/library"), class_name="button button-secondary"),
                rx.button("Ver fuentes oficiales", on_click=rx.redirect("/ecosystem"), class_name="button button-secondary"),
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
    return rx.vstack(
        rx.box(
            rx.text("Cargando expediente...", class_name="title"),
            rx.text("Estamos preparando el expediente desde la publicación local y ordenando sus rutas de verificación.", class_name="subtitle"),
            rx.hstack(
                rx.button("Reintentar", on_click=AppState.load_investigation, class_name="button button-secondary"),
                rx.button("Volver al recorrido", on_click=rx.redirect("/demo"), class_name="button button-secondary"),
                spacing="3",
                wrap="wrap",
                class_name="hero-actions",
            ),
            class_name="hero",
        ),
        rx.grid(
            loading_placeholder_card("Reconstruyendo evidencia", "Ordenamos hechos, relaciones y referencias ya disponibles."),
            loading_placeholder_card("Preparando documento", "Sincronizamos el PDF oficial y el contexto citado."),
            loading_placeholder_card("Abriendo siguientes pasos", "Dejamos lista la navegación a informes, cronología y fuentes."),
            columns="3",
            spacing="3",
            class_name="responsive-grid loading-skeleton-grid",
        ),
        spacing="4",
        align="stretch",
    )


def investigation_error_state() -> rx.Component:
    return rx.box(
        rx.text("No se pudo abrir el expediente", class_name="title"),
        rx.text(
            rx.cond(
                AppState.investigation_status_message != "",
                AppState.investigation_status_message,
                "No pudimos abrir este expediente con la publicación actual. Puedes reintentar o volver al recorrido guiado.",
            ),
            class_name="subtitle",
        ),
        rx.hstack(
            rx.button("Reintentar", on_click=AppState.load_investigation, class_name="button"),
            rx.button("Volver al recorrido", on_click=rx.redirect("/demo"), class_name="button button-secondary"),
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
            "Sin resultados por ahora",
            rx.text("No encontramos coincidencias con ese nombre o identificador en esta base local publicada.", class_name="muted"),
            rx.text(
                "Puede tratarse de otra denominacion oficial, una entidad aun no publicada o una busqueda que necesita mas contexto.",
                class_name="muted small",
            ),
            rx.hstack(
                rx.link("Usar entrada guiada", href="/discover", class_name="badge badge-purple"),
                rx.link("Explorar fuentes oficiales", href="/sources", class_name="document-inline-link"),
                rx.link("Ir a Pulso", href="/", class_name="document-inline-link"),
                spacing="3",
                wrap="wrap",
            ),
            subtitle="Prueba con una institucion, empresa, persona o documento usando su nombre oficial mas reconocible.",
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
        state_graph_connections_panel(),
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
        subtitle="Estado de cada fuente en la publicación actual y qué aporta al expediente.",
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


@rx.page(
    route="404",
    title="Esta página no sobrevivió a la burocracia",
    description="No encontramos este documento.",
    image=PUBLIC_OG_IMAGE_URL,
    meta=_page_meta(
        "/404",
        "404, expediente, documento, evidencia, datosenorden",
        "Esta página no sobrevivió a la burocracia",
        "No encontramos este documento.",
    ),
)
def not_found() -> rx.Component:
    return shell(
        rx.box(
            rx.grid(
                rx.vstack(
                    rx.text("Esta página no sobrevivió a la burocracia.", class_name="title"),
                    rx.text("No encontramos este documento.", class_name="subtitle"),
                    rx.text(
                        "Al parecer alguien archivó la página en una carpeta imposible de encontrar.",
                        class_name="story-summary",
                    ),
                    rx.hstack(
                        rx.button("Inicio", on_click=rx.redirect("/"), class_name="button"),
                        rx.button("Buscar", on_click=rx.redirect("/search"), class_name="button button-secondary"),
                        rx.button("Pulso del Estado", on_click=rx.redirect("/"), class_name="button button-secondary"),
                        spacing="3",
                        wrap="wrap",
                        class_name="hero-actions",
                    ),
                    spacing="4",
                    align="stretch",
                ),
                not_found_document_illustration(),
                columns="2",
                spacing="4",
                class_name="not-found-hero",
            ),
            class_name="hero",
        ),
        page_section(
            "Sigue explorando",
            rx.grid(
                next_step_card("Abrir lectura principal", "Volver al documento y su explicación ciudadana.", "Ir a Lectura", "/topic"),
                next_step_card("Buscar una entidad", "Entrar por una búsqueda guiada o directa.", "Ir a Buscar", "/search"),
                next_step_card("Revisar fuentes", "Explorar las fuentes oficiales publicadas y su cobertura.", "Ir a Fuentes", "/sources"),
                columns="3",
                spacing="3",
                class_name="responsive-grid",
            ),
            subtitle="DatosEnOrden sigue priorizando documentos, fuentes y evidencia visible.",
        ),
        active_page=PAGE_NOT_FOUND,
    )


@rx.page(
    route="/",
    title="DatosEnOrden - Pulso del Estado",
    description="Pulso ciudadano de documentos, expedientes y fuentes oficiales para abrir una lectura verificable.",
    image=PUBLIC_OG_IMAGE_URL,
    meta=_page_meta(
        "/",
        "datos públicos, documentos oficiales, evidencia, expedientes, lectura ciudadana, fuentes oficiales",
        "DatosEnOrden - Pulso del Estado",
        "Pulso ciudadano de documentos, expedientes y fuentes oficiales para abrir una lectura verificable.",
    ),
)
def home() -> rx.Component:
    return shell(
        rx.box(
            rx.text("Pulso del Estado", class_name="title"),
            rx.text(
                "Un lugar para entender que cambio, que documento lo sostiene y que lectura abrir primero.",
                class_name="subtitle",
            ),
            rx.hstack(
                rx.button("Abrir lectura principal", on_click=rx.redirect("/topic"), class_name="button primary-action"),
                rx.text("Documento oficial visible en menos de un minuto.", class_name="hero-action-note"),
                spacing="3",
                wrap="wrap",
                class_name="hero-actions",
            ),
            class_name="hero home-pulse-hero",
        ),
        page_section(
            "Eventos recientes",
            rx.cond(
                AppState.current_topic_rows,
                rx.grid(
                    rx.foreach(AppState.current_topic_rows, home_pulse_card),
                    columns="3",
                    spacing="3",
                    class_name="responsive-grid home-pulse-grid",
                ),
                rx.text("Todavia no hay eventos publicos recientes para mostrar.", class_name="muted small"),
            ),
            subtitle="Cada tarjeta responde una sola pregunta: que paso, que fuente lo sostiene y que lectura abre.",
        ),
        on_mount=AppState.load_home,
        active_page=PAGE_HOME,
    )


@rx.page(
    route="/ecosystem",
    title="Fuentes oficiales - DatosEnOrden",
    description="Mapa ciudadano de fuentes oficiales, cobertura documental y conexiones disponibles en DatosEnOrden.",
    image=PUBLIC_OG_IMAGE_URL,
    meta=_page_meta(
        "/sources",
        "fuentes oficiales, cobertura documental, datos públicos, trazabilidad, mapa de fuentes",
        "Fuentes oficiales - DatosEnOrden",
        "Mapa ciudadano de fuentes oficiales, cobertura documental y conexiones disponibles en DatosEnOrden.",
    ),
)
def ecosystem() -> rx.Component:
    return shell(
        rx.box(
            rx.text("Fuentes oficiales", class_name="title"),
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
            card_grid_or_empty(
                AppState.ecosystem_active_sources,
                ecosystem_source_card,
                columns="3",
                empty_title="Aún no hay fuentes activas visibles",
                empty_body="Esta publicación todavía no expone fuentes activas en esta vista.",
                action_label="Volver al inicio",
                href="/",
            ),
            rx.text("Fuentes en desarrollo", class_name="section-subtitle"),
            card_grid_or_empty(
                AppState.ecosystem_prototype_sources,
                ecosystem_source_card,
                columns="3",
                empty_title="Sin fuentes en desarrollo para mostrar",
                empty_body="La hoja de ruta pública todavía no expone prototipos adicionales en esta sección.",
                action_label="Ver el proyecto",
                href="/project",
            ),
            rx.text("Fuentes planificadas", class_name="section-subtitle"),
            card_grid_or_empty(
                AppState.ecosystem_planned_sources,
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
                AppState.ecosystem_concepts,
                ecosystem_concept_card,
                columns="4",
                empty_title="Todavía no hay conceptos publicados",
                empty_body="Esta superficie necesita fuentes publicadas para mostrar cruces conceptuales útiles.",
                action_label="Revisar el proyecto",
                href="/project",
            ),
            subtitle="Conceptos visibles en cada fuente.",
        ),
        page_section(
            "Estado interno de datos reales",
            rx.hstack(
                metric("Listas", AppState.real_data_ready_count),
                metric("Parciales", AppState.real_data_partial_count),
                metric("Con demo", AppState.real_data_demo_count),
                metric("Sin loader", AppState.real_data_without_loader_count),
                spacing="3",
                wrap="wrap",
            ),
            card_grid_or_empty(
                AppState.real_data_sources,
                real_data_source_card,
                columns="2",
                empty_title="Sin estado público de fuentes reales",
                empty_body="La cobertura pública todavía no expone fuentes reales adicionales en esta vista.",
                action_label="Ver fuentes",
                href="/sources",
            ),
            subtitle="Vista avanzada de cobertura: que fuentes tienen informacion disponible, parcial o pendiente.",
        ),
        page_section(
            "Cómo se cruzan las fuentes",
            rx.text("Cada concepto indica qué fuentes lo alimentan y si su cobertura es activa, parcial o futura.", class_name="muted"),
            card_grid_or_empty(
                AppState.ecosystem_roadmap,
                ecosystem_roadmap_card,
                columns="3",
                empty_title="No hay cruces publicados todavía",
                empty_body="Los cruces aparecen cuando una fuente publicada ya tiene cobertura suficiente para compararse con otra.",
                action_label="Explorar fuentes",
                href="/sources",
            ),
            subtitle="Lectura de cobertura y cruce entre fuentes.",
        ),
        page_section(
            "Catálogo de metadatos",
            card_grid_or_empty(
                AppState.ecosystem_sources,
                ecosystem_source_card,
                columns="3",
                empty_title="No hay metadatos publicados",
                empty_body="Esta vista necesita fuentes cargadas para mostrar su detalle y trazabilidad técnica.",
                action_label="Volver al inicio",
                href="/",
            ),
            subtitle="Detalle completo y trazabilidad técnica bajo demanda.",
        ),
        page_section(
            "Siguientes pasos",
            rx.grid(
                next_step_card("Descubrir una pregunta", "Si todavía no sabes qué buscar, empieza por una pregunta guiada.", "Ir a Descubre", "/discover"),
                next_step_card("Abrir expediente de ejemplo", "Ver cómo las fuentes se conectan en una entidad concreta.", "Abrir expediente", _investigation_href(DEMO_INVESTIGATION_TARGET)),
                next_step_card("Leer reporte ciudadano", "Ver una lectura menos técnica del caso publicado.", "Ir a Informes", "/reports"),
                columns="3",
                spacing="3",
                class_name="responsive-grid",
            ),
            subtitle="Las fuentes son el mapa; el expediente y el reporte muestran el recorrido.",
        ),
        on_mount=AppState.load_ecosystem,
        active_page=PAGE_ECOSYSTEM,
    )


@rx.page(
    route="/sources",
    title="Fuentes oficiales - DatosEnOrden",
    description="Mapa ciudadano de fuentes oficiales, cobertura documental y conexiones disponibles en DatosEnOrden.",
    image=PUBLIC_OG_IMAGE_URL,
    meta=_page_meta(
        "/sources",
        "fuentes oficiales, cobertura documental, datos públicos, trazabilidad, mapa de fuentes",
        "Fuentes oficiales - DatosEnOrden",
        "Mapa ciudadano de fuentes oficiales, cobertura documental y conexiones disponibles en DatosEnOrden.",
    ),
)
def sources() -> rx.Component:
    return ecosystem()

@rx.page(
    route="/demo",
    title="Recorrido guiado - DatosEnOrden",
    description="Recorrido público de ejemplo para entender cómo DatosEnOrden conecta fuentes, expedientes y evidencia.",
    image=PUBLIC_OG_IMAGE_URL,
    meta=_page_meta(
        "/demo",
        "muestra pública, evidencia, expedientes, fuentes públicas, datosenorden",
        "Recorrido guiado - DatosEnOrden",
        "Recorrido público de ejemplo para entender cómo DatosEnOrden conecta fuentes, expedientes y evidencia.",
    ),
)
def demo() -> rx.Component:
    return shell(
        rx.box(
            rx.text("Recorrido guiado", class_name="title"),
            rx.text(
                "Recorrido público con datos locales de prueba. No son datos oficiales y no implican causalidad, irregularidad ni responsabilidad.",
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
            "Checklist del recorrido",
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
            "Cómo recorrer esta publicación",
            rx.grid(
                flow_card(1, "Ver fuentes disponibles", "Abrir Fuentes para explicar qué datos locales de prueba están cargados."),
                flow_card(2, "Abrir expediente de ejemplo", "Entrar al expediente canonico del Servicio de Salud Arauco Hospital de Arauco."),
                flow_card(3, "Revisar evidencia y trazabilidad", "Mostrar resumen ciudadano, seguimiento, reportes, fuentes consultadas y detalles tecnicos colapsados."),
                columns="3",
                spacing="3",
                class_name="responsive-grid",
            ),
            subtitle="Ruta recomendada para una primera lectura pública.",
        ),
        page_section(
            "Aclaración",
            rx.text(
                "Este recorrido muestra cómo se vería un expediente ciudadano al cruzar fuentes públicas. "
                "Los registros son datos locales de prueba, no oficiales, y sirven para explicar el producto sin inferir irregularidades.",
                class_name="story-summary",
            ),
            subtitle="Contexto recomendado antes de mostrar el expediente.",
        ),
        on_mount=AppState.load_demo,
        active_page=PAGE_DEMO,
    )


@rx.page(
    route="/discover",
    title="Buscar - DatosEnOrden",
    description="Búsqueda y entrada guiada para explorar expedientes, entidades y documentos en DatosEnOrden.",
    image=PUBLIC_OG_IMAGE_URL,
    meta=_page_meta(
        "/search",
        "buscar, expedientes, entidades, documentos oficiales, entrada guiada",
        "Buscar - DatosEnOrden",
        "Búsqueda y entrada guiada para explorar expedientes, entidades y documentos en DatosEnOrden.",
    ),
)
def discover() -> rx.Component:
    return search()


def result_card(row: dict) -> rx.Component:
    return workspace_match_card(row)


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
            rx.text(AppState.topic_title, class_name="document-title"),
            rx.text(
                "Primero el documento. Luego la explicacion ciudadana y la evidencia que permite verificar cada afirmacion.",
                class_name="document-subtitle",
            ),
            rx.hstack(
                rx.text(AppState.topic_status, class_name="document-meta-pill"),
                rx.text(AppState.topic_read_time, class_name="document-meta-pill"),
                rx.text(AppState.topic_updated_at, class_name="document-meta-reference"),
                spacing="2",
                wrap="wrap",
                class_name="document-meta-row",
            ),
            topic_mode_selector(),
            rx.text(AppState.topic_organizations_text, class_name="document-meta-reference"),
            class_name="document-hero topic-hero",
        ),
        topic_mode_body(),
        support_cta_block(),
        on_mount=AppState.load_topic,
        active_page=PAGE_TOPIC,
    )

@rx.page(
    route="/tracking",
    title="Cronología - DatosEnOrden",
    description="Cronología ciudadana de documentos, hitos y evidencia para seguir una propuesta pública.",
    image=PUBLIC_OG_IMAGE_URL,
    meta=_page_meta(
        "/chronology",
        "cronología, seguimiento, documentos oficiales, hitos, evidencia pública",
        "Cronología - DatosEnOrden",
        "Cronología ciudadana de documentos, hitos y evidencia para seguir una propuesta pública.",
    ),
)
def tracking() -> rx.Component:
    return shell(
        rx.box(
            rx.text("Sigue la historia de una propuesta pública", class_name="title"),
            rx.text(
                "Cronología local de documentos, propuestas, estados, evidencia, expedientes relacionados y cambios históricos.",
                class_name="subtitle",
            ),
            rx.hstack(
                rx.button("Abrir expediente", on_click=AppState.open_tracking_investigation, class_name="button"),
                rx.button("Ver recorrido", on_click=rx.redirect("/demo"), class_name="button button-secondary"),
                spacing="3",
                wrap="wrap",
                class_name="hero-actions",
            ),
            class_name="hero",
        ),
        page_section(
            "Qué significa cronología",
            rx.grid(
                help_card("Estado", "Indica en qué punto está una historia documental según los datos disponibles."),
                help_card("Evento", "Es un hito con fecha que ayuda a entender qué pasó antes y después."),
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
            subtitle="Seguimientos locales marcados como datos de prueba, sin APIs externas ni PDFs pesados.",
        ),
        page_section(
            "Timeline de seguimiento",
            rx.text(AppState.tracking_summary, class_name="story-summary"),
            rx.hstack(
                rx.text(AppState.tracking_current_status, class_name="badge badge-teal"),
                rx.text("Muestra local no oficial", class_name="mini-pill evidence-trust"),
                spacing="2",
                wrap="wrap",
            ),
            rx.grid(
                rx.foreach(AppState.tracking_events, tracking_event_card),
                columns="1",
                spacing="4",
                class_name="timeline-list",
            ),
            subtitle="Propuesta -> documento oficial -> presupuesto -> compra pública -> proveedor -> publicación/cargo -> control -> expediente relacionado.",
        ),
        page_section(
            "Documentos oficiales relacionados",
            card_grid_or_empty(
                AppState.tracking_documents,
                tracking_document_card,
                columns="2",
                empty_title="Todavía no hay documentos relacionados publicados",
                empty_body="Este seguimiento aún no expone documentos oficiales adicionales en la publicación actual.",
                action_label="Ver documento fuente",
                href="/official-document",
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
            subtitle="La cronología no reemplaza el expediente: lo conecta con historia documental.",
        ),
        page_section(
            "Evidencia y fuentes consultadas",
            card_grid_or_empty(
                AppState.tracking_evidence,
                tracking_evidence_card,
                columns="2",
                empty_title="Sin evidencia publicada en esta cronología",
                empty_body="Cuando el seguimiento tenga referencias visibles, aparecerán aquí con su contexto de lectura.",
                action_label="Explorar fuentes",
                href="/sources",
            ),
            rx.cond(
                AppState.tracking_related_sources,
                rx.hstack(
                    rx.foreach(AppState.tracking_related_sources, lambda item: rx.text(item, class_name="search-chip")),
                    spacing="2",
                    wrap="wrap",
                ),
                rx.text("Todavía no hay fuentes relacionadas publicadas para este seguimiento.", class_name="muted small"),
            ),
            subtitle="Referencias locales descriptivas; no afirman causalidad, irregularidad ni responsabilidad.",
        ),
        page_section(
            "Siguientes pasos",
            rx.grid(
                next_step_card("Abrir expediente", "Ver la entidad, relaciones y evidencia asociada.", "Ir al expediente", _investigation_href(DEMO_INVESTIGATION_TARGET)),
                next_step_card("Leer reporte ciudadano", "Ver una lectura tipo articulo del caso.", "Ir a Informes", "/reports"),
                next_step_card("Ver documento fuente", "Abrir el visor para revisar paginas y fragmentos.", "Ver documento", "/official-document"),
                columns="3",
                spacing="3",
                class_name="responsive-grid",
            ),
            subtitle="Por ahora no hay suscripciones reales; el seguimiento es local y read-only.",
        ),
        on_mount=AppState.load_tracking,
        active_page=PAGE_TRACKING,
    )

@rx.page(
    route="/chronology",
    title="Cronología - DatosEnOrden",
    description="Cronología ciudadana de documentos, hitos y evidencia para seguir una propuesta pública.",
    image=PUBLIC_OG_IMAGE_URL,
    meta=_page_meta(
        "/chronology",
        "cronología, seguimiento, documentos oficiales, hitos, evidencia pública",
        "Cronología - DatosEnOrden",
        "Cronología ciudadana de documentos, hitos y evidencia para seguir una propuesta pública.",
    ),
)
def chronology() -> rx.Component:
    return tracking()


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
                rx.button("Abrir expediente", on_click=AppState.open_knowledge_investigation, class_name="button"),
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
                rx.text("Muestra local no oficial", class_name="mini-pill evidence-trust"),
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
            subtitle="El mismo digest conecta expediente, cronologia, informe ciudadano y fuente publica.",
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
                rx.text(AppState.knowledge_title, class_name="document-title"),
                rx.text(
                    "Responde: de donde salio esta informacion. El documento queda visible junto a sus referencias.",
                    class_name="document-subtitle",
                ),
                class_name="document-hero-copy",
            ),
            rx.hstack(
                rx.text(AppState.knowledge_document["source"], class_name="document-meta-pill"),
                rx.text(AppState.knowledge_document["published_at"], class_name="document-meta-pill"),
                rx.text(AppState.knowledge_document["official_status"], class_name="document-meta-pill"),
                rx.text(AppState.knowledge_document["official_url"], class_name="document-meta-reference"),
                spacing="2",
                wrap="wrap",
                class_name="document-meta-row",
            ),
            class_name="document-hero",
        ),
        rx.box(
            rx.box(
                rx.cond(
                    AppState.knowledge_document_has_pdf,
                    official_document_pdf_viewer(
                        AppState.knowledge_selected_page,
                        AppState.knowledge_selected_fragment_id,
                        AppState.knowledge_selected_excerpt,
                    ),
                    official_document_viewer(
                        AppState.knowledge_document["id"],
                        AppState.knowledge_selected_page,
                        AppState.knowledge_selected_fragment_id,
                        AppState.knowledge_selected_excerpt,
                    ),
                ),
                class_name="document-main-column",
            ),
            rx.box(
                reading_guide_panel(),
                class_name="document-side-column",
            ),
            class_name="official-document-layout",
        ),
        rx.box(
            rx.text("Evidencia dentro del documento", class_name="section-title"),
            rx.text("Cada referencia conserva pagina, fragmento y extracto verificable del documento fuente.", class_name="section-subtitle"),
            rx.cond(
                AppState.knowledge_evidence,
                rx.box(
                    rx.foreach(AppState.knowledge_evidence, guide_evidence),
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
        on_mount=AppState.load_knowledge,
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
                AppState.knowledge_documents,
                rx.grid(
                    rx.foreach(AppState.knowledge_documents, knowledge_document_card),
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
            rx.text(AppState.knowledge_title, class_name="card-title"),
            rx.text(AppState.knowledge_summary, class_name="story-summary"),
            rx.hstack(
                rx.text("Muestra local no oficial", class_name="mini-pill evidence-trust"),
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
            "Anclas y evidencia",
            rx.cond(
                AppState.knowledge_evidence,
                rx.grid(
                    rx.foreach(AppState.knowledge_evidence, tracking_evidence_card),
                    columns="2",
                    spacing="3",
                    class_name="responsive-grid",
                ),
                rx.text("Todavía no hay anclas de evidencia disponibles.", class_name="muted small"),
            ),
            rx.text(AppState.knowledge_notice, class_name="muted small"),
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
        on_mount=AppState.load_knowledge,
        active_page=PAGE_LIBRARY,
    )


@rx.page(
    route="/reports",
    title="Informes ciudadanos - DatosEnOrden",
    description="Informes ciudadanos con contexto, hitos, evidencia y rutas de verificación.",
    image=PUBLIC_OG_IMAGE_URL,
    meta=_page_meta(
        "/reports",
        "informes ciudadanos, evidencia, contexto, hitos, verificación",
        "Informes ciudadanos - DatosEnOrden",
        "Informes ciudadanos con contexto, hitos, evidencia y rutas de verificación.",
    ),
)
def reports() -> rx.Component:
    loaded_report = rx.box(
        page_section(
            "Resumen",
            rx.text(AppState.citizen_report_summary, class_name="story-summary"),
            rx.hstack(
                rx.text(AppState.citizen_report_status, class_name="badge badge-teal"),
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
            rx.link("Abrir version HTML local", href=AppState.citizen_report_path, class_name="button button-secondary"),
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
                rx.button("Abrir expediente", on_click=AppState.open_report_investigation, class_name="button"),
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
                AppState.citizen_reports,
                rx.grid(
                    rx.foreach(AppState.citizen_reports, citizen_report_card),
                    columns="2",
                    spacing="3",
                    class_name="responsive-grid",
                ),
                rx.text("No hay informes ciudadanos locales disponibles.", class_name="muted small"),
            ),
            subtitle="Prototipos read-only marcados como datos locales de prueba.",
            class_name="reports-catalog-section",
        ),
        rx.cond(AppState.citizen_report_title != "", loaded_report, empty_report),
        on_mount=AppState.load_reports,
        active_page=PAGE_REPORTS,
    )

@rx.page(
    route="/project",
    title="Estado del proyecto - DatosEnOrden",
    description="Estado público del proyecto DatosEnOrden, su propósito, alcance y límites.",
    image=PUBLIC_OG_IMAGE_URL,
    meta=_page_meta(
        "/project",
        "DatosEnOrden, proyecto, evidencia verificable, lectura pública, MVP",
        "Estado del proyecto - DatosEnOrden",
        "Por qué existe DatosEnOrden, cómo funciona y qué significa un MVP con evidencia verificable.",
    ),
)
def project() -> rx.Component:
    return shell(
        rx.box(
            rx.text("Estado del proyecto", class_name="title"),
            rx.text(
                "DatosEnOrden existe para que la información pública se pueda leer como una historia verificable, no como un listado suelto de registros.",
                class_name="subtitle",
            ),
            rx.text("MVP con datos locales de prueba. No representa datos oficiales reales.", class_name="badge badge-purple launch-notice"),
            rx.hstack(
                rx.button("Volver al inicio", on_click=rx.redirect("/"), class_name="button"),
                rx.button("Abrir expediente de ejemplo", on_click=rx.redirect(_investigation_href(DEMO_INVESTIGATION_TARGET)), class_name="button button-secondary"),
                spacing="3",
                wrap="wrap",
                class_name="hero-actions",
            ),
            class_name="hero",
        ),
        page_section(
            "Qué es DatosEnOrden",
            rx.grid(
                help_card("Leer evidencia", "Tomar documentos, relaciones y cronologías y convertirlos en una lectura pública útil."),
                help_card("Conectar fuentes", "Cruzar compras, presupuesto, lobby, publicaciones, empresas y control en un mismo recorrido."),
                help_card("Mantener trazabilidad", "Cada afirmación visible debe poder volver a una referencia o fragmento concreto."),
                columns="3",
                spacing="3",
                class_name="responsive-grid",
            ),
            subtitle="La versión pública muestra el producto sin esconder sus límites ni prometer automatizaciones inexistentes.",
        ),
        page_section(
            "Por qué existe",
            rx.text(
                "El problema no es la falta de datos, sino que los datos suelen venir dispersos, con lenguaje técnico y sin una ruta clara para verificarlos.",
                class_name="story-summary",
            ),
            rx.text(
                "DatosEnOrden junta fuentes, evidencia y contexto para que una persona pueda entender qué pasó, dónde verlo y qué parte del texto lo sostiene.",
                class_name="story-summary",
            ),
            subtitle="El foco no es deslumbrar con volumen; es reducir fricción de lectura y hacer visible la procedencia.",
        ),
        page_section(
            "Cómo funciona",
            rx.grid(
                flow_card(1, "Fuentes", "Cada registro nace desde un origen identificable y marcado como local de prueba cuando corresponde."),
                flow_card(2, "Evidencia", "Fragmentos, documentos y anclas permiten volver a la parte exacta del contenido."),
                flow_card(3, "Relaciones", "EntityEngine, RelationshipGraph y StateGraph ordenan los cruces sin inventar conclusiones."),
                flow_card(4, "Lectura", "La interfaz traduce la trazabilidad técnica a una experiencia pública clara."),
                columns="4",
                spacing="3",
                class_name="responsive-grid",
            ),
            subtitle="La arquitectura existente se reutiliza; el valor está en la lectura y en la trazabilidad, no en cambiarla.",
        ),
        page_section(
            "Qué significa MVP",
            rx.grid(
                help_card("Más cobertura", "Seguir completando fuentes y aumentando la conectividad útil de los demos."),
                help_card("Mejor lectura", "Pulir búsquedas, documento, cronología y vistas de producto con menos fricción."),
                help_card("Publicación segura", "Mantener despliegue, backups y monitoreo simples para el primer lanzamiento público."),
                help_card("Studio", "Mostrar el uso para organizaciones sin vender humo ni prometer magia."),
                columns="2",
                spacing="3",
                class_name="responsive-grid",
            ),
            subtitle="El proyecto avanza por iteraciones pequeñas y visibles, con evidencia verificable antes que marketing.",
        ),
        page_section(
            "Cómo ayudar",
            rx.grid(
                help_card("Menos fricción", "Equipos no técnicos pueden revisar, compartir y seguir un caso sin fricción innecesaria."),
                help_card("Universidades", "Explorar investigación, convenios, fuentes públicas y evidencia institucional."),
                help_card("ONG", "Monitorear temas públicos con trazabilidad y lenguaje ciudadano."),
                help_card("Organismos públicos", "Centralizar evidencia pública y seguimiento documental."),
                columns="2",
                spacing="3",
                class_name="responsive-grid",
            ),
            subtitle="Pensado para quien necesita una lectura de trabajo, no una demo técnica.",
        ),
        page_section(
            "Límite actual",
            rx.text(
                "No hay afirmaciones automáticas, ni inferencias encubiertas, ni fuentes inventadas. Hay lectura verificable con demo local.",
                class_name="story-summary",
            ),
            rx.text(
                "DatosEnOrden Studio se encuentra en desarrollo activo. Algunas capacidades ya forman parte de la plataforma pública y otras se incorporarán progresivamente.",
                class_name="story-summary",
            ),
            subtitle="Eso es suficiente para un primer lanzamiento público y deja claro dónde termina la demo.",
        ),
        page_section(
            "Cómo seguir",
            rx.text(
                "Si encuentras una mejora obvia, reporta la ruta y el texto exacto: eso ayuda más que ideas vagas.",
                class_name="story-summary",
            ),
            subtitle="La iteración siguiente debe mejorar la lectura sin cambiar la arquitectura base.",
        ),
        active_page=PAGE_PROJECT,
    )

@rx.page(
    route="/studio",
    title="DatosEnOrden Studio",
    description="Entrada comercial para organizaciones que necesitan expedientes, fuentes y automatización documental verificable.",
    image=PUBLIC_OG_IMAGE_URL,
    meta=_page_meta(
        "/studio",
        "datosenorden studio, expedientes, fuentes oficiales, automatización documental, organizaciones",
        "DatosEnOrden Studio",
        "Entrada comercial para organizaciones que necesitan expedientes, fuentes y automatización documental verificable.",
    ),
)
def studio() -> rx.Component:
    return shell(
        rx.box(
            rx.text("DatosEnOrden Studio", class_name="title"),
            rx.text(
                "La plataforma para municipalidades, universidades y equipos que necesitan ordenar información pública con evidencia y contexto.",
                class_name="subtitle",
            ),
            rx.text(
                "Explora conectores, expedientes, cronologías y documentos para trabajar con una lectura trazable, no con hojas sueltas.",
                class_name="muted small",
            ),
            rx.hstack(
                rx.link("Solicitar una conversación", href=STUDIO_CONVERSATION_URL, class_name="button primary-action"),
                rx.link("Enviar correo", href=f"mailto:{STUDIO_CONTACT_EMAIL}", class_name="button button-secondary"),
                spacing="3",
                wrap="wrap",
                class_name="hero-actions",
            ),
            class_name="hero studio-hero",
        ),
        page_section(
            "Qué obtiene una organización",
            rx.grid(
                help_card("Visibilidad", "Una ruta única para leer compras, presupuestos, publicaciones y evidencia relacionada."),
                help_card("Contexto", "Las piezas dejan de vivir en pantallas separadas y pasan a un expediente entendible."),
                help_card("Trazabilidad", "Cada lectura puede volver a su documento o fragmento de origen."),
                help_card("Menos fricción", "Equipos no técnicos pueden revisar, compartir y seguir un caso sin fricción innecesaria."),
                columns="2",
                spacing="3",
                class_name="responsive-grid",
            ),
            subtitle="Pensado para quien necesita una lectura de trabajo, no una demo técnica.",
        ),
        page_section(
            "Casos de uso",
            rx.grid(
                help_card("Municipalidades", "Ordenar documentos, compras, actos administrativos y seguimiento local."),
                help_card("Universidades", "Explorar investigación, convenios, fuentes públicas y evidencia institucional."),
                help_card("ONG", "Monitorear temas públicos con trazabilidad y lenguaje ciudadano."),
                help_card("Empresas", "Comprender proveedores, licitaciones, publicaciones y contexto regulatorio."),
                help_card("Consultoras", "Preparar expedientes verificables para análisis y reportes."),
                help_card("Organismos públicos", "Centralizar evidencia pública y seguimiento documental."),
                columns="2",
                spacing="3",
                class_name="responsive-grid",
            ),
            subtitle="Casos orientativos para conversaciones iniciales; cada implementación se revisa con evidencia y límites claros.",
        ),
        page_section(
            "Flujo",
            rx.grid(
                flow_card(1, "Entrar", "La organización llega por un caso, una fuente o un documento ya conocido."),
                flow_card(2, "Relacionar", "La plataforma conecta entidades, eventos, evidencia y cronología."),
                flow_card(3, "Revisar", "Se abren fragmentos y documentos para validar el texto original."),
                flow_card(4, "Compartir", "La lectura se puede mover internamente sin perder el enlace estable."),
                columns="4",
                spacing="3",
                class_name="responsive-grid",
            ),
            subtitle="Un flujo simple reduce el costo de adopción y hace más fácil explicar valor interno.",
        ),
        page_section(
            "Estado actual",
            rx.text(
                "DatosEnOrden Studio se encuentra en desarrollo activo. Algunas capacidades ya forman parte de la plataforma pública y otras se incorporarán progresivamente.",
                class_name="story-summary",
            ),
            subtitle="La versión pública muestra el producto sin esconder límites ni prometer automatizaciones inexistentes.",
        ),
        active_page=PAGE_STUDIO,
    )

@rx.page(
    route="/support",
    title="Apoyar DatosEnOrden",
    description="Página pública de apoyo y colaboración para el lanzamiento de DatosEnOrden.",
    image=PUBLIC_OG_IMAGE_URL,
    meta=_page_meta(
        "/support",
        "apoyar datosenorden, colaboración, lanzamiento público, feedback",
        "Apoyar DatosEnOrden",
        "Página pública de apoyo y colaboración para el lanzamiento de DatosEnOrden.",
    ),
)
def support() -> rx.Component:
    return shell(
        rx.box(
            rx.text("Apoyar DatosEnOrden", class_name="title"),
            rx.text(
                "El apoyo se canaliza mediante enlaces externos mientras el lanzamiento público mantiene una operación simple.",
                class_name="subtitle",
            ),
            rx.text(
                "Las donaciones no compran influencia ni alteran la prioridad de fuentes; solo ayudan a sostener infraestructura y trabajo continuo.",
                class_name="muted small",
            ),
            rx.text("Evidencia primero.", class_name="muted small"),
            support_cta_block(),
            rx.grid(
                support_action_card("Apoyo", "La plataforma sigue abierta a feedback, correcciones y colaboración puntual.", "Abrir enlace de apoyo", SUPPORT_DONATION_URL),
                support_action_card("Sugerir fuente", "Si falta una fuente pública, deja el enlace y el motivo para revisarlo.", "Sugerir una fuente", SUPPORT_SOURCE_SUGGESTION_URL),
                columns="2",
                spacing="3",
                class_name="responsive-grid",
            ),
        ),
        active_page=PAGE_SUPPORT,
    )


@rx.page(
    route="/search",
    title="Buscar - DatosEnOrden",
    description="Búsqueda y entrada guiada para explorar expedientes, entidades y documentos en DatosEnOrden.",
    image=PUBLIC_OG_IMAGE_URL,
    meta=_page_meta(
        "/search",
        "buscar, expedientes, entidades, documentos oficiales, entrada guiada",
        "Buscar - DatosEnOrden",
        "Búsqueda y entrada guiada para explorar expedientes, entidades y documentos en DatosEnOrden.",
    ),
)
def search() -> rx.Component:
    return shell(
        rx.box(
            rx.text("Buscar", class_name="title"),
            rx.text(
                "Empieza por una pregunta guiada. Si ya sabes que buscar, usa el buscador superior.",
                class_name="subtitle",
            ),
            class_name="hero",
        ),
        guided_discovery_panel(),
        what_to_investigate_panel(),
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
            rx.cond(AppState.query != "", search_empty_state()),
        ),
        on_mount=AppState.load_discover,
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


@rx.page(
    route="/investigation",
    title="Expediente - DatosEnOrden",
    description="Expediente ciudadano para reunir entidades, relaciones, evidencia y trazabilidad en una sola lectura.",
    image=PUBLIC_OG_IMAGE_URL,
    meta=_page_meta(
        "/investigation",
        "expediente, evidencia, relaciones, trazabilidad, lectura ciudadana",
        "Expediente - DatosEnOrden",
        "Expediente ciudadano para reunir entidades, relaciones, evidencia y trazabilidad en una sola lectura.",
    ),
    on_load=AppState.load_investigation,
)
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
                            next_step_card("Leer reporte ciudadano", "Ver una explicacion en formato articulo.", "Ir a Informes", "/reports"),
                            next_step_card("Ver documento fuente", "Revisar el documento junto a sus referencias.", "Ver documento", "/official-document"),
                            next_step_card("Seguir proyecto", "Ver la historia en el tiempo y sus hitos.", "Ir a Cronologia", "/tracking"),
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


@rx.page(
    route="/dashboard",
    title="Vista ciudadana - DatosEnOrden",
    description="Vista ciudadana de presupuesto, compras, proveedores y reuniones para explorar datos locales de muestra.",
    image=PUBLIC_OG_IMAGE_URL,
    meta=_page_meta(
        "/dashboard",
        "vista ciudadana, presupuesto, compras públicas, proveedores, reuniones",
        "Vista ciudadana - DatosEnOrden",
        "Vista ciudadana de presupuesto, compras, proveedores y reuniones para explorar datos locales de muestra.",
    ),
)
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
    ".shell-main": {"margin_left": "236px", "transition": "margin-left 220ms ease"},
    ".shell.sidebar-collapsed .shell-main": {"margin_left": "72px"},
    ".app-sidebar": {
        "position": "fixed",
        "top": "0",
        "left": "0",
        "bottom": "0",
        "width": "236px",
        "padding": "14px 10px",
        "border_right": "1px solid rgba(161, 161, 170, 0.16)",
        "background": "rgba(15, 15, 18, 0.96)",
        "backdrop_filter": "blur(18px)",
        "z_index": "45",
        "display": "grid",
        "grid_template_rows": "auto",
        "gap": "14px",
        "transition": "width 220ms ease",
    },
    ".shell.theme-light .app-sidebar": {"background": "rgba(255, 255, 255, 0.96)", "border_right": "1px solid rgba(113, 113, 122, 0.18)"},
    ".app-sidebar-collapsed": {"width": "72px"},
    ".sidebar-menu-button": {
        "width": "38px",
        "height": "38px",
        "padding": "0",
        "border_radius": "8px",
        "border": "1px solid rgba(161, 161, 170, 0.2)",
        "background": "rgba(255, 255, 255, 0.06)",
        "justify_self": "center",
        "margin_bottom": "6px",
    },    ".hamburger-icon": {"gap": "4px"},
    ".hamburger-line": {"width": "18px", "height": "2px", "border_radius": "999px", "background": "#e4e4e7"},
    ".shell.theme-light .hamburger-line": {"background": "#18181b"},
    ".sidebar-collapse-button, .sidebar-toggle": {
        "border_radius": "6px",
        "border": "1px solid rgba(161, 161, 170, 0.2)",
        "background": "rgba(255, 255, 255, 0.06)",
        "color": "#e4e4e7",
        "font_weight": "850",
        "min_width": "36px",
    },
    ".shell.theme-light .sidebar-collapse-button, .shell.theme-light .sidebar-toggle, .shell.theme-light .sidebar-menu-button": {"background": "#ffffff", "color": "#18181b"},
    ".sidebar-nav": {"overflow_y": "auto", "padding_right": "2px"},
    ".sidebar-group-label": {"padding": "8px 10px 4px", "color": "#71717a", "font_size": "11px", "font_weight": "850", "letter_spacing": "0.08em", "text_transform": "uppercase"},
    ".sidebar-divider": {"height": "1px", "margin": "10px 8px", "background": "rgba(161, 161, 170, 0.16)"},
    ".sidebar-nav-link": {
        "display": "grid",
        "grid_template_columns": "28px minmax(0, 1fr)",
        "align_items": "center",
        "gap": "8px",
        "padding": "9px 10px",
        "border_radius": "8px",
        "color": "#d4d4d8",
        "font_weight": "750",
        "font_size": "13px",
    },
    ".sidebar-nav-link-active": {"background": "rgba(45, 212, 191, 0.12)", "color": "#ccfbf1"},
    ".shell.theme-light .sidebar-nav-link": {"color": "#3f3f46"},
    ".shell.theme-light .sidebar-nav-link-active": {"background": "rgba(13, 148, 136, 0.12)", "color": "#0f766e"},
    ".sidebar-initial": {"display": "inline-flex", "align_items": "center", "justify_content": "center", "width": "26px", "height": "26px", "border_radius": "6px", "background": "rgba(255, 255, 255, 0.06)", "font_weight": "900"},
    ".sidebar-advanced-toggle": {
        "display": "flex",
        "align_items": "center",
        "justify_content": "space-between",
        "gap": "8px",
        "padding": "9px 10px",
        "border_radius": "8px",
        "border": "1px solid transparent",
        "background": "transparent",
        "color": "#a1a1aa",
        "font_weight": "800",
    },
    ".sidebar-advanced-symbol": {"font_weight": "900", "color": "#ccfbf1"},
    ".sidebar-secondary-nav": {"padding_left": "8px", "border_left": "1px solid rgba(161, 161, 170, 0.16)", "margin_left": "14px"},
    ".app-sidebar-collapsed .sidebar-label, .app-sidebar-collapsed .sidebar-group-label, .app-sidebar-collapsed .sidebar-advanced-symbol, .app-sidebar-collapsed .sidebar-divider": {"display": "none"},
    ".app-sidebar-collapsed .sidebar-nav-link": {"grid_template_columns": "1fr", "justify_items": "center", "padding": "9px 6px"},
    ".app-sidebar-collapsed .sidebar-advanced-toggle": {"justify_content": "center", "padding": "9px 6px"},
    ".shell-header": {
        "width": "100%",
        "border_bottom": "1px solid rgba(161, 161, 170, 0.10)",
        "background": "rgba(15, 15, 18, 0.72)",
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
        "padding": "10px 0",
        "gap": "16px",
    },
    ".page": {"max_width": "1760px", "margin": "0 auto", "width": "min(calc(100% - 48px), 1760px)"},
    ".site-footer": {
        "width": "min(calc(100% - 48px), 1760px)",
        "max_width": "1760px",
        "margin": "28px auto 0",
        "padding": "26px 0 0",
        "border_top": "1px solid rgba(161, 161, 170, 0.18)",
        "display": "grid",
        "gap": "18px",
    },
    ".footer-grid": {"max_width": "900px", "width": "100%", "margin": "0 auto", "align_items": "start"},
    ".footer-column": {"display": "grid", "gap": "8px", "align_content": "start"},
    ".footer-column-title": {"font_size": "11px", "font_weight": "850", "letter_spacing": "0.08em", "text_transform": "uppercase", "color": "#a1a1aa"},
    ".footer-copy": {"font_size": "13px", "color": "#a1a1aa"},
    ".footer-column-copy": {"margin_bottom": "2px"},
    ".footer-bottom-copy": {"text_align": "center"},
    ".footer-link": {"font_size": "13px", "color": "#d4d4d8", "font_weight": "600"},
    ".footer-column-link": {"width": "fit-content"},
    ".footer-link-icon": {"font_size": "13px", "width": "18px", "color": "#a1a1aa"},
    ".footer-link-label": {"font_size": "13px"},
    ".support-inline-block": {"display": "grid", "gap": "8px", "padding": "14px", "border": "1px solid rgba(45, 212, 191, 0.16)", "border_radius": "8px", "background": "rgba(45, 212, 191, 0.06)", "max_width": "520px"},
    ".support-copy": {"font_size": "14px", "line_height": "1.45", "color": "#d4d4d8"},
    ".support-mini-button": {"width": "fit-content"},
    ".support-action-card": {"display": "grid", "gap": "10px", "align_content": "start"},
    ".support-action-link": {"width": "fit-content"},
    ".shell.theme-light .footer-copy": {"color": "#71717a"},
    ".shell.theme-light .footer-link": {"color": "#374151"},
    ".shell.theme-light .support-copy": {"color": "#374151"},
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
    ".shell-alert": {
        "width": "min(calc(100% - 48px), 1760px)",
        "max_width": "1760px",
        "margin": "16px auto 0",
        "display": "grid",
        "gap": "10px",
        "border_left": "3px solid rgba(250, 204, 21, 0.58)",
    },
    ".shell-alert-actions": {"gap": "10px"},
    "a:focus-visible, button:focus-visible, input:focus-visible, textarea:focus-visible, select:focus-visible, iframe:focus-visible": {
        "outline": "3px solid rgba(45, 212, 191, 0.72)",
        "outline_offset": "3px",
    },
    ".hero": {
        "border": "1px solid rgba(161, 161, 170, 0.10)",
        "border_radius": "10px",
        "padding": "28px",
        "background": "rgba(24, 24, 27, 0.72)",
    },
    ".page-home .hero": {
        "padding": "54px 0 34px",
        "border": "0",
        "border_radius": "0",
        "background": "transparent",
        "max_width": "960px",
    },
    ".page-investigation .hero": {"border_left": "4px solid rgba(45, 212, 191, 0.55)"},
    ".page-library .hero": {"border_left": "4px solid rgba(167, 139, 250, 0.58)"},
    ".page-document .hero": {"border_left": "4px solid rgba(228, 228, 231, 0.58)"},
    ".page-tracking .hero": {"border_left": "4px solid rgba(74, 222, 128, 0.56)"},
    ".page-reports .hero": {"border_left": "4px solid rgba(251, 146, 60, 0.58)"},
    ".page-ecosystem .hero": {"border_left": "4px solid rgba(96, 165, 250, 0.58)"},
    ".page-project .hero": {"border_left": "4px solid rgba(161, 161, 170, 0.62)"},
    ".page-home .title": {"color": "#f4f4f5"},
    ".page-investigation .title": {"color": "#ccfbf1"},
    ".page-library .title": {"color": "#ddd6fe"},
    ".page-document .title": {"color": "#f4f4f5"},
    ".page-tracking .title": {"color": "#bbf7d0"},
    ".page-reports .title": {"color": "#fed7aa"},
    ".page-ecosystem .title": {"color": "#bfdbfe"},
    ".page-project .title": {"color": "#e4e4e7"},
    ".shell.theme-light .hero": {
        "background": "linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(247, 247, 248, 0.98))",
        "border_color": "rgba(113, 113, 122, 0.18)",
    },
    ".title": {"font_size": "42px", "font_weight": "850", "line_height": "1.08"},
    ".subtitle": {"color": "#a1a1aa", "max_width": "820px", "line_height": "1.55"},
    ".shell.theme-light .subtitle": {"color": "#71717a"},
    ".section-title": {"font_size": "20px", "font_weight": "700", "margin_bottom": "12px", "color": "#f4f4f5"},
    ".page-reports .section-title": {"font_size": "24px", "font_weight": "800", "color": "#fed7aa"},
    ".page-library .section-title": {"color": "#ddd6fe"},
    ".page-document .section-title": {"color": "#f4f4f5"},
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
        "padding": "10px 0 22px",
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
    ".page-document .page-section": {
        "padding": "18px 0",
        "border_top": "1px solid rgba(228, 228, 231, 0.12)",
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
    ".current-topic-card": {
        "border": "1px solid rgba(161, 161, 170, 0.10)",
        "border_radius": "8px",
        "padding": "16px",
        "background": "#18181b",
        "display": "grid",
        "gap": "10px",
        "align_content": "start",
    },
    ".shell.theme-light .current-topic-card": {"background": "#ffffff", "border_color": "rgba(113, 113, 122, 0.18)"},
    ".topic-answer-card": {
        "border": "1px solid rgba(161, 161, 170, 0.10)",
        "border_radius": "8px",
        "padding": "14px",
        "background": "#18181b",
        "display": "grid",
        "gap": "8px",
        "align_content": "start",
    },
    ".topic-status-card": {"min_height": "110px", "align_content": "start"},
    ".topic-card-document": {"border_left": "3px solid rgba(45, 212, 191, 0.62)"},
    ".topic-card-proposes": {"border_left": "3px solid rgba(96, 165, 250, 0.62)"},
    ".topic-card-changes": {"border_left": "3px solid rgba(167, 139, 250, 0.62)"},
    ".topic-card-no-change": {"border_left": "3px solid rgba(250, 204, 21, 0.62)"},
    ".topic-card-next": {"border_left": "3px solid rgba(74, 222, 128, 0.62)"},
    ".topic-card-evidence": {"border_left": "3px solid rgba(251, 146, 60, 0.62)"},
    ".topic-card-evidence-active": {"border_color": "rgba(251, 146, 60, 0.64)", "background": "rgba(251, 146, 60, 0.10)", "box_shadow": "0 0 0 3px rgba(251, 146, 60, 0.10)"},
    ".page-topic .shell-header": {"position": "sticky", "top": "0", "z_index": "20"},
    ".page-topic .nav-inner": {"padding": "8px 0", "gap": "10px"},
    ".page-topic .nav-links": {"gap": "12px", "font_size": "13px"},
    ".page-topic .header-search-toggle, .page-topic .theme-toggle": {"padding": "6px 10px"},
    ".sidebar-ready-nav": {"min_width": "0"},
    ".top-minimal-nav": {"flex": "0 1 auto"},
    ".scroll-top-button": {
        "position": "fixed",
        "right": "24px",
        "bottom": "24px",
        "z_index": "60",
        "opacity": "0",
        "pointer_events": "none",
        "transform": "translateY(14px)",
        "transition": "opacity 180ms ease, transform 180ms ease",
        "border_radius": "999px",
        "border": "1px solid rgba(45, 212, 191, 0.34)",
        "background": "rgba(15, 118, 110, 0.92)",
        "color": "#ecfeff",
        "font_weight": "850",
        "box_shadow": "0 14px 40px rgba(0, 0, 0, 0.22)",
    },
    ".scroll-top-button.scroll-top-visible": {"opacity": "1", "pointer_events": "auto", "transform": "translateY(0)"},
    ".home-pulse-hero": {"padding_bottom": "34px"},
    ".hero-action-note": {"color": "#a1a1aa", "font_size": "14px", "align_self": "center"},
    ".primary-action": {"padding": "13px 18px", "border_radius": "8px"},
    ".topic-mode-selector": {
        "padding": "6px",
        "border": "1px solid rgba(161, 161, 170, 0.10)",
        "border_radius": "8px",
        "background": "rgba(255, 255, 255, 0.04)",
        "width": "fit-content",
    },
    ".topic-mode-button": {
        "border_radius": "6px",
        "border": "1px solid transparent",
        "background": "transparent",
        "color": "#d4d4d8",
        "font_weight": "800",
    },
    ".topic-mode-button-active": {"background": "rgba(45, 212, 191, 0.14)", "border_color": "rgba(45, 212, 191, 0.28)", "color": "#ccfbf1"},
    ".shell.theme-light .topic-mode-selector": {"background": "rgba(255, 255, 255, 0.72)", "border_color": "rgba(113, 113, 122, 0.18)"},
    ".shell.theme-light .topic-mode-button": {"color": "#3f3f46"},
    ".shell.theme-light .topic-mode-button-active": {"background": "rgba(13, 148, 136, 0.12)", "border_color": "rgba(13, 148, 136, 0.24)", "color": "#0f766e"},
    ".topic-mode-shell": {"min_width": "0"},
    ".topic-single-mode": {"display": "grid", "gap": "14px", "max_width": "980px", "width": "100%", "margin": "0 auto", "padding": "0 0 22px"},
    ".topic-single-mode .topic-source-panel": {"position": "relative", "top": "auto", "max_height": "80vh"},
    ".topic-system-placeholder": {
        "display": "grid",
        "gap": "16px",
        "padding": "18px",
        "border": "1px solid rgba(74, 222, 128, 0.22)",
        "border_radius": "8px",
        "background": "#18181b",
    },
    ".topic-evidence-mode-panel": {"align_self": "start"},
    ".pulse-field": {"display": "grid", "gap": "4px", "padding_top": "8px", "border_top": "1px solid rgba(161, 161, 170, 0.12)"},
    ".pulse-field-label": {"font_size": "11px", "font_weight": "850", "letter_spacing": "0.07em", "text_transform": "uppercase", "color": "#a1a1aa"},
    ".document-sheet": {
        "border": "1px solid rgba(113, 113, 122, 0.18)",
        "border_radius": "8px",
        "padding": "38px",
        "background": "#f8fafc",
        "color": "#18181b",
        "box_shadow": "0 18px 60px rgba(0, 0, 0, 0.18)",
    },
    ".document-sheet-cover": {"display": "grid", "gap": "6px", "padding_bottom": "18px", "border_bottom": "1px solid rgba(113, 113, 122, 0.18)", "margin_bottom": "6px"},
    ".document-sheet-title": {"font_size": "20px", "font_weight": "850", "line_height": "1.25", "color": "#111827"},
    ".live-system-heading": {"display": "grid", "gap": "6px"},
    ".live-stage-grid": {"align_items": "stretch"},
    ".live-stage-card": {
        "min_height": "118px",
        "padding": "14px",
        "border": "1px solid rgba(45, 212, 191, 0.18)",
        "border_radius": "8px",
        "background": "rgba(255, 255, 255, 0.04)",
        "display": "grid",
        "gap": "7px",
        "align_content": "start",
    },
    ".live-stage-state": {"font_size": "12px", "font_weight": "850", "color": "#ccfbf1"},
    ".live-stage-title": {"font_size": "16px", "font_weight": "850", "color": "#f4f4f5"},
    ".live-stage-body": {"font_size": "13px", "line_height": "1.45", "color": "#a1a1aa"},
    ".live-timeline-panel": {"overflow": "hidden"},
    ".live-timeline-strip": {"overflow_x": "auto", "padding_bottom": "8px", "scroll_snap_type": "x proximity"},
    ".live-timeline-strip .tracking-event-card": {"flex": "0 0 270px", "scroll_snap_align": "start"},
    ".topic-document-first-layout": {
        "display": "grid",
        "grid_template_columns": "minmax(0, 58fr) minmax(64px, 0.08fr) minmax(0, 42fr)",
        "gap": "14px",
        "align_items": "start",
        "width": "100%",
        "padding": "0 0 22px",
    },
    ".topic-source-panel": {
        "position": "sticky",
        "top": "72px",
        "max_height": "86vh",
        "overflow_y": "auto",
        "border": "1px solid rgba(45, 212, 191, 0.18)",
        "border_radius": "8px",
        "padding": "14px",
        "background": "#18181b",
        "display": "grid",
        "gap": "12px",
        "align_content": "start",
    },
    ".shell.theme-light .topic-source-panel": {"background": "#ffffff", "color": "#18181b"},
    ".topic-source-header": {"align_items": "center"},
    ".topic-current-anchor": {"position": "sticky", "top": "0", "z_index": "3"},
    ".topic-source-guidance": {"font_size": "13px", "line_height": "1.45", "color": "#a1a1aa", "border_left": "3px solid rgba(45, 212, 191, 0.34)", "padding_left": "10px"},
    ".shell.theme-light .topic-source-guidance": {"color": "#52525b"},
    ".topic-source-excerpt": {"color": "#27272a", "font_size": "14px", "line_height": "1.55"},
    ".topic-document-page": {"gap": "12px"},
    ".topic-original-link": {"width": "fit-content"},
    ".topic-pdf-document-viewer": {"display": "grid", "gap": "12px"},
    ".topic-pdf-frame": {"width": "100%", "min_height": "68vh", "border": "1px solid rgba(113, 113, 122, 0.18)", "border_radius": "8px", "background": "#f8fafc"},
    ".topic-pdf-citation-panel": {"border_left": "4px solid #0f766e", "padding": "10px 12px", "background": "rgba(13, 148, 136, 0.08)", "display": "grid", "gap": "6px"},
    ".topic-context-rail": {"position": "sticky", "top": "72px", "max_height": "86vh", "display": "grid", "gap": "7px", "align_content": "start", "padding": "8px 6px", "border_left": "1px solid rgba(161, 161, 170, 0.16)", "border_right": "1px solid rgba(161, 161, 170, 0.10)"},
    ".topic-rail-label": {"font_size": "11px", "font_weight": "850", "text_transform": "uppercase", "letter_spacing": "0.04em", "color": "#a1a1aa"},
    ".topic-rail-link": {"font_size": "12px", "line_height": "1.25", "color": "#ccfbf1", "border_radius": "6px", "padding": "5px 6px", "background": "rgba(45, 212, 191, 0.07)"},
    ".shell.theme-light .topic-rail-link": {"color": "#0f766e", "background": "rgba(45, 212, 191, 0.08)"},
    ".topic-reading-column": {"min_width": "0", "display": "grid", "gap": "16px"},
    ".topic-reading-flow": {"width": "100%"},
    ".topic-reading-section": {
        "border": "1px solid rgba(161, 161, 170, 0.10)",
        "border_radius": "8px",
        "padding": "16px",
        "background": "#18181b",
        "display": "grid",
        "gap": "14px",
        "scroll_margin_top": "82px",
    },
    ".shell.theme-light .topic-reading-section": {"background": "#ffffff", "border_color": "rgba(113, 113, 122, 0.18)"},
    ".topic-compact-grid": {"width": "100%"},
    ".topic-evidence-grid": {"align_items": "stretch"},
    ".shell.theme-light .topic-answer-card": {"background": "#ffffff", "border_color": "rgba(113, 113, 122, 0.18)"},
    ".card": {
        "border": "1px solid rgba(161, 161, 170, 0.10)",
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
    ".document-hero": {
        "padding": "20px 0 10px",
        "display": "grid",
        "gap": "14px",
        "border_bottom": "1px solid rgba(228, 228, 231, 0.12)",
    },
    ".document-hero-copy": {"display": "grid", "gap": "8px", "max_width": "1040px"},
    ".document-kicker": {"font_size": "13px", "font_weight": "800", "letter_spacing": "0.08em", "text_transform": "uppercase", "color": "#2dd4bf"},
    ".document-title": {"font_size": "34px", "font_weight": "850", "line_height": "1.12", "color": "#f4f4f5", "max_width": "1080px"},
    ".document-subtitle": {"font_size": "16px", "line_height": "1.55", "color": "#a1a1aa", "max_width": "860px"},
    ".document-meta-row": {"align_items": "center"},
    ".document-meta-pill": {
        "border": "1px solid rgba(161, 161, 170, 0.22)",
        "border_radius": "999px",
        "padding": "5px 10px",
        "font_size": "12px",
        "color": "#d4d4d8",
        "background": "rgba(24, 24, 27, 0.72)",
    },
    ".document-meta-reference": {"font_family": "Consolas, monospace", "font_size": "12px", "color": "#a1a1aa", "overflow_wrap": "anywhere"},
    ".official-document-layout": {
        "display": "grid",
        "grid_template_columns": "minmax(0, 1.95fr) minmax(340px, 0.72fr)",
        "gap": "28px",
        "align_items": "start",
        "padding": "22px 0",
    },
    ".document-main-column": {"min_width": "0"},
    ".document-side-column": {"min_width": "0", "position": "sticky", "top": "88px"},
    ".official-document-viewer": {"display": "grid", "gap": "14px"},
    ".reading-context-bar": {
        "border": "1px solid rgba(161, 161, 170, 0.10)",
        "border_radius": "8px",
        "padding": "12px",
        "background": "#18181b",
        "display": "grid",
        "grid_template_columns": "minmax(190px, 1fr) repeat(4, minmax(110px, auto))",
        "gap": "10px",
        "align_items": "center",
    },
    ".document-reading-status": {"font_weight": "800", "color": "#ccfbf1"},
    ".document-metric": {"display": "grid", "gap": "2px"},
    ".document-metric-value": {"font_size": "20px", "font_weight": "850", "color": "#f4f4f5"},
    ".document-metric-label": {"font_size": "11px", "color": "#a1a1aa", "text_transform": "uppercase", "letter_spacing": "0.04em"},
    ".document-paper": {
        "border": "1px solid rgba(228, 228, 231, 0.16)",
        "border_radius": "8px",
        "padding": "28px",
        "background": "#f8fafc",
        "color": "#18181b",
        "display": "grid",
        "gap": "18px",
        "box_shadow": "0 18px 60px rgba(0, 0, 0, 0.18)",
    },
    ".document-label": {"font_size": "12px", "font_weight": "850", "letter_spacing": "0.08em", "text_transform": "uppercase", "color": "#0f766e"},
    ".document-page-nav": {"border_bottom": "1px solid rgba(113, 113, 122, 0.18)", "padding_bottom": "12px"},
    ".page-chip": {
        "border": "1px solid rgba(113, 113, 122, 0.22)",
        "border_radius": "6px",
        "background": "#ffffff",
        "color": "#18181b",
        "font_weight": "800",
    },
    ".page-chip-active": {"border_color": "#0f766e", "background": "rgba(13, 148, 136, 0.1)", "color": "#0f766e"},
    ".document-current-anchor": {
        "border_left": "4px solid #0f766e",
        "padding": "10px 12px",
        "background": "rgba(13, 148, 136, 0.08)",
        "display": "grid",
        "gap": "6px",
    },
    ".document-page-label": {"font_weight": "850", "color": "#18181b"},
    ".document-highlight": {"color": "#374151", "line_height": "1.55"},
    ".document-location-notice": {"font_size": "12px", "line_height": "1.4", "color": "#92400e", "background": "rgba(251, 191, 36, 0.16)", "border": "1px solid rgba(251, 191, 36, 0.28)", "border_radius": "6px", "padding": "7px 9px"},
    ".document-page": {"display": "grid", "gap": "18px", "scroll_behavior": "smooth"},
    ".document-fragment": {
        "border": "1px solid transparent",
        "border_radius": "4px",
        "padding": "12px 4px 14px",
        "background": "transparent",
        "display": "grid",
        "gap": "8px",
        "cursor": "pointer",
        "scroll_margin_top": "28px",
    },
    ".document-fragment + .document-fragment": {"border_top": "1px solid rgba(113, 113, 122, 0.13)"},
    ".document-fragment-active": {"border_color": "rgba(13, 148, 136, 0.55)", "background": "rgba(204, 251, 241, 0.72)", "box_shadow": "0 0 0 3px rgba(13, 148, 136, 0.13)", "animation": "document-pulse 2.8s ease-out"},
    ".document-page-marker": {"font_size": "11px", "font_weight": "850", "color": "#0f766e", "letter_spacing": "0.05em", "text_transform": "uppercase"},
    ".document-section-title": {"font_size": "13px", "font_weight": "850", "color": "#374151"},
    ".document-fragment-text": {"font_size": "17px", "line_height": "1.85", "color": "#18181b"},
    ".fragment-supports": {"border_top": "1px solid rgba(113, 113, 122, 0.14)", "padding_top": "10px", "display": "grid", "gap": "8px"},
    ".document-cross-label": {"font_size": "12px", "font_weight": "800", "color": "#52525b"},
    ".document-inline-link": {
        "border_bottom": "1px solid rgba(13, 148, 136, 0.45)",
        "color": "#0f766e",
        "font_weight": "800",
        "font_size": "13px",
    },
    ".reading-guide-panel": {
        "border_left": "1px solid rgba(161, 161, 170, 0.18)",
        "padding_left": "20px",
        "display": "grid",
        "gap": "16px",
    },
    ".reading-guide-title": {"font_size": "24px", "font_weight": "850", "color": "#f4f4f5"},
    ".reading-guide-summary": {"font_size": "15px", "line_height": "1.55", "color": "#d4d4d8"},
    ".reading-guide-section": {"display": "grid", "gap": "9px", "padding_top": "12px", "border_top": "1px solid rgba(161, 161, 170, 0.14)"},
    ".reading-guide-heading": {"font_size": "12px", "font_weight": "850", "letter_spacing": "0.06em", "text_transform": "uppercase", "color": "#a1a1aa"},
    ".guide-entry": {"display": "grid", "gap": "7px", "padding": "3px 0", "cursor": "pointer"},
    ".guide-title": {"font_size": "15px", "font_weight": "850", "color": "#f4f4f5", "line_height": "1.35"},
    ".guide-copy": {"font_size": "13px", "line_height": "1.5", "color": "#a1a1aa"},
    ".guide-evidence": {"display": "grid", "gap": "6px"},
    ".reference-button": {
        "width": "fit-content",
        "border_radius": "6px",
        "background": "rgba(45, 212, 191, 0.12)",
        "border": "1px solid rgba(45, 212, 191, 0.18)",
        "color": "#ccfbf1",
        "font_weight": "850",
        "font_size": "12px",
    },
    ".document-reference-section": {"padding": "18px 0 8px", "border_top": "1px solid rgba(228, 228, 231, 0.12)", "display": "grid", "gap": "12px"},
    ".reference-strip": {"display": "grid", "grid_template_columns": "repeat(4, minmax(0, 1fr))", "gap": "18px"},
    ".shell.theme-light .document-title, .shell.theme-light .reading-guide-title, .shell.theme-light .guide-title": {"color": "#18181b"},
    ".shell.theme-light .document-subtitle, .shell.theme-light .reading-guide-summary, .shell.theme-light .guide-copy": {"color": "#52525b"},
    ".shell.theme-light .reading-context-bar": {"background": "#ffffff", "border_color": "rgba(113, 113, 122, 0.18)"},
    ".shell.theme-light .document-reading-status": {"color": "#0f766e"},
    ".shell.theme-light .document-metric-value": {"color": "#18181b"},
    ".shell.theme-light .reading-guide-panel": {"border_left": "1px solid rgba(113, 113, 122, 0.2)"},
    ".knowledge-point": {
        "border": "1px solid rgba(45, 212, 191, 0.16)",
        "border_left": "3px solid rgba(45, 212, 191, 0.42)",
        "border_radius": "8px",
        "padding": "12px",
        "background": "rgba(24, 24, 27, 0.42)",
        "display": "grid",
        "gap": "8px",
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
        "border": "1px solid rgba(161, 161, 170, 0.10)",
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
    ".loading-shell": {"min_height": "100vh"},
    ".loading-skeleton-hero": {"display": "grid", "gap": "14px"},
    ".loading-skeleton-card": {"min_height": "210px", "display": "grid", "gap": "10px", "align_content": "start"},
    ".loading-skeleton-line": {
        "height": "12px",
        "border_radius": "999px",
        "background": "linear-gradient(90deg, rgba(45, 212, 191, 0.18), rgba(228, 228, 231, 0.14), rgba(45, 212, 191, 0.18))",
        "background_size": "200% 100%",
        "animation": "loading-pulse 1.6s ease-in-out infinite",
    },
    ".loading-skeleton-line-medium": {"width": "68%"},
    ".loading-skeleton-line-short": {"width": "42%"},
    ".not-found-hero": {
        "grid_template_columns": "minmax(0, 1.35fr) minmax(240px, 0.7fr)",
        "align_items": "center",
        "width": "100%",
    },
    ".not-found-illustration": {"position": "relative", "display": "grid", "justify_items": "center", "padding": "12px"},
    ".not-found-document-card": {
        "width": "220px",
        "min_height": "260px",
        "border": "1px solid rgba(161, 161, 170, 0.18)",
        "border_radius": "16px",
        "padding": "18px",
        "background": "linear-gradient(180deg, rgba(45, 212, 191, 0.12), rgba(24, 24, 27, 0.92))",
        "display": "grid",
        "gap": "12px",
        "box_shadow": "0 18px 50px rgba(0, 0, 0, 0.22)",
    },
    ".shell.theme-light .not-found-document-card": {
        "background": "linear-gradient(180deg, rgba(45, 212, 191, 0.12), #ffffff)",
        "border_color": "rgba(113, 113, 122, 0.18)",
    },
    ".not-found-document-tab": {"width": "72px", "height": "10px", "border_radius": "999px", "background": "rgba(45, 212, 191, 0.52)"},
    ".not-found-document-body": {"display": "grid", "gap": "10px"},
    ".not-found-document-line": {"height": "12px", "border_radius": "999px", "background": "rgba(212, 212, 216, 0.24)"},
    ".not-found-document-line-medium": {"width": "76%"},
    ".not-found-document-line-short": {"width": "52%"},
    ".not-found-badge": {
        "position": "absolute",
        "right": "18px",
        "bottom": "18px",
        "padding": "7px 12px",
        "border_radius": "999px",
        "background": "rgba(250, 204, 21, 0.16)",
        "border": "1px solid rgba(250, 204, 21, 0.28)",
        "color": "#fde68a",
        "font_size": "12px",
        "font_weight": "800",
    },
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
    "@keyframes loading-pulse": {
        "0%": {"background_position": "0% 50%", "opacity": "0.72"},
        "50%": {"background_position": "100% 50%", "opacity": "1"},
        "100%": {"background_position": "0% 50%", "opacity": "0.72"},
    },
    "@keyframes document-pulse": {
        "0%": {"background": "#ccfbf1"},
        "35%": {"background": "#ecfeff"},
        "100%": {"background": "#ffffff"},
    },
    "@media (max-width: 900px)": {
        ".shell-main": {"margin_left": "0"},
        ".shell.sidebar-collapsed .shell-main": {"margin_left": "0"},
        ".app-sidebar": {"display": "none"},
        ".nav-inner": {"flex_wrap": "wrap"},
        ".nav-links": {"justify_content": "flex-start"},
        ".investigation-layout": {"grid_template_columns": "1fr"},
        ".context-panel": {"position": "static"},
        ".investigation-sidebar": {"max_height": "none"},
        ".search-input": {"min_width": "0"},
        ".search-bar": {"flex_direction": "column", "align_items": "stretch"},
        ".search-button": {"width": "100%"},
        ".home-lower-layout": {"grid_template_columns": "1fr"},
        ".official-document-layout": {"grid_template_columns": "1fr"},
        ".document-side-column": {"position": "static"},
        ".not-found-hero": {"grid_template_columns": "1fr"},
        ".reading-context-bar": {"grid_template_columns": "1fr 1fr", "align_items": "start"},
        ".topic-document-first-layout": {"grid_template_columns": "1fr"},
        ".topic-context-rail": {"display": "none"},
        ".topic-source-panel": {"position": "static", "max_height": "72vh"},
        ".footer-grid": {"grid_template_columns": "1fr"},
        ".topic-evidence-grid": {"grid_template_columns": "1fr"},
        ".reference-strip": {"grid_template_columns": "1fr"},
    },
}

style.update({
    ".section-icon": {"font_size": "18px", "color": "#34d399", "font_weight": "900"},
    ".source-card-icon": {"font_size": "18px", "color": "#60a5fa", "font_weight": "900"},
    ".reading-share-actions": {"margin_top": "10px"},
    ".share-pill": {"text_decoration": "none", "font_weight": "850"},
    ".fragment-nav-grid": {"grid_template_columns": "1fr", "gap": "10px"},
    ".topic-fragment-nav-item": {"border": "1px solid rgba(148, 163, 184, 0.16)", "background": "rgba(15, 23, 42, 0.55)", "text_align": "left", "padding": "12px 14px", "border_radius": "16px", "transition": "transform 160ms ease, border-color 160ms ease, background 160ms ease, box-shadow 160ms ease"},
    ".topic-fragment-nav-item-active": {"border_color": "rgba(52, 211, 153, 0.5)", "background": "rgba(20, 83, 45, 0.26)", "box_shadow": "0 12px 32px rgba(15, 23, 42, 0.35)"},
    ".reading-share-actions .button": {"min_height": "36px"},
    ".site-footer": {"border_top": "1px solid rgba(148, 163, 184, 0.14)", "background": "linear-gradient(180deg, rgba(15, 15, 18, 0.92), rgba(8, 8, 11, 0.98))"},
    ".footer-column": {"display": "grid", "gap": "10px"},
    ".footer-copy": {"max_width": "56ch"},
    ".footer-column-copy": {"margin_bottom": "2px"},
    ".document-paper": {"gap": "12px"},
    ".document-current-anchor": {"display": "grid", "gap": "8px"},
    ".topic-pdf-citation-panel": {"display": "grid", "gap": "8px"},
    ".document-inline-link": {"text_decoration": "none"},
    ".badge-blue": {"background": "rgba(59, 130, 246, 0.12)", "color": "#bfdbfe"},
    ".badge-green": {"background": "rgba(34, 197, 94, 0.12)", "color": "#bbf7d0"},
    ".badge-red": {"background": "rgba(239, 68, 68, 0.12)", "color": "#fecaca"},
    ".badge-purple": {"background": "rgba(168, 85, 247, 0.12)", "color": "#e9d5ff"},
})


def _global_head_components() -> list[rx.Component]:
    return [
        rx.el.link(rel="icon", href="/favicon.ico"),
        rx.el.link(rel="apple-touch-icon", href="/apple-touch-icon.png"),
        rx.el.link(rel="manifest", href=PUBLIC_MANIFEST_PATH),
        rx.el.meta(name="application-name", content=PUBLIC_SITE_NAME),
        rx.el.meta(name="apple-mobile-web-app-title", content=PUBLIC_SITE_NAME),
        rx.el.meta(name="theme-color", content=PUBLIC_THEME_COLOR),
    ]


app = rx.App(
    style=style,
    head_components=_global_head_components(),
    html_lang="es",
    hydrate_fallback=public_hydrate_fallback(),
)
