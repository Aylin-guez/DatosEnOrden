from dataclasses import dataclass
from datetime import date
from typing import Any

import httpx

from datosenorden.etl.chilecompra.config import ChileCompraSettings
from datosenorden.etl.core.errors import ExtractError
from datosenorden.etl.core.time import format_api_date


@dataclass(frozen=True)
class ApiResponse:
    url: str
    params: dict[str, str]
    payload: dict[str, Any]


class ChileCompraClient:
    def __init__(self, settings: ChileCompraSettings) -> None:
        self._settings = settings

    def list_tenders(self, day: date, status: str = "todos") -> ApiResponse:
        params = {"fecha": format_api_date(day), "estado": status}
        return self._get_json("licitaciones.json", params)

    def get_tender(self, code: str) -> ApiResponse:
        return self._get_json("licitaciones.json", {"codigo": code})

    def list_purchase_orders(self, day: date, status: str = "todos") -> ApiResponse:
        params = {"fecha": format_api_date(day), "estado": status}
        return self._get_json("ordenesdecompra.json", params)

    def get_purchase_order(self, code: str) -> ApiResponse:
        return self._get_json("ordenesdecompra.json", {"codigo": code})

    def list_buyers(self) -> ApiResponse:
        return self._get_json("Empresas/BuscarComprador", {})

    def find_supplier_by_rut(self, rut: str) -> ApiResponse:
        return self._get_json("Empresas/BuscarProveedor", {"rutempresaproveedor": rut})

    def _get_json(self, resource: str, params: dict[str, str]) -> ApiResponse:
        safe_params = {key: value for key, value in params.items() if value not in ("", None)}
        request_params = {**safe_params, "ticket": self._settings.ticket}
        url = f"{self._settings.base_url}/{resource.lstrip('/')}"

        last_error: Exception | None = None
        for attempt in range(1, self._settings.max_retries + 1):
            try:
                with httpx.Client(timeout=self._settings.timeout_seconds) as client:
                    response = client.get(url, params=request_params)
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict):
                    raise ExtractError(f"Unexpected non-object response from {resource}")
                return ApiResponse(url=url, params=safe_params, payload=payload)
            except (httpx.HTTPError, ValueError, ExtractError) as exc:
                last_error = exc
                if attempt == self._settings.max_retries:
                    break

        raise ExtractError(f"Failed to fetch {resource}: {last_error}") from last_error
