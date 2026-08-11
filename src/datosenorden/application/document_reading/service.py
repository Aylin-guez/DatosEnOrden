from __future__ import annotations

from datetime import date
from pathlib import Path

from datosenorden.application.document_reading.context import (
    document_pdf_href,
    document_share_links,
    field,
    json_dict,
    json_list,
    load_document_fragments_with_source,
    document_paragraphs_from_fragments,
    official_document_fragment_href,
    pdf_page_value,
    selected_fragment_payload,
)
from datosenorden.web.app_services import get_knowledge_demo, get_knowledge_documents
from datosenorden.application.public_deployment.sanitization import public_asset_reference


DEMO_INVESTIGATION_TARGET = "Municipalidad de Providencia"
TOPIC_BUDGET_2013_TITLE = "Ley de Presupuestos del Sector Público 2013"
TOPIC_BUDGET_2013_TARGET = "cl-congreso-boletin-8575-05"


def format_chilean_date(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        parsed = date.fromisoformat(text[:10])
    except ValueError:
        return text
    return parsed.strftime("%d-%m-%Y")


def build_knowledge_payload(
    *,
    requested_fragment_id: str,
    requested_page: int | None,
    published_view_path: Path,
    published_reading_path: Path,
    processing_fragments_path: Path,
    pdf_asset_exists: bool,
    pdf_path: Path,
    pdf_public_href: str,
    public_url,
) -> dict:
    documents = json_list(get_knowledge_documents())
    demo = json_dict(get_knowledge_demo())
    document = json_dict(demo.get("document", {}))
    fragments = json_list(demo.get("fragments", []))
    document_fragments, document_source_path, document_source_is_fallback = load_document_fragments_with_source(
        fallback_fragments=fragments,
        published_view_path=published_view_path,
        published_reading_path=published_reading_path,
        processing_fragments_path=processing_fragments_path,
    )
    contexts = json_list(demo.get("fragment_contexts", []))
    selected_context = json_dict(demo.get("selected_context", {}))
    if requested_fragment_id:
        selected_context = next(
            (
                row
                for row in contexts
                if str(row.get("fragment_id", "")) == requested_fragment_id
            ),
            selected_context,
        )
    selected_fragment_id = str(selected_context.get("fragment_id", demo.get("default_fragment_id", "")))
    selected = selected_fragment_payload(
        contexts=contexts,
        fragment_id=selected_fragment_id,
        requested_page=requested_page or pdf_page_value(selected_context.get("page")),
        has_pdf=pdf_asset_exists,
        pdf_public_href=pdf_public_href,
    )
    metrics = {str(row.get("id", "")): int(row.get("value", 0) or 0) for row in json_list(demo.get("metrics", []))}
    coverage = json_dict(demo.get("document_coverage", {}))
    fragment_count = metrics.get("fragments", 0)
    total_fragment_count = int(coverage.get("total_fragments", len(fragments)) or len(fragments))
    reference_count = metrics.get("references", 0)
    payload = {
        "knowledge_documents": documents,
        "knowledge_document": document,
        "knowledge_title": str(field(document, "title", "")),
        "knowledge_summary": str(field(demo, "citizen_summary", "")),
        "knowledge_key_points": json_list(demo.get("key_points", [])),
        "knowledge_questions": json_list(demo.get("citizen_questions", demo.get("questions", []))),
        "knowledge_claims": json_list(demo.get("claims", [])),
        "knowledge_evidence": json_list(demo.get("references", demo.get("evidence", []))),
        "knowledge_pages": json_list(demo.get("pages", [])),
        "knowledge_fragments": fragments,
        "knowledge_document_paragraphs": document_paragraphs_from_fragments(document_fragments),
        "knowledge_document_source_reference": "Documento publicado" if not document_source_is_fallback else "Lectura publicada de respaldo",
        "knowledge_document_source_is_fallback": document_source_is_fallback,
        "knowledge_document_has_pdf": pdf_asset_exists,
        "knowledge_document_pdf_reference": public_asset_reference(pdf_public_href) if pdf_asset_exists else "",
        "knowledge_document_pdf_href": document_pdf_href(pdf_public_href, 1) if pdf_asset_exists else "",
        "knowledge_citations": json_list(demo.get("citations", [])),
        "knowledge_connections": [
            {"label": str(key), "value": str(value)}
            for key, value in json_dict(demo.get("connections", {})).items()
        ],
        "knowledge_notice": str(field(demo, "notice", "")),
        "knowledge_expediente_target": str(field(demo, "related_expediente", field(document, "related_expediente_target", DEMO_INVESTIGATION_TARGET))),
        "knowledge_fragment_contexts": contexts,
        "knowledge_fragment_count": fragment_count,
        "knowledge_total_fragment_count": total_fragment_count,
        "knowledge_question_count": metrics.get("questions", 0),
        "knowledge_claim_count": metrics.get("claims", 0),
        "knowledge_reference_count": reference_count,
        "knowledge_coverage_text": str(coverage.get("label", "")) or f"Fragmentos utilizados: {fragment_count} de {total_fragment_count}",
        "knowledge_reference_text": str(coverage.get("references_label", "")) or f"Referencias: {reference_count}",
        "knowledge_error": "",
    }
    payload.update(selected)
    payload.update(_share_payload(payload, public_url))
    return payload


def knowledge_error_payload(error: str) -> dict:
    return {
        "knowledge_documents": [],
        "knowledge_document": {},
        "knowledge_title": "",
        "knowledge_summary": "",
        "knowledge_key_points": [],
        "knowledge_questions": [],
        "knowledge_claims": [],
        "knowledge_evidence": [],
        "knowledge_pages": [],
        "knowledge_fragments": [],
        "knowledge_document_paragraphs": [],
        "knowledge_document_source_reference": "",
        "knowledge_document_source_is_fallback": False,
        "knowledge_document_has_pdf": False,
        "knowledge_document_pdf_reference": "",
        "knowledge_document_pdf_href": "",
        "knowledge_document_pdf_page_href": "",
        "knowledge_citations": [],
        "knowledge_connections": [],
        "knowledge_notice": "",
        "knowledge_expediente_target": DEMO_INVESTIGATION_TARGET,
        "knowledge_selected_page": 18,
        "knowledge_selected_fragment_id": "",
        "knowledge_selected_reference_label": "Pagina 18",
        "knowledge_selected_excerpt": "",
        "knowledge_selected_summary": [],
        "knowledge_selected_questions": [],
        "knowledge_selected_claims": [],
        "knowledge_selected_evidence": [],
        "knowledge_selected_connections": [],
        "knowledge_pdf_highlight_target": {},
        "knowledge_selected_page_is_approximate": False,
        "knowledge_pdf_location_notice": "",
        "knowledge_fragment_contexts": [],
        "knowledge_fragment_count": 0,
        "knowledge_total_fragment_count": 0,
        "knowledge_question_count": 0,
        "knowledge_claim_count": 0,
        "knowledge_reference_count": 0,
        "knowledge_coverage_text": "",
        "knowledge_reference_text": "",
        "knowledge_share_path": "",
        "knowledge_share_url": "",
        "knowledge_share_title": "",
        "knowledge_share_x_url": "",
        "knowledge_share_whatsapp_url": "",
        "knowledge_share_linkedin_url": "",
        "knowledge_share_copy_script": "",
        "knowledge_error": error,
    }


def select_document_payload(
    *,
    contexts: list[dict],
    fragment_id: str,
    requested_page: int | None,
    has_pdf: bool,
    pdf_public_href: str,
    public_url,
) -> dict:
    selected = str(fragment_id or "")
    if not selected and requested_page is not None:
        page_context = next((row for row in contexts if pdf_page_value(row.get("page")) == requested_page), {})
        selected = str(page_context.get("fragment_id", ""))
    payload = selected_fragment_payload(
        contexts=contexts,
        fragment_id=selected,
        requested_page=requested_page,
        has_pdf=has_pdf,
        pdf_public_href=pdf_public_href,
    )
    payload.update(_share_payload(payload, public_url))
    return payload


def build_topic_payload(*, knowledge: dict, investigation: dict, graph: dict) -> dict:
    document = json_dict(knowledge.get("knowledge_document", {}))
    legislative = json_dict(investigation.get("legislative", {}))
    compact_metrics = json_dict(investigation.get("compact_metrics", {}))
    source_records = json_list(legislative.get("source_records", []))
    organizations = topic_organizations(document, source_records, investigation)
    timeline_rows = json_list(investigation.get("timeline", []))
    title = TOPIC_BUDGET_2013_TITLE
    topic_timeline = topic_timeline_rows(timeline_rows)
    vote_count = int(legislative.get("votes_found", 0) or 0)
    document_count = 1 if document else 0
    evidence_count = int(compact_metrics.get("evidence_count", 0) or 0)
    return {
        "topic_title": title,
        "topic_status": str(document.get("official_status", "")) or str(investigation.get("official_status", "")),
        "topic_read_time": topic_read_time(json_list(knowledge.get("knowledge_fragments", []))),
        "topic_document_count": document_count,
        "topic_updated_at": format_chilean_date(document.get("published_at", "")) or topic_latest_record_date(source_records),
        "topic_organizations_text": " | ".join(organizations),
        "topic_official_document": {
            "title": str(document.get("title", title)),
            "source": str(document.get("source", "")),
            "document_type": str(document.get("document_type", "")),
            "published_at": format_chilean_date(document.get("published_at", "")),
            "summary": str(knowledge.get("knowledge_summary", "")),
            "official_url": str(document.get("official_url", "")),
        },
        "topic_proposes_rows": json_list(knowledge.get("knowledge_key_points", []))[:3],
        "topic_changes_rows": topic_change_rows(json_list(knowledge.get("knowledge_claims", []))),
        "topic_no_changes_rows": topic_no_change_rows(json_list(knowledge.get("knowledge_claims", [])), str(knowledge.get("knowledge_notice", ""))),
        "topic_timeline_rows": topic_timeline,
        "topic_evidence_rows": topic_evidence_rows(json_list(knowledge.get("knowledge_evidence", []))),
        "topic_state_graph_rows": format_state_graph_topic_rows(graph),
        "topic_reading_rows": [
            {
                "title": str(knowledge.get("knowledge_title", "")) or title,
                "summary": str(knowledge.get("knowledge_summary", "")),
                "href": "/official-document",
                "coverage": str(knowledge.get("knowledge_coverage_text", "")),
            }
        ],
        "topic_expediente_title": str(field(investigation.get("entity", {}), "name", "Boletin 8575-05")),
        "topic_expediente_summary": str(investigation.get("narrative_summary", investigation.get("summary", ""))),
        "topic_expediente_metrics": (
            f"Evidencia: {evidence_count} | "
            f"Relaciones: {int(compact_metrics.get('relationship_count', 0) or 0)}"
        ),
        "topic_tracking_summary": topic_tracking_summary(topic_timeline, investigation),
        "topic_vote_summary": (
            topic_vote_summary(vote_count, topic_timeline, str(legislative.get("source", "Datos Abiertos Legislativos")))
            if vote_count
            else "La vista de expediente no expone votaciones para este tema."
        ),
        "topic_vote_count": vote_count,
        "topic_status_rows": topic_status_rows(
            document_available=bool(document),
            expediente_available=bool(investigation.get("found", False)),
            votes_available=vote_count > 0,
            text_processed=bool(knowledge.get("knowledge_fragments", [])),
        ),
        "topic_hero_answer_rows": topic_hero_answer_rows(
            title=title,
            document_count=document_count,
            vote_count=vote_count,
            evidence_count=evidence_count,
        ),
        "topic_original_url": str(document.get("official_url", "")),
    }


def topic_read_time(fragments: list[dict]) -> str:
    words = sum(len(str(field(row, "text", "")).split()) for row in fragments)
    minutes = max(1, round(words / 220)) if words else 1
    return f"{minutes} min"


def topic_latest_record_date(source_records: list[dict]) -> str:
    dates = sorted(str(field(row, "retrieved_at", ""))[:10] for row in source_records if str(field(row, "retrieved_at", "")))
    return format_chilean_date(dates[-1]) if dates else ""


def topic_organizations(document: dict, source_records: list[dict], investigation: dict) -> list[str]:
    values = [str(field(document, "source", "")), str(field(investigation, "official_source", ""))]
    values.extend(str(field(row, "source", "")) for row in source_records[:3])
    seen: list[str] = []
    for value in values:
        cleaned = value.strip()
        if cleaned and cleaned not in seen:
            seen.append(cleaned)
    return seen


def topic_no_change_rows(claims: list[dict], notice: str) -> list[dict]:
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
            "fragment_id": str(field(claims[0], "fragment_id", "")) if claims else "",
            "page": int(field(claims[0], "page", 1) or 1) if claims else 1,
            "reference_label": str(field(claims[0], "reference_label", "Lectura documentada")) if claims else "Lectura documentada",
        }
    )
    return rows


