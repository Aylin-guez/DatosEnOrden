from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import sys

from datosenorden.maintenance.entity_explorer import EntityListSummary
from datosenorden.maintenance.entity_explorer import EntityPurchaseOrderSummary

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import list_buyers
import list_contracts
import list_entities
import list_suppliers


def _session_manager(session):
    @contextmanager
    def _manager():
        yield session

    return _manager()


def test_list_buyers_script_prints_rows(monkeypatch, capsys) -> None:
    monkeypatch.setattr(list_buyers, "SessionLocal", lambda: _session_manager(object()))
    monkeypatch.setattr(
        list_buyers,
        "list_buyers",
        lambda session: (
            EntityPurchaseOrderSummary(
                id="11111111-1111-1111-1111-111111111111",
                name="Direccion de Compras y Contratacion Publica",
                purchase_orders=5,
            ),
        ),
    )

    exit_code = list_buyers.main([])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "buyer:" in captured.out
    assert "purchase_orders=5" in captured.out
    assert captured.err == ""


def test_list_suppliers_script_prints_rows(monkeypatch, capsys) -> None:
    monkeypatch.setattr(list_suppliers, "SessionLocal", lambda: _session_manager(object()))
    monkeypatch.setattr(
        list_suppliers,
        "list_suppliers",
        lambda session: (
            EntityPurchaseOrderSummary(
                id="22222222-2222-2222-2222-222222222222",
                name="SKY AIRLINE S.A.",
                purchase_orders=7,
            ),
        ),
    )

    exit_code = list_suppliers.main([])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "supplier:" in captured.out
    assert "name=SKY AIRLINE S.A." in captured.out
    assert captured.err == ""


def test_list_entities_script_uses_limit(monkeypatch, capsys) -> None:
    called = {}

    def _list_entities(session, limit):  # noqa: ANN001
        called["limit"] = limit
        return (
            EntityListSummary(
                id="33333333-3333-3333-3333-333333333333",
                entity_type="CONTRACT",
                name="Pasajes aereos",
                external_id="contract-1",
            ),
        )

    monkeypatch.setattr(list_entities, "SessionLocal", lambda: _session_manager(object()))
    monkeypatch.setattr(list_entities, "list_entities", _list_entities)

    exit_code = list_entities.main(["--limit", "50"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert called["limit"] == 50
    assert "entity:" in captured.out
    assert "type=CONTRACT" in captured.out
    assert captured.err == ""


def test_list_contracts_script_prints_rows(monkeypatch, capsys) -> None:
    monkeypatch.setattr(list_contracts, "SessionLocal", lambda: _session_manager(object()))
    monkeypatch.setattr(
        list_contracts,
        "list_contracts",
        lambda session: (
            EntityListSummary(
                id="44444444-4444-4444-4444-444444444444",
                entity_type="CONTRACT",
                name="Pasajes aereos",
                external_id="contract-1",
            ),
        ),
    )

    exit_code = list_contracts.main([])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "contract:" in captured.out
    assert "external_id=contract-1" in captured.out
    assert captured.err == ""
