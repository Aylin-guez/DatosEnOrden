"""Provider-agnostic production configuration validation."""

from __future__ import annotations

from dataclasses import dataclass
import os
from urllib.parse import urlparse


REQUIRED_SECRET = ("DATABASE_URL",)
REQUIRED_CONFIG = ("DATOSENORDEN_ENV", "DATOSENORDEN_PUBLIC_BASE_URL", "API_URL")
OPTIONAL_CONFIG = ("DATOSENORDEN_SUPPORT_URL", "REFLEX_BACKEND_PATH", "DATOSENORDEN_LOG_LEVEL")
DERIVED_CONFIG = ("canonical_public_url", "backend_path")


@dataclass(frozen=True)
class ProductionConfig:
    canonical_public_url: str
    api_url: str
    backend_path: str
    debug_investigation: bool


def load_production_config(environ: dict[str, str] | None = None) -> ProductionConfig:
    values = os.environ if environ is None else environ
    if values.get("DATOSENORDEN_ENV", "").strip().lower() != "production":
        raise ValueError("DATOSENORDEN_ENV must be production")
    for name in REQUIRED_SECRET + REQUIRED_CONFIG:
        if not values.get(name, "").strip():
            raise ValueError(f"missing required production configuration: {name}")
    public_url = _public_https_url(values["DATOSENORDEN_PUBLIC_BASE_URL"], "DATOSENORDEN_PUBLIC_BASE_URL")
    api_url = _public_https_url(values["API_URL"], "API_URL")
    if values.get("DATOSENORDEN_DEBUG_INVESTIGATION", "0").strip() not in {"", "0", "false", "False"}:
        raise ValueError("DATOSENORDEN_DEBUG_INVESTIGATION must be disabled in production")
    return ProductionConfig(public_url, api_url, _backend_path(values.get("REFLEX_BACKEND_PATH", "/api")), False)


def _public_https_url(value: str, name: str) -> str:
    parsed = urlparse(value.strip())
    if parsed.scheme != "https" or not parsed.netloc or parsed.hostname in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError(f"{name} must be a public HTTPS URL")
    return value.rstrip("/")


def _backend_path(value: str) -> str:
    text = value.strip() or "/api"
    if not text.startswith("/") or text.startswith("//"):
        raise ValueError("REFLEX_BACKEND_PATH must be a site-relative path")
    return text.rstrip("/") or "/api"
