from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from datosenorden.application.provenance.models import ProvenanceClass


class ExpedientStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    WITHDRAWN = "withdrawn"


class EpistemicClass(StrEnum):
    FACT = "FACT"
    SUPPORTED_INFERENCE = "SUPPORTED_INFERENCE"
    OPEN_QUESTION = "OPEN_QUESTION"
    UNKNOWN = "UNKNOWN"


class ReferenceKind(StrEnum):
    CLAIM = "claim"
    EVIDENCE = "evidence"
    RELATIONSHIP = "relationship"
    ENTITY = "entity"
    DOCUMENT = "document"
    SOURCE = "source"


@dataclass(frozen=True)
class ExpedientReferences:
    claim_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    relationship_ids: tuple[str, ...] = ()
    entity_ids: tuple[str, ...] = ()
    document_ids: tuple[str, ...] = ()
    source_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for values in self.by_kind().values():
            if len(values) != len(set(values)) or any(not value.strip() for value in values):
                raise ValueError("expedient references must be non-empty and unique by kind")

    def by_kind(self) -> dict[ReferenceKind, tuple[str, ...]]:
        return {
            ReferenceKind.CLAIM: self.claim_ids,
            ReferenceKind.EVIDENCE: self.evidence_ids,
            ReferenceKind.RELATIONSHIP: self.relationship_ids,
            ReferenceKind.ENTITY: self.entity_ids,
            ReferenceKind.DOCUMENT: self.document_ids,
            ReferenceKind.SOURCE: self.source_ids,
        }


@dataclass(frozen=True)
class NarrativeStatement:
    statement_id: str
    section: str
    text: str
    epistemic_class: EpistemicClass
    claim_ids: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.statement_id.strip() or not self.section.strip() or not self.text.strip():
            raise ValueError("narrative statements require id, section, and text")
        if self.epistemic_class in {
            EpistemicClass.FACT,
            EpistemicClass.SUPPORTED_INFERENCE,
        } and not (self.claim_ids or self.evidence_ids):
            raise ValueError("factual or inferred statements require claim or evidence support")


@dataclass(frozen=True)
class ExpedientSpecification:
    expedient_id: str
    title: str
    question: str
    summary: str
    provenance_class: ProvenanceClass
    status: ExpedientStatus
    version: int
    references: ExpedientReferences
    statements: tuple[NarrativeStatement, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.provenance_class, ProvenanceClass):
            raise ValueError("expedient provenance must be explicit")
        if not all(
            value.strip() for value in (self.expedient_id, self.title, self.question, self.summary)
        ):
            raise ValueError("expedient id, title, question, and summary are required")
        if self.version < 1:
            raise ValueError("expedient version must be positive")
        statement_ids = tuple(item.statement_id for item in self.statements)
        if len(statement_ids) != len(set(statement_ids)):
            raise ValueError("narrative statement ids must be unique")
        known_claims = set(self.references.claim_ids)
        known_evidence = set(self.references.evidence_ids)
        for statement in self.statements:
            if (
                not set(statement.claim_ids) <= known_claims
                or not set(statement.evidence_ids) <= known_evidence
            ):
                raise ValueError(
                    "narrative support must reference content included in the expedient version"
                )


@dataclass(frozen=True)
class StoredExpedient:
    specification: ExpedientSpecification
    content_fingerprint: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class ProvisioningResult:
    expedient: StoredExpedient
    created: bool
