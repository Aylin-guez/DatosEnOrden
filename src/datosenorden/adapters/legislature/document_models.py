from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


SENADO_PROJECT_URL = "https://tramitacion.senado.cl/wspublico/tramitacion.php"
SENADO_DOCUMENT_BASE_URL = "https://www.senado.cl/appsenado/index.php"
SENADO_SOURCE_NAME = "Senado de la Republica de Chile"
CAMARA_DOCUMENT_SOURCE_NAME = "Camara de Diputadas y Diputados"


@dataclass(frozen=True)
class LegislativeProjectXmlResponse:
    url: str
    params: dict[str, str]
    xml_text: str
    retrieved_at: datetime


@dataclass(frozen=True)
class LegislativeDownloadedDocument:
    url: str
    content: bytes
    content_type: str | None
    filename: str | None
    size: int
    retrieved_at: datetime


@dataclass(frozen=True)
class LegislativeDocumentCandidate:
    document_id: str
    type: str
    title: str
    format: str
    url: str
    size: int | None = None
    publication_date: str | None = None
    source: str = SENADO_SOURCE_NAME
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class LegislativeDocumentCatalog:
    bulletin_id: str
    source: str
    documents: tuple[LegislativeDocumentCandidate, ...]
    project_url: str
    retrieved_at: datetime
    metadata: dict[str, str] = field(default_factory=dict)
