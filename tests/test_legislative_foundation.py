from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pytest

from datosenorden.adapters.legislature.candidate_discovery import assess_known_resources
from datosenorden.adapters.legislature.foundation import (
    AcquisitionManifest,
    AcquisitionMethod,
    AcquisitionState,
    DiscoveryQuery,
    IdentityConfidence,
    LegislativeFoundationError,
    OfficialLegislativeAcquisitionClient,
    OfficialResourceDescriptor,
    classify_change,
    validate_descriptor,
)
from datosenorden.application.legislative_discovery.assessment import (
    CandidateEvidence,
    EvidenceSufficiency,
    ProvisionRecommendation,
    assess_candidate,
)


def _descriptor(**overrides: object) -> OfficialResourceDescriptor:
    values: dict[str, object] = {
        "source_id": "senado",
        "stable_identity": "boletin:15975-25",
        "resource_type": "project_xml",
        "official_url": "https://tramitacion.senado.cl/wspublico/tramitacion.php?boletin=15975",
        "acquisition_method": AcquisitionMethod.STRUCTURED_ENDPOINT,
        "expected_content_types": ("application/xml",),
        "identity_confidence": IdentityConfidence.EXACT,
    }
    values.update(overrides)
    return OfficialResourceDescriptor(**values)  # type: ignore[arg-type]


def test_registry_rejects_non_official_or_unregistered_resources() -> None:
    with pytest.raises(LegislativeFoundationError):
        validate_descriptor(_descriptor(official_url="https://example.invalid/data.xml"))
    with pytest.raises(LegislativeFoundationError):
        validate_descriptor(_descriptor(resource_type="unknown"))


def test_bounded_acquisition_hashes_and_reuses_artifact(tmp_path) -> None:  # type: ignore[no-untyped-def]
    def responder(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "tramitacion.senado.cl"
        return httpx.Response(200, headers={"content-type": "application/xml"}, content=b"<project />")

    client = OfficialLegislativeAcquisitionClient(staging_dir=tmp_path, transport=httpx.MockTransport(responder))
    first = client.acquire(_descriptor())
    second = client.acquire(_descriptor())
    assert first.manifest.sha256 == second.manifest.sha256
    assert first.manifest.byte_count == 11
    assert second.reused_staged_file is True
    assert first.staging_path.exists()


def test_acquisition_fails_closed_for_content_type_and_oversized_payload(tmp_path) -> None:  # type: ignore[no-untyped-def]
    html = OfficialLegislativeAcquisitionClient(
        staging_dir=tmp_path,
        transport=httpx.MockTransport(lambda request: httpx.Response(200, headers={"content-type": "text/html"}, content=b"<html/>")),
    )
    with pytest.raises(LegislativeFoundationError):
        html.acquire(_descriptor())
    huge = OfficialLegislativeAcquisitionClient(
        staging_dir=tmp_path,
        transport=httpx.MockTransport(lambda request: httpx.Response(200, headers={"content-type": "application/xml", "content-length": str(99_999_999)}, content=b"x")),
    )
    with pytest.raises(LegislativeFoundationError):
        huge.acquire(_descriptor())


def test_acquisition_rejects_redirect_outside_official_allowlist(tmp_path) -> None:  # type: ignore[no-untyped-def]
    def responder(request: httpx.Request) -> httpx.Response:
        if request.url.host == "tramitacion.senado.cl":
            return httpx.Response(302, headers={"location": "https://example.invalid/file.xml"}, request=request)
        return httpx.Response(200, headers={"content-type": "application/xml"}, content=b"<project />", request=request)

    client = OfficialLegislativeAcquisitionClient(staging_dir=tmp_path, transport=httpx.MockTransport(responder))
    with pytest.raises(LegislativeFoundationError):
        client.acquire(_descriptor())


def test_discovery_is_identity_first_and_never_fuzzy() -> None:
    query = DiscoveryQuery("senado", "boletin:15975-25", "project_xml", "inteligencia economica")
    other = _descriptor(stable_identity="boletin:15975-26")
    result = assess_known_resources(query, (other,))
    assert result.confidence is IdentityConfidence.NONE
    assert result.resources == ()


def test_change_detection_and_temporal_status_are_explicit() -> None:
    initial = AcquisitionManifest("senado", "boletin:15975-25", "https://tramitacion.senado.cl/a", datetime(2026, 8, 1, tzinfo=UTC), "application/xml", 1, "a" * 64, AcquisitionMethod.STRUCTURED_ENDPOINT, 200)
    unchanged = AcquisitionManifest("senado", "boletin:15975-25", "https://tramitacion.senado.cl/a", datetime(2026, 8, 2, tzinfo=UTC), "application/xml", 1, "a" * 64, AcquisitionMethod.STRUCTURED_ENDPOINT, 200)
    changed = AcquisitionManifest("senado", "boletin:15975-25", "https://tramitacion.senado.cl/a", datetime(2026, 8, 3, tzinfo=UTC), "application/xml", 2, "b" * 64, AcquisitionMethod.STRUCTURED_ENDPOINT, 200)
    assert classify_change(initial, unchanged).acquisition_state is AcquisitionState.UNCHANGED
    event = classify_change(unchanged, changed)
    assert event.acquisition_state is AcquisitionState.CHANGED
    assert event.future_gate.value == "REVIEW_REQUIRED"


def test_candidate_assessment_requires_identity_and_evidence() -> None:
    strong = assess_candidate(CandidateEvidence("pension", ("senado", "leychile"), 3, 2, IdentityConfidence.EXACT, "HIGH", True, True, 0))
    assert strong.evidence_sufficiency is EvidenceSufficiency.STRONG
    assert strong.recommendation is ProvisionRecommendation.PROVISION
    blocked = assess_candidate(CandidateEvidence("ambiguous", ("senado",), 4, 2, IdentityConfidence.POSSIBLE, "HIGH", True, True, 0))
    assert blocked.evidence_sufficiency is EvidenceSufficiency.NOT_READY
    assert blocked.recommendation is ProvisionRecommendation.NOT_READY


def test_foundation_has_no_database_dependency() -> None:
    import datosenorden.adapters.legislature.foundation as foundation

    assert "datosenorden.db" not in foundation.__file__ and foundation.__file__ is not None
    assert "datosenorden.db" not in open(foundation.__file__, encoding="utf-8").read()
