"""Certified REAL content specification for BCN History / LeyChile Law 21.827.

The module contains the editorial projection only.  Acquisition is performed by
the bounded BCN and LeyChile adapters; persistence is deterministic and uses
their artifact hashes as provenance metadata.
"""
from __future__ import annotations

from datetime import UTC, date, datetime
from hashlib import sha256

from sqlalchemy import select
from sqlalchemy.orm import Session

from datosenorden.application.provenance.models import ProvenanceClass
from datosenorden.application.real_expedient.citizen_projection import (
    CitizenDocument, CitizenEvidence, CitizenKnowledgeCutoff,
    CitizenProjectionContext, CitizenQuestionAnswer, CitizenTimelineEvent,
)
from datosenorden.application.real_expedient.eligibility import ProvenanceReferenceEligibility
from datosenorden.application.real_expedient.models import (
    EpistemicClass, ExpedientReferences, ExpedientSpecification, ExpedientStatus,
    NarrativeStatement,
)
from datosenorden.application.real_expedient.service import ExpedientProvisioningService
from datosenorden.etl.core.contracts import (
    ClaimRecord, DatasetRecord, EntityRecord, EntityType, EvidenceRecord, GraphBatch,
    SourceInfo, SourceRecordPayload, WorkflowStatus,
)
from datosenorden.etl.loaders.graph_loader import GraphLoader
from datosenorden.infrastructure.real_expedient.repository import PostgresExpedientRepository
from datosenorden.models import Claim, Evidence, Entity, Source, SourceRecord

EXPEDIENT_ID = "EXP-REAL-ESCUELAS-PROTEGIDAS-18156-04"
BULLETIN = "18156-04"
LAW_NUMBER = "21.827"
LAW_URL = "https://www.bcn.cl/leychile/navegar?idNorma=1226950&idVersion=2026-08-12"
HISTORY_URL = "https://www.bcn.cl/historiadelaley/nc/historia-de-la-ley/8521/"
LAW_HASH = "96122d21cf14ad83c50481a7003277cf9dbb6406eba67a17daf00ad033f4dca5"
HISTORY_HASH = "6076b42a7cc70a4c9e7e167b9e33a7bc358adce08ef699d2c86641ef1be71172"
PHONE_VOTE_HASH = "f64c9cfcb37f19e9e3fad72304657a50d546fcbbc2ec85c2bc8a39b171d4bfe5"


def _record(external_id: str, payload: dict[str, object], retrieved_at: datetime) -> SourceRecordPayload:
    return SourceRecordPayload(external_id, "bcn:escuelas_protegidas", sha256(repr(sorted(payload.items())).encode()).hexdigest(), payload, retrieved_at, status=WorkflowStatus.VALIDATED)


def _subject() -> EntityRecord:
    return EntityRecord(EntityType.PUBLIC_PROJECT, "Escuelas Protegidas", "cl-congreso-boletin-18156-04", "Boletín 18.156-04", "escuelas-protegidas-18156-04")


