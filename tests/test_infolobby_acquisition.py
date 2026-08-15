from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from datosenorden.adapters.infolobby.acquisition import InfoLobbyAcquisitionError, InfoLobbyCatalogClient, _validate_csv_bytes
from datosenorden.adapters.infolobby.dry_run import deterministic_matches
from datosenorden.adapters.infolobby.models import AcquisitionMetadata, CATALOGS, CatalogKey
from datosenorden.adapters.infolobby.parser import parse_catalog


def _metadata(tmp_path: Path, content: str) -> AcquisitionMetadata:
    path = tmp_path / "catalog.csv"
    path.write_text(content, encoding="utf-8")
    return AcquisitionMetadata(CATALOGS[CatalogKey.AUDIENCIAS], __import__("datetime").datetime.now(__import__("datetime").UTC), "digest", path.stat().st_size, "application/msexcel", path, False)


def test_parser_normalizes_columns_and_rows(tmp_path: Path) -> None:
    catalog = parse_catalog(_metadata(tmp_path, "ID Audiencia;Fecha Realizado;Organismo\nA-1;2025-01-03;Dirección de Educación Pública\n"))
    assert catalog.columns == ("id_audiencia", "fecha_realizado", "organismo")
    assert catalog.rows[0]["id_audiencia"] == "A-1"


def test_parser_rejects_ambiguous_headers(tmp_path: Path) -> None:
    with pytest.raises(InfoLobbyAcquisitionError, match="ambiguous"):
        parse_catalog(_metadata(tmp_path, "ID;Id\n1;2\n"))


def test_csv_validation_rejects_html_or_empty_payload() -> None:
    with pytest.raises(InfoLobbyAcquisitionError):
        _validate_csv_bytes(b"<html>not a csv</html>")
    with pytest.raises(InfoLobbyAcquisitionError):
        _validate_csv_bytes(b"")


def test_deterministic_match_never_uses_fuzzy_name_matching(tmp_path: Path) -> None:
    catalog = parse_catalog(_metadata(tmp_path, "Institucion;Codigo\nDIRECCION DE EDUCACION PUBLICA;1\nDireccion Educacion;2\n"))
    matches = deterministic_matches((catalog,), (("entity-1", "PUBLIC_ORGANIZATION", "DIRECCION DE EDUCACION PUBLICA", "chilecompra:buyer:1593363"),))
    assert len(matches) == 1
    assert matches[0].classification == "STRONG_INSTITUTION_MATCH"


def test_deterministic_match_does_not_resolve_company_name(tmp_path: Path) -> None:
    catalog = parse_catalog(_metadata(tmp_path, "Organismo;Fecha\nProveedor S.A.;2026-01-01\n"))
    matches = deterministic_matches((catalog,), (("entity-2", "COMPANY", "Proveedor S.A.", None),))
    assert matches == ()


def test_deterministic_match_allows_same_rut_in_identifier_field(tmp_path: Path) -> None:
    catalog = parse_catalog(_metadata(tmp_path, "Rut Pasivo;Fecha\n76.231.700-5;2026-01-01\n"))
    matches = deterministic_matches((catalog,), (("entity-3", "COMPANY", "Proveedor S.A.", "chilecompra:supplier:76231700-5"),))
    assert matches[0].classification == "EXACT_ID_MATCH"


def test_acquisition_is_allowlisted_and_idempotently_reuses_staging(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "datosinfolobby.cplt.cl"
        return httpx.Response(200, content=b"id;fecha\n1;2026-01-01\n", headers={"content-type": "application/msexcel"})

    client = InfoLobbyCatalogClient(staging_dir=tmp_path, max_bytes=1024, transport=httpx.MockTransport(handler))
    first = client.acquire((CatalogKey.AUDIENCIAS,))[0]
    second = client.acquire((CatalogKey.AUDIENCIAS,))[0]

    assert first.sha256 == second.sha256
    assert first.reused_staged_file is False
    assert second.reused_staged_file is True
    assert first.public_countable is False
