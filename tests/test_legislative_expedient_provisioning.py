from datosenorden.application.legislative_ingestion.expedient import EXPEDIENT_ID
from datosenorden.application.real_expedient.models import EpistemicClass, ExpedientReferences, ExpedientSpecification, ExpedientStatus, NarrativeStatement
from datosenorden.application.provenance.models import ProvenanceClass


def test_reviewed_legislative_expedient_contract_requires_explicit_limits() -> None:
    specification = ExpedientSpecification(
        EXPEDIENT_ID, "Titulo", "Pregunta", "Resumen", ProvenanceClass.REAL, ExpedientStatus.PUBLISHED, 1,
        ExpedientReferences(("claim",), ("evidence",), entity_ids=("matter",), source_ids=("senado", "camara")),
        (
            NarrativeStatement("fact", "verified", "Hecho.", EpistemicClass.FACT, ("claim",), ("evidence",)),
            NarrativeStatement("unknown", "limitations", "No se afirma vigencia.", EpistemicClass.UNKNOWN),
            NarrativeStatement("open", "open_questions", "Falta texto legislativo.", EpistemicClass.OPEN_QUESTION),
        ),
    )
    assert specification.expedient_id == "EXP-REAL-LEGISLATIVE-15975-25"
    assert {item.epistemic_class for item in specification.statements} == {EpistemicClass.FACT, EpistemicClass.UNKNOWN, EpistemicClass.OPEN_QUESTION}