def escuelas_batches(retrieved_at: datetime | None = None) -> tuple[GraphBatch, GraphBatch]:
    """Build immutable, source-separated Law and history batches for this corpus."""
    retrieved_at = retrieved_at or datetime.now(UTC)
    subject = _subject()
    law_payload = {"hosting_source": "LeyChile", "document_origin": "Diario Oficial", "canonical_url": LAW_URL, "norm_id": "1226950", "version": "2026-08-12", "sha256": LAW_HASH, "locator": "Ley 21.827, artículo 1, artículo 16 J"}
    law = _record("leychile:1226950:2026-08-12", law_payload, retrieved_at)
    law_evidence = EvidenceRecord(law, "LeyChile", "Ley 21.827, texto vigente", LAW_URL, date(2026, 8, 12), "Artículo 16 J", law_payload)
    law_claims = tuple(ClaimRecord(subject, predicate, law, law_evidence, object_value={"locator": "Artículo 16 J", "text": text}, valid_from=date(2026, 8, 12), status=WorkflowStatus.VALIDATED) for predicate, text in (
        ("LAW_PUBLISHED", "La Ley 21.827 fue publicada el 12 de agosto de 2026."),
        ("BACKPACK_REVIEW_RULE", "Los sostenedores pueden incorporar la revisión de mochilas, bolsos u otros efectos personales, excluidas las vestimentas."),
        ("BODY_AND_CLOTHING_LIMIT", "Se prohíbe requerir que el estudiante se desnude y la revisión corporal y de vestimentas que esté usando."),
        ("FORCED_SEARCH_LIMIT", "El personal del establecimiento no puede realizar la revisión de manera forzosa."),
        ("RIGHTS_SAFEGUARDS", "La medida debe resguardar igualdad ante la ley, no discriminación arbitraria, vida privada, honra, interés superior y derecho a la educación."),
        ("PHONE_FINAL_TEXT", "El texto íntegro de la Ley 21.827 no contiene una regla explícita sobre teléfonos, desbloqueo, contenido digital o exhibición."),
    ))
    law_batch = GraphBatch(SourceInfo("LeyChile", "Biblioteca del Congreso Nacional de Chile", "https://www.bcn.cl/leychile/", retrieved_at=retrieved_at, metadata={"source_status": "DATA_AVAILABLE", "connector_status": "NOT_ACTIVE"}), DatasetRecord("LeyChile", "leychile-norm", "Versión canónica de una ley vigente", "1226950@2026-08-12", LAW_URL, LAW_HASH, retrieved_at, law_payload), (law,), (subject,), (law_evidence,), law_claims, (), 1)
    history_payload = {"hosting_source": "Biblioteca del Congreso Nacional de Chile", "document_origin": "Cámara de Diputadas y Diputados", "official_url": HISTORY_URL, "law_number": LAW_NUMBER, "bulletin": BULLETIN, "sha256": HISTORY_HASH, "history_id": "8521"}
    history = _record("bcn-history:8521", history_payload, retrieved_at)
    vote_payload = {**history_payload, "section": "1-5", "section_sha256": PHONE_VOTE_HASH, "locator": "Sesión 15, 21-04-2026; indicación renovada al artículo 16 J; votación 88690"}
    vote_evidence = EvidenceRecord(history, "Biblioteca del Congreso Nacional de Chile", "Historia de la Ley 21.827 — discusión en Sala, Cámara", HISTORY_URL + "#collapse1_subacordeon5", date(2026, 4, 21), "Indicación sobre dispositivos móviles y desbloqueo; resultado de votación.", vote_payload)
    history_claims = (
        ClaimRecord(subject, "PHONE_PROPOSAL", history, vote_evidence, object_value={"locator": vote_payload["locator"], "text": "La indicación renovada propuso excluir dispositivos móviles electrónicos de comunicación personal y prohibir manipulación, revisión, acceso al contenido, desbloqueo o exhibición."}, status=WorkflowStatus.VALIDATED),
        ClaimRecord(subject, "PHONE_VOTE", history, vote_evidence, object_value={"vote_id": "88690", "date": "2026-04-21", "for": 60, "against": 89, "abstentions": 0, "result": "REJECTED", "locator": vote_payload["locator"]}, status=WorkflowStatus.VALIDATED),
    )
    history_batch = GraphBatch(SourceInfo("Biblioteca del Congreso Nacional de Chile", "Biblioteca del Congreso Nacional de Chile", "https://www.bcn.cl/historiadelaley/", retrieved_at=retrieved_at, metadata={"source_status": "DATA_AVAILABLE", "connector_status": "NOT_ACTIVE"}), DatasetRecord("Biblioteca del Congreso Nacional de Chile", "bcn-law-history", "Historia legislativa consolidada de Ley 21.827", "8521@2026-08-12", HISTORY_URL, HISTORY_HASH, retrieved_at, history_payload), (history,), (subject,), (vote_evidence,), history_claims, (), 1)
    return law_batch, history_batch


