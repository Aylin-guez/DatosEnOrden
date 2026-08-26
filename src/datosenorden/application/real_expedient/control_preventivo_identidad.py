"""Bounded official citizen expedient for preventive identity controls.

The current-rule claims are derived from the current LeyChile version of Law
20.931.  Legislative history and the constitutional-review record are preserved
as context, not as a substitute for the current text.
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
from datosenorden.application.real_expedient.eligibility import (
    ProvenanceReferenceEligibility,
)
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
from datosenorden.infrastructure.real_expedient.repository import (
    PostgresExpedientRepository,
)
from datosenorden.models import Claim, Entity, Evidence, Source, SourceRecord


EXPEDIENT_ID = "EXP-REAL-CONTROL-PREVENTIVO-IDENTIDAD"
TITLE = "Control preventivo de identidad"
QUESTION = (
    "¿Cuándo puede la policía controlar preventivamente la identidad de una persona, "
    "qué puede exigir y cuáles son los límites de esa facultad?"
)
SUMMARY = (
    "El artículo 12 de la Ley 20.931 regula un control preventivo de identidad "
    "para personas mayores de 18 años, en lugares definidos y por un máximo de una "
    "hora. La verificación tecnológica de identidad no autoriza por sí sola revisar "
    "un teléfono ni sus comunicaciones; el artículo 12 bis contiene una regla migratoria distinta."
)
RECORD_TYPE = "control-preventivo-identidad:law-20931"


DOCUMENTS = (
    (
        "law-current",
        "LeyChile",
        "Biblioteca del Congreso Nacional de Chile",
        "https://www.bcn.cl/leychile/navegar?idNorma=1092269&idVersion=2026-08-12",
        date(2026, 8, 12),
        "Ley N° 20.931, versión vigente desde 12-08-2026",
        "Artículos 12 y 12 bis; SHA-256 0da9e53fdb0b4e937dc4ed4d2962caa2ac2ce11cd29c50e417915311a6f3f72f.",
    ),
    (
        "law-original",
        "LeyChile",
        "Biblioteca del Congreso Nacional de Chile",
        "https://www.bcn.cl/leychile/navegar?idNorma=1092269&idVersion=2016-07-05",
        date(2016, 7, 5),
        "Ley N° 20.931, versión publicada",
        "Texto histórico; SHA-256 d9ee449d011f3b62a299cdb91bbabf59d6237b6610d51cf113dc2a397a1dfe2e.",
    ),
    (
        "law-21560",
        "LeyChile",
        "Biblioteca del Congreso Nacional de Chile",
        "https://www.bcn.cl/leychile/navegar?idNorma=1191005&idVersion=2023-04-10",
        date(2023, 4, 10),
        "Ley N° 21.560",
        "Modificación histórica del inciso vehicular; SHA-256 b23d524457c3d21b8b29418ad0d7a7ba819c0e9ebea53a21c6e668bc386afc29.",
    ),
    (
        "law-21567",
        "LeyChile",
        "Biblioteca del Congreso Nacional de Chile",
        "https://www.bcn.cl/leychile/navegar?idNorma=1191683&idVersion=2023-04-29",
        date(2023, 4, 29),
        "Ley N° 21.567",
        "Incorpora el artículo 12 bis; SHA-256 aec1e36d9d748487ea5ce22a0b7b11b74d01aab2d456b60f96e283d595315eb0.",
    ),
    (
        "law-21601",
        "LeyChile",
        "Biblioteca del Congreso Nacional de Chile",
        "https://www.bcn.cl/leychile/navegar?idNorma=1195774&idVersion=2023-09-11",
        date(2023, 9, 11),
        "Ley N° 21.601",
        "Amplía la regla vehicular; SHA-256 0658222bf2ec7e801383f1f74d02fb8629f9e8b2e65126813aa236aec5f9d150.",
    ),
    (
        "cpp-current",
        "LeyChile",
        "Biblioteca del Congreso Nacional de Chile",
        "https://www.bcn.cl/leychile/navegar?idNorma=176595&idVersion=2026-04-02",
        date(2026, 4, 2),
        "Código Procesal Penal, artículos 83 y 85",
        "Remisión de policías habilitadas y control investigativo; SHA-256 3cddfb9ac9f62a26cdb6162e0e9b33472c9e9f3f65c3c0af65c182ebaf6e38ad.",
    ),
    (
        "history",
        "Biblioteca del Congreso Nacional de Chile",
        "Biblioteca del Congreso Nacional de Chile",
        "https://www.bcn.cl/historiadelaley/fileadmin/file_ley/5088/HLD_5088_96471a26e756aa8c5c8a4488469ad9d1.pdf",
        date(2016, 7, 5),
        "Historia de la Ley N° 20.931",
        "Historia legislativa; SHA-256 5f9777c28cab9cc6f4ed5b02894cd5dfddca5b1904f636cff9d84640fe125e0b.",
    ),
    (
        "tc-3081",
        "Tribunal Constitucional",
        "Tribunal Constitucional de Chile",
        "https://www.bcn.cl/historiadelaley/nc/historia-de-la-ley/5088/",
        date(2016, 6, 14),
        "Oficio del Tribunal Constitucional, Rol N° 3081-16-CPR",
        "Trámite 5.3, documento BCN 655389; SHA-256 4ca0a93f223fbef0336448e43ab2374a722236b0a0b9a17bb9ce6f2a103cc8f1.",
    ),
)


def _record(key: str, payload: dict[str, object], retrieved_at: datetime) -> SourceRecordPayload:
    fingerprint = sha256(repr(sorted(payload.items())).encode()).hexdigest()
    return SourceRecordPayload(
        key,
        RECORD_TYPE,
        fingerprint,
        payload,
        retrieved_at,
        status=WorkflowStatus.VALIDATED,
    )


def control_preventivo_identidad_batches(
    retrieved_at: datetime | None = None,
) -> tuple[GraphBatch, ...]:
    retrieved_at = retrieved_at or datetime.now(UTC)
    subject = EntityRecord(
        EntityType.PUBLIC_PROJECT,
        TITLE,
        "cl-law-20931-control-preventivo-identidad",
        "Regla vigente, historia y límites del control preventivo de identidad.",
        "control-preventivo-identidad",
    )
    records: list[SourceRecordPayload] = []
    evidence: list[EvidenceRecord] = []
    claims: list[ClaimRecord] = []
    for key, source, origin, url, when, title, locator in DOCUMENTS:
        payload = {
            "hosting_source": source,
            "document_origin": origin,
            "official_url": url,
            "locator": locator,
        }
        record = _record(f"{RECORD_TYPE}:{key}", payload, retrieved_at)
        item = EvidenceRecord(record, source, title, url, when, locator, payload)
        records.append(record)
        evidence.append(item)
        claims.append(
            ClaimRecord(
                subject,
                key.upper().replace("-", "_"),
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
                "control-preventivo-identidad",
                "Corpus oficial de Ley 20.931, modificaciones y control constitucional.",
                "1092269@2026-08-12",
                DOCUMENTS[0][3],
                "0da9e53fdb0b4e937dc4ed4d2962caa2ac2ce11cd29c50e417915311a6f3f72f",
                retrieved_at,
            ),
            tuple(records),
            (subject,),
            tuple(evidence),
            tuple(claims),
            (),
            len(records),
        ),
    )


def provision_control_preventivo_identidad(session: Session):
    for batch in control_preventivo_identidad_batches():
        GraphLoader(session).load(batch)
    entity = session.scalar(
        select(Entity).where(Entity.external_id == "cl-law-20931-control-preventivo-identidad")
    )
    records = sorted(
        session.scalars(
            select(SourceRecord).where(SourceRecord.record_type == RECORD_TYPE)
        ).all(),
        key=lambda item: str(item.id),
    )
    claims = sorted(
        session.scalars(
            select(Claim).join(SourceRecord).where(SourceRecord.record_type == RECORD_TYPE)
        ).all(),
        key=lambda item: str(item.id),
    )
    evidence = sorted(
        session.scalars(
            select(Evidence).join(SourceRecord).where(SourceRecord.record_type == RECORD_TYPE)
        ).all(),
        key=lambda item: str(item.id),
    )
    source_names = tuple(sorted({row[1] for row in DOCUMENTS}))
    sources = sorted(
        session.scalars(select(Source).where(Source.name.in_(source_names))).all(),
        key=lambda item: str(item.id),
    )
    if entity is None or any(len(rows) != len(DOCUMENTS) for rows in (records, claims, evidence)):
        raise RuntimeError("control preventivo de identidad corpus is incomplete")

    claim_ids = tuple(str(item.id) for item in claims)
    evidence_ids = tuple(str(item.id) for item in evidence)

    def fact(key: str, section: str, text: str) -> NarrativeStatement:
        return NarrativeStatement(key, section, text, EpistemicClass.FACT, claim_ids, evidence_ids)

    spec = ExpedientSpecification(
        EXPEDIENT_ID,
        TITLE,
        QUESTION,
        SUMMARY,
        ProvenanceClass.REAL,
        ExpedientStatus.PUBLISHED,
        1,
        ExpedientReferences(
            claim_ids,
            evidence_ids,
            entity_ids=(str(entity.id),),
            source_ids=tuple(str(item.id) for item in sources),
        ),
        (
            fact("authority", "current_rule", "El artículo 12 de la Ley 20.931 regula el control preventivo de identidad y remite a los funcionarios policiales indicados en el artículo 83 del Código Procesal Penal."),
            fact("age", "current_rule", "El control preventivo ordinario se dirige a personas mayores de 18 años. Ante duda sobre la edad, la norma ordena considerar a la persona menor de edad."),
            fact("places", "current_rule", "La norma permite verificar identidad en vías públicas, otros lugares públicos y lugares privados de acceso público."),
            fact("trigger", "current_rule", "El texto del artículo 12 no exige un indicio individual previo; lo diferencia expresamente del artículo 85 del Código Procesal Penal."),
            fact("identification", "current_rule", "La identidad puede acreditarse, entre otros medios, con cédula, licencia de conducir, pasaporte o tarjeta estudiantil, y deben darse facilidades para hacerlo."),
            fact("technology", "current_rule", "El artículo 12 permite usar un dispositivo tecnológico idóneo para verificar identidad; esa regla describe verificación de identidad."),
            fact("duration", "current_rule", "El procedimiento debe limitarse al tiempo estrictamente necesario y no puede exceder de una hora."),
            fact("ordinary-no-transport", "current_rule", "Si no es posible verificar identidad en el mismo lugar, el procedimiento ordinario debe terminar inmediatamente."),
            fact("warrant", "current_rule", "Si la persona mantiene órdenes de detención pendientes, la policía procede a su detención conforme al artículo 129 del Código Procesal Penal."),
            fact("refusal", "current_rule", "Negarse a acreditar identidad, ocultarla o proporcionar una identidad falsa tiene las consecuencias legales que remite el artículo 12."),
            fact("officer-identification", "guarantees", "El funcionario debe exhibir su placa e indicar nombre, grado y dotación; el texto exige igualdad de trato y no discriminación arbitraria."),
            fact("complaint", "guarantees", "Las policías deben elaborar un procedimiento estandarizado de reclamo para quienes estimen abusivo o denigrante el ejercicio de la facultad."),
            fact("vehicle-register", "register", "En la supervigilancia de las normas de tránsito, Carabineros puede controlar ocupantes de vehículos y registrar maleteros o portaequipajes, además de contenedores o mochilas que sirvan para transportar mercancías."),
            fact("migration", "special_rule", "El artículo 12 bis regula un supuesto migratorio distinto: bajo sus requisitos, contempla registro y traslado a PDI para corroborar situación migratoria regular."),
            fact("tc-scope", "constitutional_review", "En el Rol 3081-16-CPR, el Tribunal Constitucional no emitió pronunciamiento preventivo sobre el artículo 12, por tratarlo como materia de ley simple."),
            fact("comparison", "comparison", "Control preventivo: el artículo 12 permite verificar identidad de mayores de 18 años en lugares definidos, sin exigir en su texto un indicio individual previo y con máximo de una hora."),
            fact("investigative-comparison", "comparison", "Control investigativo: el artículo 85 del Código Procesal Penal es una facultad distinta, vinculada a indicios legalmente definidos y con reglas propias de registro y cotejo."),
            NarrativeStatement("search-limit", "limitations", "Control de identidad no equivale a un registro corporal general. La regla de registro acreditada en el artículo 12 es específica para el contexto vehicular y de transporte de mercancías.", EpistemicClass.UNKNOWN),
            NarrativeStatement("device-limit", "limitations", "Verificar identidad mediante tecnología no equivale a autorización para revisar el contenido de un dispositivo.", EpistemicClass.UNKNOWN),
            NarrativeStatement("phone-unlock-limit", "limitations", "No se encontró en el corpus revisado una facultad expresa del artículo 12 para exigir el desbloqueo de un teléfono.", EpistemicClass.UNKNOWN),
            NarrativeStatement("phone-content-limit", "limitations", "No se encontró en el corpus revisado una facultad expresa del artículo 12 para revisar contenido digital.", EpistemicClass.UNKNOWN),
            NarrativeStatement("communications-limit", "limitations", "No se encontró en el corpus revisado una autorización general del artículo 12 para interceptar comunicaciones.", EpistemicClass.UNKNOWN),
            NarrativeStatement("investigative-limit", "limitations", "El control preventivo del artículo 12 no debe confundirse con el control investigativo regulado en el artículo 85 del Código Procesal Penal.", EpistemicClass.UNKNOWN),
            NarrativeStatement("tc-limit", "limitations", "El Rol 3081-16-CPR no acredita que el Tribunal Constitucional haya aprobado en general el control preventivo de identidad.", EpistemicClass.UNKNOWN),
            NarrativeStatement("proposal-limit", "limitations", "Los proyectos modificatorios posteriores no describen por sí mismos el derecho vigente.", EpistemicClass.UNKNOWN),
        ),
    )
    return ExpedientProvisioningService(
        PostgresExpedientRepository(session), ProvenanceReferenceEligibility(session)
    ).create_if_absent(spec)


def control_preventivo_identidad_citizen_context() -> CitizenProjectionContext:
    evidence = tuple(
        CitizenEvidence(key, title, source, url, locator, when.isoformat())
        for key, source, _origin, url, when, title, locator in DOCUMENTS
    )
    return CitizenProjectionContext(
        "Seguridad pública y derechos",
        evidence,
        (
            CitizenTimelineEvent("2016-06-14", "CONSTITUTIONAL", "Oficio del Tribunal Constitucional, Rol N° 3081-16-CPR.", "tc-3081"),
            CitizenTimelineEvent("2016-07-05", "SUBSTANTIVE", "Publicación de la Ley 20.931.", "law-original"),
            CitizenTimelineEvent("2023-04-10", "SUBSTANTIVE", "Ley 21.560 incorporó una regla vehicular al artículo 12.", "law-21560"),
            CitizenTimelineEvent("2023-04-29", "SUBSTANTIVE", "Ley 21.567 incorporó el artículo 12 bis.", "law-21567"),
            CitizenTimelineEvent("2023-09-11", "SUBSTANTIVE", "Ley 21.601 amplió la regla sobre vehículos y transporte de mercancías.", "law-21601"),
            CitizenTimelineEvent("2026-08-12", "ADMINISTRATIVE", "Versión vigente de la Ley 20.931 utilizada por este expediente.", "law-current"),
        ),
        actors=("Carabineros de Chile", "Policía de Investigaciones de Chile", "Ministerio de Seguridad Pública", "Tribunal Constitucional", "Biblioteca del Congreso Nacional de Chile"),
        documents=tuple(
            CitizenDocument(title, origin, "Documento oficial", "Regla vigente, antecedente o modificación", url, when.isoformat())
            for _key, _source, origin, url, when, title, _locator in DOCUMENTS
        ),
        sources=("LeyChile / Biblioteca del Congreso Nacional de Chile", "Tribunal Constitucional"),
        topics=("Seguridad pública", "Control de identidad", "Facultades policiales", "Derechos y garantías", "Menores de edad", "Registro", "Procedimiento", "Reclamos", "Control constitucional"),
        answers=(
            CitizenQuestionAnswer("¿Me pueden controlar sin sospechar que cometí un delito?", "El texto del artículo 12 no exige un indicio individual previo para el control preventivo. Es una regla distinta del control investigativo del artículo 85 CPP.", "FACT"),
            CitizenQuestionAnswer("¿Quién puede controlarme?", "Los funcionarios de Carabineros de Chile y de la Policía de Investigaciones de Chile indicados en el artículo 83 CPP.", "FACT"),
            CitizenQuestionAnswer("¿Dónde pueden hacerlo?", "En vías públicas, otros lugares públicos y lugares privados de acceso público.", "FACT"),
            CitizenQuestionAnswer("¿Tengo que llevar carnet?", "La ley no exige ese único documento: permite acreditar identidad por distintos medios y ordena dar facilidades para hacerlo.", "FACT"),
            CitizenQuestionAnswer("¿Puedo identificarme con otro documento?", "El artículo menciona cédula, licencia de conducir, pasaporte y tarjeta estudiantil, entre otros medios de identificación.", "FACT"),
            CitizenQuestionAnswer("¿Cuánto puede durar el control?", "Sólo el tiempo estrictamente necesario y, como máximo, una hora.", "FACT"),
            CitizenQuestionAnswer("¿Pueden llevarme a una comisaría si no pueden identificarme?", "En el procedimiento ordinario, si no pueden verificar identidad en el lugar, deben terminarlo. El artículo 12 bis contiene una regla migratoria distinta de traslado a PDI bajo sus propios requisitos.", "FACT"),
            CitizenQuestionAnswer("¿Qué pasa si tengo una orden de detención pendiente?", "El artículo 12 remite a la detención conforme al artículo 129 CPP si la persona mantiene una orden pendiente.", "FACT"),
            CitizenQuestionAnswer("¿Qué pasa si me niego a identificarme?", "El artículo 12 remite a consecuencias legales específicas por negarse, ocultar la identidad o proporcionar una falsa.", "FACT"),
            CitizenQuestionAnswer("¿Pueden revisar mi mochila?", "El artículo 12 no establece una revisión general de mochilas: menciona contenedores o mochilas que sirvan para transportar mercancías, dentro de la regla vehicular acreditada.", "LIMITATION"),
            CitizenQuestionAnswer("¿Pueden revisar mi vehículo?", "En labores de supervigilancia de tránsito, Carabineros puede controlar ocupantes y registrar maleteros o portaequipajes en los términos del artículo 12.", "FACT"),
            CitizenQuestionAnswer("¿Pueden revisar mi teléfono?", "No se encontró en el corpus revisado una facultad expresa del artículo 12 para revisar contenido digital. Verificar identidad con tecnología no equivale a revisar un teléfono.", "LIMITATION"),
            CitizenQuestionAnswer("¿Pueden obligarme a desbloquear un teléfono o celular?", "No se encontró en el corpus revisado una facultad expresa del artículo 12 para exigir el desbloqueo de un teléfono o celular. Eso no permite afirmar una prohibición absoluta fuera del alcance del corpus.", "UNKNOWN"),
            CitizenQuestionAnswer("¿Qué pasa si soy menor de edad?", "El control preventivo ordinario se dirige a mayores de 18 años; ante duda sobre la edad, la ley ordena considerar a la persona menor de edad.", "FACT"),
            CitizenQuestionAnswer("¿Cómo puedo reclamar si considero abusivo el procedimiento?", "Las policías deben elaborar un procedimiento estandarizado de reclamo por ejercicio abusivo o trato denigrante.", "FACT"),
            CitizenQuestionAnswer("¿Qué diferencia hay con el control investigativo?", "El artículo 85 CPP regula un procedimiento distinto, basado en indicios y con facultades propias. No deben mezclarse sus requisitos ni sus reglas de registro.", "LIMITATION"),
            CitizenQuestionAnswer("¿El Tribunal Constitucional declaró constitucional todo el control preventivo?", "No. En el Rol 3081-16-CPR el TC no emitió pronunciamiento preventivo sobre el artículo 12, por tratarlo como materia de ley simple.", "LIMITATION"),
            CitizenQuestionAnswer("¿Qué cambió desde 2016?", "El corpus identifica modificaciones de 2023 sobre controles vehiculares, transporte de mercancías y una regla migratoria especial; la regla actual se determina por la versión vigente de LeyChile.", "FACT"),
        ),
        missing_knowledge=(
            "No se incorporó un protocolo operativo completo de Carabineros o PDI.",
            "No se encontró una facultad expresa en este corpus para desbloquear teléfonos o revisar contenido digital.",
            "Los proyectos posteriores se mantienen fuera de la regla vigente hasta verificar su publicación y versión legal aplicable.",
        ),
        knowledge_cutoff=CitizenKnowledgeCutoff(
            "2026-08-26",
            "2026-08-12",
            "Regla vigente LeyChile, modificaciones, historia legislativa y oficio constitucional incorporados.",
        ),
        official_title="Ley N° 20.931, artículos 12 y 12 bis",
        section_titles={"comparison": "Control preventivo vs. control investigativo"},
    )
