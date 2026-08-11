from __future__ import annotations

import os

from reflex_app.constants.routes import INVESTIGATION_STATUS_IDLE
from reflex_app.helpers.public_values import _clean
from reflex_app.helpers.routing import _investigation_href
from reflex_app.models.source import SOURCE_COVERAGE_TEMPLATE
from reflex_app.serialization.json_safe import _json_dict, _json_list
from datosenorden.maintenance.safe_access import _field as _safe_field

GRAPH_EXPLANATION = (
    "Esta entidad aparece conectada con compras publicas, roles publicos y registros de lobby. "
    "Cada conexion proviene de una fuente cargada y evidencia asociada. "
    "Esto no implica causalidad ni irregularidad."
)

_field = _safe_field


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

def _public_error_message(action: str, *, next_step: str = "Puedes recargar, volver al inicio o seguir con una ruta estable.") -> str:
    return f"No pudimos {action}. {next_step}"

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
    self.report_available = False
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
