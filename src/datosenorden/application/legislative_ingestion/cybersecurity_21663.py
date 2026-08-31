"""Bounded official corpus and public projection for Chile's Law 21.663.

The current-law assertions in this module are tied only to LeyChile.  The
Senate documents explain the proposal and legislative history; they are never
used as authority for what is currently in force.
"""

# ruff: noqa: E501

from __future__ import annotations

from dataclasses import replace
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

EXPEDIENT_ID = "EXP-REAL-CYBERSECURITY-14847-06"
BULLETIN = "14847-06"
LAW_NUMBER = "21.663"
TITLE = "Ley Marco de Ciberseguridad"
LAW_URL = "https://www.bcn.cl/leychile/navegar?idNorma=1202434&idVersion=2025-03-01"
PROJECT_URL = (
    "https://tramitacion.senado.cl/appsenado/templates/tramitacion/index.php?boletin_ini=14847-06"
)
MESSAGE_URL = "https://tramitacion.senado.cl/appsenado/index.php?mo=tramitacion&ac=getDocto&iddocto=12056&tipodoc=mensaje_mocion"
COMPARE_URL = "https://tramitacion.senado.cl/appsenado/index.php?mo=tramitacion&ac=getDocto&iddocto=4677&tipodoc=compa"
FINAL_COMPARE_URL = "https://tramitacion.senado.cl/appsenado/index.php?mo=tramitacion&ac=getDocto&iddocto=4885&tipodoc=compa"
TC_URL = "https://www.bcn.cl/obtienearchivo?id=recursoslegales/10221.3/75046/1/STC_Rol_15043-23-CPR_-_Crea_Agencia_de_Ciberseguridad.pdf"
HASHES = {
    "law": "06424ce45af10b7b3d440b1d0efac895f5060b8af3a046963d983feddb06fa22",
    "proposal": "A1F0FB3EC392C3C0FF56250B3F22202D96634351DE91E66F31C3EE1271C5FCAF",
    "final": "5AC52A84B718B6E5ED9DAC134010EB884090557A5A221ACA91E320C726C1CA14",
    "tc": "8770CD8ABC26C87825F939A8128A1AA8C4FFDFB2CD6F8688A049E6FC018E39C8",
}


def _record(key: str, payload: dict[str, object], retrieved_at: datetime) -> SourceRecordPayload:
    return SourceRecordPayload(
        key,
        "cybersecurity:21663",
        sha256(repr(sorted(payload.items())).encode()).hexdigest(),
        payload,
        retrieved_at,
        status=WorkflowStatus.VALIDATED,
    )


