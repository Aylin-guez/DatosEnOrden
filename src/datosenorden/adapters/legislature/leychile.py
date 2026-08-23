"""Read-only minimum vertical slice for explicitly selected LeyChile norms."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from tempfile import NamedTemporaryFile

import httpx


class LeyChileError(RuntimeError):
    pass


@dataclass(frozen=True)
class LeyChileArtifact:
    norm_id: str
    version: str
    canonical_url: str
    retrieved_at: datetime
    sha256: str
    staging_path: Path
    payload: dict[str, object]


def canonical_url(norm_id: str, version: str) -> str:
    if not norm_id.isdigit() or len(version) != 10:
        raise LeyChileError("LeyChile norm identity is invalid")
    return f"https://www.bcn.cl/leychile/navegar?idNorma={norm_id}&idVersion={version}"


def acquire_norm(*, norm_id: str, version: str, staging_dir: Path, transport: httpx.BaseTransport | None = None) -> LeyChileArtifact:
    """Acquire exactly one canonical version through LeyChile's public JSON API."""
    url = canonical_url(norm_id, version)
    api_url = (
        "https://nuevo.leychile.cl/servicios/Navegar/get_norma_json?"
        f"idNorma={norm_id}&idVersion={version}&idLey=&tipoVersion=&cve=&agrupa_partes=1&r="
    )
    with httpx.Client(timeout=20, follow_redirects=True, transport=transport) as client:
        response = client.get(api_url, headers={"Accept": "application/json", "User-Agent": "DatosEnOrden-Legislative-Discovery/0.1"})
        response.raise_for_status()
    try:
        payload = response.json()
        metadata = payload["metadatos"]
        if str(metadata["id_norma"]) != norm_id or str(metadata["fecha_version"]) != version:
            raise KeyError("identity")
        html = payload["html"]
        if not isinstance(html, list) or not html:
            raise KeyError("html")
    except (KeyError, TypeError, ValueError) as exc:
        raise LeyChileError("LeyChile response does not prove canonical norm identity") from exc
    content = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    digest = sha256(content).hexdigest()
    staging_dir.mkdir(parents=True, exist_ok=True)
    target = staging_dir / f"{digest}.artifact"
    if not target.exists():
        with NamedTemporaryFile(mode="wb", dir=staging_dir, prefix=".leychile-", suffix=".partial", delete=False) as handle:
            handle.write(content)
            partial = Path(handle.name)
        partial.replace(target)
    return LeyChileArtifact(norm_id, version, url, datetime.now(UTC), digest, target, payload)