def provision_escuelas_protegidas(session: Session):
    for batch in escuelas_batches():
        GraphLoader(session).load(batch)
    entity = session.scalar(select(Entity).where(Entity.external_id == "cl-congreso-boletin-18156-04"))
    records = session.scalars(select(SourceRecord).where(SourceRecord.record_type == "bcn:escuelas_protegidas").order_by(SourceRecord.external_id)).all()
    claims = session.scalars(select(Claim).join(SourceRecord).where(SourceRecord.record_type == "bcn:escuelas_protegidas").order_by(Claim.predicate)).all()
    evidence = session.scalars(select(Evidence).join(SourceRecord).where(SourceRecord.record_type == "bcn:escuelas_protegidas").order_by(Evidence.title)).all()
    sources = session.scalars(select(Source).where(Source.name.in_(("LeyChile", "Biblioteca del Congreso Nacional de Chile"))).order_by(Source.name)).all()
    if entity is None or len(records) != 2 or len(claims) != 8 or len(evidence) != 2 or len(sources) != 2:
        raise RuntimeError("Escuelas Protegidas corpus is incomplete")
    ids = {item.predicate: str(item.id) for item in claims}; evidence_ids = tuple(str(item.id) for item in evidence)
    support = tuple(ids.values())
    fact = lambda key, section, text: NarrativeStatement(key, section, text, EpistemicClass.FACT, support, evidence_ids)
    specification = ExpedientSpecification(EXPEDIENT_ID, "Escuelas Protegidas: revisión de pertenencias", "¿Qué puede revisar ahora un establecimiento educacional y cuáles son los límites de esa facultad?", "La Ley 21.827 fue publicada el 12 de agosto de 2026. El texto vigente permite que los reglamentos internos incorporen revisiones de pertenencias bajo condiciones y límites expresos. Este expediente separa esa norma de una indicación sobre teléfonos que fue rechazada durante la tramitación.", ProvenanceClass.REAL, ExpedientStatus.PUBLISHED, 1, ExpedientReferences(tuple(str(item.id) for item in claims), evidence_ids, entity_ids=(str(entity.id),), source_ids=tuple(str(item.id) for item in sources)), (
        fact("fact-publication", "current_law", "La Ley 21.827 fue publicada el 12 de agosto de 2026."),
        fact("fact-backpacks", "current_law", "El artículo 16 J permite incorporar en los reglamentos internos la revisión de mochilas, bolsos u otros efectos personales, excluidas las vestimentas."),
        fact("fact-limits", "current_law", "El texto prohíbe requerir que el estudiante se desnude, la revisión corporal y de vestimentas que esté usando, y que el personal realice la revisión de manera forzosa."),
        fact("fact-rights", "current_law", "El ejercicio de la medida debe resguardar vida privada y honra, igualdad ante la ley, no discriminación arbitraria, interés superior y derecho a la educación."),
        fact("fact-phone-history", "legislative_history", "Durante la tramitación se propuso excluir dispositivos móviles y exigir que no se pidiera desbloqueo o exhibición; esa indicación fue rechazada en la Cámara el 21 de abril de 2026, con 60 votos a favor, 89 en contra y 0 abstenciones."),
        fact("fact-phone-final", "current_law", "El texto íntegro de la Ley 21.827 no contiene una regla explícita específica sobre teléfonos o desbloqueo."),
        NarrativeStatement("limitation-phone", "limitations", "El rechazo de una prohibición propuesta no permite inferir por sí solo una facultad no escrita: este expediente no concluye que la ley autorice revisar o desbloquear teléfonos.", EpistemicClass.UNKNOWN),
        NarrativeStatement("limitation-implementation", "limitations", "El texto legal no permite afirmar cómo cada establecimiento aplicará la medida en un caso concreto.", EpistemicClass.UNKNOWN),
    ))
    return ExpedientProvisioningService(PostgresExpedientRepository(session), ProvenanceReferenceEligibility(session)).create_if_absent(specification)


