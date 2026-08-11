from __future__ import annotations

from datetime import date
from urllib.parse import quote_plus


def _format_chilean_date(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        parsed = date.fromisoformat(text[:10])
    except ValueError:
        return text
    return parsed.strftime("%d-%m-%Y")


def _official_document_fragment_href(fragment_id: str, page: int = 1) -> str:
    query_parts = []
    if fragment_id:
        query_parts.append(f"fragment_id={quote_plus(fragment_id)}")
    if page:
        query_parts.append(f"page={int(page)}")
    base = "/official-document" if not query_parts else "/official-document?" + "&".join(query_parts)
    return f"{base}#fragmento-{quote_plus(fragment_id)}" if fragment_id else base


def _pdf_page_value(value: object) -> int | None:
    try:
        page = int(value or 0)
    except (TypeError, ValueError):
        return None
    return page if page > 0 else None
