from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import quote_plus


PDF_LOCATION_APPROXIMATE_NOTICE = "Ubicación aproximada por fragmento; el documento original no entregó coordenadas."


def field(obj: object, name: str, fallback: object = None) -> object:
    if isinstance(obj, dict):
        return obj.get(name, fallback)
    return getattr(obj, name, fallback)


def json_dict(value: object) -> dict:
    return dict(value) if isinstance(value, dict) else {}


def json_list(value: object) -> list:
    return list(value) if isinstance(value, list) else []


def clean(value: object, fallback: str = "") -> str:
    text = str(value or "").strip()
    return text or fallback


def pdf_page_value(value: object) -> int | None:
    try:
        page = int(value or 0)
    except (TypeError, ValueError):
        return None
    return page if page > 0 else None


def official_document_fragment_href(fragment_id: str, page: int = 1) -> str:
    query_parts = []
    if fragment_id:
        query_parts.append(f"fragment_id={quote_plus(fragment_id)}")
    if page:
        query_parts.append(f"page={int(page)}")
    base = "/official-document" if not query_parts else "/official-document?" + "&".join(query_parts)
    return f"{base}#fragmento-{quote_plus(fragment_id)}" if fragment_id else base


def processed_fragment_order(row: dict, fallback: int) -> int:
    raw_order = field(row, "order", fallback)
    try:
        return int(raw_order or fallback)
    except (TypeError, ValueError):
        return fallback


def document_blocks(text: str) -> list[str]:
    normalized = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    blocks = [block.strip() for block in normalized.split("\n\n")]
    return [block for block in blocks if block]


def looks_like_document_heading(text: str) -> bool:
    clean_text = str(text or "").strip()
    if not clean_text or len(clean_text) > 140:
        return False
    return clean_text.isupper() or clean_text.startswith(("MENSAJE", "PROYECTO DE LEY", "ANTECEDENTES", "I.", "II.", "III."))


def load_document_view_blocks(path: Path) -> list[dict]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return []
    blocks = []
    for index, row in enumerate(json_list(field(payload, "blocks", [])), start=1):
        text = clean(field(row, "text"), "")
        if not text:
            continue
        fragment_id = clean(field(row, "source_fragment_id", field(row, "fragment_id", f"document-view-{index}")), f"document-view-{index}")
        blocks.append(
            {
                "id": clean(field(row, "id"), f"{fragment_id}-p{index}"),
                "fragment_id": fragment_id,
                "marker": clean(field(row, "marker"), ""),
                "text": text,
                "is_heading": bool(field(row, "is_heading", False)),
            }
        )
    return blocks


def load_document_fragments_from_file(path: Path) -> list[dict]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return []
    return json_list(field(payload, "fragments", []))


def load_document_fragments_with_source(
    *,
    fallback_fragments: list[dict],
    published_view_path: Path,
    published_reading_path: Path,
    processing_fragments_path: Path,
) -> tuple[list[dict], str, bool]:
    view_blocks = load_document_view_blocks(published_view_path)
    if view_blocks:
        return view_blocks, str(published_view_path), False
    for path, is_fallback in (
        (published_reading_path, False),
        (processing_fragments_path, True),
    ):
        fragments = load_document_fragments_from_file(path)
        if fragments:
            return fragments, str(path), is_fallback
    if fallback_fragments:
        return fallback_fragments, "knowledge_demo_payload", True
    return [], "", False


def document_paragraphs_from_fragments(fragments: list[dict]) -> list[dict]:
    sorted_fragments = sorted(json_list(fragments), key=lambda row: processed_fragment_order(row, 9999))
    paragraphs: list[dict] = []
    for fragment_index, fragment in enumerate(sorted_fragments, start=1):
        fragment_id = clean(field(fragment, "fragment_id", field(fragment, "id", f"fragment-{fragment_index}")), f"fragment-{fragment_index}")
        text = clean(field(fragment, "text"), "")
        for paragraph_index, paragraph in enumerate(document_blocks(text), start=1):
            paragraphs.append(
                {
                    "id": f"{fragment_id}-p{paragraph_index}",
                    "fragment_id": fragment_id,
                    "marker": f"Fragmento {fragment_index:02d}" if paragraph_index == 1 else "",
                    "text": paragraph,
                    "is_heading": looks_like_document_heading(paragraph),
                }
            )
    return paragraphs


