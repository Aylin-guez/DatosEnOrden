"""Read-only, bounded SPARQL discovery against InfoLobby's official endpoint."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import json
import re
from typing import Any, Final

import httpx


OFFICIAL_SPARQL_ENDPOINT: Final[str] = "http://datos.infolobby.cl/sparql"
MAX_RESPONSE_BYTES: Final[int] = 2 * 1024 * 1024
MAX_IDENTITY_LIMIT: Final[int] = 20
_UPDATE_KEYWORDS: Final[re.Pattern[str]] = re.compile(r"\b(?:INSERT|DELETE|LOAD|CLEAR|CREATE|DROP|MOVE|COPY|ADD)\b", re.IGNORECASE)
_LIMIT: Final[re.Pattern[str]] = re.compile(r"\bLIMIT\s+(\d+)\b", re.IGNORECASE)


class InfoLobbySparqlError(RuntimeError):
    """A deliberately sanitised discovery failure."""


class IdentityClassification(StrEnum):
    EXACT_ID_MATCH = "EXACT_ID_MATCH"
    STRONG_INSTITUTION_MATCH = "STRONG_INSTITUTION_MATCH"
    POSSIBLE_MATCH = "POSSIBLE_MATCH"
    NO_MATCH = "NO_MATCH"


@dataclass(frozen=True)
class InstitutionTarget:
    key: str
    label: str
    official_identifiers: tuple[str, ...] = ()


TARGETS: Final[tuple[InstitutionTarget, ...]] = (
    InstitutionTarget("hospital_felix_bulnes", "Hospital Dr. Félix Bulnes"),
    InstitutionTarget("division_logistica_ejercito", "División Logística del Ejército"),
    InstitutionTarget("direccion_educacion_publica", "Dirección de Educación Pública"),
)


@dataclass(frozen=True)
class SparqlResult:
    variables: tuple[str, ...]
    bindings: tuple[dict[str, str], ...]


@dataclass(frozen=True)
class IdentityDiscovery:
    target: InstitutionTarget
    classification: IdentityClassification
    entity_uris: tuple[str, ...]
    result: SparqlResult


class InfoLobbySparqlClient:
    """Only executes bounded SELECT discovery queries at the official endpoint."""

    def __init__(
        self,
        *,
        timeout_seconds: float = 20.0,
        max_response_bytes: int = MAX_RESPONSE_BYTES,
        max_attempts: int = 2,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if timeout_seconds <= 0 or max_response_bytes < 1 or not 1 <= max_attempts <= 2:
            raise ValueError("invalid bounded SPARQL client configuration")
        self._timeout_seconds = timeout_seconds
        self._max_response_bytes = max_response_bytes
        self._max_attempts = max_attempts
        self._transport = transport

    def select(self, query: str, *, limit_ceiling: int = MAX_IDENTITY_LIMIT) -> SparqlResult:
        serialised = _validate_and_serialise(query, limit_ceiling)
        for attempt in range(self._max_attempts):
            try:
                return self._request(serialised)
            except (httpx.HTTPError, InfoLobbySparqlError) as exc:
                if attempt + 1 == self._max_attempts or not _retryable(exc):
                    if isinstance(exc, InfoLobbySparqlError):
                        raise
                    raise InfoLobbySparqlError("InfoLobby SPARQL discovery request failed") from exc
        raise AssertionError("unreachable")

    def discover_identity(self, target: InstitutionTarget) -> IdentityDiscovery:
        result = self.select(identity_query(target.label))
        entity_uris = tuple(sorted({row["entity"] for row in result.bindings if row.get("entity", "").startswith("http")}))
        return IdentityDiscovery(target, classify_identity(target, result), entity_uris, result)

    def _request(self, query: str) -> SparqlResult:
        headers = {"Accept": "application/sparql-results+json, application/json;q=0.9", "User-Agent": "DatosEnOrden-InfoLobby-Discovery/0.1"}
        with httpx.Client(timeout=self._timeout_seconds, follow_redirects=False, transport=self._transport) as client:
            with client.stream("GET", OFFICIAL_SPARQL_ENDPOINT, params={"query": query, "format": "json"}, headers=headers) as response:
                endpoint = httpx.URL(OFFICIAL_SPARQL_ENDPOINT)
                if (response.url.scheme, response.url.host, response.url.port, response.url.path) != (
                    endpoint.scheme,
                    endpoint.host,
                    endpoint.port,
                    endpoint.path,
                ):
                    raise InfoLobbySparqlError("InfoLobby SPARQL redirect is outside the allowlist")
                response.raise_for_status()
                content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
                if content_type not in {"application/sparql-results+json", "application/json", "application/ld+json"}:
                    raise InfoLobbySparqlError("InfoLobby SPARQL response has an unsupported content type")
                chunks: list[bytes] = []
                total = 0
                for chunk in response.iter_bytes():
                    total += len(chunk)
                    if total > self._max_response_bytes:
                        raise InfoLobbySparqlError("InfoLobby SPARQL response exceeds configured byte limit")
                    chunks.append(chunk)
        return _parse_results(b"".join(chunks))


def identity_query(label: str) -> str:
    escaped = label.replace("\\", "\\\\").replace('"', '\\"')
    return f'''PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
SELECT ?entity ?entityType ?label WHERE {{
  VALUES ?labelPredicate {{ rdfs:label skos:prefLabel }}
  ?entity ?labelPredicate ?label .
  FILTER(STR(?label) = "{escaped}")
  OPTIONAL {{ ?entity a ?entityType }}
}} LIMIT {MAX_IDENTITY_LIMIT}'''


def audience_query(entity_uri: str) -> str:
    """Bounded generic sample; callers may use it only after deterministic identity."""
    if not entity_uri.startswith(("http://", "https://")) or any(char in entity_uri for char in "<>\"{}"):
        raise ValueError("invalid InfoLobby resource URI")
    return f'''SELECT DISTINCT ?audience WHERE {{
  ?audience ?institutionPredicate <{entity_uri}> .
}} LIMIT {MAX_IDENTITY_LIMIT}'''


def classify_identity(target: InstitutionTarget, result: SparqlResult) -> IdentityClassification:
    target_label = target.label.casefold().strip()
    for row in result.bindings:
        identifier = row.get("identifier", "").casefold().strip()
        if identifier and identifier in {value.casefold().strip() for value in target.official_identifiers}:
            return IdentityClassification.EXACT_ID_MATCH
    exact_labels = [row for row in result.bindings if row.get("label", "").casefold().strip() == target_label]
    if any(_institution_type(row.get("entityType", "")) for row in exact_labels):
        return IdentityClassification.STRONG_INSTITUTION_MATCH
    return IdentityClassification.POSSIBLE_MATCH if exact_labels else IdentityClassification.NO_MATCH


def _validate_and_serialise(query: str, limit_ceiling: int) -> str:
    serialised = " ".join(query.split())
    if not serialised.upper().startswith("SELECT ") and " SELECT " not in serialised.upper():
        raise InfoLobbySparqlError("InfoLobby discovery accepts SELECT queries only")
    if _UPDATE_KEYWORDS.search(serialised):
        raise InfoLobbySparqlError("InfoLobby discovery rejects update operations")
    limits = [int(value) for value in _LIMIT.findall(serialised)]
    if not limits or any(value > limit_ceiling for value in limits):
        raise InfoLobbySparqlError("InfoLobby discovery query requires a bounded LIMIT")
    return serialised


def _parse_results(content: bytes) -> SparqlResult:
    try:
        payload: Any = json.loads(content)
        variables = tuple(str(value) for value in payload["head"]["vars"])
        rows = payload["results"]["bindings"]
        bindings = tuple(
            {str(key): str(value["value"]) for key, value in row.items() if isinstance(value, dict) and "value" in value}
            for row in rows
        )
    except (TypeError, ValueError, KeyError) as exc:
        raise InfoLobbySparqlError("InfoLobby SPARQL response is not valid results JSON") from exc
    return SparqlResult(variables, bindings)


def _institution_type(value: str) -> bool:
    return any(token in value.casefold() for token in ("institucion", "institution", "entidad", "organization", "organizacion"))


def _retryable(exc: Exception) -> bool:
    return isinstance(exc, httpx.TransportError)
