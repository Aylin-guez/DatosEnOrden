from __future__ import annotations

from copy import deepcopy

from .models import (
    Claim,
    EvidenceItem,
    Expedient,
    Hypothesis,
    Indicator,
    LABORATORY_EXPEDIENT_ID,
    Problem,
    Relationship,
    Source,
)


_SECTIONS = (
    {"id": "summary", "title": "Resumen", "summary": "Lectura general del Expediente.", "status": "READY"},
    {"id": "problem", "title": "Problema", "summary": "Problema público y alcance que se quiere comprender.", "status": "READY"},
    {"id": "evidence", "title": "Evidencia", "summary": "Fuentes y materiales que todavía requieren investigación.", "status": "PARTIAL"},
    {"id": "claims", "title": "Afirmaciones", "summary": "Afirmaciones públicas y su estado de respaldo.", "status": "PARTIAL"},
    {"id": "hypotheses", "title": "Hipótesis", "summary": "Alternativas iniciales, beneficios esperados y riesgos.", "status": "READY"},
    {"id": "indicators", "title": "Indicadores", "summary": "Indicadores previstos, sin valores inventados.", "status": "PARTIAL"},
    {"id": "sources", "title": "Fuentes", "summary": "Fuentes públicas previstas para la investigación.", "status": "PARTIAL"},
    {"id": "relationships", "title": "Relaciones", "summary": "Relaciones de contexto, sin inferencia automática.", "status": "PENDING_DATA"},
    {"id": "participation", "title": "Participación", "summary": "Participación informativa, aún no habilitada.", "status": "LOCKED"},
)

_DEMO = Expedient(
    id=LABORATORY_EXPEDIENT_ID,
    title="Trabajo flexible, protección social e infraestructura pública de confianza",
    summary="Expediente inicial para estudiar barreras de acceso, continuidad y distribución de oportunidades en el sistema laboral chileno.",
    status="IN_RESEARCH",
    problem=Problem(
        id="PROB-001",
        title="Acceso y continuidad de oportunidades laborales",
        description="Existen barreras de acceso, continuidad y distribución de oportunidades en el sistema laboral chileno.",
        scope="Mercado laboral, protección social e infraestructura pública.",
        affected_population="Personas que buscan oportunidades laborales y organizaciones que necesitan capacidades.",
        territory="Chile",
        period="Primera formulación pública",
        status="PENDING_RESEARCH",
    ),
    scope="Estudio público inicial del problema y de hipótesis de infraestructura.",
    territory="Chile",
    period="Primera formulación pública",
    updated_at="2026-07-25",
    reading_progress=0,
    sections=_SECTIONS,
    hypotheses=(
        Hypothesis(
            id="HYP-001",
            title="Infraestructura pública interoperable para un mercado laboral flexible, distribuido e inclusivo",
            summary="Una infraestructura pública de confianza podría conectar capacidades demostrables, necesidades de trabajo y protección social sin exigir que toda oportunidad dependa de títulos formales.",
            mechanism="Combinar interoperabilidad pública, contratación por necesidades o proyectos, mecanismos de cumplimiento, protección y cotizaciones.",
            expected_benefits=("Acceso gradual para personas y organizaciones.", "Convivencia con el sistema laboral actual.", "Distribución más amplia de oportunidades."),
            risks=("Exclusión digital o territorial.", "Desprotección si los mecanismos de cumplimiento son débiles.", "Adopción desigual entre sectores."),
            maturity="INITIAL",
            status="OPEN_FOR_RESEARCH",
            public_origin_type="Hipótesis inicial del Expediente",
        ),
    ),
    evidence_items=(
        EvidenceItem("EVID-001", "Fuentes laborales públicas por identificar", "PUBLIC_SOURCE_SET", "Fuentes públicas", "Pendiente de fragmentos", "PENDING_DATA", "La cobertura y autenticidad deben revisarse antes de usar valores.", ("CLM-001",)),
        EvidenceItem("EVID-002", "Material documental sobre protección y cotizaciones", "DOCUMENT_SET", "Documentos oficiales", "Pendiente de lectura", "PENDING_DATA", "No se presenta todavía una conclusión documental.", ("CLM-001",)),
    ),
    claims=(
        Claim("CLM-001", "La hipótesis requiere combinar acceso a oportunidades con mecanismos de protección social.", "SCOPE", "OPEN", "NOT_ASSESSED", ("EVID-001", "EVID-002"), ()),
    ),
    indicators=tuple(
        Indicator(f"IND-{index:03d}", name, "Indicador previsto para la investigación del Expediente.", "Pendiente", None, "Pendiente", "Fuente pública por seleccionar", "PENDING_DATA", "No hay valor cargado; no usar como estadística.")
        for index, name in enumerate((
            "Desempleo nacional", "Desempleo regional", "Duración del desempleo", "Informalidad",
            "Regularidad de cotizaciones", "Concentración de oportunidades", "Ingresos",
            "Tiempo hasta el primer proyecto",
        ), 1)
    ),
    sources=(
        Source("SRC-001", "Fuentes laborales públicas", "PUBLIC_DATASET", "Organismo público por seleccionar", "PENDING_REVIEW", "PENDING_REVIEW", "PENDING_DATA", "La fuente y su disponibilidad deben verificarse."),
    ),
    relationships=(
        Relationship("REL-001", "Problema público", "REQUIRES_RESEARCH", "Hipótesis HYP-001", "CONTEXT_ONLY", "Relación editorial de alcance, no inferencia."),
    ),
    open_questions_summary="La cobertura territorial, la protección efectiva y la interoperabilidad requieren investigación posterior.",
    participation_status="LOCKED",
)


def load_expedient_catalog() -> list[dict]:
    return [{"id": _DEMO.id, "title": _DEMO.title, "summary": _DEMO.summary, "status": _DEMO.status, "updated_at": _DEMO.updated_at}]


def get_expedient(expedient_id: str) -> dict | None:
    if str(expedient_id or "").strip().upper() != _DEMO.id:
        return None
    return deepcopy(_DEMO.to_dict())
