"""Explicit composition of a regenerated base with certified historical enrichment."""

from __future__ import annotations

from dataclasses import dataclass

from .models import ExpedientReferences, ExpedientSpecification, NarrativeStatement, StoredExpedient


class ExpedientCompositionError(ValueError):
    pass


@dataclass(frozen=True)
class HistoricalEnrichmentSnapshot:
    """Components added by one certified version over its exact base version."""

    expedient_id: str
    base_version: int
    enrichment_version: int
    references: ExpedientReferences
    statements: tuple[NarrativeStatement, ...]


def extract_historical_enrichment(
    base: StoredExpedient, enriched: StoredExpedient
) -> HistoricalEnrichmentSnapshot:
    """Extract only persisted additions; ownership comes from version boundaries, never text."""
    base_spec = base.specification
    enriched_spec = enriched.specification
    if (
        base_spec.expedient_id != enriched_spec.expedient_id
        or base_spec.provenance_class != enriched_spec.provenance_class
        or enriched_spec.version != base_spec.version + 1
    ):
        raise ExpedientCompositionError("historical versions are not a composable lineage")
    references = ExpedientReferences(**{
        field: _added(getattr(base_spec.references, field), getattr(enriched_spec.references, field))
        for field in ("claim_ids", "evidence_ids", "relationship_ids", "entity_ids", "document_ids", "source_ids")
    })
    base_ids = {statement.statement_id for statement in base_spec.statements}
    statements = tuple(statement for statement in enriched_spec.statements if statement.statement_id not in base_ids)
    _validate_enrichment(references, statements)
    return HistoricalEnrichmentSnapshot(
        enriched_spec.expedient_id, base_spec.version, enriched_spec.version, references, statements
    )


def compose_versioned_enrichment(
    base: ExpedientSpecification,
    enrichment: HistoricalEnrichmentSnapshot,
    *,
    version: int,
) -> ExpedientSpecification:
    """Compose a new version without inheriting historical title, question, or summary."""
    if base.expedient_id != enrichment.expedient_id:
        raise ExpedientCompositionError("base and enrichment identity differ")
    if version < 1:
        raise ExpedientCompositionError("composed version must be positive")
    refs = ExpedientReferences(**{
        field: _merge(getattr(base.references, field), getattr(enrichment.references, field))
        for field in ("claim_ids", "evidence_ids", "relationship_ids", "entity_ids", "document_ids", "source_ids")
    })
    base_ids = {statement.statement_id for statement in base.statements}
    if base_ids & {statement.statement_id for statement in enrichment.statements}:
        raise ExpedientCompositionError("enrichment statement duplicates base statement")
    return ExpedientSpecification(
        base.expedient_id, base.title, base.question, base.summary,
        base.provenance_class, base.status, version, refs, base.statements + enrichment.statements,
    )


def _added(base: tuple[str, ...], enriched: tuple[str, ...]) -> tuple[str, ...]:
    if not set(base) <= set(enriched):
        raise ExpedientCompositionError("historical enrichment removed a base reference")
    return tuple(item for item in enriched if item not in set(base))


def _merge(base: tuple[str, ...], enrichment: tuple[str, ...]) -> tuple[str, ...]:
    if set(base) & set(enrichment):
        raise ExpedientCompositionError("enrichment duplicates base reference")
    return base + enrichment


def _validate_enrichment(
    references: ExpedientReferences, statements: tuple[NarrativeStatement, ...]
) -> None:
    known_claims = set(references.claim_ids)
    known_evidence = set(references.evidence_ids)
    for statement in statements:
        if not set(statement.claim_ids) <= known_claims or not set(statement.evidence_ids) <= known_evidence:
            raise ExpedientCompositionError("enrichment support reaches outside enrichment references")
