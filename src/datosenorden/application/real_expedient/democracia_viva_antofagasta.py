"""Official, bounded citizen expedient for Democracia Viva in Antofagasta.

OCR is used only to locate and verify material in the original official PDFs.
The persisted evidence remains the official document URL, hash and page locator.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from hashlib import sha256

from sqlalchemy import select
from sqlalchemy.orm import Session

from datosenorden.application.provenance.models import ProvenanceClass
from datosenorden.application.real_expedient.citizen_projection import (
    CitizenDocument,
    CitizenEvidence,
    CitizenKnowledgeCutoff,
    CitizenProjectionContext,
    CitizenQuestionAnswer,
    CitizenTimelineEvent,
)
from datosenorden.application.real_expedient.eligibility import ProvenanceReferenceEligibility
from datosenorden.application.real_expedient.models import (
    EpistemicClass,
    ExpedientReferences,
    ExpedientSpecification,
    ExpedientStatus,
    NarrativeStatement,
)
from datosenorden.application.real_expedient.service import ExpedientProvisioningService
from datosenorden.etl.core.contracts import (
    ClaimRecord,
    DatasetRecord,
    EntityRecord,
    EntityType,
    EvidenceRecord,
    GraphBatch,
    SourceInfo,
    SourceRecordPayload,
    WorkflowStatus,
)
from datosenorden.etl.loaders.graph_loader import GraphLoader
from datosenorden.infrastructure.real_expedient.repository import PostgresExpedientRepository
from datosenorden.models import Claim, Entity, Evidence, Source, SourceRecord


EXPEDIENT_ID = "EXP-REAL-DEMOCRACIA-VIVA-ANTOFAGASTA"
TITLE = "Democracia Viva y los convenios de Antofagasta"
QUESTION = "¿Qué ocurrió con los $426 millones transferidos mediante los tres convenios con Fundación Democracia Viva y qué está acreditado hasta ahora?"
SUMMARY = (
    "Tres convenios de la SEREMI MINVU de Antofagasta con Fundación Democracia Viva "
    "suman $426 millones. El corpus distingue transferencias, rendiciones y restitución "
    "ordenada: no acredita cuánto fue recuperado ni una condena penal de fondo."
)
RECORD_TYPE = "democracia-viva:antofagasta"

DOCUMENTS = (
    ("re-504", "MINVU", "SEREMI MINVU Antofagasta", "https://documentos.minvu.cl/regionII/seremi/resoluciones_exentas/Documentos/res_ex_504_2022.pdf", date(2022, 10, 3), "Resolución Exenta N°504/2022", "SHA-256 0e04e15e99d67d500bdb1320b9b8bf09931468fc21b019fea625ec55243b6b8a; p. 1, 3 y 9; OCR verificado"),
    ("re-576", "MINVU", "SEREMI MINVU Antofagasta", "https://documentos.minvu.cl/regionII/seremi/resoluciones_exentas/Documentos/res_ex_576_2022.pdf", date(2022, 10, 27), "Resolución Exenta N°576/2022", "SHA-256 0dd6a3d97b5210106cb46bd2243255d52385b71f078f830082902d584fe26fc3; p. 1, 4 y 9; OCR verificado"),
    ("re-641", "MINVU", "SEREMI MINVU Antofagasta", "https://documentos.minvu.cl/regionII/seremi/resoluciones_exentas/Documentos/res_ex_641_2022.pdf", date(2022, 11, 29), "Resolución Exenta N°641/2022", "SHA-256 8530cfe82bcbfd9f98e472de68cb545a8b29c9bc0b7b03cbae56312a0b80af20; p. 1, 11 y 12; OCR verificado"),
    ("dijur-1302", "MINVU", "Ministerio de Vivienda y Urbanismo", "https://documentos.minvu.cl/min_vivienda/resoluciones_exentas/Documents/RE.DIJURN%C2%B0%201302.pdf", date(2023, 8, 4), "Resolución DIJUR N°1302", "SHA-256 819c621d7b03964414bc44ea48f0e983af2d490daa8c6b865cbb68ff1ff05487; p. 1, 2 y 6; OCR verificado salvo fecha de transferencia incierta"),
    ("cgr-465", "Contraloría General de la República", "Contraloría General de la República", "https://documentos.minvu.cl/bitstreams/46f53dd4-acc5-4e22-9be7-484be344688a/download", date(2023, 8, 31), "Informe Final de Avance N°465-1/2023", "SHA-256 13a5bbe1de502007111325772533712ccd0dd39c8dda1c5d8111d597abdb3090; pp. 8-10 y 41-42; OCR verificado"),
    ("minvu-termination", "MINVU", "Ministerio de Vivienda y Urbanismo", "https://www.minvu.gob.cl/noticia/minvu-pone-fin-a-los-contratos-con-democracia-viva-y-fundacion-debera-restituir-los-dineros-otorgados-por-la-cartera/", date(2023, 7, 14), "Comunicación MINVU sobre término y restitución", "Término de tres convenios y restitución agregada ordenada"),
    ("transparency-387", "MINVU", "SEREMI MINVU Antofagasta", "https://documentos.minvu.cl/bitstreams/306c7686-f7f7-4f64-a52f-d4a3e37b6ee9/download", date(2023, 8, 25), "Resolución Exenta N°387/2023", "SHA-256 6f6977c7ce9054279ff6521d463966bdd05ac9edd15b250b9fcab7ae05ab9aff; p. 1; decisión de acceso, no rendición"),
    ("fiscalia-formalization", "Fiscalía de Chile", "Ministerio Público", "https://www.fiscaliadechile.cl/actualidad/noticias/regionales/caso-convenios-equipo-de-la-fiscalia-formalizo-por-fraude-al-fisco", date(2023, 12, 18), "Caso Convenios: formalización en arista Democracia Viva", "Estado procesal informado por Fiscalía; no sentencia"),
    ("pjud-6594", "Poder Judicial", "Corte de Apelaciones de Antofagasta", "https://www.pjud.cl/prensa-y-comunicaciones/noticias-del-poder-judicial/98661", date(2023, 9, 14), "Rol 6.594-2023", "Recurso de protección relativo al término administrativo; no mérito penal"),
    ("cgr-followup", "Contraloría General de la República", "Contraloría General de la República", "https://documentos.minvu.cl/bitstreams/1f2ac6a9-ae98-46ee-9cc2-ec17ebfc09da/download", date(2025, 5, 30), "Seguimiento al Informe de Investigación Especial N°465/2023", "Seguimiento administrativo"),
)


def _record(key: str, payload: dict[str, object], retrieved_at: datetime) -> SourceRecordPayload:
    return SourceRecordPayload(key, RECORD_TYPE, sha256(repr(sorted(payload.items())).encode()).hexdigest(), payload, retrieved_at, status=WorkflowStatus.VALIDATED)


def democracia_viva_batches(retrieved_at: datetime | None = None) -> tuple[GraphBatch, ...]:
    retrieved_at = retrieved_at or datetime.now(UTC)
    subject = EntityRecord(EntityType.PUBLIC_PROJECT, TITLE, "cl-public-money-democracia-viva-antofagasta", "Tres convenios SEREMI MINVU Antofagasta y Fundación Democracia Viva", "democracia-viva-antofagasta")
    records: list[SourceRecordPayload] = []
    evidence: list[EvidenceRecord] = []
    claims: list[ClaimRecord] = []
    for key, source, origin, url, when, title, locator in DOCUMENTS:
        payload = {"hosting_source": source, "document_origin": origin, "official_url": url, "document_sha256": locator.split(";", 1)[0].replace("SHA-256 ", "") if locator.startswith("SHA-256") else None, "locator": locator}
        record = _record(f"{RECORD_TYPE}:{key}", payload, retrieved_at)
        item = EvidenceRecord(record, source, title, url, when, locator, payload)
        records.append(record); evidence.append(item)
        claims.append(ClaimRecord(subject, key.upper().replace("-", "_"), record, item, object_value={"locator": locator}, valid_from=when, status=WorkflowStatus.VALIDATED))
    return (GraphBatch(SourceInfo("MINVU", "Ministerio de Vivienda y Urbanismo", "https://www.minvu.gob.cl/", retrieved_at=retrieved_at, metadata={"source_status": "DATA_AVAILABLE", "connector_status": "NOT_ACTIVE"}), DatasetRecord("MINVU", "democracia-viva-antofagasta", "Corpus oficial acotado: convenios, fiscalización y estados procedimentales", "2026-08-26", "https://www.minvu.gob.cl/", None, retrieved_at), tuple(records), (subject,), tuple(evidence), tuple(claims), (), len(records)),)


def provision_democracia_viva_antofagasta(session: Session):
    for batch in democracia_viva_batches():
        GraphLoader(session).load(batch)
    entity = session.scalar(select(Entity).where(Entity.external_id == "cl-public-money-democracia-viva-antofagasta"))
    records = sorted(session.scalars(select(SourceRecord).where(SourceRecord.record_type == RECORD_TYPE)).all(), key=lambda item: str(item.id))
    claims = sorted(session.scalars(select(Claim).join(SourceRecord).where(SourceRecord.record_type == RECORD_TYPE)).all(), key=lambda item: str(item.id))
    evidence = sorted(session.scalars(select(Evidence).join(SourceRecord).where(SourceRecord.record_type == RECORD_TYPE)).all(), key=lambda item: str(item.id))
    source_names = tuple(sorted({row[1] for row in DOCUMENTS}))
    sources = sorted(session.scalars(select(Source).where(Source.name.in_(source_names))).all(), key=lambda item: str(item.id))
    if entity is None or len(records) != len(DOCUMENTS) or len(claims) != len(DOCUMENTS) or len(evidence) != len(DOCUMENTS):
        raise RuntimeError("Democracia Viva Antofagasta corpus is incomplete")
    claim_ids, evidence_ids = tuple(str(item.id) for item in claims), tuple(str(item.id) for item in evidence)
    def fact(key: str, section: str, text: str) -> NarrativeStatement:
        return NarrativeStatement(key, section, text, EpistemicClass.FACT, claim_ids, evidence_ids)
    spec = ExpedientSpecification(EXPEDIENT_ID, TITLE, QUESTION, SUMMARY, ProvenanceClass.REAL, ExpedientStatus.PUBLISHED, 1, ExpedientReferences(claim_ids, evidence_ids, entity_ids=(str(entity.id),), source_ids=tuple(str(item.id) for item in sources)), (
        fact("three-agreements", "convenios", "El corpus oficial identifica tres convenios: RE N°504/2022 por $200.000.000 para habitabilidad primaria en Ecuachilepe; RE N°576/2022 por $170.000.000 para habitabilidad primaria en Irarrázabal Etapa I; y RE N°641/2022 por $56.000.000 para diagnósticos, planes de intervención y acciones sociales y comunitarias."),
        fact("amount-reconciliation", "dinero_publico", "Los montos individuales suman $426.000.000, cifra que coincide con el universo de tres convenios informado por Contraloría."),
        fact("cgr-cutoff", "rendiciones", "La tabla de Contraloría, con corte al 30 de junio de 2023, registra para Democracia Viva $426.000.000 transferidos, $116.963.639 rendidos, $12.146.280 aprobados por la SEREMI y $309.036.361 por rendir."),
        fact("cgr-findings", "fiscalizacion", "Contraloría registró falta de fundamentos documentados para la designación, falta de antecedentes para asociar fondos, prestaciones, tiempos y costos, y deficiencias de control y monitoreo de transferencias y rendiciones."),
        fact("restitution", "restitucion", "MINVU informó una restitución agregada ordenada de $391.768.516. La Resolución DIJUR N°1302 menciona una solicitud de reintegro de $52.574.302 relativa al convenio RE N°641."),
        fact("criminal-status", "proceso_penal", "Fiscalía informó formalizaciones en la arista Democracia Viva. El corpus incorporado no certifica una sentencia penal de fondo."),
        NarrativeStatement("transfer-limit", "limitations", "$426 millones transferidos no equivale a $426 millones robados, ni acredita por sí solo un delito o responsabilidad individual.", EpistemicClass.UNKNOWN),
        NarrativeStatement("rendition-limit", "limitations", "Un monto rendido no equivale necesariamente a un monto aprobado; y el monto por rendir al corte de Contraloría no equivale a dinero robado.", EpistemicClass.UNKNOWN),
        NarrativeStatement("recovery-limit", "limitations", "Una restitución ordenada o solicitada no acredita recuperación efectiva. El corpus no permite determinar cuánto dinero fue recuperado.", EpistemicClass.UNKNOWN),
        NarrativeStatement("cgr-limit", "limitations", "Los hallazgos de Contraloría son fiscalizadores y administrativos; no acreditan por sí mismos culpabilidad penal.", EpistemicClass.UNKNOWN),
        NarrativeStatement("formalization-limit", "limitations", "Una formalización es una etapa de investigación penal y no equivale a una condena.", EpistemicClass.UNKNOWN),
        NarrativeStatement("source-limit", "limitations", "No se adquirieron las rendiciones individuales originales y el saldo de restitución ordenada no está distribuido documentalmente entre los convenios N°504 y N°576.", EpistemicClass.UNKNOWN),
    ))
    return ExpedientProvisioningService(PostgresExpedientRepository(session), ProvenanceReferenceEligibility(session)).create_if_absent(spec)


def democracia_viva_citizen_context() -> CitizenProjectionContext:
    evidence = tuple(CitizenEvidence(key, title, source, url, locator, when.isoformat()) for key, source, _origin, url, when, title, locator in DOCUMENTS)
    return CitizenProjectionContext(
        "Trazabilidad de dinero público / arista administrativa y penal", evidence,
        (CitizenTimelineEvent("2022-09-20", "ADMINISTRATIVE", "Suscripción de los convenios RE N°504 y RE N°576.", "re-504"), CitizenTimelineEvent("2022-10-03", "ADMINISTRATIVE", "Resolución Exenta N°504.", "re-504"), CitizenTimelineEvent("2022-10-27", "ADMINISTRATIVE", "Resolución Exenta N°576.", "re-576"), CitizenTimelineEvent("2022-10-25", "ADMINISTRATIVE", "Suscripción del convenio RE N°641.", "re-641"), CitizenTimelineEvent("2022-11-29", "ADMINISTRATIVE", "Resolución Exenta N°641.", "re-641"), CitizenTimelineEvent("2023-06-30", "ADMINISTRATIVE", "Corte de rendiciones informado por Contraloría.", "cgr-465"), CitizenTimelineEvent("2023-07-14", "ADMINISTRATIVE", "MINVU informó término de tres convenios y restitución agregada ordenada.", "minvu-termination"), CitizenTimelineEvent("2023-08-04", "ADMINISTRATIVE", "Resolución DIJUR N°1302 sobre recurso administrativo relativo al convenio RE N°641.", "dijur-1302"), CitizenTimelineEvent("2023-12-18", "JUDICIAL", "Fiscalía informó formalizaciones en la arista Democracia Viva.", "fiscalia-formalization"), CitizenTimelineEvent("2025-05-30", "ADMINISTRATIVE", "Seguimiento de Contraloría al Informe N°465/2023.", "cgr-followup")),
        actors=("SEREMI MINVU Antofagasta", "SERVIU Antofagasta", "Fundación Democracia Viva", "Contraloría General de la República", "Ministerio Público", "Poder Judicial"),
        documents=tuple(CitizenDocument(title, origin, "Documento oficial", "Corpus primario", url, when.isoformat()) for _key, _source, origin, url, when, title, _locator in DOCUMENTS),
        sources=("MINVU", "SERVIU Antofagasta", "Contraloría General de la República", "Fiscalía de Chile", "Poder Judicial"),
        topics=("Dinero público", "Transferencias", "Convenios", "Rendiciones", "Fiscalización", "Restitución", "Investigación penal", "Proceso judicial"),
        answers=(
            CitizenQuestionAnswer("¿Cuánto dinero recibió Democracia Viva?", "Los tres convenios suman $426.000.000. Esa cifra identifica un universo de transferencias; no prueba por sí sola un delito.", "FACT"),
            CitizenQuestionAnswer("¿Cuántos convenios fueron?", "Tres: RE N°504, RE N°576 y RE N°641 de 2022.", "FACT"),
            CitizenQuestionAnswer("¿Para qué era cada convenio?", "Los dos primeros trataban habitabilidad primaria en Ecuachilepe e Irarrázabal Etapa I; el tercero, diagnósticos y planes de intervención en campamentos.", "FACT"),
            CitizenQuestionAnswer("¿Cuánto dinero estaba rendido al corte de Contraloría?", "Al 30 de junio de 2023, la tabla CGR registra $116.963.639 rendidos.", "FACT"),
            CitizenQuestionAnswer("¿Cuánto faltaba por rendir?", "La misma tabla registra $309.036.361 por rendir a esa fecha de corte. No lo presenta como una cifra de robo.", "FACT"),
            CitizenQuestionAnswer("¿Contraloría dijo que se robaron esos recursos?", "No. El informe contiene hallazgos de fiscalización y control; no es una sentencia penal.", "LIMITATION"),
            CitizenQuestionAnswer("¿Cuánto dinero se ordenó restituir?", "MINVU informó una restitución agregada ordenada de $391.768.516.", "FACT"),
            CitizenQuestionAnswer("¿Cuánto dinero fue efectivamente recuperado?", "No está acreditado por el corpus oficial incorporado.", "UNKNOWN"),
            CitizenQuestionAnswer("¿Qué observó Contraloría?", "Entre otros puntos, registró falta de fundamentos documentados para la designación y debilidades de control de transferencias y rendiciones.", "FACT"),
            CitizenQuestionAnswer("¿Qué investiga Fiscalía?", "Fiscalía informó formalizaciones en la arista Democracia Viva. Esa etapa no equivale a culpabilidad ni a condena.", "FACT"),
            CitizenQuestionAnswer("¿Hay personas condenadas?", "El corpus incorporado no certifica una sentencia penal de fondo.", "UNKNOWN"),
            CitizenQuestionAnswer("¿Qué sabemos del convenio RE N°641?", "Fue aprobado el 29 de noviembre de 2022, por $56.000.000, para diagnósticos y planes de intervención; DIJUR N°1302 trata su liquidación administrativa.", "FACT"),
            CitizenQuestionAnswer("¿Tenemos las rendiciones individuales?", "No. Se adquirió una resolución de transparencia sobre una solicitud, no las rendiciones mismas.", "UNKNOWN"),
            CitizenQuestionAnswer("¿Qué parte sigue sin estar acreditada?", "La recuperación efectiva, las rendiciones individuales y una sentencia penal de fondo no están certificadas en este corpus.", "LIMITATION"),
        ),
        missing_knowledge=("No se adquirieron las rendiciones individuales originales.", "No hay evidencia de recuperación efectiva.", "No hay sentencia penal de fondo certificada."),
        knowledge_cutoff=CitizenKnowledgeCutoff("2025-05-30", "2025-05-30", "Corpus oficial incorporado con convenios, informe CGR, actos administrativos y comunicaciones procesales."),
        official_title="Arista SEREMI MINVU Antofagasta – Fundación Democracia Viva",
    )
