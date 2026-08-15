"""Deterministic, explainable assessment for future legislative expedient review."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from datosenorden.adapters.legislature.foundation import IdentityConfidence


class EvidenceSufficiency(StrEnum):
    STRONG = "STRONG"
    ADEQUATE = "ADEQUATE"
    WEAK = "WEAK"
    NOT_READY = "NOT_READY"


class ProvisionRecommendation(StrEnum):
    PROVISION = "PROVISION"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    NOT_READY = "NOT_READY"


@dataclass(frozen=True)
class CandidateEvidence:
    candidate_id: str
    official_sources: tuple[str, ...]
    document_count: int
    event_count: int
    identity_confidence: IdentityConfidence
    current_relevance: str
    temporal_coverage: bool
    cross_source_potential: bool
    uncertainty_count: int
    duplication_risk: bool = False


@dataclass(frozen=True)
class CandidateAssessment:
    candidate_id: str
    score_version: str
    score: int
    evidence_sufficiency: EvidenceSufficiency
    recommendation: ProvisionRecommendation
    reasons: tuple[str, ...]


def assess_candidate(evidence: CandidateEvidence) -> CandidateAssessment:
    """Assess evidence conservatively; it neither creates nor updates expedients."""
    score = min(len(set(evidence.official_sources)), 4) * 2 + min(evidence.document_count, 5) + min(evidence.event_count, 3)
    score += 2 if evidence.temporal_coverage else 0
    score += 2 if evidence.cross_source_potential else 0
    score -= evidence.uncertainty_count * 2
    score -= 3 if evidence.duplication_risk else 0
    reasons = [f"official_sources={len(set(evidence.official_sources))}", f"documents={evidence.document_count}", f"events={evidence.event_count}"]
    if evidence.identity_confidence not in {IdentityConfidence.EXACT, IdentityConfidence.STRONG}:
        reasons.append("identity requires review")
        return CandidateAssessment(evidence.candidate_id, "legislative-candidate-v0.1", max(score, 0), EvidenceSufficiency.NOT_READY, ProvisionRecommendation.NOT_READY, tuple(reasons))
    if evidence.document_count >= 2 and evidence.temporal_coverage and evidence.uncertainty_count == 0:
        sufficiency = EvidenceSufficiency.STRONG if len(set(evidence.official_sources)) >= 2 else EvidenceSufficiency.ADEQUATE
        recommendation = ProvisionRecommendation.PROVISION if sufficiency is EvidenceSufficiency.STRONG else ProvisionRecommendation.REVIEW_REQUIRED
        return CandidateAssessment(evidence.candidate_id, "legislative-candidate-v0.1", max(score, 0), sufficiency, recommendation, tuple(reasons))
    if evidence.document_count >= 1:
        return CandidateAssessment(evidence.candidate_id, "legislative-candidate-v0.1", max(score, 0), EvidenceSufficiency.ADEQUATE, ProvisionRecommendation.REVIEW_REQUIRED, tuple(reasons))
    return CandidateAssessment(evidence.candidate_id, "legislative-candidate-v0.1", max(score, 0), EvidenceSufficiency.WEAK, ProvisionRecommendation.NOT_READY, tuple(reasons))
