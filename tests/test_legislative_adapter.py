from datetime import UTC, datetime

import pytest

from datosenorden.adapters.legislature import LegislativeAdapter
from datosenorden.adapters.legislature.models import LegislativeXmlResponse
from datosenorden.adapters.legislature.parser import (
    bulletin_aliases,
    canonical_bill_id,
    normalize_bulletin_id,
)
from datosenorden.etl.core.contracts import EntityType, WorkflowStatus


SAMPLE_VOTES_XML = """<?xml version="1.0" encoding="utf-8"?>
<Votaciones xmlns="http://tempuri.org/">
  <Votacion>
    <ID>16197</ID>
    <Fecha>2026-01-02T10:30:00</Fecha>
    <Tipo>General</Tipo>
    <Resultado>Aprobado</Resultado>
    <Quorum>Simple</Quorum>
    <Sesion>
      <ID>3162</ID>
      <Numero>12</Numero>
      <Fecha>2026-01-02T09:00:00</Fecha>
      <FechaTermino>2026-01-02T12:00:00</FechaTermino>
      <Tipo>Ordinaria</Tipo>
      <Estado>Finalizada</Estado>
    </Sesion>
    <Boletin>8575-05</Boletin>
    <Articulo>Articulo 1</Articulo>
    <Tramite>Primer tramite constitucional</Tramite>
    <Informe>Informe de comision</Informe>
    <TotalAfirmativos>80</TotalAfirmativos>
    <TotalNegativos>20</TotalNegativos>
    <TotalAbstenciones>5</TotalAbstenciones>
    <TotalDispensados>0</TotalDispensados>
  </Votacion>
</Votaciones>
"""


class FakeLegislativeClient:
    def __init__(self) -> None:
        self.requested_bulletins: list[str] = []

    def get_votes_by_bulletin(self, bulletin_id: str) -> LegislativeXmlResponse:
        self.requested_bulletins.append(bulletin_id)
        return LegislativeXmlResponse(
            url="https://opendata.camara.cl/wscamaradiputados.asmx/getVotaciones_Boletin",
            params={"prmBoletin": bulletin_id},
            xml_text=SAMPLE_VOTES_XML,
            retrieved_at=datetime(2026, 1, 2, 13, 0, tzinfo=UTC),
        )


def test_bulletin_identity_helpers_preserve_complete_bulletin() -> None:
    assert normalize_bulletin_id(" 8575-05 ") == "8575-05"
    assert canonical_bill_id("8575-05") == "cl-congreso-boletin-8575-05"
    assert bulletin_aliases("8575-05") == ("8575-05", "8575")


def test_bulletin_identity_rejects_unexpected_format() -> None:
    with pytest.raises(ValueError):
        normalize_bulletin_id("../8575")


def test_load_bill_maps_single_bulletin_to_platform_contracts() -> None:
    client = FakeLegislativeClient()
    batch = LegislativeAdapter(client=client).load_bill("8575-05")  # type: ignore[arg-type]

    assert client.requested_bulletins == ["8575-05"]
    assert batch.source.name == "Datos Abiertos Legislativos Congreso Nacional"
    assert batch.dataset.name == "congreso-votaciones-boletin"
    assert batch.dataset.version == "8575-05"
    assert batch.raw_count == 1
    assert batch.rejected_count == 0
    assert len(batch.source_records) == 2
    assert len(batch.entities) == 1
    assert batch.entities[0].entity_type == EntityType.PUBLIC_PROJECT
    assert batch.entities[0].external_id == "cl-congreso-boletin-8575-05"
    assert batch.entities[0].metadata["aliases"] == ("8575-05", "8575")
    assert len(batch.evidence) == 1
    assert "16197" in batch.evidence[0].url
    assert len(batch.claims) == 1
    assert batch.claims[0].predicate == "LEGISLATIVE_BILL_HAS_VOTE"
    assert batch.claims[0].status == WorkflowStatus.VALIDATED
    assert batch.claims[0].object_value["totals"]["affirmative"] == 80  # type: ignore[index]
    assert batch.claims[0].object_value["session"]["source_id"] == "camara-sesion-3162"  # type: ignore[index]
    assert batch.public_relationships == ()
