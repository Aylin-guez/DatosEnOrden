from __future__ import annotations

from datosenorden.web.app_services import get_guided_discovery_options, get_guided_questions, search_workspace


def _public_text(value: object, default: str = "") -> str:
    """Keep presentation DTOs textual; never surface a Python object representation."""
    if isinstance(value, str):
        return value.strip() or default
    if isinstance(value, (int, float)):
        return str(value)
    return default


def _public_count(value: object) -> int:
    """Keep absent or serialized state out of public result cards."""
    if isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)):
        return max(0, int(value))
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return 0


def _citizen_result_type_label(value: object) -> str:
    labels = {
        "COMPANY": "Proveedor",
        "SUPPLIER": "Proveedor",
        "PUBLIC_ORGANIZATION": "Organismo público",
        "PERSON": "Persona",
        "AUTHORITY": "Autoridad",
        "OFFICIAL_PUBLICATION": "Publicación oficial",
        "PUBLICATION": "Publicación oficial",
        "LOBBY_MEETING": "Reunión registrada",
        "CONTRACT": "Contrato o compra",
        "PURCHASE_ORDER": "Contrato o compra",
        "DOCUMENT": "Documento oficial",
        "PUBLIC_PROJECT": "Proyecto legislativo",
        "EXPEDIENTE PÚBLICO": "Expediente",
    }
    normalized = _public_text(value).upper()
    return labels.get(normalized, "Información pública")


def _pluralize_citizen_label(label: str, count: int) -> str:
    plurals = {
        "Proveedor": "proveedores",
        "Organismo público": "organismos públicos",
        "Persona": "personas",
        "Autoridad": "autoridades",
        "Publicación oficial": "publicaciones oficiales",
        "Reunión registrada": "reuniones registradas",
        "Contrato o compra": "contratos o compras",
        "Documento oficial": "documentos oficiales",
        "Proyecto legislativo": "proyectos legislativos",
    }
    return label.lower() if count == 1 else plurals.get(label, "resultados")


def state_graph_badges_for_match(row: dict) -> str:
    datasets = " ".join(str(item) for item in row.get("datasets", [])).lower()
    entity_type = str(row.get("entity_type", "") or row.get("entity_type_label", "")).lower()
    labels: list[str] = []
    if "chilecompra" in datasets or "compra" in entity_type:
        labels.append("compras")
    if "lobby" in datasets or "reunion" in entity_type or "reunion" in entity_type:
        labels.append("reuniones")
    if "diario" in datasets or "publicacion" in entity_type or "publicacion" in entity_type:
        labels.append("publicaciones")
    if "document" in entity_type or "documento" in entity_type:
        labels.append("documentos")
    unique = list(dict.fromkeys(labels))
    return "Información relacionada: " + " | ".join(label.capitalize() for label in unique) if unique else ""


def action_label_for_match(row: dict) -> str:
    if row.get("action_href"):
        return str(row.get("action_label", "Abrir"))
    if bool(row.get("is_record", False)):
        return "Ver informacion disponible"
    if _public_count(row.get("relationship_count")) or _public_count(row.get("evidence_count")):
        return "Abrir expediente actualizado"
    if "document" in str(row.get("entity_type", "")).lower() or "documento" in str(row.get("entity_type_label", "")).lower():
        return "Ver lectura desde fuentes disponibles"
    return "Ver informacion disponible"


def coverage_summary_for_match(row: dict) -> str:
    evidence = _public_count(row.get("evidence_count"))
    relationships = _public_count(row.get("relationship_count"))
    if evidence or relationships:
        return f"Cobertura local: {evidence} evidencias y {relationships} relaciones disponibles."
    return "Cobertura local insuficiente para formar una lectura completa."


def format_guided_options(rows: list[dict]) -> list[dict]:
    return [
        {
            **dict(row),
            "sources_text": str(row.get("sources_text") or " | ".join(str(item) for item in row.get("sources", [])) or "Fuentes locales"),
            "canonical_entity_id": str(row.get("canonical_entity_id", row.get("entity_id", ""))),
            "canonical_entity_name": str(row.get("canonical_entity_name", row.get("title", ""))),
            "canonical_investigation_href": _investigation_href_value(str(row.get("canonical_entity_id", row.get("entity_id", "")))),
            "record_badge": "Registro especifico" if bool(row.get("is_record", False)) else str(row.get("type_label", row.get("type", ""))),
            "related_text": (
                f"Relacionado con: {row.get('canonical_entity_name')}"
                if bool(row.get("is_record", False)) and row.get("canonical_entity_name")
                else ""
            ),
        }
        for row in rows
    ]


