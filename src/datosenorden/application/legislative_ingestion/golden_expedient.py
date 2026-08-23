"""Reviewed v2 content for the legislative golden case.

This module contains only the human-approved interpretation boundary.  Source
identifiers are received from the existing immutable v1, so provisioning never
performs acquisition or creates unaudited source material.
"""

# ruff: noqa: E501

from __future__ import annotations

from datosenorden.application.real_expedient.models import (
    EpistemicClass,
    ExpedientSpecification,
    NarrativeStatement,
    ProvisioningResult,
)
from datosenorden.application.real_expedient.citizen_projection import (
    CitizenDocument,
    CitizenEvidence,
    CitizenKnowledgeCutoff,
    CitizenProjectionContext,
    CitizenQuestionAnswer,
    CitizenTimelineEvent,
)
from datosenorden.application.real_expedient.service import (
    ExpedientConflictError,
    ExpedientProvisioningService,
    content_fingerprint,
)

GOLDEN_QUESTION = (
    "¿Qué cambió durante la tramitación del proyecto de Inteligencia Económica "
    "y qué sabemos sobre la discusión del secreto bancario?"
)
GOLDEN_SUMMARY = (
    "El mensaje original propuso un Sistema de Inteligencia Económica. Senado y "
    "Cámara discreparon en cuatro modificaciones y el oficio 36701 declaró la "
    "formación de una Comisión Mixta. La evidencia incorporada muestra una discusión "
    "sobre información protegida por secreto bancario, pero no acredita su resultado "
    "final ni su vigencia."
)


def golden_citizen_context() -> CitizenProjectionContext:
    """Certified human labels and chronology for the reviewed local golden case."""
    evidence = CitizenEvidence(
        "evidence-official", "Oficio 36701", "Senado de la República",
        "https://tramitacion.senado.cl/appsenado/index.php?mo=tramitacion&ac=getDocto&iddocto=36701&tipodoc=ofic",
        "Corresponde la formación de una Comisión Mixta.", "2026-06-09",
    )
    return CitizenProjectionContext(
        expedient_type="Expediente legislativo",
        evidence=(evidence,),
        timeline=(
            CitizenTimelineEvent("2023-06-01", "PROCEDURAL", "Cuenta del proyecto."),
            CitizenTimelineEvent("2025-03-25", "PROCEDURAL", "Oficio de ley a Cámara Revisora."),
            CitizenTimelineEvent("2026-03-05", "SUBSTANTIVE", "La Cámara introduce modificaciones."),
            CitizenTimelineEvent("2026-04-21", "SUBSTANTIVE", "Informe de Comisión de Seguridad Pública."),
            CitizenTimelineEvent("2026-06-09", "SUBSTANTIVE", "El Senado rechaza cuatro modificaciones."),
            CitizenTimelineEvent("2026-06-09", "PROCEDURAL", "Se declara formación de Comisión Mixta.", "evidence-official"),
            CitizenTimelineEvent("2026-08-05", "ADMINISTRATIVE", "La Cámara designa integrantes para Comisión Mixta."),
        ),
        actors=("Senado", "Cámara de Diputadas y Diputados", "Comisión de Seguridad Pública", "Comisión Mixta", "UAF", "SII", "Servicio Nacional de Aduanas", "Jaime Araya Guerrero", "Cristián Araya Lerdo de Tejada", "Eduardo Cretton Rebolledo", "Francisco Orrego Gutiérrez", "Tatiana Urrutia Herrera"),
        documents=(
            CitizenDocument("Mensaje original", "Senado de la República", "Mensaje", "Propuesta original", "https://tramitacion.senado.cl/appsenado/index.php?mo=tramitacion&ac=getDocto&iddocto=16514&tipodoc=mensaje_mocion", "2023-06-01"),
            CitizenDocument("Oficio 36701", "Senado de la República", "Oficio", "Tercer trámite", "https://tramitacion.senado.cl/appsenado/index.php?mo=tramitacion&ac=getDocto&iddocto=36701&tipodoc=ofic", "2026-06-09"),
        ),
        sources=("Senado de la República", "Cámara de Diputadas y Diputados"),
        answers=(
            CitizenQuestionAnswer("¿Por qué este proyecto terminó en Comisión Mixta?", "El Senado aprobó la mayor parte de las enmiendas de Cámara, pero rechazó cuatro modificaciones; el oficio 36701 declara expresamente que corresponde formar Comisión Mixta."),
            CitizenQuestionAnswer("¿El Senado rechazó que la UAF accediera sin autorización judicial?", "No puede afirmarse con la evidencia incorporada: la regla bancaria de Cámara no es D3, que pertenece a la Ley N° 18.046."),
        ),
        knowledge_cutoff=CitizenKnowledgeCutoff("2026-06-09", "2026-08-05", "Esto indica hasta dónde llega la evidencia incorporada y verificada en este expediente. No significa que no existan actuaciones posteriores."),
    )


