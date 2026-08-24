from datetime import UTC, datetime

from datosenorden.application.legislative_ingestion.reconstruccion_nacional import (
    EXPEDIENT_ID,
    TITLE,
    reconstruccion_citizen_context,
)
from datosenorden.application.provenance.models import ProvenanceClass
from datosenorden.application.real_expedient.citizen_projection import (
    CitizenProjectionContext,
    citizen_expedient_projection,
)
from datosenorden.application.real_expedient.models import (
    ExpedientReferences,
    ExpedientSpecification,
    ExpedientStatus,
    StoredExpedient,
)


def test_reconstruccion_projection_exposes_certified_matters_and_gaps() -> None:
    context = reconstruccion_citizen_context()
    stored = StoredExpedient(
        ExpedientSpecification(
            EXPEDIENT_ID,
            TITLE,
            "¿Qué cambia este proyecto y cómo fue modificándose durante su tramitación?",
            "Resumen.",
            ProvenanceClass.REAL,
            ExpedientStatus.PUBLISHED,
            2,
            ExpedientReferences((), ()),
        ),
        "reconstruccion-v2",
        datetime(2026, 8, 23, tzinfo=UTC),
        datetime(2026, 8, 23, tzinfo=UTC),
    )

    projection = citizen_expedient_projection(stored, context)

    assert projection["topics"] == [
        "Tributación",
        "Crédito al empleo",
        "Normas ambientales",
        "Educación superior",
        "Propiedad intelectual",
        "Contribuciones",
    ]
    assert projection["missing_knowledge"] == list(context.missing_knowledge)
    assert projection["version"] == 2


def test_empty_context_omits_projection_only_sections() -> None:
    stored = StoredExpedient(
        ExpedientSpecification(
            "EXP-REAL-EMPTY-PROJECTION",
            "Expediente de prueba",
            "¿Qué muestra?",
            "Resumen.",
            ProvenanceClass.REAL,
            ExpedientStatus.PUBLISHED,
            1,
            ExpedientReferences((), ()),
        ),
        "empty-projection",
        datetime(2026, 8, 23, tzinfo=UTC),
        datetime(2026, 8, 23, tzinfo=UTC),
    )

    projection = citizen_expedient_projection(stored, CitizenProjectionContext())

    assert "topics" not in projection
    assert "missing_knowledge" not in projection