def format_workspace_matches(workspace: dict) -> list[dict]:
    return [_format_workspace_match(row) for row in workspace.get("matches", [])]


def _format_workspace_match(row: dict) -> dict:
    datasets = [_public_text(item) for item in row.get("datasets", [])]
    datasets = [item for item in datasets if item]
    entity_id = _public_text(row.get("entity_id"))
    entity_name = _public_text(row.get("entity_name"), "Información pública disponible")
    entity_type = _public_text(row.get("entity_type"), "Entidad")
    action_href = _public_text(row.get("action_href"))
    return {
            "id": _public_text(row.get("id"), entity_id),
            "result_type": _public_text(row.get("result_type"), "entidad"),
            "official_status": _public_text(row.get("official_status")),
            "source_label": _public_text(row.get("source_label")),
            "source_hint": (
                "Contenido DEMO (separado de datos incorporados)"
                if str(row.get("classification", "REAL")) == "DEMO"
                else
                "Registro específico"
                if bool(row.get("is_record", False))
                else "Información pública incorporada"
                if _public_count(row.get("relationship_count")) or _public_count(row.get("evidence_count"))
                else "Información disponible"
            ),
            "datasets": datasets,
            "datasets_text": " | ".join(datasets) if datasets else "Fuentes disponibles",
            "entity_id": entity_id,
            "entity_name": entity_name,
            "entity_type": entity_type,
            "entity_type_label": _citizen_result_type_label(entity_type),
            "canonical_entity_id": _public_text(row.get("canonical_entity_id"), entity_id),
            "canonical_entity_name": _public_text(row.get("canonical_entity_name"), entity_name),
            "canonical_investigation_href": _investigation_href_value(_public_text(row.get("canonical_entity_id"), entity_id)),
            "related_label": _public_text(row.get("related_label")),
            "is_record": bool(row.get("is_record", False)),
            "state_graph_badges_text": state_graph_badges_for_match(row),
            "match_reason": _public_text(row.get("why_it_appears"), "Aparece por la consulta realizada en información pública incorporada."),
            "coverage_summary": coverage_summary_for_match(row),
            "source_contribution": (
                "Fuentes que contribuyen: " + " | ".join(datasets)
                if datasets
                else "Fuente pública incorporada sin detalle disponible."
            ),
            "action_label": (
                "Ver información disponible"
                if action_href.startswith("/investigation")
                else _public_text(row.get("action_label"), action_label_for_match(row))
            ),
            "classification": _public_text(row.get("classification"), "REAL"),
            "action_href": action_href,
            "guidance_eligible": bool(row.get("guidance_eligible", False)),
            "evidence_count": _public_count(row.get("evidence_count")),
            "relationship_count": _public_count(row.get("relationship_count")),
            "evidence_label": (
                f"Evidencia: {_public_count(row.get('evidence_count'))}"
                if _public_count(row.get("evidence_count"))
                else ""
            ),
            "relationship_label": (
                f"Relaciones: {_public_count(row.get('relationship_count'))}"
                if _public_count(row.get("relationship_count"))
                else ""
            ),
        }


def run_workspace_search(query: str) -> list[dict]:
    return format_workspace_matches(search_workspace(query))


