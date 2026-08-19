"""Pure adapters from validated ChileCompra content to generator input."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from datosenorden.application.canonical_entity_identity import CanonicalPublicNameRegistry

from .models import ChileCompraExpedientInput


class ChileCompraAdapterError(ValueError):
    pass


def _official_text(value: str) -> str:
    return " ".join(unicodedata.normalize("NFC", str(value or "")).split())


@dataclass(frozen=True)
class PublicSubject:
    text: str
    source_field: str
    source_record_id: str
    provenance: str = "REAL_USABLE_CHILECOMPRA"
    normalization_version: str = "unicode-nfc-whitespace-v1"


@dataclass(frozen=True)
class ChileCompraValidatedContent:
    source_record_id: str
    order_id: str
    buyer_identity: str
    official_order_name: str | None
    official_item_products: tuple[str, ...]
    source_id: str
    claim_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    entity_ids: tuple[str, ...]
    relationship_ids: tuple[str, ...] = ()
    supplier_observed_name: str | None = None
    amount: Decimal | None = None
    currency: str | None = None
    order_date: date | None = None


class ChileCompraCanonicalIdentityResolver:
    def __init__(self, registry: CanonicalPublicNameRegistry) -> None:
        self._registry = registry

    def resolve(self, buyer_identity: str) -> str:
        if not buyer_identity.startswith("chilecompra:buyer:"):
            raise ChileCompraAdapterError("CANONICAL_IDENTITY_REVIEW_REQUIRED")
        return self._registry.get_canonical_public_name(buyer_identity)


def resolve_public_subject(content: ChileCompraValidatedContent) -> PublicSubject:
    products = tuple(sorted({_official_text(value) for value in content.official_item_products if _official_text(value)}))
    if len(products) == 1:
        return PublicSubject(products[0], "items[].Producto", content.source_record_id)
    order_name = _official_text(content.official_order_name or "")
    if order_name:
        return PublicSubject(order_name, "Nombre", content.source_record_id)
    raise ChileCompraAdapterError("PUBLIC_SUBJECT_REVIEW_REQUIRED")


def build_chilecompra_input(
    content: ChileCompraValidatedContent,
    resolver: ChileCompraCanonicalIdentityResolver,
) -> ChileCompraExpedientInput:
    subject = resolve_public_subject(content)
    return ChileCompraExpedientInput(
        order_id=content.order_id,
        buyer_name=resolver.resolve(content.buyer_identity),
        public_subject=subject.text,
        supplier_name=_official_text(content.supplier_observed_name or "") or None,
        amount=content.amount,
        currency=content.currency,
        order_date=content.order_date,
        source_id=content.source_id,
        claim_ids=content.claim_ids,
        evidence_ids=content.evidence_ids,
        entity_ids=content.entity_ids,
        relationship_ids=content.relationship_ids,
    )