def cybersecurity_batches(retrieved_at: datetime | None = None) -> tuple[GraphBatch, ...]:
    retrieved_at = retrieved_at or datetime.now(UTC)
    subject = EntityRecord(
        EntityType.PUBLIC_PROJECT,
        TITLE,
        "cl-congreso-boletin-14847-06",
        "Boletín 14.847-06",
        "cybersecurity-14847-06",
    )
    items = (
        (
            "law",
            "LeyChile",
            "Diario Oficial",
            LAW_URL,
            date(2024, 4, 8),
            "Ley 21.663, texto vigente",
            "Ley 21.663; versión vigente desde 01-03-2025",
        ),
        (
            "proposal",
            "Senado de Chile",
            "Presidencia de la República",
            COMPARE_URL,
            date(2023, 4, 20),
            "Comparado del segundo informe",
            "Proyecto original y modificaciones de las Comisiones unidas",
        ),
        (
            "final",
            "Senado de Chile",
            "Senado de Chile",
            FINAL_COMPARE_URL,
            date(2024, 1, 24),
            "Comparado del tercer trámite",
            "Texto remitido por Cámara Revisora",
        ),
        (
            "tc",
            "Biblioteca del Congreso Nacional de Chile",
            "Tribunal Constitucional",
            TC_URL,
            date(2024, 3, 19),
            "Sentencia Rol 15043-23-CPR",
            "Control preventivo de disposiciones individualizadas",
        ),
    )
    records = []
    evidence = []
    claims = []
    for key, source, origin, url, when, title, locator in items:
        payload = {
            "hosting_source": source,
            "document_origin": origin,
            "official_url": url,
            "bulletin": BULLETIN,
            "sha256": HASHES[key],
            "locator": locator,
        }
        record = _record(f"cybersecurity:21663:{key}", payload, retrieved_at)
        records.append(record)
        item = EvidenceRecord(record, source, title, url, when, locator, payload)
        evidence.append(item)
        claims.append(
            ClaimRecord(
                subject,
                key.upper(),
                record,
                item,
                object_value={"locator": locator},
                valid_from=when,
                status=WorkflowStatus.VALIDATED,
            )
        )
    return (
        GraphBatch(
            SourceInfo(
                "LeyChile",
                "Biblioteca del Congreso Nacional de Chile",
                "https://www.bcn.cl/leychile/",
                retrieved_at=retrieved_at,
                metadata={"source_status": "DATA_AVAILABLE", "connector_status": "NOT_ACTIVE"},
            ),
            DatasetRecord(
                "LeyChile",
                "cybersecurity-law",
                "Texto vigente Ley 21.663",
                "1202434@2025-03-01",
                LAW_URL,
                HASHES["law"],
                retrieved_at,
                {"law_number": LAW_NUMBER},
            ),
            tuple(records),
            (subject,),
            tuple(evidence),
            tuple(claims),
            (),
            1,
        ),
    )