def build_guided_journey(question_id: str, title: str, description: str, query: str) -> dict:
    """Project a completed guided question without mutating manual-search state.

    Guided questions are a distinct citizen interaction.  They may surface zero,
    one, or several locally published readings, and only real expedients receive
    the direct-reader action.
    """
    cleaned_query = _public_text(query)
    matches = [
        row
        for row in run_workspace_search(cleaned_query)
        if row["classification"] == "REAL"
        and (
            not row["action_href"].startswith("/laboratory/expedient?id=")
            or row["guidance_eligible"]
        )
    ] if cleaned_query else []
    expedients = [
        row
        for row in matches
        if row["action_href"].startswith("/laboratory/expedient?id=") and row["guidance_eligible"]
    ]
    entities = [row for row in matches if not row["action_href"].startswith("/laboratory/expedient?id=")]
    if len(entities) == 1:
        entities = [
            {
                **entities[0],
                "related_expedient_count": len(expedients),
                "related_expedient_count_text": (
                    f"{len(expedients)} expediente relacionado disponible"
                    if len(expedients) == 1
                    else f"{len(expedients)} expedientes relacionados disponibles"
                    if expedients
                    else "Sin expediente ciudadano relacionado disponible todavía"
                ),
            }
        ]
    else:
        entities = [
            {**row, "related_expedient_count": 0, "related_expedient_count_text": ""}
            for row in entities
        ]
    result_count = len(entities)
    displayed_count = len(matches)
    source_scope = list(dict.fromkeys(source for row in matches for source in row["datasets"] if source))
    result_type_labels = list(dict.fromkeys(row["entity_type_label"] for row in entities))
    entity_label = _pluralize_citizen_label(result_type_labels[0], result_count) if len(result_type_labels) == 1 else "resultados"
    if not displayed_count:
        status = "EMPTY"
        summary = "No encontramos información disponible para responder esta pregunta con los datos incorporados actualmente."
    elif len(expedients) == 1:
        status = "ONE_EXPEDIENT"
        summary = "Encontramos una lectura ciudadana relacionada, disponible para abrir directamente."
    elif len(expedients) > 1:
        status = "MULTIPLE_RESULTS"
        summary = f"Encontramos {len(expedients)} lecturas ciudadanas relacionadas. Puedes abrir cada una directamente."
    else:
        status = "CONTEXT_ONLY"
        summary = "Encontramos información relacionada, pero todavía no una lectura ciudadana disponible para abrir directamente."
    scope_copy = (
        "La respuesta usa información actualmente incorporada de: " + " y ".join(source_scope) + "."
        if source_scope
        else "La respuesta usa información pública actualmente incorporada en DatosEnOrden."
    )
    count_copy = (
        f"Encontramos {result_count} {entity_label} relacionado{'' if result_count == 1 else 's'} con esta pregunta."
        if result_count
        else f"Encontramos {len(expedients)} expediente{'' if len(expedients) == 1 else 's'} disponible{'' if len(expedients) == 1 else 's'} para esta pregunta."
        if expedients
        else "No hay resultados disponibles en el corpus incorporado para esta pregunta."
    )
    return {
        "question_id": _public_text(question_id),
        "title": _public_text(title, "Recorrido guiado"),
        "description": _public_text(description),
        "query": cleaned_query,
        "status": status,
        "summary": summary,
        "scope_copy": scope_copy,
        "count_copy": count_copy,
        "entity_rows": entities,
        "expedient_rows": expedients,
        "result_count": result_count,
        "displayed_count": displayed_count,
        "result_limit": 12,
        "offset": 0,
        "next_cursor": "",
        "filters_available": [],
        "sort_options": ["relevancia"],
        "result_type_labels": result_type_labels,
    }


def build_guided_questions(payload: dict | None = None) -> list[dict]:
    guided = payload if payload is not None else get_guided_questions()
    return [
        {
            **dict(row),
            "concepts_text": " | ".join(str(item) for item in row.get("concepts", [])),
            "sources_text": " | ".join(str(item) for item in row.get("suggested_sources", [])),
            "path_text": "Este recorrido conectara: "
            + " -> ".join(str(item) for item in row.get("concepts", [])[:6]),
            "search_href": _search_href_value(str(row.get("search_query", row.get("example_query", "")))),
        }
        for row in guided.get("questions", [])
    ]


def build_guided_categories(payload: dict | None = None) -> list[dict]:
    guided = payload if payload is not None else get_guided_questions()
    return [
        {
            **dict(row),
            "examples_text": " | ".join(str(item) for item in row.get("examples", [])),
            "sources_text": " | ".join(str(item) for item in row.get("suggested_sources", [])),
            "path_text": "Fuentes sugeridas: "
            + " | ".join(str(item) for item in row.get("suggested_sources", [])),
            "search_href": _search_href_value(str(row.get("search_query", ""))),
        }
        for row in guided.get("categories", [])
    ]


def load_guided_options(category_id: str) -> list[dict]:
    return format_guided_options(get_guided_discovery_options(category_id))


def _search_href_value(query: str) -> str:
    from urllib.parse import quote_plus

    value = str(query or "").strip()
    return f"/search?q={quote_plus(value)}" if value else "/search"


def _investigation_href_value(target: str) -> str:
    from urllib.parse import quote_plus

    value = str(target or "").strip()
    return f"/investigation?id={quote_plus(value)}" if value else "/investigation"
