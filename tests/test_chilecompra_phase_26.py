from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

from datosenorden.etl.chilecompra.client import ApiResponse
from datosenorden.etl.chilecompra.pipeline import ChileCompraPipeline
from datosenorden.etl.loaders.graph_loader import GraphLoader


def test_chilecompra_minimal_purchase_order_flow_builds_full_chain(monkeypatch) -> None:
    response = ApiResponse(
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
                }
            ],
        },
    )

    client = MagicMock()
    client.list_purchase_orders.return_value = response
    session = MagicMock()

    captured: dict[str, object] = {}

    def fake_load(self, batch, dry_run=False):  # noqa: ANN001
        captured["batch"] = batch
        captured["dry_run"] = dry_run
        return None

    monkeypatch.setattr(GraphLoader, "load", fake_load)

    pipeline = ChileCompraPipeline(client=client, session=session)
    result = pipeline.run_purchase_orders_for_day(date(2026, 1, 1), dry_run=True)

    assert result.resource == "purchase_orders"
    assert result.raw_count == 1
    assert result.rejected_count == 0
    assert result.loaded is False
    assert result.source_record_count == 1
    assert result.claim_count == 2
    assert result.evidence_count == 2
    assert result.public_relationship_count == 2
    assert result.errors == ()

    client.list_purchase_orders.assert_called_once_with(day=date(2026, 1, 1), status="todos")
    assert captured["dry_run"] is True

    batch = captured["batch"]
    assert batch.raw_count == 1
    assert len(batch.source_records) == 1
    assert len(batch.claims) == 2
    assert len(batch.evidence) == 2
    assert len(batch.public_relationships) == 2

    source_record = batch.source_records[0]
    claims = batch.claims
    evidence = batch.evidence
    public_relationships = batch.public_relationships

    assert all(claim.source_record is source_record for claim in claims)
    assert all(item.source_record is source_record for item in evidence)
    assert all(item.evidence in evidence for item in claims)
    assert all(item.claim in claims for item in public_relationships)

    predicates = {claim.predicate for claim in claims}
    relationship_types = {relationship.relationship_type.value for relationship in public_relationships}
    assert predicates == {"ISSUES_PURCHASE_ORDER", "RECEIVES_CONTRACT"}
    assert relationship_types == {"ISSUES_PURCHASE_ORDER", "RECEIVES_CONTRACT"}