def provision_cybersecurity_21663(session: Session):
    for batch in cybersecurity_batches():
        GraphLoader(session).load(batch)
    entity = session.scalar(
        select(Entity).where(Entity.external_id == "cl-congreso-boletin-14847-06")
    )
    records = sorted(
        session.scalars(
            select(SourceRecord).where(SourceRecord.record_type == "cybersecurity:21663")
        ).all(),
        key=lambda item: str(item.id),
    )
    claims = sorted(
        session.scalars(
            select(Claim)
            .join(SourceRecord)
            .where(SourceRecord.record_type == "cybersecurity:21663")
        ).all(),
        key=lambda item: str(item.id),
    )
    evidence = sorted(
        session.scalars(
            select(Evidence)
            .join(SourceRecord)
            .where(SourceRecord.record_type == "cybersecurity:21663")
        ).all(),
        key=lambda item: str(item.id),
    )
    sources = sorted(
        session.scalars(
            select(Source).where(
                Source.name.in_(
                    ("LeyChile", "Senado de Chile", "Biblioteca del Congreso Nacional de Chile")
                )
            )
        ).all(),
        key=lambda item: str(item.id),
    )
    if entity is None or len(records) != 4 or len(claims) != 4 or len(evidence) != 4:
        raise RuntimeError("Cybersecurity corpus is incomplete")
    support = tuple(str(item.id) for item in claims)
    evidence_ids = tuple(str(item.id) for item in evidence)
    def fact(key: str, section: str, text: str) -> NarrativeStatement:
        return NarrativeStatement(
            key, section, text, EpistemicClass.FACT, support, evidence_ids
        )
    spec = ExpedientSpecification(
        EXPEDIENT_ID,
        TITLE,
        "¿Qué facultades creó la Ley Marco de Ciberseguridad, a quiénes obliga y qué controles y límites existen sobre esas facultades?",
        "La Ley 21.663 crea un marco institucional de ciberseguridad y obligaciones para sujetos definidos por la ley. Este expediente separa el texto vigente de su tramitación y distingue requerir información de acceder a redes o sistemas, que tienen reglas distintas.",
        ProvenanceClass.REAL,
        ExpedientStatus.PUBLISHED,
        1,
        ExpedientReferences(
            support,
            evidence_ids,
            entity_ids=(str(entity.id),),
            source_ids=tuple(str(item.id) for item in sources),
        ),
        (
            fact(
                "publication",
                "current_law",
                "La Ley 21.663 fue publicada el 8 de abril de 2024; la versión vigente revisada en LeyChile rige desde el 1 de marzo de 2025.",
            ),
            fact(
                "anci",
                "current_law",
                "La ley crea la Agencia Nacional de Ciberseguridad como organismo técnico y especializado encargado de asesorar, coordinar y supervisar la ciberseguridad en los ámbitos que la ley establece.",
            ),
            fact(
                "subjects",
                "current_law",
                "La ley regula obligaciones para instituciones prestadoras de servicios esenciales y operadores de importancia vital, según sus definiciones y procedimientos de calificación.",
            ),
            fact(
                "reporting",
                "current_law",
                "El artículo 9 regula reportes de incidentes significativos al CSIRT Nacional: contempla un aviso inicial de hasta tres horas, actualizaciones y un informe final.",
            ),
            fact(
                "information",
                "current_law",
                "El artículo 11 permite requerir información estrictamente necesaria y, en los casos que indica, registros de actividad de redes y sistemas mediante instrucción individualizada y fundada; ordena anonimizar datos personales cuando sea posible.",
            ),
            fact(
                "system-access",
                "current_law",
                "El artículo 11 contempla acceso a redes y sistemas sólo ante incidentes significativos y cuando sea indispensable; si una entidad privada se opone, la Agencia requiere autorización judicial en los términos de la ley.",
            ),
            fact(
                "tc",
                "legislative_history",
                "El Tribunal Constitucional realizó control preventivo en la causa Rol 15043-23-CPR sobre disposiciones individualizadas del proyecto.",
            ),
            NarrativeStatement(
                "device-limit",
                "limitations",
                "El texto revisado regula información y, bajo condiciones, acceso a redes y sistemas. Este expediente no infiere de ello una autorización explícita para acceder a dispositivos individuales o al contenido de comunicaciones.",
                EpistemicClass.UNKNOWN,
            ),
            NarrativeStatement(
                "report-limit",
                "limitations",
                "El deber de reporte se aplica a los sujetos y a los incidentes definidos por la ley; no permite describirlo como un deber general de reporte para toda persona.",
                EpistemicClass.UNKNOWN,
            ),
            NarrativeStatement(
                "tc-limit",
                "limitations",
                "El control preventivo del Tribunal Constitucional se refiere a disposiciones sometidas a ese control; no acredita una validación general de toda la ley o de una política pública.",
                EpistemicClass.UNKNOWN,
            ),
        ),
    )
    service = ExpedientProvisioningService(
        PostgresExpedientRepository(session), ProvenanceReferenceEligibility(session)
    )
    existing = service.get(EXPEDIENT_ID)
    if existing is not None:
        spec = _with_existing_reference_order_if_equivalent(spec, existing.specification)
    return service.create_if_absent(spec)


def _with_existing_reference_order_if_equivalent(
    candidate: ExpedientSpecification, existing: ExpedientSpecification
) -> ExpedientSpecification:
    """Preserve immutable v1 ordering only when every referenced item is identical.

    PostgreSQL does not guarantee the order of the source, claim, or evidence
    queries above.  Order is stored in an expedient version, so an older v1 may
    legitimately use a different (but semantically identical) ordering.  This
    compatibility path never merges different references or statement support:
    any material difference remains a provisioning conflict.
    """
    if candidate.expedient_id != existing.expedient_id:
        return candidate
    if candidate.version != existing.version:
        return candidate
    if any(
        set(candidate.references.by_kind()[kind]) != set(existing.references.by_kind()[kind])
        for kind in candidate.references.by_kind()
    ):
        return candidate
    existing_statements = {item.statement_id: item for item in existing.statements}
    ordered_statements = []
    for statement in candidate.statements:
        previous = existing_statements.get(statement.statement_id)
        if previous is None or (
            statement.section,
            statement.text,
            statement.epistemic_class,
            set(statement.claim_ids),
            set(statement.evidence_ids),
        ) != (
            previous.section,
            previous.text,
            previous.epistemic_class,
            set(previous.claim_ids),
            set(previous.evidence_ids),
        ):
            return candidate
        ordered_statements.append(
            replace(
                statement,
                claim_ids=previous.claim_ids,
                evidence_ids=previous.evidence_ids,
            )
        )
    if len(existing_statements) != len(ordered_statements):
        return candidate
    return replace(
        candidate,
        references=existing.references,
        statements=tuple(ordered_statements),
    )


