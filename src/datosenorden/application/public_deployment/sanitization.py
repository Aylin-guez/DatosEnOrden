"""Contracts that keep server-only values out of public Reflex payloads."""

from __future__ import annotations

import re
from urllib.parse import urlparse


PUBLIC_ERROR_CODE = "PUBLIC_SERVICE_UNAVAILABLE"
PUBLIC_ERROR_MESSAGE = "No pudimos completar esta acción. Intenta nuevamente o vuelve a una ruta estable."
_LOCAL_PATH = re.compile(r"(?:[A-Za-z]:[\\/]|^\\\\|^/home/|^/opt/|^/tmp/|^/var/|^file://)", re.IGNORECASE)


def public_error() -> tuple[str, str]:
    """Return the only error contract that may cross the public boundary."""
    return PUBLIC_ERROR_CODE, PUBLIC_ERROR_MESSAGE



def public_asset_reference(value: object) -> str:
    """Allow only an intentional site-relative asset reference."""
    text = str(value or "").strip()
    if not text or _LOCAL_PATH.search(text) or not text.startswith("/") or text.startswith("//"):
        return ""
    return text


def public_url(value: object) -> str:
    """Allow only ordinary http(s) public URLs, never filesystem locations."""
    text = str(value or "").strip()
    parsed = urlparse(text)
    if _LOCAL_PATH.search(text) or parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    return text


def public_opaque_reference(value: object) -> str:
    """Keep a stable opaque identifier; reject values that look like local paths."""
    text = str(value or "").strip()
    return "" if _LOCAL_PATH.search(text) else text
