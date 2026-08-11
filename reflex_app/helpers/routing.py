from __future__ import annotations

from urllib.parse import parse_qs, quote_plus, urlparse

from reflex_app.helpers.public_values import _safe_public_values


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
