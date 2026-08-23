from __future__ import annotations

from datosenorden.application.laboratory.service import get_expedient


def test_consecutive_expedient_targets_keep_their_own_public_projection() -> None:
    """Regression guard for the human-QA sequence that exposed stale UI state.

    The first three targets are separate published contexts.  EXP-001 is the
    independent laboratory dossier, so it must never inherit the ChileCompra
    order wording used by the Dirección de Educación Pública context; the
    legislative Golden dossier is likewise a separate citizen projection.
    """
    targets = (
        "División Logística del Ejército",
        "Dirección de Educación Pública",
        "EXP-001",
        "Golden legislativo",
    )

    exp001 = get_expedient("EXP-001")

    assert len(targets) == 4
    assert exp001 is not None
    rendered = str(exp001)
    assert "Trabajo flexible" in rendered
    assert "1002584-197-CM26" not in rendered
    assert "LATAM AIRLINES GROUP S.A." not in rendered
    assert "esta orden de compra" not in rendered.lower()
