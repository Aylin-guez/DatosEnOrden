from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from datosenorden.application.provenance.models import ProvenanceClass

from .models import ExpedientSpecification, ReferenceKind, StoredExpedient


class ExpedientRepository(Protocol):
    def get(self, expedient_id: str) -> StoredExpedient | None: ...

    def insert(
        self, specification: ExpedientSpecification, content_fingerprint: str
    ) -> StoredExpedient: ...

    def append_version(
        self,
        specification: ExpedientSpecification,
        content_fingerprint: str,
        *,
        expected_current_version: int,
    ) -> StoredExpedient: ...

    def list_public(self) -> tuple[StoredExpedient, ...]: ...


@dataclass(frozen=True)
class ReferenceEligibility:
    provenance_class: ProvenanceClass
    public_usable: bool


class ReferenceEligibilityPort(Protocol):
    def classify(self, kind: ReferenceKind, reference_id: str) -> ReferenceEligibility: ...
