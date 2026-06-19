from datetime import date

from datosenorden.etl.chilecompra.client import ApiResponse
from datosenorden.etl.chilecompra.mappers import ChileCompraGraphMapper
from datosenorden.etl.chilecompra.normalizers import ChileCompraNormalizer


def test_maps_purchase_order_to_contract_graph() -> None:
    response = ApiResponse(
        url="https://api.mercadopublico.cl/servicios/v1/publico/ordenesdecompra.json",
        params={"fecha": "01012026"},
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

    normalized = ChileCompraNormalizer().normalize(response, query_date=date(2026, 1, 1))
    batch = ChileCompraGraphMapper().map_purchase_orders(normalized)

    assert batch.raw_count == 1
    assert batch.rejected_count == 0
    assert len(batch.source_records) == 1
    assert {entity.entity_type.value for entity in batch.entities} == {
        "COMPANY",
        "CONTRACT",
        "PUBLIC_ORGANIZATION",
    }
    assert {claim.predicate for claim in batch.claims} == {
        "ISSUES_PURCHASE_ORDER",
        "RECEIVES_CONTRACT",
    }
    assert {relation.relationship_type.value for relation in batch.public_relationships} == {
        "ISSUES_PURCHASE_ORDER",
        "RECEIVES_CONTRACT",
    }
    assert len(batch.evidence) == 2
