"""Validated, database-independent input for ChileCompra expedient generation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from datosenorden.application.provenance.models import ProvenanceClass


class ChileCompraExpedientInputError(ValueError):
    """Raised when an authoritative input cannot safely form public text."""


_CORRUPTION_MARKERS = ("\ufffd", "Ã", "Â", "Direcci?n", "Educaci?n", "P?blica")


def _clean_text(value: str, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ChileCompraExpedientInputError(f"{field} is required")
    if any(marker in text for marker in _CORRUPTION_MARKERS):
        raise ChileCompraExpedientInputError(f"{field} contains known Unicode corruption")
    return text


def _ordered(values: tuple[str, ...], field: str, *, required: bool) -> tuple[str, ...]:
    cleaned = tuple(sorted({_clean_text(value, field) for value in values}))
    if required and not cleaned:
        raise ChileCompraExpedientInputError(f"{field} is required")
    return cleaned


@dataclass(frozen=True)
class ChileCompraExpedientInput:
    """Only normalized, already-authorized inputs; never a raw ChileCompra payload."""

    order_id: str
    buyer_name: str
    public_subject: str
    source_id: str
    claim_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    entity_ids: tuple[str, ...]
    relationship_ids: tuple[str, ...] = ()
    supplier_name: str | None = None
    amount: Decimal | None = None
    currency: str | None = None
    order_date: date | None = None
    provenance_class: ProvenanceClass = ProvenanceClass.REAL
    references_public_usable: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "order_id", _clean_text(self.order_id, "order_id"))
        object.__setattr__(self, "buyer_name", _clean_text(self.buyer_name, "buyer_name"))
        object.__setattr__(self, "public_subject", _clean_text(self.public_subject, "public_subject"))
        object.__setattr__(self, "source_id", _clean_text(self.source_id, "source_id"))
        if self.supplier_name is not None:
            object.__setattr__(self, "supplier_name", _clean_text(self.supplier_name, "supplier_name"))
        object.__setattr__(self, "claim_ids", _ordered(self.claim_ids, "claim_ids", required=True))
        object.__setattr__(self, "evidence_ids", _ordered(self.evidence_ids, "evidence_ids", required=True))
        object.__setattr__(self, "entity_ids", _ordered(self.entity_ids, "entity_ids", required=True))
        object.__setattr__(self, "relationship_ids", _ordered(self.relationship_ids, "relationship_ids", required=False))
        if self.provenance_class is not ProvenanceClass.REAL or not self.references_public_usable:
            raise ChileCompraExpedientInputError("input must be REAL and public usable")
        if (self.amount is None) != (self.currency is None):
            raise ChileCompraExpedientInputError("amount and currency must be supplied together")
        if self.amount is not None and self.amount < 0:
            raise ChileCompraExpedientInputError("amount cannot be negative")
