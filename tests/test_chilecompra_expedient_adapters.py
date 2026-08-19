from datetime import date
from decimal import Decimal

import pytest

from datosenorden.application.canonical_entity_identity import bootstrap_public_name_registry
from datosenorden.application.chilecompra_expedient import ChileCompraCanonicalIdentityResolver, ChileCompraValidatedContent, build_chilecompra_input, resolve_public_subject
from datosenorden.application.chilecompra_expedient.adapters import ChileCompraAdapterError


def _content(**changes):
    values = dict(source_record_id="record-1", order_id="1002584-197-CM26", buyer_identity="chilecompra:buyer:1593363", official_order_name="NOMBRE OFICIAL", official_item_products=("  PASAJE AÉREO NACIONAL  ",), source_id="source-1", claim_ids=("claim-1",), evidence_ids=("evidence-1",), entity_ids=("entity-1",), supplier_observed_name="LATAM AIRLINES GROUP S.A.", amount=Decimal("1021374"), currency="CLP", order_date=date(2026, 6, 17))
    values.update(changes)
    return ChileCompraValidatedContent(**values)


def test_resolves_registered_buyer_and_official_item_subject() -> None:
    value = build_chilecompra_input(_content(), ChileCompraCanonicalIdentityResolver(bootstrap_public_name_registry()))
    assert value.buyer_name == "Dirección de Educación Pública"
    assert value.public_subject == "PASAJE AÉREO NACIONAL"


def test_subject_is_mechanical_and_deterministic() -> None:
    subject = resolve_public_subject(_content(official_item_products=(" SUTURA QUIRÚRGICA ", "SUTURA QUIRÚRGICA")))
    assert (subject.text, subject.source_field, subject.normalization_version) == ("SUTURA QUIRÚRGICA", "items[].Producto", "unicode-nfc-whitespace-v1")


def test_falls_back_only_to_official_order_name_or_fails_closed() -> None:
    assert resolve_public_subject(_content(official_item_products=(), official_order_name=" Orden oficial ")).text == "Orden oficial"
    with pytest.raises(ChileCompraAdapterError, match="PUBLIC_SUBJECT_REVIEW_REQUIRED"):
        resolve_public_subject(_content(official_item_products=(), official_order_name=None))


def test_unknown_identity_never_uses_observed_spelling() -> None:
    with pytest.raises(Exception, match="CANONICAL_IDENTITY_REVIEW_REQUIRED"):
        build_chilecompra_input(_content(buyer_identity="chilecompra:buyer:unknown"), ChileCompraCanonicalIdentityResolver(bootstrap_public_name_registry()))
