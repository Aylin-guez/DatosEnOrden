from __future__ import annotations

from datetime import date
from pathlib import Path
import sys
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from datosenorden.etl.chilecompra.client import ApiResponse
from datosenorden.etl.chilecompra.pipeline import ChileCompraPipeline
from datosenorden.etl.loaders.graph_loader import GraphLoader
from run_chilecompra_etl import main


def _purchase_order_response(code: str) -> ApiResponse:
    return ApiResponse(
        url="https://api.mercadopublico.cl/servicios/v1/publico/ordenesdecompra.json",
        params={"codigo": code},
        payload={
            "Version": "v1",
            "FechaCreacion": "2026-01-01T00:00:00",
            "Listado": [
                {
                    "Codigo": code,
                    "Nombre": "Compra de servicios",
                    "CodigoOrganismo": "6945",
                    "NombreOrganismo": "Direccion de Compras y Contratacion Publica",
                    "CodigoProveedor": "17793",
                    "NombreProveedor": "Camara de Comercio de Santiago A.G.",
                    "FechaEnvio": "2026-01-01T12:00:00",
                }
            ],
        },
    )


def test_purchase_order_code_command_persists_single_record(monkeypatch) -> None:
    client = MagicMock()
    client.get_purchase_order.return_value = _purchase_order_response("2097-241-SE14")
    session = MagicMock()
    captured: dict[str, object] = {}

    def fake_load(self, batch, dry_run=False):  # noqa: ANN001
        captured["batch"] = batch
        captured["dry_run"] = dry_run
        return None

    monkeypatch.setattr(GraphLoader, "load", fake_load)

    pipeline = ChileCompraPipeline(client=client, session=session)
    result = pipeline.run_purchase_order_by_code("2097-241-SE14")

    client.get_purchase_order.assert_called_once_with("2097-241-SE14")
    assert result.resource == "purchase_order"
    assert result.loaded is True
    assert result.source_record_count == 1
    assert result.claim_count == 2
    assert result.evidence_count == 2
    assert result.public_relationship_count == 2
    assert result.errors == ()

    batch = captured["batch"]
    assert batch.raw_count == 1
    assert len(batch.source_records) == 1
    assert len(batch.claims) == 2
    assert len(batch.evidence) == 2
    assert len(batch.public_relationships) == 2


def test_purchase_orders_limit_applies_before_mapping(monkeypatch) -> None:
    client = MagicMock()
    client.list_purchase_orders.return_value = ApiResponse(
        url="https://api.mercadopublico.cl/servicios/v1/publico/ordenesdecompra.json",
        params={"fecha": "01012026", "estado": "todos"},
        payload={
            "Version": "v1",
            "FechaCreacion": "2026-01-01T00:00:00",
            "Listado": [
                {
                    "Codigo": "2097-241-SE14",
                    "Nombre": "Compra de servicios",
                    "CodigoOrganismo": "6945",
                    "NombreOrganismo": "Direccion de Compras y Contratacion Publica",
                    "CodigoProveedor": "17793",
                    "NombreProveedor": "Camara de Comercio de Santiago A.G.",
                    "FechaEnvio": "2026-01-01T12:00:00",
                },
                {
                    "Codigo": "2097-242-SE14",
                    "Nombre": "Compra secundaria",
                    "CodigoOrganismo": "6945",
                    "NombreOrganismo": "Direccion de Compras y Contratacion Publica",
                    "CodigoProveedor": "17793",
                    "NombreProveedor": "Camara de Comercio de Santiago A.G.",
                    "FechaEnvio": "2026-01-01T12:30:00",
                },
            ],
        },
    )
    session = MagicMock()
    captured: dict[str, object] = {}

    def fake_load(self, batch, dry_run=False):  # noqa: ANN001
        captured["batch"] = batch
        captured["dry_run"] = dry_run
        return None

    monkeypatch.setattr(GraphLoader, "load", fake_load)

    pipeline = ChileCompraPipeline(client=client, session=session)
    result = pipeline.run_purchase_orders_for_day(date(2026, 1, 1), limit=1)

    client.list_purchase_orders.assert_called_once_with(day=date(2026, 1, 1), status="todos")
    assert result.raw_count == 1
    assert result.source_record_count == 1
    assert result.claim_count == 2
    assert result.evidence_count == 2
    assert result.public_relationship_count == 2

    batch = captured["batch"]
    assert batch.raw_count == 1
    assert len(batch.source_records) == 1


def test_main_reports_missing_ticket_without_secrets(monkeypatch, capsys) -> None:
    def raise_missing_ticket():
        raise ValueError("DATOSENORDEN_CHILECOMPRA_TICKET is required")

    monkeypatch.setattr("run_chilecompra_etl.get_chilecompra_settings", raise_missing_ticket)

    exit_code = main(["--purchase-order", "2097-241-SE14"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Falta DATOSENORDEN_CHILECOMPRA_TICKET" in captured.err
    assert "DATOSENORDEN_CHILECOMPRA_TICKET is required" in captured.err