def cybersecurity_citizen_context() -> CitizenProjectionContext:
    evidence = (
        CitizenEvidence(
            "law",
            "Ley 21.663, texto vigente",
            "LeyChile",
            LAW_URL,
            "Artículos 4 a 11 y reglas de fiscalización y sanción.",
            "2025-03-01",
        ),
        CitizenEvidence(
            "proposal",
            "Comparado del segundo informe",
            "Senado de Chile",
            COMPARE_URL,
            "Proyecto original y modificaciones de las Comisiones unidas.",
            "2023-04-20",
        ),
        CitizenEvidence(
            "final",
            "Comparado del tercer trámite",
            "Senado de Chile",
            FINAL_COMPARE_URL,
            "Texto remitido por Cámara Revisora.",
            "2024-01-24",
        ),
        CitizenEvidence(
            "tc",
            "Sentencia Rol 15043-23-CPR",
            "Tribunal Constitucional",
            TC_URL,
            "Control preventivo de disposiciones individualizadas.",
            "2024-03-19",
        ),
    )
    return CitizenProjectionContext(
        "Expediente legislativo / ley vigente",
        evidence,
        (
            CitizenTimelineEvent(
                "2022-03-15",
                "PROCEDURAL",
                "Ingreso del mensaje presidencial en el Senado.",
                "proposal",
            ),
            CitizenTimelineEvent(
                "2023-04-20",
                "SUBSTANTIVE",
                "Segundo informe de Comisiones unidas y comparado del primer trámite.",
                "proposal",
            ),
            CitizenTimelineEvent(
                "2024-01-24", "SUBSTANTIVE", "Comparado del tercer trámite constitucional.", "final"
            ),
            CitizenTimelineEvent(
                "2024-03-19",
                "ADMINISTRATIVE",
                "Control preventivo del Tribunal Constitucional.",
                "tc",
            ),
            CitizenTimelineEvent(
                "2024-04-08", "ADMINISTRATIVE", "Publicación de la Ley 21.663.", "law"
            ),
        ),
        actors=(
            "Presidencia de la República",
            "Senado de Chile",
            "Cámara de Diputadas y Diputados",
            "Agencia Nacional de Ciberseguridad (ANCI)",
            "Tribunal Constitucional",
        ),
        documents=(
            CitizenDocument(
                "Ley 21.663, Ley Marco de Ciberseguridad",
                "LeyChile",
                "Texto vigente",
                "Ley publicada",
                LAW_URL,
                "2025-03-01",
            ),
            CitizenDocument(
                "Comparado del segundo informe",
                "Senado de Chile",
                "Comparado legislativo; origen Senado",
                "Primer trámite",
                COMPARE_URL,
                "2023-04-20",
            ),
            CitizenDocument(
                "Comparado del tercer trámite",
                "Senado de Chile",
                "Comparado legislativo; origen Senado",
                "Tercer trámite",
                FINAL_COMPARE_URL,
                "2024-01-24",
            ),
            CitizenDocument(
                "Sentencia Rol 15043-23-CPR",
                "Tribunal Constitucional",
                "Control preventivo",
                "Tribunal Constitucional",
                TC_URL,
                "2024-03-19",
            ),
        ),
        sources=(
            "LeyChile",
            "Senado de Chile",
            "Biblioteca del Congreso Nacional de Chile",
            "Tribunal Constitucional",
        ),
        topics=(
            "Institucionalidad de ciberseguridad",
            "Sujetos obligados",
            "Reportes de incidentes",
            "Información y datos",
            "Fiscalización y sanciones",
            "Controles y reclamación",
        ),
        answers=(
            CitizenQuestionAnswer(
                "¿Qué creó la Ley Marco de Ciberseguridad?",
                "La Ley 21.663 establece un marco institucional y crea la Agencia Nacional de Ciberseguridad.",
                "FACT",
            ),
            CitizenQuestionAnswer(
                "¿A quiénes se aplica?",
                "La ley establece reglas para instituciones prestadoras de servicios esenciales y operadores de importancia vital, conforme a sus definiciones y procedimientos de calificación.",
                "FACT",
            ),
            CitizenQuestionAnswer(
                "¿Qué información puede exigir la Agencia Nacional de Ciberseguridad?",
                "Puede requerir información estrictamente necesaria y, en los casos del artículo 11, registros de actividad de redes y sistemas mediante una instrucción individualizada y fundada.",
                "FACT",
            ),
            CitizenQuestionAnswer(
                "¿Puede la Agencia acceder directamente a computadores, sistemas o dispositivos?",
                "La ley regula acceso a redes y sistemas en incidentes significativos cuando sea indispensable, con autorización judicial si una entidad privada se opone. El expediente no infiere de esa regla un acceso explícito a dispositivos individuales.",
                "LIMITATION",
            ),
            CitizenQuestionAnswer(
                "¿Qué incidentes deben reportarse y quién debe hacerlo?",
                "El artículo 9 regula reportes de incidentes significativos por los sujetos definidos en la ley, con un aviso inicial, actualizaciones y un informe final.",
                "FACT",
            ),
            CitizenQuestionAnswer(
                "¿Qué puede fiscalizar la Agencia?",
                "La ley le atribuye funciones de supervisión y, en los casos establecidos, fiscalización y procedimiento sancionatorio.",
                "FACT",
            ),
            CitizenQuestionAnswer(
                "¿Qué sanciones existen por incumplimiento?",
                "La ley clasifica infracciones y contempla sanciones administrativas; su aplicación depende del procedimiento y de los sujetos regulados.",
                "FACT",
            ),
            CitizenQuestionAnswer(
                "¿Qué garantías existen sobre la información entregada?",
                "El artículo 11 exige que los requerimientos estén individualizados y fundados, y ordena anonimizar datos personales cuando sea posible.",
                "FACT",
            ),
            CitizenQuestionAnswer(
                "¿Qué controles o mecanismos de reclamación existen frente a decisiones de la Agencia?",
                "La ley prevé procedimientos administrativos y recursos en materias individualizadas; el acceso a redes o sistemas frente a oposición privada requiere autorización judicial.",
                "FACT",
            ),
            CitizenQuestionAnswer(
                "¿Qué cambió entre el proyecto original y la ley finalmente publicada?",
                "Los comparados oficiales permiten identificar modificaciones durante la tramitación. La regla vigente se determina exclusivamente por LeyChile, no por el proyecto o las indicaciones.",
                "LIMITATION",
            ),
            CitizenQuestionAnswer(
                "¿Qué revisó el Tribunal Constitucional?",
                "La sentencia Rol 15043-23-CPR corresponde a control preventivo de disposiciones individualizadas del proyecto; no permite afirmar una aprobación constitucional general de toda la ley.",
                "LIMITATION",
            ),
            CitizenQuestionAnswer(
                "¿Qué no podemos afirmar con el corpus incorporado?",
                "No se puede inferir acceso a dispositivos individuales, interceptación de comunicaciones ni una obligación general de reporte cuando el texto revisado no lo establece expresamente.",
                "UNKNOWN",
            ),
        ),
        knowledge_cutoff=CitizenKnowledgeCutoff(
            "2025-03-01",
            "2025-03-01",
            "Texto vigente de LeyChile desde 01-03-2025; documentos legislativos y sentencia oficial incorporados.",
        ),
    )
