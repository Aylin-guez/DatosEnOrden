from __future__ import annotations

from datosenorden.application.provenance.models import ProvenanceClass
from datosenorden.application.public_deployment.sanitization import public_opaque_reference

from .models import ExpedientStatus, StoredExpedient


def public_expedient_projection(expedient: StoredExpedient) -> dict[str, object]:
    specification = expedient.specification
    if specification.status is not ExpedientStatus.PUBLISHED:
        raise ValueError("only published expedients have a public projection")
    if specification.provenance_class not in {ProvenanceClass.REAL, ProvenanceClass.DEMO}:
        raise ValueError("only REAL or DEMO expedients have a public projection")
    references = specification.references
    return {
        "id": public_opaque_reference(specification.expedient_id),
        "title": public_opaque_reference(specification.title),
        "question": public_opaque_reference(specification.question),
        "summary": public_opaque_reference(specification.summary),
        "provenance_class": specification.provenance_class.value,
        "status": specification.status.value,
        "version": specification.version,
        "references": {
            "claims": _safe_ids(references.claim_ids),
            "evidences": _safe_ids(references.evidence_ids),
            "relationships": _safe_ids(references.relationship_ids),
            "entities": _safe_ids(references.entity_ids),
            "documents": _safe_ids(references.document_ids),
            "sources": _safe_ids(references.source_ids),
        },
        "statements": [
            {
                "id": public_opaque_reference(item.statement_id),
                "section": public_opaque_reference(item.section),
                "text": public_opaque_reference(item.text),
                "epistemic_class": item.epistemic_class.value,
                "claim_ids": _safe_ids(item.claim_ids),
                "evidence_ids": _safe_ids(item.evidence_ids),
            }
            for item in specification.statements
        ],
        "created_at": expedient.created_at.isoformat(),
        "updated_at": expedient.updated_at.isoformat(),
    }


def _safe_ids(values: tuple[str, ...]) -> list[str]:
    return [safe for value in values if (safe := public_opaque_reference(value))]
