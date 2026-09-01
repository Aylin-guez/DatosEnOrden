from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from datosenorden.application.data_release.contract import (
    PackageCompatibilityError,
    VerifiedPackage,
    canonical_json,
)
from datosenorden.application.data_release.importer import TargetExpectation, import_package
from datosenorden.application.data_release.semantic_integrity import (
    PublicTextIntegrityError,
    validate_public_text_integrity,
)


def _rows() -> dict[str, tuple[dict[str, object], ...]]:
    expedient_id = "EXP-REAL-CHILECOMPRA-ORDER-1"
    return {
        "real_expedient": (
            {"expedient_id": expedient_id, "current_version": 2},
        ),
        "real_expedient_version": (
            {
                "expedient_id": expedient_id,
                "version": 1,
                "title": "Historical superseded version with explained loss ?",
                "question": "?Texto histórico?",
                "summary": "Histórico",
            },
            {
                "expedient_id": expedient_id,
                "version": 2,
                "title": "Orden de División Logística del Ejército",
                "question": "¿Qué muestran los registros públicos?",
                "summary": (
                    "División Logística del Ejército: á é í ó ú Á É Í Ó Ú "
                    "ñ Ñ ü Ü"
                ),
            },
        ),
        "real_expedient_narrative": (
            {
                "expedient_id": expedient_id,
                "version": 2,
                "statement_id": "fact-1",
                "statement": "Información pública íntegra.",
            },
        ),
        "real_expedient_reference": (
            {
                "expedient_id": expedient_id,
                "version": 2,
                "reference_type": "entity",
                "reference_id": "buyer-entity",
            },
        ),
        "entity": (
            {
                "id": "buyer-entity",
                "external_id": "chilecompra:buyer:111870",
            },
        ),
    }


def test_current_public_unicode_round_trips_exactly() -> None:
    rows = _rows()
    validate_public_text_integrity(rows)
    payload = canonical_json(rows)
    assert payload.decode("utf-8").encode("utf-8") == payload
    for value in (
        "División Logística del Ejército",
        "Dirección de Educación Pública",
        "Félix Bulnes",
        "referencias públicas",
        "á é í ó ú Á É Í Ó Ú ñ Ñ ü Ü",
    ):
        assert value.encode("utf-8").decode("utf-8") == value


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("title", "Orden de la Divisi?n Log?stica del Ej?rcito"),
        ("summary", "Direcci?n de Educaci?n P?blica"),
        ("question", "?Qu? muestran los registros p?blicos?"),
    ),
)
def test_current_public_lossy_question_marks_fail_closed(field: str, value: str) -> None:
    rows = deepcopy(_rows())
    rows["real_expedient_version"][1][field] = value
    with pytest.raises(PublicTextIntegrityError, match="lossy question-mark"):
        validate_public_text_integrity(rows)


def test_terminal_question_mark_is_allowed_but_narrative_loss_is_not() -> None:
    rows = deepcopy(_rows())
    rows["real_expedient_narrative"][0]["statement"] = "referencias p?blicas"
    with pytest.raises(PublicTextIntegrityError, match="lossy question-mark"):
        validate_public_text_integrity(rows)


def test_known_mojibake_sequence_fails_closed() -> None:
    rows = deepcopy(_rows())
    rows["real_expedient_version"][1]["summary"] = "DirecciÃ³n pÃºblica"
    with pytest.raises(PublicTextIntegrityError, match="mojibake"):
        validate_public_text_integrity(rows)


def test_authoritative_buyer_name_mismatch_fails_closed() -> None:
    rows = deepcopy(_rows())
    rows["real_expedient_version"][1]["title"] = "Orden de organización pública"
    with pytest.raises(PublicTextIntegrityError, match="buyer-name mismatch"):
        validate_public_text_integrity(rows)


def test_historical_recovery_waiver_cannot_target_production() -> None:
    package = VerifiedPackage(
        path=Path("historical-recovery.zip"),
        archive_sha256="0" * 64,
        manifest={},
        rows={},
        semantic_integrity_verified=False,
    )
    with pytest.raises(PackageCompatibilityError, match="isolated-test"):
        import_package(
            None,  # type: ignore[arg-type]
            package,
            expectation=TargetExpectation(
                database_name="production",
                environment="production",
                code_release="0" * 40,
                production_confirmation="historical",
            ),
        )
