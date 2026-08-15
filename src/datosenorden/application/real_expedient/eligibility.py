"""Concrete REAL-expedient eligibility derived from provenance authority."""

from __future__ import annotations

from sqlalchemy.orm import Session

from datosenorden.application.provenance.models import ProvenanceClass
from datosenorden.application.provenance.service import (
    build_public_usable_content,
    classify_document_id,
)

from .models import ReferenceKind
from .ports import ReferenceEligibility


class ProvenanceReferenceEligibility:
    """Snapshot the authoritative public-usable references for one provision."""

    def __init__(self, session: Session) -> None:
        content = build_public_usable_content(session)
        self._real_usable = {
            ReferenceKind.CLAIM: {str(row.id) for row in content["claims"]},
            ReferenceKind.EVIDENCE: {str(row.id) for row in content["evidences"]},
            ReferenceKind.RELATIONSHIP: {
                str(row.id) for row in content["relationships"]
            },
            ReferenceKind.ENTITY: {str(value) for value in content["entity_ids"]},
            ReferenceKind.SOURCE: {str(value) for value in content["source_ids"]},
        }

    def classify(
        self, kind: ReferenceKind, reference_id: str
    ) -> ReferenceEligibility:
        if kind is ReferenceKind.DOCUMENT:
            decision = classify_document_id(reference_id)
            return ReferenceEligibility(
                provenance_class=decision.provenance_class,
                public_usable=decision.public_countable,
            )
        if str(reference_id) in self._real_usable.get(kind, set()):
            return ReferenceEligibility(ProvenanceClass.REAL, public_usable=True)
        return ReferenceEligibility(ProvenanceClass.UNKNOWN, public_usable=False)