def topic_change_rows(claims: list[dict]) -> list[dict]:
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
            "claim": str(field(row, "claim", "")) or "Afirmacion documentada sin texto disponible.",
            "review_note": str(field(row, "review_note", "")) or "Revisar el fragmento citado antes de interpretar efectos.",
        }
        for row in claims[:3]
    ]


def topic_evidence_rows(rows: list[dict]) -> list[dict]:
    return [
        {
            **dict(row),
            "href": official_document_fragment_href(
                str(field(row, "fragment_id", "")),
                int(field(row, "page", 1) or 1),
            ),
        }
        for row in rows[:6]
    ]


def topic_timeline_rows(rows: list[dict]) -> list[dict]:
    grouped: dict[tuple[str, str, str], dict] = {}
    for row in rows:
        event_date = str(field(row, "event_date", ""))
        title = str(field(row, "title", ""))
        source = str(field(row, "dataset_name", field(row, "dataset", "")))
        key = (event_date, title, source)
        if key not in grouped:
            grouped[key] = {
                "date": format_chilean_date(event_date),
                "sort_date": event_date,
                "status": str(field(row, "dataset", "")),
                "title": title,
                "description": str(field(row, "explanation", "")),
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


def topic_vote_summary(vote_count: int, timeline_rows: list[dict], source: str) -> str:
    grouped_count = len(timeline_rows)
    if grouped_count:
        return f"{vote_count} votaciones registradas en {source}, agrupadas en {grouped_count} hitos visibles."
    return f"{vote_count} votaciones registradas en {source}."


def topic_status_rows(*, document_available: bool, expediente_available: bool, votes_available: bool, text_processed: bool) -> list[dict]:
    return [
        {"label": "Documento fuente disponible", "status": "Disponible" if document_available else "No disponible", "ready": document_available},
        {"label": "Expediente disponible", "status": "Disponible" if expediente_available else "No disponible", "ready": expediente_available},
        {"label": "Votaciones disponibles", "status": "Disponible" if votes_available else "No disponible", "ready": votes_available},
        {"label": "Texto completo procesado", "status": "Disponible" if text_processed else "No disponible", "ready": text_processed},
    ]


def topic_hero_answer_rows(title: str, document_count: int, vote_count: int, evidence_count: int) -> list[dict]:
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


def topic_tracking_summary(rows: list[dict], investigation: dict) -> str:
    if rows:
        first = rows[0]
        return f"Primer hito visible: {first.get('date', '')} - {first.get('title', '')}"
    return str(investigation.get("summary", ""))


def format_state_graph_topic_rows(graph: object, *, limit: int = 6) -> list[dict]:
    payload = json_dict(graph)
    rows = []
    for node in json_list(payload.get("nodes", [])):
        node_type = _state_graph_display_type(field(node, "node_type", ""))
        if node_type in {"fuente", "cargo"}:
            continue
        rows.append(
            {
                "title": str(field(node, "label", "Nodo relacionado")),
                "node_type": node_type,
                "sources_text": " | ".join(str(item) for item in json_list(field(node, "sources", []))) or "fuente local",
                "evidence_text": _state_graph_evidence_text(field(node, "evidence", [])),
            }
        )
    return rows[:limit]


def _state_graph_display_type(value: object) -> str:
    labels = {
        "PUBLIC_ORGANIZATION": "organismo",
        "MUNICIPALITY": "municipio",
        "PERSON": "persona",
        "ROLE": "cargo",
        "COMPANY": "empresa",
        "SUPPLIER": "proveedor",
        "CONTRACT": "contrato",
        "TENDER": "licitacion",
        "LOBBY_MEETING": "reunion",
        "DOCUMENT": "documento",
        "PUBLICATION": "publicacion",
        "SOURCE": "fuente",
    }
    return labels.get(str(value or "").upper(), str(value or "").lower() or "nodo")


def _state_graph_evidence_text(evidence: object) -> str:
    rows = json_list(evidence)
    if not rows:
        return "Sin evidencia visible"
    return " | ".join(str(field(row, "source", field(row, "dataset", "evidencia"))) for row in rows[:3])


def _share_payload(payload: dict, public_url) -> dict:
    share_path = official_document_fragment_href(
        str(payload.get("knowledge_selected_fragment_id", "")),
        int(payload.get("knowledge_selected_page", 1) or 1),
    )
    return document_share_links(
        fragment_id=str(payload.get("knowledge_selected_fragment_id", "")),
        page=int(payload.get("knowledge_selected_page", 1) or 1),
        reference_label=str(payload.get("knowledge_selected_reference_label", "")),
        public_url=public_url(share_path),
    )
