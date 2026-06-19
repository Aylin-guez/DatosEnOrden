from __future__ import annotations

from datetime import date
from pathlib import Path
import sys
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from datosenorden.etl.chilecompra.client import ApiResponse
from datosenorden.etl.chilecompra.debug import summarize_normalized_record, summarize_payload_shape
from datosenorden.etl.chilecompra.normalizers import ChileCompraNormalizer
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
                    "FechaEnvio": "2026-01-01T12:00:00",
                    "Comprador": {
                        "CodigoOrganismo": "6945",
                        "NombreOrganismo": "Direccion de Compras y Contratacion Publica",
                    },
                    "Proveedor": {
                        "CodigoProveedor": "17793",
                        "NombreProveedor": "Camara de Comercio de Santiago A.G.",
                    },
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
                },
                {
                    "Codigo": "2097-242-SE14",
                    "Nombre": "Compra secundaria",
                },
            ],
        },
    )
    client.get_purchase_order.return_value = _purchase_order_response("2097-241-SE14")
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
    client.get_purchase_order.assert_called_once_with("2097-241-SE14")
    assert result.raw_count == 1
    assert result.source_record_count == 1
    assert result.claim_count == 2
    assert result.evidence_count == 2
    assert result.public_relationship_count == 2

    batch = captured["batch"]
    assert batch.raw_count == 1
    assert len(batch.source_records) == 1


def test_batch_purchase_orders_hydrate_details_before_mapping(monkeypatch) -> None:
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
                    "Nombre": "Resumen sin identidad comprador/proveedor",
                }
            ],
        },
    )
    client.get_purchase_order.return_value = _purchase_order_response("2097-241-SE14")
    session = MagicMock()
    captured: dict[str, object] = {}

    def fake_load(self, batch, dry_run=False):  # noqa: ANN001
        captured["batch"] = batch
        captured["dry_run"] = dry_run
        return None

    monkeypatch.setattr(GraphLoader, "load", fake_load)

    pipeline = ChileCompraPipeline(client=client, session=session)
    result = pipeline.run_purchase_orders_for_day(date(2026, 1, 1), limit=10)

    client.list_purchase_orders.assert_called_once_with(day=date(2026, 1, 1), status="todos")
    client.get_purchase_order.assert_called_once_with("2097-241-SE14")
    assert result.source_record_count == 1
    assert result.rejected_count == 0
    assert result.claim_count == 2
    assert result.public_relationship_count == 2

    batch = captured["batch"]
    assert batch.source_records[0].raw_payload["Comprador"]["CodigoOrganismo"] == "6945"
    assert {claim.predicate for claim in batch.claims} == {
        "ISSUES_PURCHASE_ORDER",
        "RECEIVES_CONTRACT",
    }


def test_batch_purchase_order_detail_failure_is_rejected_with_error_log(monkeypatch) -> None:
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
                    "Nombre": "Resumen sin identidad comprador/proveedor",
                }
            ],
        },
    )
    client.get_purchase_order.side_effect = RuntimeError("temporary API failure")
    session = MagicMock()
    captured: dict[str, object] = {}

    def fake_load(self, batch, dry_run=False):  # noqa: ANN001
        captured["batch"] = batch
        captured["dry_run"] = dry_run
        return None

    monkeypatch.setattr(GraphLoader, "load", fake_load)

    pipeline = ChileCompraPipeline(client=client, session=session)
    result = pipeline.run_purchase_orders_for_day(date(2026, 1, 1), limit=10)

    assert result.source_record_count == 1
    assert result.rejected_count == 1
    assert result.claim_count == 0
    assert result.public_relationship_count == 0
    assert "detail fetch failed" in result.errors[0]

    batch = captured["batch"]
    assert batch.source_records[0].status.value == "rejected"
    assert batch.source_records[0].error_log is not None
    assert "temporary API failure" in batch.source_records[0].error_log
    assert "_datosenorden_error_log" not in batch.source_records[0].raw_payload


def test_main_reports_missing_ticket_without_secrets(monkeypatch, capsys) -> None:
    def raise_missing_ticket():
        raise ValueError("DATOSENORDEN_CHILECOMPRA_TICKET is required")

    monkeypatch.setattr("run_chilecompra_etl.get_chilecompra_settings", raise_missing_ticket)

    exit_code = main(["--purchase-order", "2097-241-SE14"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Falta DATOSENORDEN_CHILECOMPRA_TICKET" in captured.err
    assert "DATOSENORDEN_CHILECOMPRA_TICKET is required" in captured.err


def test_debug_helpers_keep_sensitive_values_out_of_output() -> None:
    response = _purchase_order_response("2097-241-SE14")
    normalized = ChileCompraNormalizer().normalize(response)

    payload_summary = summarize_payload_shape(response.payload)
    normalized_summary = summarize_normalized_record(normalized.records[0])

    assert "ticket" not in payload_summary.lower()
    assert "ticket" not in normalized_summary.lower()
    assert "Camara de Comercio" not in payload_summary
    assert "Camara de Comercio" not in normalized_summary
    assert "Comprador_keys" in payload_summary
    assert "Proveedor_keys" in payload_summary
