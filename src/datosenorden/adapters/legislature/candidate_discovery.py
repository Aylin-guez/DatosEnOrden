"""Deterministic legislative discovery over explicitly known official identities."""

from __future__ import annotations

from dataclasses import dataclass

from .foundation import DiscoveryQuery, IdentityConfidence, OfficialResourceDescriptor


@dataclass(frozen=True)
class DiscoveryResult:
    query: DiscoveryQuery
    confidence: IdentityConfidence
    resources: tuple[OfficialResourceDescriptor, ...]
    review_required: bool
    reason: str


def assess_known_resources(query: DiscoveryQuery, resources: tuple[OfficialResourceDescriptor, ...]) -> DiscoveryResult:
    """Classify supplied official resources without name matching or network search."""
    matching = tuple(resource for resource in resources if resource.stable_identity == query.stable_identity and resource.source_id == query.source_id)
    if not matching:
        return DiscoveryResult(query, IdentityConfidence.NONE, (), False, "No resource matched the explicit official identity.")
    confidences = {resource.identity_confidence for resource in matching}
    if IdentityConfidence.AMBIGUOUS in confidences:
        return DiscoveryResult(query, IdentityConfidence.AMBIGUOUS, matching, True, "Official resources need human identity review.")
    if IdentityConfidence.POSSIBLE in confidences:
        return DiscoveryResult(query, IdentityConfidence.POSSIBLE, matching, True, "Official resources are possible only; no automatic progression.")
    confidence = IdentityConfidence.EXACT if IdentityConfidence.EXACT in confidences else IdentityConfidence.STRONG
    return DiscoveryResult(query, confidence, matching, False, "Resources match the explicit official identity.")
