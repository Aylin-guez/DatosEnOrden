from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


LABORATORY_EXPEDIENT_ID = "EXP-001"


@dataclass(frozen=True)
class Problem:
    id: str
    title: str
    description: str
    scope: str
    affected_population: str
    territory: str
    period: str
    status: str


@dataclass(frozen=True)
class Hypothesis:
    id: str
    title: str
    summary: str
    mechanism: str
    expected_benefits: tuple[str, ...]
    risks: tuple[str, ...]
    maturity: str
    status: str
    public_origin_type: str


@dataclass(frozen=True)
class EvidenceItem:
    id: str
    title: str
    type: str
    source: str
    fragment_reference: str
    status: str
    limitations: str
    related_claim_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class Claim:
    id: str
    text: str
    type: str
    status: str
    certainty: str
    supporting_evidence_ids: tuple[str, ...] = ()
    contradicting_evidence_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class Indicator:
    id: str
    name: str
    description: str
    unit: str
    latest_value: Any
    period: str
    source: str
    status: str
    methodological_warning: str


@dataclass(frozen=True)
class Source:
    id: str
    name: str
    type: str
    issuer: str
    status: str
    authenticity: str
    availability: str
    warning: str


@dataclass(frozen=True)
class Relationship:
    id: str
    source_entity: str
    relation_type: str
    target_entity: str
    status: str
    context: str


@dataclass(frozen=True)
class Expedient:
    id: str
    title: str
    summary: str
    status: str
    problem: Problem
    scope: str
    territory: str
    period: str
    updated_at: str
    reading_progress: int
    sections: tuple[dict[str, str], ...] = ()
    hypotheses: tuple[Hypothesis, ...] = ()
    evidence_items: tuple[EvidenceItem, ...] = ()
    claims: tuple[Claim, ...] = ()
    indicators: tuple[Indicator, ...] = ()
    sources: tuple[Source, ...] = ()
    relationships: tuple[Relationship, ...] = ()
    open_questions_summary: str = ""
    participation_status: str = "LOCKED"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LaboratorySection:
    id: str
    title: str
    summary: str
    status: str = "READY"


@dataclass(frozen=True)
class ParticipationStatus:
    code: str
    label: str
    enabled: bool
