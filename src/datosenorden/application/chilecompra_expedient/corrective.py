"""Idempotent corrective version orchestration for validated ChileCompra content."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum

from datosenorden.application.real_expedient.composition import (
    HistoricalEnrichmentSnapshot,
    compose_versioned_enrichment,
)
from datosenorden.application.real_expedient.models import StoredExpedient
from datosenorden.application.real_expedient.service import (
    ExpedientConflictError,
    ExpedientProvisioningService,
    content_fingerprint,
)

from .adapters import ChileCompraCanonicalIdentityResolver, ChileCompraValidatedContent, build_chilecompra_input
from .generator import build_chilecompra_expedient_candidate


class CorrectiveStatus(StrEnum):
    CREATED = "created_corrective_version"
    ALREADY_CORRECT = "already_correct"
    CONFLICT = "conflict"


@dataclass(frozen=True)
class CorrectiveResult:
    status: CorrectiveStatus
    expedient: StoredExpedient


def repair_chilecompra_expedient(
    content: ChileCompraValidatedContent,
    *,
    expected_current_version: int,
    service: ExpedientProvisioningService,
    identity_resolver: ChileCompraCanonicalIdentityResolver,
    enrichment: HistoricalEnrichmentSnapshot | None = None,
) -> CorrectiveResult:
    """Append one clean corrective version, or prove the current version already matches."""
    generated = build_chilecompra_expedient_candidate(build_chilecompra_input(content, identity_resolver))
    current = service.get(generated.expedient_id)
    if current is None:
        raise ExpedientConflictError("corrective repair requires an existing expedient")
    target = replace(generated, version=expected_current_version + 1)
    if enrichment is not None:
        target = compose_versioned_enrichment(target, enrichment, version=target.version)
    if current.specification.version == target.version and current.content_fingerprint == content_fingerprint(target):
        return CorrectiveResult(CorrectiveStatus.ALREADY_CORRECT, current)
    if current.specification.version != expected_current_version:
        raise ExpedientConflictError("expedient version conflict")
    return CorrectiveResult(CorrectiveStatus.CREATED, service.revise(target, expected_current_version=expected_current_version))
