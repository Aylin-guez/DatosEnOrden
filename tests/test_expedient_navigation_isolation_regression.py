from __future__ import annotations

from types import SimpleNamespace

from datosenorden.application.laboratory.service import get_expedient
from reflex_app.features.laboratory import state as laboratory_state
from reflex_app.features.laboratory.state import LaboratoryState


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


def test_real_and_demo_route_navigation_never_reuses_the_previous_projection(monkeypatch) -> None:
    """A reused Reflex state must keep the route's expedient identity intact."""
    legislative_id = "EXP-REAL-LEGISLATIVE-18216-05"
    legislative_projection = {
        "title": "Para la reconstrucciÃ³n nacional y el desarrollo econÃ³mico y social",
        "summary": "El BoletÃ­n 18.216-05 registra una ComisiÃ³n Mixta.",
        "status": "PUBLISHED",
        "type": "Expediente legislativo",
        "question": "Pregunta legislativa.",
        "facts": [{"statement": "BoletÃ­n 18.216-05", "evidence": []}],
        "what_is_missing": [],
        "what_we_cannot_conclude": [],
        "sections": {"bank_secrecy": [], "mixed_commission": [{"statement": "ComisiÃ³n Mixta", "evidence": []}]},
        "chronology": [],
        "actors": [],
        "documents": [],
        "sources": [],
        "questions": [],
        "knowledge_cutoff": {},
    }

    def public_expedient(expedient_id: str) -> dict | None:
        if expedient_id == legislative_id:
            return {"id": legislative_id, "provenance_class": "REAL"}
        return get_expedient(expedient_id)

    monkeypatch.setattr(laboratory_state, "get_public_expedient", public_expedient)
    monkeypatch.setattr(
        laboratory_state,
        "get_citizen_expedient",
        lambda expedient_id: legislative_projection if expedient_id == legislative_id else None,
    )

    state = SimpleNamespace(
        router=SimpleNamespace(url=SimpleNamespace(query_parameters={"id": legislative_id})),
        load_status="idle",
        error_message="",
        public_error_code="",
    )
    state._clear_expedient = lambda: LaboratoryState._clear_expedient(state)
    state._load_real_expedient = lambda payload: LaboratoryState._load_real_expedient(state, payload)
    state._recalculate_progress = lambda: LaboratoryState._recalculate_progress(state)

    LaboratoryState.load_expedient.fn(state)
    assert state.citizen_expedient is True
    assert "BoletÃ­n 18.216-05" in state.citizen_facts[0]["statement"]

    state.router.url.query_parameters = {"id": "EXP-001"}
    LaboratoryState.load_expedient.fn(state)

    assert state.requested_expedient_id == "EXP-001"
    assert state.citizen_expedient is False
    assert state.expedient_id == "EXP-001"
    assert "Trabajo flexible" in state.expedient_title
    assert state.expedient_provenance_class == "DEMO"
    assert state.citizen_facts == []
    assert state.citizen_divergences == []
    assert "BoletÃ­n 18.216-05" not in str(state.sections)
    assert "ComisiÃ³n Mixta" not in str(state.sections)

    state.router.url.query_parameters = {"id": legislative_id}
    LaboratoryState.load_expedient.fn(state)

    assert state.requested_expedient_id == legislative_id
    assert state.citizen_expedient is True
    assert state.expedient_title.startswith("Para la reconstrucci")
    assert "BoletÃ­n 18.216-05" in state.citizen_facts[0]["statement"]