def document_pdf_href(href: str, page: int = 1) -> str:
    safe_page = max(int(page or 1), 1)
    return f"{href}#page={safe_page}"


def fragment_order_page(contexts: list[dict], fragment_id: str) -> int:
    selected = str(fragment_id or "")
    for index, row in enumerate(json_list(contexts), start=1):
        if str(row.get("fragment_id", "")) == selected:
            return max(processed_fragment_order(row, index), 1)
    return 1


def pdf_highlight_target(fragment_id: str, page: int, text_snippet: str) -> dict:
    return {
        "fragment_id": str(fragment_id or ""),
        "page": max(int(page or 1), 1),
        "text_snippet": str(text_snippet or ""),
        "coordinates": None,
    }


def selected_fragment_payload(
    *,
    contexts: list[dict],
    fragment_id: str,
    requested_page: int | None,
    has_pdf: bool,
    pdf_public_href: str,
) -> dict:
    selected = str(fragment_id or "")
    context = next((row for row in json_list(contexts) if str(row.get("fragment_id", "")) == selected), {})
    if not context:
        context = contexts[0] if contexts else {}
    selected_fragment_id = str(context.get("fragment_id", selected))
    context_page = pdf_page_value(context.get("page"))
    page_is_approximate = context_page is None and requested_page is None
    selected_page = context_page or requested_page or fragment_order_page(contexts, selected_fragment_id)
    selected_excerpt = str(context.get("excerpt", ""))
    return {
        "knowledge_selected_fragment_id": selected_fragment_id,
        "knowledge_selected_page_is_approximate": page_is_approximate,
        "knowledge_selected_page": selected_page,
        "knowledge_pdf_location_notice": PDF_LOCATION_APPROXIMATE_NOTICE if page_is_approximate else "",
        "knowledge_selected_reference_label": str(context.get("reference_label", "")) or f"Pagina {selected_page}",
        "knowledge_selected_excerpt": selected_excerpt,
        "knowledge_selected_summary": json_list(context.get("summary", [])),
        "knowledge_selected_questions": json_list(context.get("questions", [])),
        "knowledge_selected_claims": json_list(context.get("claims", [])),
        "knowledge_selected_evidence": json_list(context.get("evidence", [])),
        "knowledge_selected_connections": json_list(context.get("connections", [])),
        "knowledge_pdf_highlight_target": pdf_highlight_target(selected_fragment_id, selected_page, selected_excerpt),
        "knowledge_document_pdf_page_href": document_pdf_href(pdf_public_href, selected_page) if has_pdf else "",
    }


def document_share_links(*, fragment_id: str, page: int, reference_label: str, public_url: str) -> dict:
    share_path = official_document_fragment_href(fragment_id, page)
    share_title = f"{reference_label} - DatosEnOrden"
    encoded_url = quote_plus(public_url)
    encoded_title = quote_plus(share_title)
    return {
        "knowledge_share_path": share_path,
        "knowledge_share_url": public_url,
        "knowledge_share_title": share_title,
        "knowledge_share_x_url": f"https://twitter.com/intent/tweet?url={encoded_url}&text={encoded_title}",
        "knowledge_share_whatsapp_url": f"https://wa.me/?text={quote_plus(share_title + ' ' + public_url)}",
        "knowledge_share_linkedin_url": f"https://www.linkedin.com/sharing/share-offsite/?url={encoded_url}",
        "knowledge_share_copy_script": f"navigator.clipboard.writeText({json.dumps(public_url)})",
    }
