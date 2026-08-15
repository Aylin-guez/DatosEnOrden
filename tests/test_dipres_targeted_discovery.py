from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from datosenorden.adapters.dipres.acquisition import DipresAcquisitionError, DipresTargetedClient
from datosenorden.adapters.dipres.models import AcquiredResource, IdentityClassification, ResourceDefinition, classify_identity
from datosenorden.adapters.dipres.parser import parse_budget_csv


RESOURCE = ResourceDefinition("https://www.dipres.gob.cl/597/w3-multipropertyvalues-25910-37782.html", "https://www.dipres.gob.cl/597/articles-421187_doc_csv.csv?ts=1785519425", "Segundo Trimestre 2026")


def test_acquisition_is_official_bounded_and_idempotent(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "www.dipres.gob.cl"
        return httpx.Response(200, content=b"Programa;Vigente;Devengado\n01;10;2\n", headers={"content-type": "text/csv"})

    client = DipresTargetedClient(staging_dir=tmp_path, max_bytes=1024, transport=httpx.MockTransport(handler))
    first = client.acquire(RESOURCE)
    second = client.acquire(RESOURCE)
    assert first.sha256 == second.sha256
    assert first.reused_staged_file is False
    assert second.reused_staged_file is True


def test_acquisition_rejects_non_official_redirect_or_content_type(tmp_path: Path) -> None:
    client = DipresTargetedClient(staging_dir=tmp_path, transport=httpx.MockTransport(lambda request: httpx.Response(200, content=b"<html>", headers={"content-type": "text/html"})))
    with pytest.raises(DipresAcquisitionError):
        client.acquire(RESOURCE)
    with pytest.raises(DipresAcquisitionError):
        client.acquire(ResourceDefinition(RESOURCE.official_page_url, "http://example.test/file.csv", "x"))


def test_acquisition_rejects_oversized_response(tmp_path: Path) -> None:
    client = DipresTargetedClient(staging_dir=tmp_path, max_bytes=3, transport=httpx.MockTransport(lambda request: httpx.Response(200, content=b"a;b\n1;2\n", headers={"content-type": "text/csv"})))
    with pytest.raises(DipresAcquisitionError, match="byte limit"):
        client.acquire(RESOURCE)


def test_parser_fixture_has_no_database_dependency(tmp_path: Path) -> None:
    path = tmp_path / "fixture.csv"
    path.write_text("Programa;Presupuesto Vigente;Devengado\n01;100;25\n", encoding="utf-8")
    acquired = AcquiredResource(RESOURCE, datetime.now(UTC), "hash", path.stat().st_size, "text/csv", path, False)
    parsed = parse_budget_csv(acquired)
    assert parsed.columns == ("programa", "presupuesto_vigente", "devengado")
    assert parsed.rows[0].values["devengado"] == "25"


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    (
        ({"chilecompra_label": "A", "official_label": "A", "same_entity": True, "exact_official_identifier": True}, IdentityClassification.EXACT_ID_MATCH),
        ({"chilecompra_label": "A", "official_label": "A", "same_entity": True}, IdentityClassification.STRONG_INSTITUTION_MATCH),
        ({"chilecompra_label": "A", "official_label": "Padre", "same_entity": False, "parent_budget_label": "Padre"}, IdentityClassification.PARENT_INSTITUTION_ONLY),
        ({"chilecompra_label": "A", "official_label": "A", "same_entity": False}, IdentityClassification.POSSIBLE_MATCH),
        ({"chilecompra_label": "A", "official_label": None, "same_entity": False}, IdentityClassification.NO_MATCH),
    ),
)
def test_identity_classification_is_explicit_and_never_fuzzy(kwargs: dict[str, object], expected: IdentityClassification) -> None:
    assert classify_identity(**kwargs) is expected  # type: ignore[arg-type]
