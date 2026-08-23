from datosenorden.application.legislative_ingestion.escuelas_protegidas import (
    EXPEDIENT_ID,
    LAW_URL,
    escuelas_citizen_context,
)
from datosenorden.maintenance.search_workspace import _normalize


def test_escuelas_protegidas_has_the_eight_nonduplicated_citizen_questions() -> None:
    answers = escuelas_citizen_context().answers
    assert len(answers) == 8
    assert len({item.question for item in answers}) == 8
    assert "teléfono" in answers[3].question
    assert answers[3].epistemic_class == "LIMITATION"
    assert "no puede inferirse" in answers[3].answer


def test_escuelas_protegidas_public_context_keeps_current_law_separate() -> None:
    context = escuelas_citizen_context()
    assert LAW_URL.endswith("idNorma=1226950&idVersion=2026-08-12")
    assert EXPEDIENT_ID.startswith("EXP-REAL-")
    assert any(item.title == "Ley 21.827" for item in context.documents)
    assert any("rechazó" in item.text for item in context.timeline)


def test_search_normalization_retains_citizen_terms() -> None:
    assert _normalize("Escuelas Protegidas") == "escuelas protegidas"
    assert _normalize("teléfono") == "telefono"