def escuelas_citizen_context() -> CitizenProjectionContext:
    evidence = (CitizenEvidence("law", "Ley 21.827, texto vigente", "LeyChile", LAW_URL, "Artículo 16 J.", "2026-08-12"), CitizenEvidence("history", "Historia de la Ley N° 21.827", "Biblioteca del Congreso Nacional de Chile", HISTORY_URL, "Sesión 15, Cámara, 21-04-2026.", "2026-04-21"))
    return CitizenProjectionContext("Expediente legislativo / ley vigente", evidence, (
        CitizenTimelineEvent("2026-04-07", "PROCEDURAL", "Ingreso del mensaje."), CitizenTimelineEvent("2026-04-21", "SUBSTANTIVE", "La Cámara rechazó la indicación sobre dispositivos móviles y desbloqueo.", "history"), CitizenTimelineEvent("2026-05-19", "SUBSTANTIVE", "El Senado aprobó el proyecto con modificaciones."), CitizenTimelineEvent("2026-06-02", "PROCEDURAL", "La Cámara aprobó las modificaciones del Senado."), CitizenTimelineEvent("2026-08-12", "ADMINISTRATIVE", "Publicación de la Ley 21.827.", "law")), documents=(CitizenDocument("Boletín 18.156-04 — Escuelas Protegidas", "Biblioteca del Congreso Nacional de Chile", "Ficha e historia legislativa", "Proyecto", HISTORY_URL, "2026-04-07"), CitizenDocument("Historia de la Ley N° 21.827", "Biblioteca del Congreso Nacional de Chile", "Historia legislativa; origen documental Cámara/Senado según cada etapa", "Tramitación", HISTORY_URL, "2026-08-12"), CitizenDocument("Ley 21.827", "LeyChile", "Texto vigente; materias: establecimientos educacionales y colegios", "Ley publicada", LAW_URL, "2026-08-12")), sources=("Biblioteca del Congreso Nacional de Chile", "LeyChile"), answers=(
            CitizenQuestionAnswer("¿Pueden revisar la mochila de un estudiante?", "La ley permite incorporarlo al reglamento interno bajo las condiciones del artículo 16 J.", "FACT"),
            CitizenQuestionAnswer("¿Pueden obligarlo a abrirla?", "El personal del establecimiento no puede realizar la revisión de manera forzosa.", "FACT"),
            CitizenQuestionAnswer("¿Pueden revisar su ropa?", "El texto prohíbe la revisión corporal y de las vestimentas que el estudiante esté usando.", "FACT"),
            CitizenQuestionAnswer("¿Pueden revisar o exigir desbloquear su teléfono?", "Existió una indicación sobre teléfonos y desbloqueo, que fue rechazada. La ley vigente no contiene una regla explícita específica sobre teléfonos; de ello no puede inferirse una facultad no escrita.", "LIMITATION"),
            CitizenQuestionAnswer("¿Qué resguardos exige la ley?", "El artículo 16 J exige resguardar igualdad ante la ley, no discriminación arbitraria, vida privada, honra, interés superior y derecho a la educación.", "FACT"),
            CitizenQuestionAnswer("¿Qué se propuso pero no quedó en el texto final?", "La indicación renovada propuso excluir dispositivos móviles y prohibir manipulación, acceso al contenido, desbloqueo o exhibición; fue rechazada.", "FACT"),
            CitizenQuestionAnswer("¿Qué diferencia existe entre lo discutido y la ley vigente?", "Las indicaciones y votaciones describen la tramitación; la regla aplicable se determina por el texto vigente de LeyChile. Una propuesta rechazada no es derecho vigente.", "LIMITATION"),
            CitizenQuestionAnswer("¿Cuándo se publicó la ley?", "El 12 de agosto de 2026.", "FACT"),
        ), knowledge_cutoff=CitizenKnowledgeCutoff("2026-08-12", "2026-08-12", "La ley vigente se acredita en LeyChile; la historia legislativa se acredita en el expediente consolidado de BCN."))
