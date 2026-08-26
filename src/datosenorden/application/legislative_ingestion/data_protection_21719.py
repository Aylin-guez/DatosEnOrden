"""Bounded official corpus and citizen projection for Law 21.719.

The law was published in 2024 but has deferred entry into force.  This module
therefore keeps the current Law 19.628 distinct from Law 21.719's future rules.
"""

# ruff: noqa: E501

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

EXPEDIENT_ID = "EXP-REAL-DATA-PROTECTION-21719"
TITLE = "Protección y tratamiento de datos personales"
OFFICIAL_TITLE = (
    "Regula la protección y el tratamiento de los datos personales y crea la "
    "Agencia de Protección de Datos Personales"
)
LAW_NUMBER = "21.719"
BULLETINS = "11144-07 y 11092-07, refundidos"
LAW_URL = "https://www.bcn.cl/leychile/navegar?idNorma=1209272&idVersion=2026-12-01"
CURRENT_URL = "https://www.bcn.cl/leychile/navegar?idNorma=141599&idVersion=2023-05-09"
HISTORY_URL = "https://www.bcn.cl/historiadelaley/nc/historia-de-la-ley/8352/"
TC_URL = "https://www.bcn.cl/leychile/Navegar?idNorma=1209272&idVersion=2026-12-01"
HASHES = {
    "future": "df5e9d778a7f8d5dfe1f3f40753f6a1bde51926b23907bd68dc1e83400e598e8",
    "current": "358c57e1b7f4b4c7df485f5b8cd5c1ccd444e91ec8dd0974f0ce949de3e39df9",
    "history": "25d8249a44eaf301805fab031d27255c8b7e0985a2f920ba69e4573e34933b1a",
    "index": "160fe10aed0233ba2e75dfd3ac76db721f7821d59773b2e3cf724d4568fd3358",
}


def _record(key: str, payload: dict[str, object], retrieved_at: datetime) -> SourceRecordPayload:
    return SourceRecordPayload(
        key,
        "data-protection:21719",
        sha256(repr(sorted(payload.items())).encode()).hexdigest(),
        payload,
        retrieved_at,
        status=WorkflowStatus.VALIDATED,
    )


