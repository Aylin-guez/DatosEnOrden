"""Bounded acquisition helpers for an explicitly identified BCN law history.

BCN's public Historia de la Ley page exposes its individual, numbered sections
through its own XAJAX endpoint.  This module intentionally accepts only a
canonical history URL and one already-listed section position; it is not a
crawler and does not attempt to access congressional hosts.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import urlparse

import httpx


class BCNHistoryError(RuntimeError):
    """The official BCN history resource could not be validated or acquired."""


@dataclass(frozen=True)
class BCNHistoryArtifact:
    official_url: str
    law_number: str
    history_id: str
    section_id: str | None
    retrieved_at: datetime
    sha256: str
    byte_count: int
    content_type: str
    staging_path: Path


def canonical_history_url(history_id: str) -> str:
    if not history_id.isdigit():
        raise BCNHistoryError("BCN history id must be numeric")
    return f"https://www.bcn.cl/historiadelaley/nc/historia-de-la-ley/{history_id}/"


def acquire_history_section(
    *, history_id: str, law_number: str, section_id: str, staging_dir: Path,
    transport: httpx.BaseTransport | None = None,
) -> BCNHistoryArtifact:
    """Acquire one public BCN section using the site's published XAJAX contract."""
    if not section_id or any(part not in "0123456789-" for part in section_id):
        raise BCNHistoryError("BCN history section id is invalid")
    url = canonical_history_url(history_id)
    with httpx.Client(timeout=20, follow_redirects=True, transport=transport) as client:
        # Establishing this public page is needed for the server-side section context.
        root = client.get(url, headers={"User-Agent": "DatosEnOrden-Legislative-Discovery/0.1"})
        root.raise_for_status()
        if f"Historia de la Ley N° {law_number}" not in root.text:
            raise BCNHistoryError("BCN history identity cannot be demonstrated")
        response = client.post(
            url,
            data={
                "xajax": "verTextoCompleto",
                "xajaxr": str(int(datetime.now(UTC).timestamp() * 1000)),
                "xajaxargs[]": section_id,
            },
            headers={
                "User-Agent": "DatosEnOrden-Legislative-Discovery/0.1",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        response.raise_for_status()
    content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
    if content_type != "text/xml" or "modal-body" not in response.text:
        raise BCNHistoryError("BCN section response is not the expected official document")
    return _stage(response.content, url, law_number, history_id, section_id, content_type, staging_dir)


def _stage(
    content: bytes, official_url: str, law_number: str, history_id: str,
    section_id: str, content_type: str, staging_dir: Path,
) -> BCNHistoryArtifact:
    digest = sha256(content).hexdigest()
    staging_dir.mkdir(parents=True, exist_ok=True)
    target = staging_dir / f"{digest}.artifact"
    if not target.exists():
        with NamedTemporaryFile(mode="wb", dir=staging_dir, prefix=".bcn-", suffix=".partial", delete=False) as handle:
            handle.write(content)
            partial = Path(handle.name)
        partial.replace(target)
    return BCNHistoryArtifact(
        official_url, law_number, history_id, section_id, datetime.now(UTC), digest,
        len(content), content_type, target,
    )
