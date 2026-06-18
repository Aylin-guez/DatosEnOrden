from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any

from datosenorden.etl.chilecompra.client import ApiResponse
from datosenorden.etl.core.hash import stable_json_hash


@dataclass(frozen=True)
class NormalizedPayload:
    source_url: str
    request_params: dict[str, str]
    api_version: str | None
    api_created_at: str | None
    query_date: date | None
    retrieved_at: datetime
    records: tuple[dict[str, Any], ...]
    raw_payload_hash: str
    raw_payload: dict[str, Any]


class ChileCompraNormalizer:
    def normalize(self, response: ApiResponse, query_date: date | None = None) -> NormalizedPayload:
        payload = response.payload
        records = payload.get("Listado") or []
        if isinstance(records, dict):
            records = [records]
        if not isinstance(records, list):
            records = []

        normalized_records = tuple(record for record in records if isinstance(record, dict))
        return NormalizedPayload(
            source_url=response.url,
            request_params=response.params,
            api_version=self._string_or_none(payload.get("Version")),
            api_created_at=self._string_or_none(payload.get("FechaCreacion")),
            query_date=query_date,
            retrieved_at=datetime.now(timezone.utc),
            records=normalized_records,
            raw_payload_hash=stable_json_hash(payload),
            raw_payload=payload,
        )

    @staticmethod
    def _string_or_none(value: object | None) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None
