"""Safe, read-only foundation for deterministic official legislative resources.

This module intentionally stops before persistence, fact extraction, or publication.
It provides the common contracts shared by Senate, Chamber and LeyChile resources.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from hashlib import sha256
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import urlparse

import httpx


class LegislativeFoundationError(RuntimeError):
    """Raised for rejected official resources without leaking operational details."""


class IdentityConfidence(StrEnum):
    EXACT = "EXACT"
    STRONG = "STRONG"
    POSSIBLE = "POSSIBLE"
    NONE = "NONE"
    AMBIGUOUS = "AMBIGUOUS"


class AcquisitionMethod(StrEnum):
    STRUCTURED_ENDPOINT = "STRUCTURED_ENDPOINT"
    MACHINE_READABLE_RESOURCE = "MACHINE_READABLE_RESOURCE"
    DETERMINISTIC_DOCUMENT = "DETERMINISTIC_DOCUMENT"


class AcquisitionState(StrEnum):
    UNCHANGED = "UNCHANGED"
    CHANGED = "CHANGED"
    UNAVAILABLE = "UNAVAILABLE"
    INVALID = "INVALID"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


class LegislativeStatus(StrEnum):
    PROPOSED = "PROPOSED"
    IN_DISCUSSION = "IN_DISCUSSION"
    APPROVED_BY_CHAMBER = "APPROVED_BY_CHAMBER"
    APPROVED_BY_CONGRESS = "APPROVED_BY_CONGRESS"
    PROMULGATED = "PROMULGATED"
    PUBLISHED = "PUBLISHED"
    IN_FORCE = "IN_FORCE"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"
    UNKNOWN = "UNKNOWN"


class ChangeKind(StrEnum):
    MINOR_CHANGE = "MINOR_CHANGE"
    MEANINGFUL_CHANGE = "MEANINGFUL_CHANGE"
    MAJOR_CHANGE = "MAJOR_CHANGE"


class FutureAutomationGate(StrEnum):
    AUTO_PUBLISH_ELIGIBLE = "AUTO_PUBLISH_ELIGIBLE"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class OfficialSourceAdapter:
    """Declarative registry entry, not an executable or a persistence adapter."""

    source_id: str
    authority: str
    base_domain: str
    allowed_hosts: tuple[str, ...]
    resource_types: tuple[str, ...]
    acquisition_methods: tuple[AcquisitionMethod, ...]
    identity_scheme: str
    update_strategy: str
    rate_limit_policy: str
    timeout_seconds: float
    max_payload_bytes: int
    provenance_eligible: bool
    public_usability_requirements: tuple[str, ...]
    access_notes: str


LEGISLATIVE_SOURCE_REGISTRY: tuple[OfficialSourceAdapter, ...] = (
    OfficialSourceAdapter(
        source_id="senado",
        authority="Senado de la Republica de Chile",
        base_domain="senado.cl",
        allowed_hosts=("tramitacion.senado.cl", "www.senado.cl", "microservicio-documentos.senado.cl"),
        resource_types=("project_xml", "legislative_document", "session_record", "official_news"),
        acquisition_methods=(AcquisitionMethod.STRUCTURED_ENDPOINT, AcquisitionMethod.DETERMINISTIC_DOCUMENT),
        identity_scheme="bulletin number; Senate document id",
        update_strategy="re-fetch an explicitly known bulletin or document identity",
        rate_limit_policy="one bounded request per explicit resource; no crawling",
        timeout_seconds=20.0,
        max_payload_bytes=16 * 1024 * 1024,
        provenance_eligible=True,
        public_usability_requirements=("official host", "stable identity", "successful content validation", "explicit provenance decision"),
        access_notes="Official public legislative-tracking resources only.",
    ),
    OfficialSourceAdapter(
        source_id="camara",
        authority="Camara de Diputadas y Diputados de Chile",
        base_domain="camara.cl",
        allowed_hosts=("opendata.camara.cl", "www.camara.cl", "extranet.camara.cl"),
        resource_types=("vote_xml", "bill_page", "commission_document"),
        acquisition_methods=(AcquisitionMethod.STRUCTURED_ENDPOINT, AcquisitionMethod.DETERMINISTIC_DOCUMENT),
        identity_scheme="bulletin number; official vote or document identifier",
        update_strategy="re-fetch an explicitly known bulletin or official document identity",
        rate_limit_policy="one bounded request per explicit resource; no crawling",
        timeout_seconds=20.0,
        max_payload_bytes=16 * 1024 * 1024,
        provenance_eligible=True,
        public_usability_requirements=("official host", "stable identity", "successful content validation", "explicit provenance decision"),
        access_notes="Official open-data and public legislative resources only.",
    ),
    OfficialSourceAdapter(
        source_id="leychile",
        authority="Biblioteca del Congreso Nacional de Chile",
        base_domain="bcn.cl",
        allowed_hosts=("www.bcn.cl",),
        resource_types=("law_text", "law_history", "ley_facil_guide", "implementation_rule"),
        acquisition_methods=(AcquisitionMethod.MACHINE_READABLE_RESOURCE, AcquisitionMethod.DETERMINISTIC_DOCUMENT),
        identity_scheme="idNorma; idVersion; published guide URI",
        update_strategy="re-fetch an explicitly known LeyChile identity or guide URI",
        rate_limit_policy="one bounded request per explicit resource; no crawling",
        timeout_seconds=20.0,
        max_payload_bytes=16 * 1024 * 1024,
        provenance_eligible=True,
        public_usability_requirements=("official host", "stable identity", "successful content validation", "explicit provenance decision"),
        access_notes="Official BCN/LeyChile resources only.",
    ),
)


@dataclass(frozen=True)
class DiscoveryQuery:
    source_id: str
    stable_identity: str
    resource_type: str
    topic: str


@dataclass(frozen=True)
class OfficialResourceDescriptor:
    source_id: str
    stable_identity: str
    resource_type: str
    official_url: str
    acquisition_method: AcquisitionMethod
    expected_content_types: tuple[str, ...]
    identity_confidence: IdentityConfidence
    title: str = ""
    event_date: datetime | None = None
    effective_date: datetime | None = None
    status: LegislativeStatus = LegislativeStatus.UNKNOWN
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class AcquisitionManifest:
    source_id: str
    stable_identity: str
    official_url: str
    retrieved_at: datetime
    content_type: str
    byte_count: int
    sha256: str
    acquisition_method: AcquisitionMethod
    http_status: int
    parser_version: str | None = None


@dataclass(frozen=True)
class AcquiredArtifact:
    descriptor: OfficialResourceDescriptor
    manifest: AcquisitionManifest
    staging_path: Path
    reused_staged_file: bool


@dataclass(frozen=True)
class ChangeEvent:
    stable_identity: str
    acquisition_state: AcquisitionState
    prior_sha256: str | None
    current_sha256: str | None
    kind: ChangeKind | None
    future_gate: FutureAutomationGate


def source_for(source_id: str) -> OfficialSourceAdapter:
    for source in LEGISLATIVE_SOURCE_REGISTRY:
        if source.source_id == source_id:
            return source
    raise LegislativeFoundationError("unknown legislative source")


def validate_descriptor(descriptor: OfficialResourceDescriptor) -> OfficialSourceAdapter:
    source = source_for(descriptor.source_id)
    parsed = urlparse(descriptor.official_url)
    if parsed.scheme != "https" or parsed.hostname not in source.allowed_hosts:
        raise LegislativeFoundationError("official resource is outside the source allowlist")
    if descriptor.resource_type not in source.resource_types:
        raise LegislativeFoundationError("resource type is not registered for this source")
    if descriptor.acquisition_method not in source.acquisition_methods:
        raise LegislativeFoundationError("acquisition method is not registered for this source")
    if not descriptor.stable_identity.strip():
        raise LegislativeFoundationError("official resource requires a stable identity")
    return source


def classify_change(previous: AcquisitionManifest | None, current: AcquisitionManifest) -> ChangeEvent:
    if previous is None:
        return ChangeEvent(current.stable_identity, AcquisitionState.CHANGED, None, current.sha256, ChangeKind.MEANINGFUL_CHANGE, FutureAutomationGate.REVIEW_REQUIRED)
    if previous.sha256 == current.sha256:
        return ChangeEvent(current.stable_identity, AcquisitionState.UNCHANGED, previous.sha256, current.sha256, None, FutureAutomationGate.REVIEW_REQUIRED)
    return ChangeEvent(current.stable_identity, AcquisitionState.CHANGED, previous.sha256, current.sha256, ChangeKind.MEANINGFUL_CHANGE, FutureAutomationGate.REVIEW_REQUIRED)


class OfficialLegislativeAcquisitionClient:
    """Bounded, deterministic acquisition for pre-validated official descriptors."""

    def __init__(self, *, staging_dir: Path, transport: httpx.BaseTransport | None = None) -> None:
        self._staging_dir = staging_dir
        self._transport = transport

    def acquire(self, descriptor: OfficialResourceDescriptor) -> AcquiredArtifact:
        source = validate_descriptor(descriptor)
        self._staging_dir.mkdir(parents=True, exist_ok=True)
        temporary: Path | None = None
        try:
            with httpx.Client(timeout=source.timeout_seconds, follow_redirects=True, transport=self._transport) as client:
                with client.stream("GET", descriptor.official_url, headers={"Accept": ", ".join(descriptor.expected_content_types) or "*/*", "User-Agent": "DatosEnOrden-Legislative-Discovery/0.1"}) as response:
                    response.raise_for_status()
                    final_descriptor = OfficialResourceDescriptor(**{**descriptor.__dict__, "official_url": str(response.url)})
                    validate_descriptor(final_descriptor)
                    content_type = _content_type(response.headers.get("content-type"))
                    if descriptor.expected_content_types and content_type not in descriptor.expected_content_types:
                        raise LegislativeFoundationError("official resource has an unexpected content type")
                    declared_size = response.headers.get("content-length")
                    if declared_size and int(declared_size) > source.max_payload_bytes:
                        raise LegislativeFoundationError("official resource exceeds payload limit")
                    digest, byte_count = sha256(), 0
                    with NamedTemporaryFile(mode="wb", dir=self._staging_dir, prefix=".legislative-", suffix=".partial", delete=False) as handle:
                        temporary = Path(handle.name)
                        for chunk in response.iter_bytes():
                            byte_count += len(chunk)
                            if byte_count > source.max_payload_bytes:
                                raise LegislativeFoundationError("official resource exceeds payload limit")
                            digest.update(chunk)
                            handle.write(chunk)
        except (httpx.HTTPError, ValueError) as exc:
            if temporary:
                temporary.unlink(missing_ok=True)
            raise LegislativeFoundationError("official legislative acquisition failed") from exc
        except Exception:
            if temporary:
                temporary.unlink(missing_ok=True)
            raise
        assert temporary is not None
        target = self._staging_dir / f"{digest.hexdigest()}.artifact"
        reused = target.exists()
        if reused:
            temporary.unlink(missing_ok=True)
        else:
            temporary.replace(target)
        manifest = AcquisitionManifest(
            source_id=descriptor.source_id,
            stable_identity=descriptor.stable_identity,
            official_url=str(response.url),
            retrieved_at=datetime.now(UTC),
            content_type=content_type,
            byte_count=byte_count,
            sha256=digest.hexdigest(),
            acquisition_method=descriptor.acquisition_method,
            http_status=response.status_code,
        )
        return AcquiredArtifact(descriptor, manifest, target, reused)


def _content_type(value: str | None) -> str:
    return (value or "").split(";", 1)[0].strip().lower()
