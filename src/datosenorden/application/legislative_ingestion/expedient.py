"""Human-reviewed v1 expedient from persisted bulletin 15975-25 evidence only."""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from datosenorden.application.provenance.models import ProvenanceClass
from datosenorden.application.real_expedient.eligibility import ProvenanceReferenceEligibility
from datosenorden.application.real_expedient.models import EpistemicClass, ExpedientReferences, ExpedientSpecification, ExpedientStatus, NarrativeStatement
from datosenorden.application.real_expedient.service import ExpedientProvisioningService
from datosenorden.infrastructure.real_expedient.repository import PostgresExpedientRepository
from datosenorden.models import Claim, Entity, Evidence, Source, SourceRecord


EXPEDIENT_ID = "EXP-REAL-LEGISLATIVE-15975-25"
CANONICAL_BULLETIN_ENTITY = "cl-congreso-boletin-15975-25"


class LegislativeExpedientReviewError(RuntimeError):
    pass


@dataclass(frozen=True)
class LegislativeExpedientReview:
    specification: ExpedientSpecification
    automatic_update_linkage: str


def review_bulletin_15975_25_payload(session: Session) -> LegislativeExpedientReview:
    """Build a complete payload without acquisition or database mutation."""
    entity = session.scalar(select(Entity).where(Entity.external_id == CANONICAL_BULLETIN_ENTITY))
    records = session.scalars(select(SourceRecord).where(SourceRecord.record_type == "legislature:matter_observation")).all()
    claims = session.scalars(select(Claim).join(SourceRecord).where(SourceRecord.record_type == "legislature:matter_observation").order_by(Claim.predicate, Claim.id)).all()
    evidence = session.scalars(select(Evidence).join(SourceRecord).where(SourceRecord.record_type == "legislature:matter_observation").order_by(Evidence.id)).all()
    sources = session.scalars(select(Source).where(Source.name.in_(("Senado de Chile", "Camara de Diputadas y Diputados"))).order_by(Source.name)).all()
    if entity is None or len(records) != 3 or len(claims) != 4 or len(evidence) != 3 or len(sources) != 2:
        raise LegislativeExpedientReviewError("certified legislative payload is incomplete")
    if any(row.status not in {"normalized", "validated", "published"} for row in records):
        raise LegislativeExpedientReviewError("legislative records are not public usable")
    event = next((item for item in claims if item.predicate == "LEGISLATIVE_MATTER_HAS_VERIFIED_EVENT"), None)
    value = event.object_value if event is not None and isinstance(event.object_value, dict) else {}
    if value.get("event_type") != "MIXED_COMMISSION" or value.get("event_date") != "2026-06-09":
        raise LegislativeExpedientReviewError("verified event differs from reviewed payload")
    claim_ids, evidence_ids = tuple(str(item.id) for item in claims), tuple(str(item.id) for item in evidence)
    specification = ExpedientSpecification(
        EXPEDIENT_ID,
        "Tramitación del proyecto sobre Subsistema de Inteligencia Económica",
        "¿Qué registra la evidencia oficial sobre la tramitación del proyecto que crea el Subsistema de Inteligencia Económica?",
        "Las observaciones oficiales disponibles identifican el boletín 15975-25 y registran que el Senado informó su paso a comisión mixta el 9 de junio de 2026. Esta evidencia no certifica por sí sola su estado actual ni que una facultad propuesta esté vigente.",
        ProvenanceClass.REAL, ExpedientStatus.PUBLISHED, 1,
        ExpedientReferences(claim_ids, evidence_ids, entity_ids=(str(entity.id),), source_ids=tuple(str(item.id) for item in sources)),
        (
            NarrativeStatement("fact-bulletin-identity", "what_is_verified", "El proyecto corresponde al boletín 15975-25 y se titula “Crea el Subsistema de Inteligencia Económica y establece otras medidas para la prevención y alerta de actividades que digan relación con el crimen organizado”.", EpistemicClass.FACT, claim_ids[:3], evidence_ids),
            NarrativeStatement("fact-source-observations", "source_observations", "Senado y Cámara mantienen observaciones oficiales separadas que identifican el mismo boletín canónico 15975-25.", EpistemicClass.FACT, claim_ids[:3], evidence_ids),
            NarrativeStatement("fact-mixed-commission-event", "verified_event", "Senado registró el paso del proyecto a comisión mixta el 9 de junio de 2026.", EpistemicClass.FACT, (str(event.id),), (str(event.evidence_id),)),
            NarrativeStatement("unknown-current-status", "limitations", "La evidencia disponible no permite afirmar cuál es el estado actual del proyecto ni que una facultad propuesta se encuentre vigente.", EpistemicClass.UNKNOWN),
            NarrativeStatement("open-question-substantive-content", "open_questions", "La evidencia disponible no detalla aquí las facultades específicas del proyecto; su contenido requiere documentos legislativos adicionales verificados.", EpistemicClass.OPEN_QUESTION),
        ),
    )
    return LegislativeExpedientReview(specification, "READY")


def provision_reviewed_bulletin_15975_25(session: Session):  # type: ignore[no-untyped-def]
    review = review_bulletin_15975_25_payload(session)
    service = ExpedientProvisioningService(PostgresExpedientRepository(session), ProvenanceReferenceEligibility(session))
    return review, service.create_if_absent(review.specification)
