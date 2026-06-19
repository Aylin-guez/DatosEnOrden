from __future__ import annotations

from datosenorden.maintenance.entity_explorer import EntityListSummary
from datosenorden.maintenance.entity_explorer import EntityPurchaseOrderSummary
from datosenorden.maintenance.entity_explorer import list_buyers
from datosenorden.maintenance.entity_explorer import list_contracts
from datosenorden.maintenance.entity_explorer import list_entities
from datosenorden.maintenance.entity_explorer import list_suppliers
from datosenorden.maintenance.entity_explorer import render_buyers_list_text
from datosenorden.maintenance.entity_explorer import render_contracts_list_text
from datosenorden.maintenance.entity_explorer import render_entities_list_text
from datosenorden.maintenance.entity_explorer import render_suppliers_list_text


class _ScalarResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeSession:
    def __init__(self, rows):
        self.rows = rows
        self.sql = None

    def execute(self, statement):  # noqa: ANN001
        self.sql = str(statement.compile(compile_kwargs={"literal_binds": True}))
        return _ScalarResult(self.rows)


def test_list_buyers_returns_purchase_orders_sorted_query() -> None:
    session = _FakeSession(
        [
            ("11111111-1111-1111-1111-111111111111", "Direccion de Compras y Contratacion Publica", 5),
            ("22222222-2222-2222-2222-222222222222", "Municipalidad de Santiago", 2),
        ]
    )

    buyers = list_buyers(session)

    assert buyers == (
        EntityPurchaseOrderSummary(
            id="11111111-1111-1111-1111-111111111111",
            name="Direccion de Compras y Contratacion Publica",
            purchase_orders=5,
        ),
        EntityPurchaseOrderSummary(
            id="22222222-2222-2222-2222-222222222222",
            name="Municipalidad de Santiago",
            purchase_orders=2,
        ),
    )
    assert "PUBLIC_ORGANIZATION" in session.sql
    assert "ISSUES_PURCHASE_ORDER" in session.sql
    assert "ORDER BY" in session.sql
    assert "DESC" in session.sql


def test_list_suppliers_returns_purchase_orders_sorted_query() -> None:
    session = _FakeSession(
        [
            ("33333333-3333-3333-3333-333333333333", "SKY AIRLINE S.A.", 7),
            ("44444444-4444-4444-4444-444444444444", "Camara de Comercio de Santiago A.G.", 3),
        ]
    )

    suppliers = list_suppliers(session)

    assert suppliers == (
        EntityPurchaseOrderSummary(
            id="33333333-3333-3333-3333-333333333333",
            name="SKY AIRLINE S.A.",
            purchase_orders=7,
        ),
        EntityPurchaseOrderSummary(
            id="44444444-4444-4444-4444-444444444444",
            name="Camara de Comercio de Santiago A.G.",
            purchase_orders=3,
        ),
    )
    assert "COMPANY" in session.sql
    assert "RECEIVES_CONTRACT" in session.sql


def test_list_entities_applies_limit_and_orders_by_type_then_name() -> None:
    session = _FakeSession(
        [
            ("55555555-5555-5555-5555-555555555555", "CONTRACT", "Pasajes aereos", "contract-1"),
            ("66666666-6666-6666-6666-666666666666", "COMPANY", "SKY AIRLINE S.A.", "supplier-1"),
        ]
    )

    entities = list_entities(session, limit=50)

    assert entities == (
        EntityListSummary(
            id="55555555-5555-5555-5555-555555555555",
            entity_type="CONTRACT",
            name="Pasajes aereos",
            external_id="contract-1",
        ),
        EntityListSummary(
            id="66666666-6666-6666-6666-666666666666",
            entity_type="COMPANY",
            name="SKY AIRLINE S.A.",
            external_id="supplier-1",
        ),
    )
    assert "LIMIT 50" in session.sql


def test_list_contracts_filters_contract_entities() -> None:
    session = _FakeSession(
        [
            ("77777777-7777-7777-7777-777777777777", "CONTRACT", "Pasajes aereos", "contract-1"),
        ]
    )

    contracts = list_contracts(session)

    assert contracts == (
        EntityListSummary(
            id="77777777-7777-7777-7777-777777777777",
            entity_type="CONTRACT",
            name="Pasajes aereos",
            external_id="contract-1",
        ),
    )
    assert "CONTRACT" in session.sql


def test_render_buyers_list_text_formats_rows() -> None:
    report = render_buyers_list_text(
        (
            EntityPurchaseOrderSummary(
                id="11111111-1111-1111-1111-111111111111",
                name="Direccion de Compras y Contratacion Publica",
                purchase_orders=5,
            ),
        )
    )

    assert "buyer:" in report
    assert "id=11111111-1111-1111-1111-111111111111" in report
    assert "purchase_orders=5" in report


def test_render_suppliers_list_text_formats_rows() -> None:
    report = render_suppliers_list_text(
        (
            EntityPurchaseOrderSummary(
                id="22222222-2222-2222-2222-222222222222",
                name="SKY AIRLINE S.A.",
                purchase_orders=7,
            ),
        )
    )

    assert "supplier:" in report
    assert "name=SKY AIRLINE S.A." in report


def test_render_entities_list_text_formats_rows() -> None:
    report = render_entities_list_text(
        (
            EntityListSummary(
                id="33333333-3333-3333-3333-333333333333",
                entity_type="COMPANY",
                name="SKY AIRLINE S.A.",
                external_id="supplier-1",
            ),
        )
    )

    assert "entity:" in report
    assert "type=COMPANY" in report
    assert "external_id=supplier-1" in report


def test_render_contracts_list_text_formats_rows() -> None:
    report = render_contracts_list_text(
        (
            EntityListSummary(
                id="44444444-4444-4444-4444-444444444444",
                entity_type="CONTRACT",
                name="Pasajes aereos",
                external_id="contract-1",
            ),
        )
    )

    assert "contract:" in report
    assert "name=Pasajes aereos" in report
    assert "type=" not in report
