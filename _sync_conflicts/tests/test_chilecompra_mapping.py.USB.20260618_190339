from datetime import date

from datosenorden.etl.chilecompra.client import ApiResponse
from datosenorden.etl.chilecompra.debug import summarize_normalized_record, summarize_payload_shape
from datosenorden.etl.chilecompra.mappers import ChileCompraGraphMapper
from datosenorden.etl.chilecompra.normalizers import ChileCompraNormalizer
from datosenorden.etl.core.contracts import WorkflowStatus


def _real_like_purchase_order_payload() -> dict[str, object]:
    return {
        "Version": "v1",
        "FechaCreacion": "2026-01-01T00:00:00",
        "Listado": [
            {
                "Codigo": "2097-241-SE14",
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
    }


def test_maps_purchase_order_to_contract_graph() -> None:
    response = ApiResponse(
        url="https://api.mercadopublico.cl/servicios/v1/publico/ordenesdecompra.json",
        params={"fecha": "01012026"},
        payload=_real_like_purchase_order_payload(),
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


def test_maps_missing_purchase_order_identity_as_rejected() -> None:
    response = ApiResponse(
        url="https://api.mercadopublico.cl/servicios/v1/publico/ordenesdecompra.json",
        params={"codigo": "2097-241-SE14"},
        payload={
            "Version": "v1",
            "FechaCreacion": "2026-01-01T00:00:00",
            "Listado": [
                {
                    "Codigo": "2097-241-SE14",
                    "Nombre": "Compra de servicios",
                    "FechaEnvio": "2026-01-01T12:00:00",
                }
            ],
        },
    )

    normalized = ChileCompraNormalizer().normalize(response)
    batch = ChileCompraGraphMapper().map_purchase_orders(normalized)

    assert batch.raw_count == 1
    assert batch.rejected_count == 1
    assert len(batch.source_records) == 1
    assert batch.source_records[0].status == WorkflowStatus.REJECTED
    assert batch.source_records[0].error_log is not None
    assert "no claims could be derived" in batch.source_records[0].error_log.lower()
    assert batch.claims == ()
    assert batch.evidence == ()
    assert batch.public_relationships == ()
    assert len(batch.errors) == 1


def test_debug_helpers_do_not_expose_secret_values() -> None:
    payload = _real_like_purchase_order_payload()
    normalized = ChileCompraNormalizer().normalize(
        ApiResponse(
            url="https://api.mercadopublico.cl/servicios/v1/publico/ordenesdecompra.json",
            params={"codigo": "2097-241-SE14"},
            payload=payload,
        )
    )

    payload_summary = summarize_payload_shape(payload)
    normalized_summary = summarize_normalized_record(normalized.records[0])

    assert "ticket" not in payload_summary.lower()
    assert "ticket" not in normalized_summary.lower()
    assert "CodigoOrganismo" in payload_summary
    assert "Proveedor_keys" in payload_summary
    assert "present_fields" in normalized_summary
