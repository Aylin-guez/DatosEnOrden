from datosenorden.application.real_expedient.democracia_viva_antofagasta import (
    EXPEDIENT_ID,
    TITLE,
    democracia_viva_citizen_context,
)


def test_democracia_viva_context_keeps_the_three_agreements_distinct() -> None:
    context = democracia_viva_citizen_context()
    text = " ".join(answer.answer for answer in context.answers)
    assert EXPEDIENT_ID == "EXP-REAL-DEMOCRACIA-VIVA-ANTOFAGASTA"
    assert TITLE == "Democracia Viva y los convenios de Antofagasta"
    assert "RE N°504" in text
    assert "RE N°576" in text
    assert "RE N°641" in text
    assert len(context.answers) == 14


def test_democracia_viva_context_preserves_money_and_criminal_boundaries() -> None:
    answers = {answer.question: answer.answer for answer in democracia_viva_citizen_context().answers}
    assert "no prueba por sí sola un delito" in answers["¿Cuánto dinero recibió Democracia Viva?"]
    assert "No. El informe contiene hallazgos de fiscalización" in answers["¿Contraloría dijo que se robaron esos recursos?"]
    assert "No está acreditado" in answers["¿Cuánto dinero fue efectivamente recuperado?"]
    assert "no equivale a culpabilidad ni a condena" in answers["¿Qué investiga Fiscalía?"]


def test_democracia_viva_context_uses_only_official_urls() -> None:
    context = democracia_viva_citizen_context()
    assert all(item.official_url and item.official_url.startswith("https://") for item in context.evidence)
    assert all("data/tmp" not in str(item.official_url) for item in context.evidence)
