"""REAL-or-generic guidance for the public Explore surface."""
from __future__ import annotations

from sqlalchemy.orm import Session

from datosenorden.application.public_collections import public_collection
from datosenorden.application.search.service import build_guided_categories, build_guided_questions


_QUESTION_COLLECTIONS = {
    "who_sells_to_this_body": "organisms",
    "which_suppliers_appear": "companies",
    "which_related_companies_exist": "companies",
}
_CATEGORY_COLLECTIONS = {
    "public_organizations": "organisms",
    "suppliers": "companies",
    "procurement": "contracts",
}


def public_guided_questions(session: Session) -> list[dict]:
    rows = []
    for row in build_guided_questions():
        item = dict(row)
        if item.get("interaction_type") == "CONTEXTUAL":
            continue
        example = _first_title(session, _QUESTION_COLLECTIONS.get(str(item.get("id", ""))))
        if example:
            item["example_query"] = example
            item["search_query"] = example
            item["example_authority"] = "REAL"
        else:
            item["example_query"] = _generic_example(item.get("id", ""))
            item["search_query"] = _generic_query(item.get("id", ""))
            item["example_authority"] = "GENERIC"
        rows.append(item)
    return rows


def public_guided_categories(session: Session) -> list[dict]:
    rows = []
    for row in build_guided_categories():
        item = dict(row)
        collection_key = _CATEGORY_COLLECTIONS.get(str(item.get("id", "")))
        examples = _titles(session, collection_key)
        if examples:
            item["examples"] = examples
            item["search_query"] = examples[0]
            item["example_authority"] = "REAL"
        else:
            item["examples"] = [_generic_example(item.get("id", ""))]
            item["search_query"] = _generic_query(item.get("id", ""))
            item["example_authority"] = "GENERIC"
        item["examples_text"] = " | ".join(item["examples"])
        item["search_href"] = _search_href_value(str(item["search_query"]))
        rows.append(item)
    return rows


def _titles(session: Session, key: str | None) -> list[str]:
    if not key:
        return []
    return [str(item["title"]) for item in public_collection(session, key).get("items", [])[:3]]


def _first_title(session: Session, key: str | None) -> str:
    titles = _titles(session, key)
    return titles[0] if titles else ""


def _generic_example(identifier: object) -> str:
    labels = {
        "which_authorities_appear": "Ejemplo: autoridad",
        "which_official_publications_exist": "Ejemplo: publicación oficial",
        "which_meetings_were_recorded": "Ejemplo: reunión registrada",
        "authorities": "Ejemplo: autoridad",
        "budgets": "Ejemplo: presupuesto público",
        "meetings": "Ejemplo: reunión registrada",
        "public_offices": "Ejemplo: cargo público",
    }
    return labels.get(str(identifier), "Ejemplo: información pública")


def _generic_query(identifier: object) -> str:
    labels = {
        "which_authorities_appear": "autoridad",
        "which_official_publications_exist": "publicación oficial",
        "which_meetings_were_recorded": "reunión",
        "authorities": "autoridad",
        "budgets": "presupuesto",
        "meetings": "reunión",
        "public_offices": "cargo público",
    }
    return labels.get(str(identifier), "información pública")


def _search_href_value(query: str) -> str:
    from urllib.parse import quote_plus

    return f"/search?q={quote_plus(query)}" if query else "/search"