def data_protection_batches(retrieved_at: datetime | None = None) -> tuple[GraphBatch, ...]:
    retrieved_at = retrieved_at or datetime.now(UTC)
    subject = EntityRecord(
        EntityType.PUBLIC_PROJECT,
        TITLE,
        "cl-congreso-boletin-11144-07",
        "Boletines 11.144-07 y 11.092-07",
        "data-protection-21719",
    )
    items = (
        (
            "future",
            "LeyChile",
            "Diario Oficial",
            LAW_URL,
            date(2024, 12, 13),
            "Ley 21.719, texto publicado con vigencia diferida",
            "Entrada en vigencia: 01-12-2026",
        ),
        (
            "current",
            "LeyChile",
            "Diario Oficial",
            CURRENT_URL,
            date(2023, 5, 9),
            "Ley 19.628, texto vigente antes de 01-12-2026",
            "Última versión: 09-05-2023 a 30-11-2026",
        ),
        (
            "history",
            "Biblioteca del Congreso Nacional de Chile",
            "Congreso Nacional",
            HISTORY_URL,
            date(2024, 12, 13),
            "Historia de la Ley 21.719",
            "Boletines refundidos 11.144-07 y 11.092-07",
        ),
        (
            "index",
            "Biblioteca del Congreso Nacional de Chile",
            "Tribunal Constitucional",
            TC_URL,
            date(2024, 11, 14),
            "Control preventivo Rol 15.733-24-CPR",
            "Disposiciones individualizadas; texto LeyChile",
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
            "sha256": HASHES[key],
            "bulletins": BULLETINS,
            "locator": locator,
        }
        record = _record(f"data-protection:21719:{key}", payload, retrieved_at)
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
                "data-protection-law",
                "Ley 21.719 y régimen actual Ley 19.628",
                "1209272@2026-12-01",
                LAW_URL,
                HASHES["future"],
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


def provision_data_protection_21719(session: Session):
    for batch in data_protection_batches():
        GraphLoader(session).load(batch)
    entity = session.scalar(
        select(Entity).where(Entity.external_id == "cl-congreso-boletin-11144-07")
    )
    records = sorted(
        session.scalars(
            select(SourceRecord).where(SourceRecord.record_type == "data-protection:21719")
        ).all(),
        key=lambda item: str(item.id),
    )
    claims = sorted(
        session.scalars(
            select(Claim)
            .join(SourceRecord)
            .where(SourceRecord.record_type == "data-protection:21719")
        ).all(),
        key=lambda item: str(item.id),
    )
    evidence = sorted(
        session.scalars(
            select(Evidence)
            .join(SourceRecord)
            .where(SourceRecord.record_type == "data-protection:21719")
        ).all(),
        key=lambda item: str(item.id),
    )
    sources = sorted(
        session.scalars(
            select(Source).where(
                Source.name.in_(("LeyChile", "Biblioteca del Congreso Nacional de Chile"))
            )
        ).all(),
        key=lambda item: str(item.id),
    )
    if entity is None or len(records) != 4 or len(claims) != 4 or len(evidence) != 4:
        raise RuntimeError("Data-protection corpus is incomplete")
    support = tuple(str(item.id) for item in claims)
    evidence_ids = tuple(str(item.id) for item in evidence)

    def fact(key: str, section: str, text: str) -> NarrativeStatement:
        return NarrativeStatement(key, section, text, EpistemicClass.FACT, support, evidence_ids)

    spec = ExpedientSpecification(
        EXPEDIENT_ID,
        TITLE,
        "¿Qué cambia con la Ley 21.719 sobre datos personales, cuándo empieza a aplicarse y qué derechos y controles establece?",
        "La Ley 21.719 fue publicada, pero sus reglas principales entran en vigencia el 1 de diciembre de 2026. Hasta entonces, el régimen vigente incorporado es la Ley 19.628.",
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
                "current_status",
                "La Ley 21.719 fue promulgada el 25 de noviembre de 2024 y publicada el 13 de diciembre de 2024; LeyChile la identifica con vigencia diferida desde el 1 de diciembre de 2026.",
            ),
            fact(
                "current-regime",
                "current_status",
                "Antes del 1 de diciembre de 2026, el texto incorporado de la Ley 19.628 continúa como régimen vigente sobre protección de la vida privada y datos personales.",
            ),
            fact(
                "rights",
                "future_rule",
                "Desde su vigencia, la ley reconoce derechos de acceso, rectificación, supresión, oposición, portabilidad y bloqueo, conforme a sus condiciones y excepciones.",
            ),
            fact(
                "subjects",
                "future_rule",
                "La ley regula el tratamiento de datos por personas naturales o jurídicas, incluidos órganos públicos, dentro de su ámbito de aplicación y reglas especiales.",
            ),
            fact(
                "sensitive",
                "future_rule",
                "La ley define datos personales sensibles e incorpora reglas especiales; el tratamiento de datos sensibles de adolescentes menores de dieciséis años requiere consentimiento de sus representantes, salvo autorización o mandato legal expreso.",
            ),
            fact(
                "security",
                "future_rule",
                "La ley establece medidas técnicas y organizativas y exige reportar a la Agencia vulneraciones de seguridad con riesgo razonable para derechos y libertades, sin dilaciones indebidas.",
            ),
            fact(
                "authority",
                "future_rule",
                "La Ley 21.719 crea la Agencia de Protección de Datos Personales y contempla procedimientos de tutela, fiscalización y sanción dentro de las competencias que establece.",
            ),
            fact(
                "tc",
                "legislative_history",
                "El control preventivo Rol 15.733-24-CPR se refirió a disposiciones individualizadas del proyecto; no acredita una validación general de toda la ley.",
            ),
            NarrativeStatement(
                "access-limit",
                "limitations",
                "El corpus revisado acredita requerimientos de información y documentación en competencias individualizadas, pero no permite inferir acceso directo a sistemas, dispositivos ni al contenido de comunicaciones cuando el texto no lo establece expresamente.",
                EpistemicClass.UNKNOWN,
            ),
            NarrativeStatement(
                "future-limit",
                "limitations",
                "La publicación no equivale por sí sola a que las reglas principales sean aplicables hoy: la vigencia diferida debe leerse junto con las disposiciones transitorias.",
                EpistemicClass.UNKNOWN,
            ),
            NarrativeStatement(
                "history-limit",
                "limitations",
                "La historia legislativa explica la tramitación; la regla futura publicada se determina por LeyChile y no por el mensaje o las indicaciones.",
                EpistemicClass.UNKNOWN,
            ),
        ),
    )
    return ExpedientProvisioningService(
        PostgresExpedientRepository(session), ProvenanceReferenceEligibility(session)
    ).create_if_absent(spec)


