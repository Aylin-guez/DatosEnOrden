from __future__ import annotations

from datosenorden.web.app_services import get_guided_discovery_options, get_guided_questions, search_workspace


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
    if int(row.get("relationship_count", 0) or 0) or int(row.get("evidence_count", 0) or 0):
        labels.append("eventos")
    unique = list(dict.fromkeys(labels))
    return "Conexiones disponibles: " + " | ".join(unique) if unique else ""


def action_label_for_match(row: dict) -> str:
    if row.get("action_href"):
        return str(row.get("action_label", "Abrir"))
    if bool(row.get("is_record", False)):
        return "Ver informacion disponible"
    if int(row.get("relationship_count", 0) or 0) or int(row.get("evidence_count", 0) or 0):
        return "Abrir expediente actualizado"
    if "document" in str(row.get("entity_type", "")).lower() or "documento" in str(row.get("entity_type_label", "")).lower():
        return "Ver lectura desde fuentes disponibles"
    return "Ver informacion disponible"


def coverage_summary_for_match(row: dict) -> str:
    evidence = int(row.get("evidence_count", 0) or 0)
    relationships = int(row.get("relationship_count", 0) or 0)
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
    return [
        {
            **dict(row),
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
            "canonical_investigation_href": _investigation_href_value(str(row.get("canonical_entity_id", row.get("entity_id", "")))),
            "related_label": str(row.get("related_label", "")),
            "is_record": bool(row.get("is_record", False)),
            "state_graph_badges_text": state_graph_badges_for_match(row),
            "match_reason": str(row.get("why_it_appears", "")) or "Coincide con nombre, identificador o registros locales publicados.",
            "coverage_summary": coverage_summary_for_match(row),
            "source_contribution": (
                "Fuentes que contribuyen: " + " | ".join(str(item) for item in row.get("datasets", []))
                if row.get("datasets")
                else "Fuentes contribuyentes no publicadas para este resultado."
            ),
            "action_label": action_label_for_match(row),
        }
        for row in workspace.get("matches", [])
    ]


def run_workspace_search(query: str) -> list[dict]:
    return format_workspace_matches(search_workspace(query))


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
