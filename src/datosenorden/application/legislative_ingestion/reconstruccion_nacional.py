"""Certified, bounded REAL content for bulletin 18.216-05.

This is a tramitación dossier, not a claim that the bill is current law.  Every
public assertion is tied to a specifically acquired official Senate or DIPRES
resource; the acquisition artifacts remain local staging inputs.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime
from hashlib import sha256

from sqlalchemy import select
from sqlalchemy.orm import Session

from datosenorden.application.provenance.models import ProvenanceClass
from datosenorden.application.real_expedient.citizen_projection import CitizenDocument, CitizenEvidence, CitizenKnowledgeCutoff, CitizenProjectionContext, CitizenQuestionAnswer, CitizenTimelineEvent
from datosenorden.application.real_expedient.eligibility import ProvenanceReferenceEligibility
from datosenorden.application.real_expedient.models import EpistemicClass, ExpedientReferences, ExpedientSpecification, ExpedientStatus, NarrativeStatement
from datosenorden.application.real_expedient.service import ExpedientProvisioningService
from datosenorden.etl.core.contracts import ClaimRecord, DatasetRecord, EntityRecord, EntityType, EvidenceRecord, GraphBatch, SourceInfo, SourceRecordPayload, WorkflowStatus
from datosenorden.etl.loaders.graph_loader import GraphLoader
from datosenorden.infrastructure.real_expedient.repository import PostgresExpedientRepository
from datosenorden.models import Claim, Evidence, Entity, Source, SourceRecord

EXPEDIENT_ID = "EXP-REAL-LEGISLATIVE-18216-05"
BULLETIN = "18216-05"
TITLE = "Para la reconstrucción nacional y el desarrollo económico y social"
PROJECT_URL = "https://tramitacion.senado.cl/appsenado/templates/tramitacion/index.php?boletin_ini=18216-05"
GENERAL_VOTE_URL = "https://www.senado.cl/comunicaciones/noticias/senado-aprueba-en-general-proyecto-de-reconstruccion-nacional-y-desarrollo"
MIXED_URL = "https://www.senado.cl/actividad-legislativa/sala-de-sesiones/sesiones-de-sala/10237"
VETO_URL = "https://tramitacion.senado.cl/appsenado/index.php?ac=getDocumento&mo=sesionessala&nrobol=1821605_P&teseid=81040"
FISCAL_URL = "https://tramitacion.senado.cl/appsenado/index.php?ac=getDocto&iddocto=36160&mo=tramitacion&tipodoc=ofic"
HASHES = {"project": "da42bc77357858bf4c8978b766a856fa1f2e2b6787f3a764f1abd3dd8e4b95cf", "general": "7ff26ad99845fe6087d313364bca8066ea6dbdca90aa80f4944184c819051426", "mixed": "594e209cd06060b56f7316f23dfe6a2098a26ed146e50b8fd6b2feec2241383b", "veto": "42c5fedd620fb4476ea39e16e95874797b52c195013f4ea884fb12f945e480d2", "fiscal": "09ff4a171acee76f574b92222e2b0a0ec91a6a057f9d03f6a0898152624e628b"}

def _record(key: str, payload: dict[str, object], retrieved_at: datetime) -> SourceRecordPayload:
    return SourceRecordPayload(key, "senado:reconstruccion_nacional", sha256(repr(sorted(payload.items())).encode()).hexdigest(), payload, retrieved_at, status=WorkflowStatus.VALIDATED)

def reconstruccion_batch(retrieved_at: datetime | None = None) -> GraphBatch:
    retrieved_at = retrieved_at or datetime.now(UTC)
    subject = EntityRecord(EntityType.PUBLIC_PROJECT, TITLE, "cl-congreso-boletin-18216-05", "Boletín 18.216-05", "reconstruccion-nacional-18216-05")
    entries = (("project", PROJECT_URL, "Ficha de tramitación del Boletín 18.216-05", date(2026,4,22), "Identidad, origen ejecutivo y estado en tramitación."), ("general", GENERAL_VOTE_URL, "Senado aprueba en general proyecto de reconstrucción nacional y desarrollo social", date(2026,6,24), "Aprobación de la idea de legislar: 26 a favor, 23 en contra y 1 abstención."), ("mixed", MIXED_URL, "Sesión especial N°46 — informe de Comisión Mixta", date(2026,7,22), "Comisión Mixta para resolver divergencia entre ambas Cámaras."), ("veto", VETO_URL, "Sesión del Senado — observaciones presidenciales", date(2026,8,12), "Observaciones presidenciales a los artículos 32, 39 y 40."), ("fiscal", FISCAL_URL, "Informe Financiero Complementario N°093/2026", date(2026,5,11), "Estimaciones fiscales de indicaciones; no mide resultados observados."))
    records=[]; evidence=[]; claims=[]
    for key, url, title, when, locator in entries:
        payload={"hosting_source":"Senado de la República de Chile", "document_origin":"Senado" if key != "fiscal" else "Ministerio de Hacienda / DIPRES", "official_url":url, "bulletin":BULLETIN, "sha256":HASHES[key], "locator":locator}
        record=_record(f"senado:18216-05:{key}", payload, retrieved_at); records.append(record)
        item=EvidenceRecord(record, "Senado de la República de Chile" if key != "fiscal" else "Ministerio de Hacienda / Dirección de Presupuestos", title, url, when, locator, payload); evidence.append(item)
        text={"project":"La ficha oficial identifica el Boletín 18.216-05 como un proyecto iniciado por mensaje y en tramitación.", "general":"El Senado aprobó en general la idea de legislar el 24 de junio de 2026: 26 votos a favor, 23 en contra y 1 abstención.", "mixed":"El Senado registró el informe de Comisión Mixta para resolver una divergencia entre ambas Cámaras el 22 de julio de 2026.", "veto":"El Senado trató observaciones presidenciales; el registro identifica tres disposiciones: anatocismo, olvido financiero y pago a treinta días.", "fiscal":"El IF Complementario N°093/2026 estima efectos de indicaciones y señala, entre otros, un mayor gasto anual de $4.892 millones desde 2027 para el Fondo de Promoción y Protección de la Propiedad Intelectual, bajo su supuesto de vigencia."}[key]
        claims.append(ClaimRecord(subject, key.upper(), record, item, object_value={"text":text,"locator":locator}, valid_from=when, status=WorkflowStatus.VALIDATED))
    return GraphBatch(SourceInfo("Senado de la República de Chile", "Senado de la República de Chile", PROJECT_URL, retrieved_at=retrieved_at, metadata={"source_status":"DATA_AVAILABLE","connector_status":"NOT_ACTIVE"}), DatasetRecord("Senado de la República de Chile", "reconstruccion-nacional", "Corpus oficial acotado de tramitación", BULLETIN, PROJECT_URL, HASHES["project"], retrieved_at, {"bulletin":BULLETIN}), tuple(records), (subject,), tuple(evidence), tuple(claims), (), 1)

def provision_reconstruccion_nacional(session: Session):
    GraphLoader(session).load(reconstruccion_batch())
    entity=session.scalar(select(Entity).where(Entity.external_id == "cl-congreso-boletin-18216-05"))
    records=session.scalars(select(SourceRecord).where(SourceRecord.record_type == "senado:reconstruccion_nacional")).all(); claims=session.scalars(select(Claim).join(SourceRecord).where(SourceRecord.record_type == "senado:reconstruccion_nacional")).all(); evidence=session.scalars(select(Evidence).join(SourceRecord).where(SourceRecord.record_type == "senado:reconstruccion_nacional")).all(); sources=session.scalars(select(Source).where(Source.name.in_(("Senado de la República de Chile","Ministerio de Hacienda / Dirección de Presupuestos")))).all()
    if entity is None or len(records)!=5 or len(claims)!=5 or len(evidence)!=5: raise RuntimeError("Reconstrucción Nacional corpus is incomplete")
    support=tuple(str(x.id) for x in claims); evidence_ids=tuple(str(x.id) for x in evidence)
    fact=lambda key,section,text: NarrativeStatement(key,section,text,EpistemicClass.FACT,support,evidence_ids)
    spec=ExpedientSpecification(EXPEDIENT_ID,TITLE,"¿Qué cambia este proyecto y cómo fue modificándose durante su tramitación?","El Boletín 18.216-05 reúne cambios en materias tributarias, empleo, inversión, permisos y otras regulaciones. El expediente documenta etapas verificadas de su tramitación, incluida Comisión Mixta y observaciones presidenciales; no lo presenta como una ley vigente.",ProvenanceClass.REAL,ExpedientStatus.PUBLISHED,1,ExpedientReferences(support,evidence_ids,entity_ids=(str(entity.id),),source_ids=tuple(str(x.id) for x in sources)),(fact("identity","what_happened","El proyecto fue iniciado por mensaje y figura en tramitación bajo el Boletín 18.216-05."),fact("general-vote","senate","El Senado aprobó en general la idea de legislar el 24 de junio de 2026, con 26 votos a favor, 23 en contra y 1 abstención."),fact("mixed","mixed_commission","El 22 de julio de 2026 se registró un informe de Comisión Mixta para resolver divergencias entre ambas Cámaras."),fact("veto","veto","El expediente oficial del Senado registra observaciones presidenciales supresivas sobre tres disposiciones: anatocismo, olvido financiero y pago a treinta días."),fact("fiscal","fiscal","El IF Complementario N°093/2026 estima que el Fondo de Promoción y Protección de la Propiedad Intelectual implicaría un mayor gasto anual de $4.892 millones desde 2027, bajo su supuesto de vigencia."),NarrativeStatement("law-status","limitations","No se incorpora una ley vigente: las fuentes adquiridas acreditan una tramitación con observaciones presidenciales, no una publicación de esta iniciativa.",EpistemicClass.UNKNOWN),NarrativeStatement("impact","limitations","Una estimación fiscal no equivale a un resultado económico observado ni permite concluir quién gana o pierde.",EpistemicClass.UNKNOWN),NarrativeStatement("general-vote-limit","limitations","La votación general acredita la aprobación de la idea de legislar, no el apoyo a cada artículo o indicación.",EpistemicClass.UNKNOWN),NarrativeStatement("mixed-limit","limitations","El registro de Comisión Mixta acredita su objeto general; sin un comparado completo no atribuye el texto final de cada divergencia.",EpistemicClass.UNKNOWN)))
    service = ExpedientProvisioningService(PostgresExpedientRepository(session),ProvenanceReferenceEligibility(session))
    return service.create_if_absent(spec)

def _reconstruccion_citizen_context() -> CitizenProjectionContext:
    evidence=(CitizenEvidence("project","Ficha de tramitación","Senado de la República de Chile",PROJECT_URL,"Boletín 18.216-05; ingreso 22-04-2026.","2026-04-22"),CitizenEvidence("vote","Aprobación general del Senado","Senado de la República de Chile",GENERAL_VOTE_URL,"26 a favor, 23 en contra y 1 abstención.","2026-06-24"),CitizenEvidence("veto","Observaciones presidenciales","Senado de la República de Chile",VETO_URL,"Artículos 32, 39 y 40.","2026-08-12"),CitizenEvidence("fiscal","Informe Financiero Complementario N°093/2026","Ministerio de Hacienda / Dirección de Presupuestos",FISCAL_URL,"Estimaciones de indicaciones.","2026-05-11"))
    return CitizenProjectionContext("Expediente legislativo / proyecto en tramitación",evidence,(CitizenTimelineEvent("2026-04-22","PROCEDURAL","Ingreso del proyecto por mensaje.","project"),CitizenTimelineEvent("2026-05-11","SUBSTANTIVE","DIPRES emitió el Informe Financiero Complementario N°093/2026.","fiscal"),CitizenTimelineEvent("2026-06-24","SUBSTANTIVE","El Senado aprobó en general la idea de legislar.","vote"),CitizenTimelineEvent("2026-07-22","PROCEDURAL","Se registró el informe de Comisión Mixta.","vote"),CitizenTimelineEvent("2026-08-10","PROCEDURAL","La Cámara aprobó las observaciones presidenciales, según el registro del Senado.","veto"),CitizenTimelineEvent("2026-08-12","ADMINISTRATIVE","El Senado trató observaciones presidenciales.","veto")),actors=("Presidencia de la República","Ministerio de Hacienda","Cámara de Diputadas y Diputados","Senado de la República","Dirección de Presupuestos"),documents=(CitizenDocument("Ficha de tramitación del Boletín 18.216-05","Senado de la República de Chile","Ficha oficial","Proyecto",PROJECT_URL,"2026-04-22"),CitizenDocument("Informe Financiero Complementario N°093/2026","Ministerio de Hacienda / Dirección de Presupuestos","Informe financiero","Indicaciones",FISCAL_URL,"2026-05-11"),CitizenDocument("Observaciones presidenciales al proyecto","Senado de la República de Chile","Diario de sesión","Veto",VETO_URL,"2026-08-12")),sources=("Senado de la República de Chile","Ministerio de Hacienda / Dirección de Presupuestos"),answers=(CitizenQuestionAnswer("¿Qué busca cambiar este proyecto?","La documentación oficial lo presenta como una iniciativa con medidas para reactivación, competitividad y productividad, además de ajustes tributarios; sus cambios están en tramitación.","FACT"),CitizenQuestionAnswer("¿Cuáles son sus principales materias?","El informe financiero y la tramitación acreditan medidas tributarias, crédito al empleo, normas ambientales, educación superior, propiedad intelectual y contribuciones, entre otras.","FACT"),CitizenQuestionAnswer("¿Qué cambió entre Cámara y Senado?","El expediente acredita que hubo divergencias que requirieron Comisión Mixta; el comparado completo de cada artículo no se incorpora como texto final.","LIMITATION"),CitizenQuestionAnswer("¿Por qué llegó a Comisión Mixta?","El Senado registra que se constituyó para resolver divergencias entre ambas Cámaras.","FACT"),CitizenQuestionAnswer("¿Qué resolvió la Comisión Mixta?","La fuente adquirida acredita el informe de Mixta, pero este expediente no afirma el contenido final de cada divergencia sin su comparado oficial completo.","LIMITATION"),CitizenQuestionAnswer("¿Qué observó el Presidente y qué pasó con esas observaciones?","Las observaciones fueron supresivas y recayeron sobre anatocismo, olvido financiero y pago a treinta días; Cámara las aprobó el 10 de agosto y el Senado las trató el 12 de agosto, según el registro oficial adquirido.","FACT"),CitizenQuestionAnswer("¿Cuál es el efecto fiscal estimado?","El IF N°093/2026 estima, bajo su supuesto de vigencia desde 2027, un mayor gasto anual de $4.892 millones para el Fondo de Promoción y Protección de la Propiedad Intelectual. Es una estimación, no un resultado observado.","LIMITATION"),CitizenQuestionAnswer("¿El proyecto ya es ley?","No se incorporó una publicación oficial o versión LeyChile para este boletín; por eso el expediente no lo presenta como ley vigente.","UNKNOWN"),CitizenQuestionAnswer("¿Qué queda pendiente?","La publicación de una ley o una versión LeyChile no está acreditada en este corpus.","UNKNOWN"),CitizenQuestionAnswer("¿Qué no podemos concluir todavía?","No se puede inferir la aplicación práctica, el impacto económico observado ni el texto vigente de una iniciativa aún no acreditada como publicada.","LIMITATION")),knowledge_cutoff=CitizenKnowledgeCutoff("2026-08-12","2026-08-12","Último registro oficial adquirido: discusión de observaciones presidenciales en el Senado."))


def reconstruccion_citizen_context() -> CitizenProjectionContext:
    """Add explicit, already-certified projection-only labels to the base dossier."""
    return replace(
        _reconstruccion_citizen_context(),
        topics=("Tributación", "Crédito al empleo", "Normas ambientales", "Educación superior", "Propiedad intelectual", "Contribuciones"),
        missing_knowledge=(
            "No está incorporado al corpus actual un comparado Cámara-Senado por disposición.",
            "No están incorporadas votaciones particulares de las materias del proyecto.",
            "No se ha acreditado completamente el resultado definitivo de las observaciones presidenciales.",
            "No se ha acreditado texto final, publicación o versión LeyChile de esta iniciativa.",
        ),
    )
