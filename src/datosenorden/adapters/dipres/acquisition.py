"""Bounded acquisition of an explicitly selected official DIPRES CSV."""

from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import urlparse

import httpx

from datosenorden.core.config import PROJECT_ROOT

from .models import AcquiredResource, ResourceDefinition


DEFAULT_STAGING_DIR = PROJECT_ROOT / "data" / "real_imports" / "dipres"
MAX_RESOURCE_BYTES = 32 * 1024 * 1024
OFFICIAL_HOST = "www.dipres.gob.cl"
ALLOWED_CONTENT_TYPES = {"text/csv", "application/csv", "text/plain", "application/octet-stream"}


class DipresAcquisitionError(RuntimeError):
    pass


class DipresTargetedClient:
    """Downloads one caller-selected CSV only from the official DIPRES host."""

    def __init__(self, *, staging_dir: Path = DEFAULT_STAGING_DIR, timeout_seconds: float = 30.0, max_bytes: int = MAX_RESOURCE_BYTES, transport: httpx.BaseTransport | None = None) -> None:
        if timeout_seconds <= 0 or max_bytes < 1:
            raise ValueError("invalid bounded DIPRES acquisition configuration")
        self._staging_dir = staging_dir
        self._timeout_seconds = timeout_seconds
        self._max_bytes = max_bytes
        self._transport = transport

    def acquire(self, resource: ResourceDefinition) -> AcquiredResource:
        _validate_official_url(resource.download_url)
        self._staging_dir.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        try:
            with httpx.Client(timeout=self._timeout_seconds, follow_redirects=True, transport=self._transport) as client:
                with client.stream("GET", resource.download_url, headers={"Accept": "text/csv, */*;q=0.8", "User-Agent": "DatosEnOrden-DIPRES-Discovery/0.1"}) as response:
                    response.raise_for_status()
                    _validate_official_url(str(response.url))
                    content_type = _validate_content_type(response.headers.get("content-type"))
                    declared_size = response.headers.get("content-length")
                    if declared_size and int(declared_size) > self._max_bytes:
                        raise DipresAcquisitionError("DIPRES resource exceeds configured byte limit")
                    digest = sha256()
                    total = 0
                    with NamedTemporaryFile(mode="wb", dir=self._staging_dir, prefix=".dipres-", suffix=".partial", delete=False) as temporary:
                        temporary_path = Path(temporary.name)
                        for chunk in response.iter_bytes():
                            total += len(chunk)
                            if total > self._max_bytes:
                                raise DipresAcquisitionError("DIPRES resource exceeds configured byte limit")
                            digest.update(chunk)
                            temporary.write(chunk)
        except (httpx.HTTPError, ValueError) as exc:
            if temporary_path:
                temporary_path.unlink(missing_ok=True)
            raise DipresAcquisitionError("official DIPRES resource download failed") from exc
        except Exception:
            if temporary_path:
                temporary_path.unlink(missing_ok=True)
            raise
        assert temporary_path is not None
        _validate_csv_prefix(temporary_path)
        content_digest = digest.hexdigest()
        target = self._staging_dir / f"{content_digest}.csv"
        reused = target.exists()
        if reused:
            temporary_path.unlink(missing_ok=True)
        else:
            temporary_path.replace(target)
        return AcquiredResource(resource, datetime.now(UTC), content_digest, total, content_type, target, reused)


def _validate_official_url(value: str) -> None:
    parsed = urlparse(value)
    if parsed.scheme != "https" or parsed.hostname != OFFICIAL_HOST:
        raise DipresAcquisitionError("DIPRES URL is outside the official HTTPS allowlist")


def _validate_content_type(value: str | None) -> str:
    media_type = (value or "").split(";", 1)[0].strip().lower()
    if media_type not in ALLOWED_CONTENT_TYPES:
        raise DipresAcquisitionError("official DIPRES resource has an unsupported content type")
    return media_type


def _validate_csv_prefix(path: Path) -> None:
    with path.open("rb") as handle:
        prefix = handle.read(8192)
    if not prefix.strip() or prefix.lstrip().lower().startswith(b"<html"):
        raise DipresAcquisitionError("official DIPRES resource is not a CSV payload")
    if not any(separator in prefix.splitlines()[0] for separator in (b",", b";", b"\t")):
        raise DipresAcquisitionError("official DIPRES resource is not a delimited CSV")
