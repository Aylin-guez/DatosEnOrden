from __future__ import annotations

import json

import httpx
import pytest

from datosenorden.adapters.infolobby.sparql import (
    IdentityClassification,
    InfoLobbySparqlClient,
    InfoLobbySparqlError,
    InstitutionTarget,
    SparqlResult,
    classify_identity,
)


def _result() -> bytes:
    return json.dumps({"head": {"vars": ["entity", "entityType", "label"]}, "results": {"bindings": [{"entity": {"type": "uri", "value": "http://datos.infolobby.cl/resource/1"}, "entityType": {"type": "uri", "value": "http://datos.infolobby.cl/ontology/Institucion"}, "label": {"type": "literal", "value": "Dirección de Educación Pública"}}]}}).encode()


def test_client_uses_official_endpoint_and_parses_bounded_json() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "datos.infolobby.cl"
        assert request.method == "GET"
        assert "LIMIT 20" in request.url.params["query"]
        return httpx.Response(200, content=_result(), headers={"content-type": "application/sparql-results+json"})

    discovery = InfoLobbySparqlClient(transport=httpx.MockTransport(handler)).discover_identity(InstitutionTarget("dep", "Dirección de Educación Pública"))
    assert discovery.classification is IdentityClassification.STRONG_INSTITUTION_MATCH


@pytest.mark.parametrize("query", ("SELECT * WHERE { ?s ?p ?o }", "INSERT DATA { <a> <b> <c> }", "SELECT * WHERE { ?s ?p ?o } LIMIT 21"))
def test_client_rejects_unbounded_or_mutating_queries(query: str) -> None:
    with pytest.raises(InfoLobbySparqlError):
        InfoLobbySparqlClient().select(query)


def test_client_rejects_non_json_content_type() -> None:
    client = InfoLobbySparqlClient(transport=httpx.MockTransport(lambda request: httpx.Response(200, content=b"<html>", headers={"content-type": "text/html"})))
    with pytest.raises(InfoLobbySparqlError, match="content type"):
        client.discover_identity(InstitutionTarget("dep", "Dirección de Educación Pública"))


def test_client_retries_a_transient_timeout_once_then_fails_sanitized() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ReadTimeout("network detail must not escape", request=request)

    with pytest.raises(InfoLobbySparqlError, match="request failed"):
        InfoLobbySparqlClient(transport=httpx.MockTransport(handler)).discover_identity(InstitutionTarget("dep", "Dirección de Educación Pública"))
    assert calls == 2


def test_client_rejects_response_over_its_bound() -> None:
    client = InfoLobbySparqlClient(max_response_bytes=5, transport=httpx.MockTransport(lambda request: httpx.Response(200, content=_result(), headers={"content-type": "application/json"})))
    with pytest.raises(InfoLobbySparqlError, match="byte limit"):
        client.discover_identity(InstitutionTarget("dep", "Dirección de Educación Pública"))


def test_identity_classification_never_uses_fuzzy_name() -> None:
    target = InstitutionTarget("dep", "Dirección de Educación Pública")
    assert classify_identity(target, SparqlResult(("label",), ({"label": "Direccion Educacion"},))) is IdentityClassification.NO_MATCH
    assert classify_identity(target, SparqlResult(("label",), ({"label": target.label},))) is IdentityClassification.POSSIBLE_MATCH


def test_identity_exact_identifier_requires_same_public_identifier() -> None:
    target = InstitutionTarget("dep", "Dirección de Educación Pública", ("12345678-9",))
    result = SparqlResult(("identifier",), ({"identifier": "12345678-9"},))
    assert classify_identity(target, result) is IdentityClassification.EXACT_ID_MATCH
