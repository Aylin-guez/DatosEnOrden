from datosenorden.application.legislative_ingestion.cybersecurity_21663 import (
    BULLETIN,
    EXPEDIENT_ID,
    LAW_NUMBER,
    cybersecurity_citizen_context,
)


def test_cybersecurity_context_is_a_current_law_dossier_with_official_sources() -> None:
    context = cybersecurity_citizen_context()
    assert BULLETIN == "14847-06"
    assert LAW_NUMBER == "21.663"
    assert len(context.evidence) == 4
    assert any(item.source_name == "LeyChile" for item in context.evidence)
    assert len(context.answers) == 12


def test_technical_access_is_not_inferred_from_information_request() -> None:
    answers = {item.question: item.answer for item in cybersecurity_citizen_context().answers}
    info = answers["¿Qué información puede exigir la Agencia Nacional de Ciberseguridad?"]
    access = answers[
        "¿Puede la Agencia acceder directamente a computadores, sistemas o dispositivos?"
    ]
    assert "información estrictamente necesaria" in info
    assert "redes y sistemas" in access
    assert "no infiere" in access
    assert "dispositivos individuales" in access


def test_history_never_becomes_current_law_and_reporting_is_subject_specific() -> None:
    context = cybersecurity_citizen_context()
    answers = {item.question: item.answer for item in context.answers}
    history_question = "¿Qué cambió entre el proyecto original y la ley finalmente publicada?"
    reporting_question = "¿Qué incidentes deben reportarse y quién debe hacerlo?"
    assert "LeyChile" in answers[history_question]
    assert "sujetos definidos" in answers[reporting_question]
    assert EXPEDIENT_ID == "EXP-REAL-CYBERSECURITY-14847-06"
