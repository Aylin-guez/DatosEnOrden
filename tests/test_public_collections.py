from __future__ import annotations

from types import SimpleNamespace

from datosenorden.application.public_collections import public_collection, public_collection_counts


def test_collection_projection_is_read_only_and_deduplicates_contract_entities() -> None:
    rows = [
        SimpleNamespace(entity_type="CONTRACT", name="Orden humana", external_id="chilecompra:purchase_order:1", id="one"),
        SimpleNamespace(entity_type="CONTRACT", name="Segunda orden humana", external_id="chilecompra:purchase_order:2", id="two"),
    ]
    class Session:
        def scalars(self, _query):
            return SimpleNamespace(all=lambda: rows)
    view = public_collection(Session(), "contracts")
    assert len(view["items"]) == 2
    assert all(item["classification"] == "REAL" for item in view["items"])
    assert {item["title"] for item in view["items"]} == {"Orden humana", "Segunda orden humana"}


def test_collection_counts_use_the_same_read_only_definitions() -> None:
    rows = [SimpleNamespace(id="one"), SimpleNamespace(id="two")]

    class Session:
        def scalars(self, _query):
            return SimpleNamespace(all=lambda: rows)

    assert public_collection_counts(Session()) == {
        "organisms": 2,
        "companies": 2,
        "contracts": 2,
    }


def test_unknown_collection_is_empty_without_creating_data() -> None:
    assert public_collection(SimpleNamespace(), "people") == {"found": False, "items": []}
