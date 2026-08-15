from __future__ import annotations

from types import SimpleNamespace

from datosenorden.application.provenance.models import ProvenanceClass
from datosenorden.application.real_expedient.eligibility import (
    ProvenanceReferenceEligibility,
)
from datosenorden.application.real_expedient.models import ReferenceKind


def test_provenance_eligibility_uses_only_authoritative_public_usable_content(
    monkeypatch,
) -> None:
    import datosenorden.application.real_expedient.eligibility as eligibility

    monkeypatch.setattr(
        eligibility,
        "build_public_usable_content",
        lambda session: {
            "claims": (SimpleNamespace(id="claim-real"),),
            "evidences": (SimpleNamespace(id="evidence-real"),),
            "relationships": (SimpleNamespace(id="relationship-real"),),
            "entity_ids": {"entity-real"},
            "source_ids": {"source-real"},
        },
    )
    adapter = ProvenanceReferenceEligibility(object())

    assert adapter.classify(ReferenceKind.CLAIM, "claim-real").provenance_class is ProvenanceClass.REAL
    assert adapter.classify(ReferenceKind.EVIDENCE, "missing").public_usable is False


def test_laboratory_state_loads_real_projection_without_legacy_shape(monkeypatch) -> None:
    import reflex_app.features.laboratory.state as laboratory_state

    projection = {
        "id": "EXP-REAL-TEST",
        "title": "Expediente REAL",
        "question": "¿Qué muestran las referencias?",
        "summary": "Resumen factual.",
        "provenance_class": "REAL",
        "status": "published",
        "references": {
            "claims": ["claim-real"],
            "evidences": ["evidence-real"],
            "relationships": ["relationship-real"],
            "sources": ["source-real"],
        },
        "statements": [
            {"id": "statement-1", "text": "Hecho respaldado.", "epistemic_class": "FACT"}
        ],
        "updated_at": "2026-08-13T00:00:00+00:00",
    }
    state = SimpleNamespace(_recalculate_progress=lambda: None)
    laboratory_state.LaboratoryState._load_real_expedient(state, projection)

    assert state.expedient_id == "EXP-REAL-TEST"
    assert state.expedient_provenance_class == "REAL"
    assert state.claims[0]["text"] == "Hecho respaldado."
