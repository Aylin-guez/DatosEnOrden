from datetime import UTC, datetime

from datosenorden.application.legislative_ingestion.data_protection_21719 import (
    EXPEDIENT_ID,
    LAW_NUMBER,
    OFFICIAL_TITLE,
    TITLE,
    data_protection_citizen_context,
)
from datosenorden.application.provenance.models import ProvenanceClass
from datosenorden.application.real_expedient.citizen_projection import (
    citizen_expedient_projection,
)
from datosenorden.application.real_expedient.models import (
    ExpedientReferences,
    ExpedientSpecification,
    ExpedientStatus,
    StoredExpedient,
)


def test_publication_and_future_effectiveness_remain_distinct() -> None:
    context = data_protection_citizen_context()
    answers = {item.question: item.answer for item in context.answers}
    assert LAW_NUMBER == "21.719"
    assert "publicada" in answers["¿La Ley 21.719 ya está vigente?"].lower()
    assert "1 de diciembre de 2026" in answers["¿Cuándo empieza a aplicarse?"]
    assert "Ley 19.628" in answers["¿Qué ocurre hoy?"]


def test_authority_information_is_not_system_or_device_access() -> None:
    answers = {item.question: item.answer for item in data_protection_citizen_context().answers}
    answer = answers["¿Puede la Agencia acceder directamente a sistemas o dispositivos?"]
    assert "no puede inferirse" in answer.lower()
    assert "dispositivos" in answer
    assert "interceptación" in answers["¿Qué no podemos concluir?"]


def test_context_is_bounded_to_official_sources_and_future_rules() -> None:
    context = data_protection_citizen_context()
    assert EXPEDIENT_ID == "EXP-REAL-DATA-PROTECTION-21719"
    assert len(context.evidence) == 4
    assert len(context.answers) == 12
    assert len(context.timeline) == 6
    assert all(item.official_url.startswith("https://") for item in context.evidence)


def test_citizen_title_is_not_required_to_equal_official_title() -> None:
    context = data_protection_citizen_context()
    assert TITLE == "Protección y tratamiento de datos personales"
    assert TITLE != OFFICIAL_TITLE
    assert context.official_title == OFFICIAL_TITLE

    stored = StoredExpedient(
        ExpedientSpecification(
            EXPEDIENT_ID,
            TITLE,
            "Pregunta.",
            "Resumen.",
            ProvenanceClass.REAL,
            ExpedientStatus.PUBLISHED,
            1,
            ExpedientReferences((), ()),
        ),
        "data-protection-v1",
        datetime(2026, 8, 24, tzinfo=UTC),
        datetime(2026, 8, 24, tzinfo=UTC),
    )
    projection = citizen_expedient_projection(stored, context)

    assert projection["title"] == TITLE
    assert projection["official_title"] == OFFICIAL_TITLE
    assert projection["version"] == 1
