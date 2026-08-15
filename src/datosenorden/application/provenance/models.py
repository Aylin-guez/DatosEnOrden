from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ProvenanceClass(StrEnum):
    REAL = "REAL"
    DEMO = "DEMO"
    TEST = "TEST"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class ProvenanceDecision:
    provenance_class: ProvenanceClass
    source_label: str
    dataset_identifier: str
    record_scope: str
    public_countable: bool
    evidence_basis: str
    reason: str
    confidence: str


@dataclass(frozen=True)
class ProvenanceManifestEntry:
    source_name: str
    dataset_name: str
    dataset_version: str
    provenance_class: ProvenanceClass
    source_label: str
    dataset_identifier: str
    record_scope: str
    public_countable: bool
    evidence_basis: str
    reason: str
    confidence: str


@dataclass(frozen=True)
class ProvenanceSnapshot:
    counts: dict[str, dict[str, int]]
    lifecycle: dict[str, dict[str, int]]
    source_metrics: tuple[dict[str, object], ...]

    def count(self, content_type: str, provenance_class: ProvenanceClass) -> int:
        return int(self.counts.get(content_type, {}).get(provenance_class.value, 0))
