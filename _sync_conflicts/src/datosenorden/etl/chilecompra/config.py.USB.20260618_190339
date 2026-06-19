from dataclasses import dataclass
import os

from datosenorden.core.config import _load_dotenv


@dataclass(frozen=True)
class ChileCompraSettings:
    ticket: str
    base_url: str = "https://api.mercadopublico.cl/servicios/v1/publico"
    timeout_seconds: float = 30
    max_retries: int = 3


def get_chilecompra_settings() -> ChileCompraSettings:
    _load_dotenv()
    ticket = os.getenv("DATOSENORDEN_CHILECOMPRA_TICKET", "").strip()
    if not ticket:
        raise ValueError("DATOSENORDEN_CHILECOMPRA_TICKET is required")

    return ChileCompraSettings(
        ticket=ticket,
        base_url=os.getenv(
            "DATOSENORDEN_CHILECOMPRA_BASE_URL",
            "https://api.mercadopublico.cl/servicios/v1/publico",
        ).rstrip("/"),
        timeout_seconds=float(os.getenv("DATOSENORDEN_CHILECOMPRA_TIMEOUT_SECONDS", "30")),
        max_retries=int(os.getenv("DATOSENORDEN_CHILECOMPRA_MAX_RETRIES", "3")),
    )