def golden_v2_specification(v1: ExpedientSpecification) -> ExpedientSpecification:
    """Create v2 solely from approved knowledge and v1's verified references."""
    if v1.version != 1:
        raise ValueError("golden legislative revision requires historical v1")
    claims, evidence = v1.references.claim_ids, v1.references.evidence_ids
    support_claims, support_evidence = claims[:1], evidence[:1]
    def fact(identifier: str, section: str, text: str) -> NarrativeStatement:
        return NarrativeStatement(
            identifier,
            section,
            text,
            EpistemicClass.FACT,
            support_claims,
            support_evidence,
        )
    return ExpedientSpecification(
        v1.expedient_id,
        "Tramitación del proyecto de Inteligencia Económica",
        GOLDEN_QUESTION,
        GOLDEN_SUMMARY,
        v1.provenance_class,
        v1.status,
        2,
        v1.references,
        (
            fact(
                "fact-original-system",
                "what_we_know",
                "El mensaje original propuso crear un Subsistema de Inteligencia Económica integrado por la Unidad de Análisis Financiero (UAF), el Servicio de Impuestos Internos (SII) y el Servicio Nacional de Aduanas (SNA).",
            ),
            fact(
                "fact-original-bank-proposal",
                "bank_secrecy",
                "El mensaje original del proyecto propuso que la UAF pudiera acceder, bajo las condiciones descritas en esa propuesta, a determinada información protegida por secreto o reserva bancaria.",
            ),
            fact(
                "fact-chamber-bank-stage",
                "bank_secrecy",
                "Durante el segundo trámite, el texto aprobado por la Cámara contempló un mecanismo excepcional para requerir información sujeta a secreto bancario directamente y sin autorización judicial previa, bajo las condiciones establecidas en ese texto.",
            ),
            fact(
                "fact-four-divergences",
                "mixed_commission",
                "El Senado aprobó la mayor parte de las modificaciones de Cámara, pero rechazó cuatro modificaciones concretas; el oficio 36701 declara expresamente que corresponde formar Comisión Mixta para resolver esas divergencias.",
            ),
            fact(
                "fact-d1",
                "mixed_commission",
                "D1: la Cámara sustituyó el artículo 1 aprobado por el Senado; el Senado rechazó esa sustitución, sobre el objeto, arquitectura e integrantes del Sistema.",
            ),
            NarrativeStatement(
                "unknown-d2",
                "what_is_missing",
                "D2: se conoce la modificación de la Cámara y el rechazo del Senado al inciso tercero del artículo 7, pero las fuentes incorporadas no certifican suficientemente su contenido material exacto.",
                EpistemicClass.UNKNOWN,
            ),
            fact(
                "fact-d3",
                "mixed_commission",
                "D3: el Senado rechazó la modificación de Cámara al artículo 11, número 2, letra b), ordinal iii), correspondiente a la Ley N° 18.046 sobre Sociedades Anónimas.",
            ),
            fact(
                "fact-d4",
                "mixed_commission",
                "D4: la Cámara eliminó los números 5 y 6 del artículo 15, sobre inhabilidades relacionadas con clasificadoras de riesgo y auditoría externa; el Senado rechazó esa eliminación.",
            ),
            fact(
                "fact-chamber-members",
                "actors",
                "La Cámara designó a Jaime Araya Guerrero, Cristián Araya Lerdo de Tejada, Eduardo Cretton Rebolledo, Francisco Orrego Gutiérrez y Tatiana Urrutia Herrera para concurrir a la Comisión Mixta.",
            ),
            NarrativeStatement(
                "limitation-bank-d3",
                "limitations",
                "No puede afirmarse con las fuentes incorporadas que el Senado haya rechazado la regla de acceso bancario identificada en el texto de Cámara: D3 pertenece a la Ley N° 18.046 y no a la disposición UAF identificada.",
                EpistemicClass.UNKNOWN,
            ),
            NarrativeStatement(
                "unknown-mixed-result",
                "what_is_missing",
                "En las fuentes incorporadas al expediente no se ha identificado todavía evidencia oficial de una sesión, acuerdo o texto final de la Comisión Mixta.",
                EpistemicClass.UNKNOWN,
            ),
            NarrativeStatement(
                "unknown-legal-status",
                "what_is_missing",
                "En las fuentes oficiales incorporadas y verificadas por este expediente no se ha acreditado todavía promulgación, publicación ni entrada en vigencia.",
                EpistemicClass.UNKNOWN,
            ),
            NarrativeStatement(
                "open-final-bank-rule",
                "open_questions",
                "¿Cuál fue el resultado final de la regla sobre información protegida por secreto o reserva bancaria?",
                EpistemicClass.OPEN_QUESTION,
            ),
        ),
    )


def provision_golden_v2(
    service: ExpedientProvisioningService, v1: ExpedientSpecification
) -> ProvisioningResult:
    """Append v2 once; a repeated identical invocation is explicitly idempotent."""
    specification = golden_v2_specification(v1)
    current = service.get(specification.expedient_id)
    if current is None:
        raise ExpedientConflictError("cannot create golden v2 without v1")
    if current.specification.version == 2:
        if current.content_fingerprint != content_fingerprint(specification):
            raise ExpedientConflictError("golden v2 already exists with incompatible content")
        return ProvisioningResult(current, created=False)
    if current.specification.version != 1:
        raise ExpedientConflictError("unexpected legislative expedient version")
    return ProvisioningResult(
        service.revise(specification, expected_current_version=1), created=True
    )
