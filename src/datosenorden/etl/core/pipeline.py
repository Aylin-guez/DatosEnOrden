from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from sqlalchemy.orm import Session

from datosenorden.etl.core.contracts import GraphBatch
from datosenorden.etl.loaders.graph_loader import GraphLoader


@dataclass(frozen=True)
class DatasetLoadRequest:
    dataset_id: str
    input_path: Path | None = None
    dry_run: bool = False
    metadata: dict[str, object] | None = None


@dataclass(frozen=True)
class DatasetPipelineResult:
    dataset_id: str
    loaded: bool
    dry_run: bool
    raw_count: int
    rejected_count: int
    entities: int
    claims: int
    evidence: int
    relationships: int
    errors: tuple[str, ...] = ()


class DatasetAdapter(Protocol):
    dataset_id: str

    def validate(self, request: DatasetLoadRequest) -> tuple[str, ...]:
        """Return validation errors. Empty tuple means the request can continue."""

    def normalize(self, request: DatasetLoadRequest) -> object:
        """Convert the local input into a source-specific normalized object."""

    def build_relationships(self, normalized: object) -> GraphBatch:
        """Build entities, claims, evidence and public relationships as a GraphBatch."""


def load_dataset(session: Session, adapter: DatasetAdapter, request: DatasetLoadRequest) -> DatasetPipelineResult:
    validation_errors = adapter.validate(request)
    if validation_errors:
        return DatasetPipelineResult(
            dataset_id=request.dataset_id,
            loaded=False,
            dry_run=request.dry_run,
            raw_count=0,
            rejected_count=0,
            entities=0,
            claims=0,
            evidence=0,
            relationships=0,
            errors=tuple(validation_errors),
        )

    normalized = normalize(adapter, request)
    batch = build_relationships(adapter, normalized)
    publish(session, batch, dry_run=request.dry_run)
    return DatasetPipelineResult(
        dataset_id=request.dataset_id,
        loaded=not request.dry_run,
        dry_run=request.dry_run,
        raw_count=batch.raw_count,
        rejected_count=batch.rejected_count,
        entities=len(batch.entities),
        claims=len(batch.claims),
        evidence=len(batch.evidence),
        relationships=len(batch.public_relationships),
        errors=tuple(batch.errors),
    )


def validate(adapter: DatasetAdapter, request: DatasetLoadRequest) -> tuple[str, ...]:
    return tuple(adapter.validate(request))


def normalize(adapter: DatasetAdapter, request: DatasetLoadRequest) -> object:
    return adapter.normalize(request)


def resolve_entities(batch: GraphBatch) -> tuple[str, ...]:
    return tuple(entity.normalized_key or entity.external_id or entity.name for entity in batch.entities)


def build_relationships(adapter: DatasetAdapter, normalized: object) -> GraphBatch:
    return adapter.build_relationships(normalized)


def build_evidence(batch: GraphBatch) -> tuple[str, ...]:
    return tuple(evidence.title for evidence in batch.evidence)


def publish(session: Session, batch: GraphBatch, *, dry_run: bool = False) -> None:
    GraphLoader(session).load(batch, dry_run=dry_run)
