from datetime import UTC, datetime

import httpx

from datosenorden.adapters.legislature.models import CAMARA_SERVICE_URL, LegislativeXmlResponse
from datosenorden.etl.core.errors import ExtractError


class LegislativeClient:
    """Small HTTP client for the official Camara ASMX service."""

    def __init__(
        self,
        base_url: str = CAMARA_SERVICE_URL,
        timeout_seconds: float = 15.0,
        max_retries: int = 2,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries

    def get_votes_by_bulletin(self, bulletin_id: str) -> LegislativeXmlResponse:
        bulletin = bulletin_id.strip()
        if not bulletin:
            raise ValueError("bulletin_id is required")
        return self._get_xml("getVotaciones_Boletin", {"prmBoletin": bulletin})

    def _get_xml(self, operation: str, params: dict[str, str]) -> LegislativeXmlResponse:
        url = f"{self._base_url}/{operation.lstrip('/')}"
        last_error: Exception | None = None
        for attempt in range(1, self._max_retries + 1):
            try:
                with httpx.Client(timeout=self._timeout_seconds) as client:
                    response = client.get(url, params=params)
                response.raise_for_status()
                return LegislativeXmlResponse(
                    url=url,
                    params=params,
                    xml_text=response.text,
                    retrieved_at=datetime.now(UTC),
                )
            except httpx.HTTPError as exc:
                last_error = exc
                if attempt == self._max_retries:
                    break
        raise ExtractError(f"Failed to fetch legislative operation {operation}: {last_error}") from last_error