def data_protection_citizen_context() -> CitizenProjectionContext:
    evidence = (
        CitizenEvidence(
            "future",
            "Ley 21.719, texto publicado",
            "LeyChile",
            LAW_URL,
            "Vigencia diferida: 01-12-2026.",
            "2026-12-01",
        ),
        CitizenEvidence(
            "current",
            "Ley 19.628, régimen vigente antes de la transición",
            "LeyChile",
            CURRENT_URL,
            "Versión vigente hasta 30-11-2026.",
            "2023-05-09",
        ),
        CitizenEvidence(
            "history",
            "Historia de la Ley 21.719",
            "Biblioteca del Congreso Nacional de Chile",
            HISTORY_URL,
            "Boletines 11.144-07 y 11.092-07 refundidos.",
            "2024-12-13",
        ),
        CitizenEvidence(
            "tc",
            "Control preventivo Rol 15.733-24-CPR",
            "Tribunal Constitucional",
            TC_URL,
            "Disposiciones individualizadas.",
            "2024-11-14",
        ),
    )
    answers = (
        CitizenQuestionAnswer(
            "¿La Ley 21.719 ya está vigente?",
            "Fue publicada, pero LeyChile indica vigencia diferida desde el 1 de diciembre de 2026.",
            "FACT",
        ),
        CitizenQuestionAnswer(
            "¿Cuándo empieza a aplicarse?",
            "La fecha de entrada en vigencia indicada por LeyChile es el 1 de diciembre de 2026.",
            "FACT",
        ),
        CitizenQuestionAnswer(
            "¿Qué derechos reconoce?",
            "Desde su vigencia, reconoce acceso, rectificación, supresión, oposición, portabilidad y bloqueo, conforme a la ley.",
            "FACT",
        ),
        CitizenQuestionAnswer(
            "¿Qué ocurre hoy?",
            "El régimen incorporado que continúa vigente antes de esa fecha es la Ley 19.628.",
            "FACT",
        ),
        CitizenQuestionAnswer(
            "¿Qué cambia con los datos sensibles?",
            "La ley publicada contiene reglas especiales y definiciones para datos sensibles; su aplicación general queda sujeta a la vigencia diferida.",
            "FACT",
        ),
        CitizenQuestionAnswer(
            "¿Qué obligaciones tendrán responsables y órganos públicos?",
            "La ley publicada regula sujetos definidos, incluyendo órganos públicos, con reglas y excepciones específicas; no todas las obligaciones son universales.",
            "FACT",
        ),
        CitizenQuestionAnswer(
            "¿Qué ocurre ante una brecha de datos?",
            "La regla futura contempla reportar a la Agencia vulneraciones con riesgo razonable, sin dilaciones indebidas.",
            "FACT",
        ),
        CitizenQuestionAnswer(
            "¿Qué puede hacer la Agencia?",
            "La ley crea la Agencia y contempla tutela, fiscalización y sanción en las competencias que establece.",
            "FACT",
        ),
        CitizenQuestionAnswer(
            "¿Puede la Agencia acceder directamente a sistemas o dispositivos?",
            "No puede inferirse acceso directo a sistemas o dispositivos desde facultades de requerir información o documentos cuando el texto revisado no lo establece expresamente.",
            "LIMITATION",
        ),
        CitizenQuestionAnswer(
            "¿Qué sanciones contempla?",
            "La ley publicada contempla infracciones y procedimientos sancionatorios; el expediente no resume una sanción aislada como si fuera aplicable a todos los sujetos.",
            "FACT",
        ),
        CitizenQuestionAnswer(
            "¿Qué revisó el Tribunal Constitucional?",
            "El Rol 15.733-24-CPR trató disposiciones individualizadas del proyecto, no una aprobación general de toda la ley.",
            "LIMITATION",
        ),
        CitizenQuestionAnswer(
            "¿Qué no podemos concluir?",
            "No se puede tratar una regla futura como aplicable hoy ni inferir acceso a dispositivos o interceptación de comunicaciones por silencio normativo.",
            "UNKNOWN",
        ),
    )
    return CitizenProjectionContext(
        "Ley publicada con vigencia diferida",
        evidence,
        (
            CitizenTimelineEvent(
                "2017-03-15",
                "PROCEDURAL",
                "Ingreso del mensaje presidencial, boletín 11.144-07.",
                "history",
            ),
            CitizenTimelineEvent(
                "2024-08-12", "SUBSTANTIVE", "Informe de Comisión Mixta.", "history"
            ),
            CitizenTimelineEvent(
                "2024-11-14",
                "ADMINISTRATIVE",
                "Control preventivo del Tribunal Constitucional.",
                "tc",
            ),
            CitizenTimelineEvent("2024-11-25", "ADMINISTRATIVE", "Promulgación.", "future"),
            CitizenTimelineEvent(
                "2024-12-13", "ADMINISTRATIVE", "Publicación de la Ley 21.719.", "future"
            ),
            CitizenTimelineEvent(
                "2026-12-01",
                "ADMINISTRATIVE",
                "Entrada en vigencia diferida indicada por LeyChile.",
                "future",
            ),
        ),
        actors=(
            "Presidencia de la República",
            "Senado de Chile",
            "Cámara de Diputadas y Diputados",
            "Agencia de Protección de Datos Personales",
            "Tribunal Constitucional",
        ),
        documents=(
            CitizenDocument(
                "Ley 21.719",
                "LeyChile",
                "Ley publicada",
                "Vigencia diferida",
                LAW_URL,
                "2026-12-01",
            ),
            CitizenDocument(
                "Ley 19.628",
                "LeyChile",
                "Régimen vigente actual",
                "Vigente hasta 30-11-2026",
                CURRENT_URL,
                "2023-05-09",
            ),
            CitizenDocument(
                "Historia de la Ley 21.719",
                "Biblioteca del Congreso Nacional de Chile",
                "Historia legislativa",
                "Boletines refundidos",
                HISTORY_URL,
                "2024-12-13",
            ),
            CitizenDocument(
                "Control preventivo Rol 15.733-24-CPR",
                "Tribunal Constitucional",
                "Control constitucional",
                "Disposiciones individualizadas",
                TC_URL,
                "2024-11-14",
            ),
        ),
        sources=(
            "LeyChile",
            "Biblioteca del Congreso Nacional de Chile",
            "Tribunal Constitucional",
        ),
        topics=(
            "Protección de datos personales",
            "Vigencia y transición",
            "Derechos de las personas",
            "Datos sensibles",
            "Seguridad y brechas",
            "Autoridad y sanciones",
        ),
        answers=answers,
        knowledge_cutoff=CitizenKnowledgeCutoff(
            "2026-08-24",
            "2026-08-24",
            "Texto oficial publicado con vigencia diferida y régimen actual Ley 19.628 incorporados.",
        ),
        official_title=OFFICIAL_TITLE,
    )
