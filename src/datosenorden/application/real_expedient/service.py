from __future__ import annotations

import json
from dataclasses import asdict
from hashlib import sha256

from datosenorden.application.provenance.models import ProvenanceClass

from .models import ExpedientSpecification, ExpedientStatus, ProvisioningResult, StoredExpedient
from .ports import ExpedientRepository, ReferenceEligibilityPort


class ExpedientConflictError(RuntimeError):
    pass


class ExpedientReferenceError(ValueError):
    pass


class ExpedientProvisioningService:
    def __init__(
        self, repository: ExpedientRepository, eligibility: ReferenceEligibilityPort
    ) -> None:
        self._repository = repository
        self._eligibility = eligibility

    def create_if_absent(self, specification: ExpedientSpecification) -> ProvisioningResult:
        if specification.version != 1:
            raise ValueError("initial expedient provision must use version 1")
        self._validate(specification)
        fingerprint = content_fingerprint(specification)
        existing = self._repository.get(specification.expedient_id)
        if existing is not None:
            if existing.content_fingerprint != fingerprint:
                raise ExpedientConflictError(
                    "expedient id already exists with incompatible content"
                )
            return ProvisioningResult(existing, created=False)
        return ProvisioningResult(self._repository.insert(specification, fingerprint), created=True)

    def revise(
        self, specification: ExpedientSpecification, *, expected_current_version: int
    ) -> StoredExpedient:
        self._validate(specification)
        existing = self._repository.get(specification.expedient_id)
        if existing is None:
            raise ExpedientConflictError("cannot revise an expedient that does not exist")
        if existing.specification.version != expected_current_version:
            raise ExpedientConflictError("expedient version conflict")
        if specification.version != expected_current_version + 1:
            raise ExpedientConflictError("revision must increment version by one")
        return self._repository.append_version(
            specification,
            content_fingerprint(specification),
            expected_current_version=expected_current_version,
        )

    def get(self, expedient_id: str) -> StoredExpedient | None:
        return self._repository.get(expedient_id)

    def list_public(self) -> tuple[StoredExpedient, ...]:
        return tuple(
            item
            for item in self._repository.list_public()
            if item.specification.status is ExpedientStatus.PUBLISHED
        )

    def _validate(self, specification: ExpedientSpecification) -> None:
        if specification.provenance_class is not ProvenanceClass.REAL:
            return
        if (
            not specification.references.claim_ids
            or not specification.references.evidence_ids
            or not specification.references.source_ids
        ):
            raise ExpedientReferenceError(
                "REAL expedients require claim, evidence, and source references"
            )
        for kind, values in specification.references.by_kind().items():
            for reference_id in values:
                eligibility = self._eligibility.classify(kind, reference_id)
                if (
                    eligibility.provenance_class is not ProvenanceClass.REAL
                    or not eligibility.public_usable
                ):
                    raise ExpedientReferenceError(
                        f"REAL expedient reference is not REAL usable: {kind.value}"
                    )


def content_fingerprint(specification: ExpedientSpecification) -> str:
    payload = asdict(specification)
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode(
        "utf-8"
    )
    return sha256(encoded).hexdigest()
