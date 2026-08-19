from datetime import date
from decimal import Decimal

import pytest

from datosenorden.application.chilecompra_expedient import (
    ChileCompraExpedientInput,
    ChileCompraExpedientInputError,
    build_chilecompra_expedient_candidate,
)
from datosenorden.application.real_expedient.service import content_fingerprint


def _input(**changes):
    values = {
        "order_id": "1002584-197-CM26",
        "buyer_name": "Dirección de Educación Pública",
        "public_subject": "pasajes",
        "supplier_name": "LATAM AIRLINES GROUP S.A.",
        "amount": Decimal("1234.50"),
        "currency": "CLP",
        "order_date": date(2026, 6, 18),
        "source_id": "source-chilecompra",
        "claim_ids": ("claim-b", "claim-a"),
        "evidence_ids": ("evidence-b", "evidence-a"),
        "entity_ids": ("entity-b", "entity-a"),
        "relationship_ids": ("relationship-b", "relationship-a"),
    }
    values.update(changes)
    return ChileCompraExpedientInput(**values)


def test_generates_deterministic_unicode_safe_candidate() -> None:
    candidate = build_chilecompra_expedient_candidate(_input())
    repeated = build_chilecompra_expedient_candidate(_input())
    assert candidate.expedient_id == "EXP-REAL-CHILECOMPRA-1002584-197-CM26"
    assert candidate.title == "Orden de compra de pasajes de Dirección de Educación Pública"
    assert candidate.question == "¿Qué muestran los registros públicos sobre esta orden de compra?"
    assert "Dirección de Educación Pública" in candidate.summary
    assert "1234.5 CLP" in candidate.summary
    assert candidate.references.claim_ids == ("claim-a", "claim-b")
    assert candidate.statements[0].claim_ids == candidate.references.claim_ids
    assert candidate.statements[0].evidence_ids == candidate.references.evidence_ids
    assert candidate.statements[-1].claim_ids == ()
    assert content_fingerprint(candidate) == content_fingerprint(repeated)


def test_preserves_required_unicode_without_repairing_input() -> None:
    candidate = build_chilecompra_expedient_candidate(
        _input(
            public_subject="PASAJE AÉREO áéíóúñ",
            supplier_name="Proveedor de Región con DIÁMETRO y SÓLO",
        )
    )
    rendered = " ".join((candidate.title, candidate.question, candidate.summary))
    for value in ("Dirección de Educación Pública", "PASAJE AÉREO", "Región", "DIÁMETRO", "SÓLO", "¿", "á", "é", "í", "ó", "ú", "ñ"):
        assert value in rendered


@pytest.mark.parametrize(
    ("buyer", "subject"),
    [
        ("División Logística del Ejército", "pasajes"),
        ("Dirección de Educación Pública", "pasajes"),
        ("Hospital Dr. Félix Bulnes", "suministro de suturas"),
    ],
)
def test_general_policy_supports_the_three_existing_order_shapes(buyer: str, subject: str) -> None:
    candidate = build_chilecompra_expedient_candidate(_input(buyer_name=buyer, public_subject=subject))
    assert buyer in candidate.title
    assert subject in candidate.title


def test_optional_values_are_omitted_without_inference() -> None:
    candidate = build_chilecompra_expedient_candidate(_input(supplier_name=None, amount=None, currency=None, order_date=None))
    assert "asociada a" not in candidate.summary
    assert " por " not in candidate.summary
    assert len(candidate.statements) == 2


@pytest.mark.parametrize("corrupted", ["Direcci?n de Educaci?n P?blica", "pÃºblicas", "texto\ufffd"])
def test_rejects_known_unicode_corruption(corrupted: str) -> None:
    with pytest.raises(ChileCompraExpedientInputError):
        _input(buyer_name=corrupted)


def test_requires_real_public_usable_references() -> None:
    with pytest.raises(ChileCompraExpedientInputError):
        _input(references_public_usable=False)
