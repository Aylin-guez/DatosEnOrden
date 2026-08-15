"""Contracts for the narrow DIPRES discovery boundary; no persistence types."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path


class IdentityClassification(StrEnum):
    EXACT_ID_MATCH = "EXACT_ID_MATCH"
    STRONG_INSTITUTION_MATCH = "STRONG_INSTITUTION_MATCH"
    PARENT_INSTITUTION_ONLY = "PARENT_INSTITUTION_ONLY"
    POSSIBLE_MATCH = "POSSIBLE_MATCH"
    NO_MATCH = "NO_MATCH"


@dataclass(frozen=True)
class DipresIdentity:
    chilecompra_label: str
    classification: IdentityClassification
    partida: str | None
    capitulo: str | None
    programa: str | None
    budget_label: str | None
    basis: str


def classify_identity(
    *,
    chilecompra_label: str,
    official_label: str | None,
    same_entity: bool,
    exact_official_identifier: bool = False,
    parent_budget_label: str | None = None,
) -> IdentityClassification:
    """Classify only evidence already established by targeted official discovery.

    This function deliberately performs no name normalisation or fuzzy matching.
    """
    if exact_official_identifier:
        return IdentityClassification.EXACT_ID_MATCH
    if same_entity and official_label == chilecompra_label:
        return IdentityClassification.STRONG_INSTITUTION_MATCH
    if parent_budget_label:
        return IdentityClassification.PARENT_INSTITUTION_ONLY
    if official_label:
        return IdentityClassification.POSSIBLE_MATCH
    return IdentityClassification.NO_MATCH


@dataclass(frozen=True)
class ResourceDefinition:
    official_page_url: str
    download_url: str
    period: str
    format: str = "csv"


@dataclass(frozen=True)
class AcquiredResource:
    resource: ResourceDefinition
    acquired_at: datetime
    sha256: str
    byte_count: int
    content_type: str
    staging_path: Path
    reused_staged_file: bool


@dataclass(frozen=True)
class BudgetRow:
    values: dict[str, str]


@dataclass(frozen=True)
class ParsedBudgetCsv:
    acquisition: AcquiredResource
    columns: tuple[str, ...]
    rows: tuple[BudgetRow, ...]
    delimiter: str
