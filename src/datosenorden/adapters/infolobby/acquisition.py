"""Bounded, allowlisted acquisition of official InfoLobby CSV catalogues."""

from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Iterable

import httpx

from datosenorden.core.config import PROJECT_ROOT

from .models import AcquisitionMetadata, CATALOGS, CatalogKey


DEFAULT_STAGING_DIR = PROJECT_ROOT / "data" / "real_imports" / "infolobby"
# Official monthly catalogues are currently as large as roughly 1.1 GiB.  This
# remains a hard per-file ceiling; callers must explicitly select catalogues.
MAX_CATALOG_BYTES = 1280 * 1024 * 1024
ALLOWED_CONTENT_TYPES = {"text/csv", "text/plain", "application/csv", "application/msexcel", "application/octet-stream"}
OFFICIAL_CATALOG_HOST = "datosinfolobby.cplt.cl"
OFFICIAL_CATALOG_PATH_PREFIX = "/catalogos/"


class InfoLobbyAcquisitionError(RuntimeError):
    pass


class InfoLobbyCatalogClient:
    """Download only catalogue URLs published on InfoLobby's official catalog page."""

    def __init__(
        self,
        *,
        staging_dir: Path = DEFAULT_STAGING_DIR,
        timeout_seconds: float = 30.0,
        max_bytes: int = MAX_CATALOG_BYTES,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if max_bytes < 1:
            raise ValueError("max_bytes must be positive")
        self._staging_dir = staging_dir
        self._timeout_seconds = timeout_seconds
        self._max_bytes = max_bytes
        self._transport = transport

    def acquire(self, keys: Iterable[CatalogKey]) -> tuple[AcquisitionMetadata, ...]:
        requested = tuple(dict.fromkeys(CatalogKey(key) for key in keys))
        if not requested:
            raise ValueError("at least one official catalog is required")
        return tuple(self._download(CATALOGS[key]) for key in requested)

    def _download(self, catalog):  # noqa: ANN001, ANN202
        self._staging_dir.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        with httpx.Client(timeout=self._timeout_seconds, follow_redirects=True, transport=self._transport) as client:
            try:
                with client.stream(
                    "GET",
                    catalog.url,
                    headers={
                        "Accept": "*/*",
                        "User-Agent": "DatosEnOrden-InfoLobby-Acquisition/0.1",
                    },
                ) as response:
                    response.raise_for_status()
                    _validate_response_url(response.url)
                    content_type = response.headers.get("content-type")
                    _validate_content_type(content_type)
                    declared_size = response.headers.get("content-length")
                    if declared_size and int(declared_size) > self._max_bytes:
                        raise InfoLobbyAcquisitionError("InfoLobby catalog exceeds configured byte limit")
                    total = 0
                    digest = sha256()
                    with NamedTemporaryFile(mode="wb", dir=self._staging_dir, prefix=f".{catalog.key.value}-", suffix=".partial", delete=False) as temporary:
                        temporary_path = Path(temporary.name)
                        for chunk in response.iter_bytes():
                            total += len(chunk)
                            if total > self._max_bytes:
                                raise InfoLobbyAcquisitionError("InfoLobby catalog exceeds configured byte limit")
                            digest.update(chunk)
                            temporary.write(chunk)
            except (httpx.HTTPError, ValueError) as exc:
                if temporary_path is not None:
                    temporary_path.unlink(missing_ok=True)
                raise InfoLobbyAcquisitionError("official InfoLobby catalog download failed") from exc
            except Exception:
                if temporary_path is not None:
                    temporary_path.unlink(missing_ok=True)
                raise
        assert temporary_path is not None
        with temporary_path.open("rb") as staged_file:
            _validate_csv_bytes(staged_file.read(8192))
        content_digest = digest.hexdigest()
        target = self._staging_dir / f"{catalog.key.value}-{content_digest}.csv"
        reused = target.exists()
        if reused:
            temporary_path.unlink(missing_ok=True)
        else:
            temporary_path.replace(target)
        return AcquisitionMetadata(catalog, datetime.now(UTC), content_digest, total, content_type, target, reused)


def _validate_content_type(value: str | None) -> None:
    if value is None:
        return
    media_type = value.split(";", 1)[0].strip().lower()
    if media_type not in ALLOWED_CONTENT_TYPES:
        raise InfoLobbyAcquisitionError("official InfoLobby catalog has an unsupported content type")


def _validate_response_url(url: httpx.URL) -> None:
    if url.host != OFFICIAL_CATALOG_HOST or not url.path.startswith(OFFICIAL_CATALOG_PATH_PREFIX):
        raise InfoLobbyAcquisitionError("official InfoLobby catalog redirect is outside the allowlist")


def _validate_csv_bytes(content: bytes) -> None:
    if not content.strip():
        raise InfoLobbyAcquisitionError("official InfoLobby catalog is empty")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("latin-1")
    first_line = text.splitlines()[0] if text.splitlines() else ""
    if not first_line or not any(separator in first_line for separator in (",", ";", "\t")):
        raise InfoLobbyAcquisitionError("official InfoLobby payload is not a delimited CSV")
