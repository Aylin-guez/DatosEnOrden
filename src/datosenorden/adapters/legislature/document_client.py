from __future__ import annotations

from datetime import UTC, datetime
from email.message import Message
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

from datosenorden.adapters.legislature.document_models import (
    SENADO_PROJECT_URL,
    LegislativeDownloadedDocument,
    LegislativeProjectXmlResponse,
)
from datosenorden.etl.core.errors import ExtractError


class LegislativeDocumentClient:
    """HTTP client for official legislative document sources only."""

    def __init__(
        self,
        senate_project_url: str = SENADO_PROJECT_URL,
        timeout_seconds: float = 20.0,
        max_retries: int = 2,
    ) -> None:
        self._senate_project_url = senate_project_url
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries

    def get_senate_project(self, bulletin_query_id: str) -> LegislativeProjectXmlResponse:
        query_id = bulletin_query_id.strip()
        if not query_id:
            raise ValueError("bulletin_query_id is required")
        params = {"boletin": query_id}
        response = self._get(self._senate_project_url, params=params)
        return LegislativeProjectXmlResponse(
            url=self._senate_project_url,
            params=params,
            xml_text=_decode_text(response),
            retrieved_at=datetime.now(UTC),
        )

    def download_document(self, url: str) -> LegislativeDownloadedDocument:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("document URL must be http(s)")
        response = self._get(url, params=None)
        filename = _filename_from_content_disposition(response.headers.get("content-disposition"))
        return LegislativeDownloadedDocument(
            url=str(response.url),
            content=response.content,
            content_type=response.headers.get("content-type"),
            filename=filename,
            size=len(response.content),
            retrieved_at=datetime.now(UTC),
        )

    def _get(self, url: str, params: dict[str, str] | None) -> httpx.Response:
        last_error: Exception | None = None
        for attempt in range(1, self._max_retries + 1):
            try:
                with httpx.Client(timeout=self._timeout_seconds, follow_redirects=True) as client:
                    response = client.get(url, params=params)
                response.raise_for_status()
                return response
            except httpx.HTTPError as exc:
                last_error = exc
                if attempt == self._max_retries:
                    break
        raise ExtractError(f"Failed to fetch official legislative document URL {url}: {last_error}") from last_error


def canonical_url(url: str) -> str:
    parsed = urlparse(url.replace("&amp;", "&"))
    query = urlencode({key: values[-1] for key, values in parse_qs(parsed.query).items()})
    return parsed._replace(query=query).geturl()


def _decode_text(response: httpx.Response) -> str:
    encoding = response.encoding or "utf-8"
    try:
        return response.content.decode(encoding)
    except UnicodeDecodeError:
        return response.content.decode("latin-1")


def _filename_from_content_disposition(value: str | None) -> str | None:
    if not value:
        return None
    message = Message()
    message["content-disposition"] = value
    filename = message.get_filename()
    return filename.strip() if filename else None
