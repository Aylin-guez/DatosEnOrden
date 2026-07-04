from __future__ import annotations

import json
import re
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Any

from datosenorden.maintenance.citizen_reports import DEMO_CITIZEN_REPORT_ID
from datosenorden.maintenance.tracking import DEMO_ENTITY_NAME
from datosenorden.maintenance.tracking import DEMO_TRACKING_ITEM_ID
from datosenorden.maintenance.tracking import LOCAL_TEST_DATA
from datosenorden.maintenance.tracking import NOT_OFFICIAL_DATA
from datosenorden.maintenance.platform_config import PlatformConfig
from datosenorden.maintenance.platform_config import get_default_platform_config
from datosenorden.maintenance.platform_config import vocabulary_labels


DEMO_KNOWLEDGE_DOCUMENT_ID = "knowledge-doc-arauco-hospital-demo-2026"
DEFAULT_SAMPLE_PATH = Path("data") / "sample" / "official_documents_sample.json"


@dataclass(frozen=True)
class DocumentSection:
    id: str
    title: str
    text: str
    order: int
    page: int = 1
    fragment_id: str = ""


@dataclass(frozen=True)
class DocumentReference:
    document_id: str
    title: str
    source: str
    document_type: str
    published_at: str
    official_url: str
    classification: str = LOCAL_TEST_DATA
    official_status: str = NOT_OFFICIAL_DATA


@dataclass(frozen=True)
class PageReference:
    document_id: str
    page: int
    label: str


@dataclass(frozen=True)
class DocumentFragment:
    id: str
    document_id: str
    page: int
    section_id: str
    section_title: str
    text: str
    anchor_id: str


@dataclass(frozen=True)
class FragmentAnchor:
    id: str
    document_id: str
    page: int
    section_id: str
    fragment_id: str
    label: str
    excerpt: str


@dataclass(frozen=True)
class Citation:
    id: str
    document_id: str
    page: int
    section_id: str
    fragment_id: str
    quoted_text: str
    label: str


@dataclass(frozen=True)
class OfficialDocument:
    id: str
    title: str
    source: str
    document_type: str
    published_at: str
    official_url: str
    summary: str
    related_expediente_target: str
    related_tracking_item_id: str
    related_citizen_report_id: str
    public_source: str
    sections: tuple[DocumentSection, ...]
    hash_sha256: str = ""
    classification: str = LOCAL_TEST_DATA
    official_status: str = NOT_OFFICIAL_DATA


@dataclass(frozen=True)
class KeyPoint:
    id: str
    title: str
    detail: str
    section_id: str
    evidence_id: str
    document_id: str
    page: int
    fragment_id: str
    citation_id: str
    reference_label: str


@dataclass(frozen=True)
class CitizenQuestion:
    id: str
    question: str
    why_it_matters: str
    evidence_id: str
    document_id: str
    page: int
    fragment_id: str
    citation_id: str
    reference_label: str


@dataclass(frozen=True)
class KnowledgeClaim:
    id: str
    claim: str
    evidence_ids: tuple[str, ...]
    review_note: str
    citation_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class EvidenceAnchor:
    id: str
    document_id: str
    section_id: str
    page: int
    fragment_id: str
    source: str
    label: str
    url: str
    excerpt: str
    citation_id: str
    quoted_text: str
    classification: str = LOCAL_TEST_DATA
    official_status: str = NOT_OFFICIAL_DATA


@dataclass(frozen=True)
class KnowledgeDigest:
    document: OfficialDocument
    document_reference: DocumentReference
    pages: tuple[PageReference, ...]
    fragments: tuple[DocumentFragment, ...]
    anchors: tuple[FragmentAnchor, ...]
    citations: tuple[Citation, ...]
    citizen_summary: str
    key_points: tuple[KeyPoint, ...]
    citizen_questions: tuple[CitizenQuestion, ...]
    claims: tuple[KnowledgeClaim, ...]
    evidence: tuple[EvidenceAnchor, ...]
    connections: dict[str, str]
    notice: str


def load_official_documents(path: Path | str = DEFAULT_SAMPLE_PATH) -> tuple[OfficialDocument, ...]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = payload.get("documents", payload if isinstance(payload, list) else [])
    return tuple(_official_document_from_dict(row) for row in rows)


def list_knowledge_documents(path: Path | str = DEFAULT_SAMPLE_PATH) -> list[OfficialDocument]:
    return list(load_official_documents(path))


def get_knowledge_document(document_id: str, path: Path | str = DEFAULT_SAMPLE_PATH) -> OfficialDocument | None:
    return next((document for document in load_official_documents(path) if document.id == document_id), None)


def build_knowledge_demo(path: Path | str = DEFAULT_SAMPLE_PATH) -> KnowledgeDigest:
    document = get_knowledge_document(DEMO_KNOWLEDGE_DOCUMENT_ID, path)
    if document is None:
        documents = load_official_documents(path)
        if not documents:
            raise ValueError("No knowledge documents available")
        document = documents[0]
    return build_knowledge_digest(document)


def build_knowledge_digest(document: OfficialDocument | str, path: Path | str = DEFAULT_SAMPLE_PATH) -> KnowledgeDigest:
    if isinstance(document, str):
        resolved = get_knowledge_document(document, path)
        if resolved is None:
            raise ValueError(f"Unknown knowledge document: {document}")
        document = resolved

    fragments = _build_fragments(document)
    fragment_anchors = _build_fragment_anchors(fragments)
    citations = _build_citations(fragment_anchors)
    evidence = _build_evidence(document, fragment_anchors, citations)
    key_points = _build_key_points(document, evidence)
    questions = _build_citizen_questions(document, evidence)
    claims = _build_claims(document, evidence, citations)
    return KnowledgeDigest(
        document=document,
        document_reference=_document_reference(document),
        pages=_build_pages(fragments),
        fragments=fragments,
        anchors=fragment_anchors,
        citations=citations,
        citizen_summary=_build_citizen_summary(document),
        key_points=key_points,
        citizen_questions=questions,
        claims=claims,
        evidence=evidence,
        connections={
            "expediente": document.related_expediente_target,
            "seguimiento": document.related_tracking_item_id,
            "reporte_ciudadano": document.related_citizen_report_id,
            "fuente_publica": document.public_source,
        },
        notice=(
            "Lectura documental automatica basada solo en fragmentos extraidos. No afirma irregularidad, "
            "responsabilidad ni efectos juridicos; cada afirmacion debe revisarse contra el documento original."
        ),
    )


def export_knowledge_demo_report(
    output_path: Path | str | None = None,
    digest: KnowledgeDigest | None = None,
) -> str:
    data = digest or build_knowledge_demo()
    path = Path(output_path) if output_path is not None else Path("reports") / "knowledge_demo_arauco.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_render_knowledge_html(data), encoding="utf-8")
    return str(path)


def render_knowledge_demo_summary(digest: KnowledgeDigest | None = None) -> str:
    data = digest or build_knowledge_demo()
    lines = [
        "knowledge_demo_summary:",
        f"  document_id={data.document.id}",
        f"  title={data.document.title}",
        f"  classification={data.document.classification}",
        f"  official_status={data.document.official_status}",
        f"  sections={len(data.document.sections)}",
        f"  key_points={len(data.key_points)}",
        f"  questions={len(data.citizen_questions)}",
        f"  claims={len(data.claims)}",
        f"  evidence={len(data.evidence)}",
        "  connections:",
    ]
    lines.extend(f"    - {key}: {value}" for key, value in data.connections.items())
    return "\n".join(lines)


def get_knowledge_vocabulary(config: PlatformConfig | None = None) -> dict[str, str]:
    """Return domain labels without hardcoding a specific industry in the engine."""
    return vocabulary_labels(config or get_default_platform_config())


def knowledge_digest_to_dict(digest: KnowledgeDigest) -> dict[str, Any]:
    evidence_by_id = {anchor.id: anchor for anchor in digest.evidence}
    return {
        "document": official_document_to_dict(digest.document),
        "document_reference": digest.document_reference.__dict__,
        "pages": [page.__dict__ for page in digest.pages],
        "fragments": [fragment.__dict__ for fragment in digest.fragments],
        "anchors": [anchor.__dict__ for anchor in digest.anchors],
        "citations": [citation.__dict__ for citation in digest.citations],
        "citizen_summary": digest.citizen_summary,
        "key_points": [point.__dict__ for point in digest.key_points],
        "citizen_questions": [question.__dict__ for question in digest.citizen_questions],
        "claims": [
            {
                **claim.__dict__,
                "evidence_ids": list(claim.evidence_ids),
                "fragment_id": _claim_fragment_id(claim, evidence_by_id),
                "page": _claim_page(claim, evidence_by_id),
            }
            for claim in digest.claims
        ],
        "evidence": [anchor.__dict__ for anchor in digest.evidence],
        "connections": dict(digest.connections),
        "notice": digest.notice,
    }


def _claim_fragment_id(claim: KnowledgeClaim, evidence_by_id: dict[str, EvidenceAnchor]) -> str:
    first_id = claim.evidence_ids[0] if claim.evidence_ids else ""
    anchor = evidence_by_id.get(first_id)
    return anchor.fragment_id if anchor is not None else ""


def _claim_page(claim: KnowledgeClaim, evidence_by_id: dict[str, EvidenceAnchor]) -> int | None:
    first_id = claim.evidence_ids[0] if claim.evidence_ids else ""
    anchor = evidence_by_id.get(first_id)
    return anchor.page if anchor is not None else None


def official_document_to_dict(document: OfficialDocument) -> dict[str, Any]:
    return {
        **document.__dict__,
        "sections": [section.__dict__ for section in document.sections],
    }


def _official_document_from_dict(row: dict[str, Any]) -> OfficialDocument:
    sections = tuple(
        DocumentSection(
            id=str(section.get("id", "")),
            title=str(section.get("title", "")),
            text=str(section.get("text", "")),
            order=int(section.get("order", index + 1) or index + 1),
            page=int(section.get("page", index + 1) or index + 1),
            fragment_id=str(section.get("fragment_id", "")),
        )
        for index, section in enumerate(row.get("sections", []))
    )
    return OfficialDocument(
        id=str(row.get("id", "")),
        title=str(row.get("title", "")),
        source=str(row.get("source", "")),
        document_type=str(row.get("document_type", "")),
        published_at=str(row.get("published_at", "")),
        official_url=str(row.get("official_url", "")),
        summary=str(row.get("summary", "")),
        related_expediente_target=str(row.get("related_expediente_target", "")),
        related_tracking_item_id=str(row.get("related_tracking_item_id", "")),
        related_citizen_report_id=str(row.get("related_citizen_report_id", "")),
        public_source=str(row.get("public_source", row.get("source", ""))),
        sections=tuple(sorted(sections, key=lambda section: section.order)),
        hash_sha256=str(row.get("hash_sha256", "")),
        classification=str(row.get("classification", LOCAL_TEST_DATA)),
        official_status=str(row.get("official_status", NOT_OFFICIAL_DATA)),
    )


def _build_citizen_summary(document: OfficialDocument) -> str:
    opening = _summary_opening(document)
    themes = ", ".join(_content_title(section) for section in _representative_sections(document.sections, limit=4))
    if themes:
        return (
            f"{opening} La lectura destaca materias presentes en el texto: {themes}. "
            "El resumen no agrega antecedentes externos ni interpreta responsabilidades."
        )
    return (
        f"{opening} La lectura se limita al contenido extraido del documento y mantiene referencias por fragmento."
    )


def _document_reference(document: OfficialDocument) -> DocumentReference:
    return DocumentReference(
        document_id=document.id,
        title=document.title,
        source=document.source,
        document_type=document.document_type,
        published_at=document.published_at,
        official_url=document.official_url,
        classification=document.classification,
        official_status=document.official_status,
    )


def _build_fragments(document: OfficialDocument) -> tuple[DocumentFragment, ...]:
    return tuple(
        DocumentFragment(
            id=_fragment_id(document, section),
            document_id=document.id,
            page=section.page,
            section_id=section.id,
            section_title=section.title,
            text=section.text,
            anchor_id=f"anchor-{document.id}-{_fragment_id(document, section)}",
        )
        for section in document.sections
    )


def _build_pages(fragments: tuple[DocumentFragment, ...]) -> tuple[PageReference, ...]:
    if not fragments:
        return ()
    pages = sorted({fragment.page for fragment in fragments})
    return tuple(PageReference(document_id=fragments[0].document_id, page=page, label=f"Pagina {page}") for page in pages)


def _build_fragment_anchors(fragments: tuple[DocumentFragment, ...]) -> tuple[FragmentAnchor, ...]:
    return tuple(
        FragmentAnchor(
            id=fragment.anchor_id,
            document_id=fragment.document_id,
            page=fragment.page,
            section_id=fragment.section_id,
            fragment_id=fragment.id,
            label=fragment.section_title,
            excerpt=_excerpt(fragment.text),
        )
        for fragment in fragments
    )


def _build_citations(anchors: tuple[FragmentAnchor, ...]) -> tuple[Citation, ...]:
    return tuple(
        Citation(
            id=f"citation-{anchor.document_id}-{anchor.fragment_id}",
            document_id=anchor.document_id,
            page=anchor.page,
            section_id=anchor.section_id,
            fragment_id=anchor.fragment_id,
            quoted_text=anchor.excerpt,
            label=f"Pagina {anchor.page} - {anchor.label}",
        )
        for anchor in anchors
    )


def _build_evidence(
    document: OfficialDocument,
    fragment_anchors: tuple[FragmentAnchor, ...],
    citations: tuple[Citation, ...],
) -> tuple[EvidenceAnchor, ...]:
    evidence: list[EvidenceAnchor] = []
    citation_by_fragment = {citation.fragment_id: citation for citation in citations}
    anchor_by_section = {anchor.section_id: anchor for anchor in fragment_anchors}
    for section in document.sections:
        fragment_id = _fragment_id(document, section)
        citation = citation_by_fragment.get(fragment_id)
        fragment_anchor = anchor_by_section.get(section.id)
        evidence.append(
            EvidenceAnchor(
                id=f"evidence-{document.id}-{section.id}",
                document_id=document.id,
                section_id=section.id,
                page=section.page,
                fragment_id=fragment_id,
                source=document.source,
                label=section.title,
                url=f"{document.official_url}#page={section.page}&fragment={fragment_id}",
                excerpt=fragment_anchor.excerpt if fragment_anchor is not None else _excerpt(section.text),
                citation_id=citation.id if citation is not None else "",
                quoted_text=citation.quoted_text if citation is not None else _excerpt(section.text, limit=160),
                classification=document.classification,
                official_status=document.official_status,
            )
        )
    return tuple(evidence)
def _build_key_points(document: OfficialDocument, evidence: tuple[EvidenceAnchor, ...]) -> tuple[KeyPoint, ...]:
    points: list[KeyPoint] = []
    for index, section in enumerate(_representative_sections(document.sections, limit=6), start=1):
        anchor = _anchor_for_section(evidence, section.id)
        points.append(
            KeyPoint(
                id=f"key-point-{index}",
                title=_content_title(section),
                detail=_section_detail(section) or document.summary,
                section_id=section.id,
                evidence_id=anchor.id if anchor is not None else "",
                document_id=document.id,
                page=anchor.page if anchor is not None else section.page,
                fragment_id=anchor.fragment_id if anchor is not None else _fragment_id(document, section),
                citation_id=anchor.citation_id if anchor is not None else "",
                reference_label=_reference_label(anchor),
            )
        )
    return tuple(points)


def _build_citizen_questions(
    document: OfficialDocument,
    evidence: tuple[EvidenceAnchor, ...],
) -> tuple[CitizenQuestion, ...]:
    questions: list[CitizenQuestion] = []
    selected = _representative_evidence(evidence, limit=5)
    for index, anchor in enumerate(selected, start=1):
        question, why = _question_from_evidence(anchor)
        questions.append(
            CitizenQuestion(
                id=f"citizen-question-{index}",
                question=question,
                why_it_matters=why,
                evidence_id=anchor.id,
                document_id=document.id,
                page=anchor.page,
                fragment_id=anchor.fragment_id,
                citation_id=anchor.citation_id,
                reference_label=_reference_label(anchor),
            )
        )
    return tuple(questions)


def _build_claims(
    document: OfficialDocument,
    evidence: tuple[EvidenceAnchor, ...],
    citations: tuple[Citation, ...],
) -> tuple[KnowledgeClaim, ...]:
    citation_by_fragment = {citation.fragment_id: citation.id for citation in citations}
    claims: list[KnowledgeClaim] = []
    for index, anchor in enumerate(_representative_evidence(evidence, limit=5), start=1):
        claims.append(
            KnowledgeClaim(
                id=f"claim-document-content-{index}",
                claim=_claim_from_evidence(anchor),
                evidence_ids=(anchor.id,),
                review_note=(
                    f"Afirmacion derivada del fragment_id {anchor.fragment_id}; "
                    f"pagina {anchor.page}. Revisar el texto original antes de citar."
                ),
                citation_ids=(citation_by_fragment.get(anchor.fragment_id, anchor.citation_id),),
            )
        )
    return tuple(claims)


def _render_knowledge_html(digest: KnowledgeDigest) -> str:
    document = digest.document
    key_points = "\n".join(
        f"<li><strong>{escape(point.title)}</strong><p>{escape(point.detail)}</p>"
        f"<small>Evidencia: {escape(point.evidence_id)}</small></li>"
        for point in digest.key_points
    )
    questions = "\n".join(
        f"<li><strong>{escape(question.question)}</strong><p>{escape(question.why_it_matters)}</p></li>"
        for question in digest.citizen_questions
    )
    claims = "\n".join(
        f"<li><strong>{escape(claim.claim)}</strong><p>{escape(claim.review_note)}</p>"
        f"<small>Evidencia: {escape(', '.join(claim.evidence_ids))}</small></li>"
        for claim in digest.claims
    )
    evidence = "\n".join(
        f"<li><strong>{escape(anchor.label)}</strong><p>{escape(anchor.excerpt)}</p>"
        f"<code>{escape(anchor.url)}</code></li>"
        for anchor in digest.evidence
    )
    connections = "\n".join(
        f"<li><strong>{escape(key)}:</strong> {escape(value)}</li>"
        for key, value in digest.connections.items()
    )
    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>{escape(document.title)} - DatosEnOrden</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 32px; line-height: 1.5; color: #18181b; }}
    header, section {{ max-width: 960px; margin: 0 auto 28px; }}
    li {{ margin-bottom: 14px; }}
    .badge {{ display: inline-block; border: 1px solid #0f766e; color: #0f766e; padding: 4px 8px; border-radius: 999px; }}
    code {{ background: #f4f4f5; padding: 2px 4px; }}
  </style>
</head>
<body>
  <header>
    <p class="badge">{escape(document.classification)} / {escape(document.official_status)}</p>
    <h1>{escape(document.title)}</h1>
    <p>{escape(digest.citizen_summary)}</p>
    <p><strong>Fuente:</strong> {escape(document.source)} | <strong>Tipo:</strong> {escape(document.document_type)}</p>
  </header>
  <section>
    <h2>Puntos importantes</h2>
    <ul>{key_points}</ul>
  </section>
  <section>
    <h2>Preguntas ciudadanas sugeridas</h2>
    <ul>{questions}</ul>
  </section>
  <section>
    <h2>Claims verificables</h2>
    <ul>{claims}</ul>
  </section>
  <section>
    <h2>Conexiones</h2>
    <ul>{connections}</ul>
  </section>
  <section>
    <h2>Evidencia asociada</h2>
    <ul>{evidence}</ul>
  </section>
  <section>
    <h2>Aclaracion</h2>
    <p>{escape(digest.notice)}</p>
  </section>
</body>
</html>
"""


def _anchor_for_section(evidence: tuple[EvidenceAnchor, ...], section_id: str) -> EvidenceAnchor | None:
    return next((anchor for anchor in evidence if anchor.section_id == section_id), None)


def _fragment_id(document: OfficialDocument, section: DocumentSection) -> str:
    return section.fragment_id or f"{document.id}-{section.id}"


def _reference_label(anchor: EvidenceAnchor | None) -> str:
    if anchor is None:
        return "Referencia pendiente"
    return f"Pagina {anchor.page} - {anchor.label}"


def _representative_sections(
    sections: tuple[DocumentSection, ...],
    limit: int,
) -> tuple[DocumentSection, ...]:
    if not sections:
        return ()
    topic_needles = (
        ("deficit", "deficit estructural"),
        ("educacion", "educaci"),
        ("salud", "salud"),
        ("seguridad", "seguridad ciudadana"),
        ("infraestructura", "infraestructura"),
        ("innovacion", "innovacion"),
        ("contenido", "presupuesto de ingresos y gastos"),
        ("informes", "informe de ejecucion presupuestaria"),
    )
    selected: list[DocumentSection] = []
    normalized_rows = [(section, _normalize_text(section.text)) for section in sections]
    for _topic, needle in topic_needles:
        candidates = [
            (text.index(needle), section)
            for section, text in normalized_rows
            if section not in selected and needle in text
        ]
        match = min(candidates, default=(0, None), key=lambda item: item[0])[1]
        if match is not None and match not in selected:
            selected.append(match)
            if len(selected) >= limit:
                return tuple(selected)
    for section in sections:
        if section not in selected:
            selected.append(section)
            if len(selected) >= limit:
                break
    return tuple(selected)


def _representative_evidence(
    evidence: tuple[EvidenceAnchor, ...],
    limit: int,
) -> tuple[EvidenceAnchor, ...]:
    if not evidence:
        return ()
    topic_needles = (
        "deficit estructural",
        "educaci",
        "salud",
        "seguridad ciudadana",
        "infraestructura",
        "innovacion",
        "informe de ejecucion presupuestaria",
    )
    selected: list[EvidenceAnchor] = []
    normalized_rows = [(anchor, _normalize_text(anchor.excerpt)) for anchor in evidence]
    for needle in topic_needles:
        candidates = [
            (text.index(needle), anchor)
            for anchor, text in normalized_rows
            if anchor not in selected and needle in text
        ]
        match = min(candidates, default=(0, None), key=lambda item: item[0])[1]
        if match is not None and match not in selected:
            selected.append(match)
            if len(selected) >= limit:
                return tuple(selected)
    for anchor in evidence:
        if anchor not in selected:
            selected.append(anchor)
            if len(selected) >= limit:
                break
    return tuple(selected)


def _content_title(section: DocumentSection) -> str:
    explicit = section.title.strip()
    if explicit and not explicit.lower().startswith("fragmento "):
        return explicit
    text = " ".join(section.text.split())
    markers = (
        "deficit estructural",
        "innovacion",
        "Educacion Parvularia",
        "Educacion Escolar",
        "Educacion Superior",
        "seguridad ciudadana",
        "Sistema de Concesiones",
        "infraestructura",
        "Presupuesto de Ingresos y Gastos",
        "informe de ejecucion presupuestaria",
        "Educacion Parvularia",
        "Educacion Escolar",
        "Educacion Superior",
        "Cultura",
        "Salud",
        "AUGE",
        "Plan Cuadrante",
        "Presupuesto 2013",
        "Contexto economico global",
        "Articulo",
    )
    lowered = _normalize_text(text)
    for marker in markers:
        if _normalize_text(marker) in lowered:
            return _title_from_marker(marker)
    first = _first_sentence(text)
    return first[:90].rstrip(" .") or f"Fragmento {section.order:02d}"


def _point_detail(text: str) -> str:
    sentences = _sentences(text)
    if not sentences:
        return ""
    numeric = next((sentence for sentence in sentences if any(char.isdigit() for char in sentence)), "")
    return numeric or sentences[0]


def _section_detail(section: DocumentSection) -> str:
    title = _normalize_text(_content_title(section))
    text = section.text
    if "deficit" in title:
        return _sentence_containing(text, "deficit estructural")
    if "educacion" in title:
        return _sentence_containing(text, "educaci")
    if "salud" in title:
        return _sentence_containing(text, "salud") or _sentence_containing(text, "auge")
    if "seguridad" in title:
        return _sentence_containing(text, "seguridad ciudadana") or _sentence_containing(text, "carabineros")
    if "infraestructura" in title:
        return _sentence_containing(text, "infraestructura") or _sentence_containing(text, "vialidad")
    if "innovacion" in title:
        return _sentence_containing(text, "innovacion") or _sentence_containing(text, "emprendimiento")
    if "cultura" in title:
        return _sentence_containing(text, "cultura") or _sentence_containing(text, "centros culturales")
    if "informes" in title:
        return _sentence_containing(text, "informe de ejecucion")
    return _point_detail(text)


def _question_from_evidence(anchor: EvidenceAnchor) -> tuple[str, str]:
    text = _normalize_text(anchor.excerpt)
    if "deficit" in text:
        return (
            "Que regla fiscal y deficit declara el mensaje presupuestario?",
            "Permite revisar el marco fiscal informado por el Ejecutivo en el propio texto.",
        )
    if "educacion" in text:
        return (
            "Que aumentos y coberturas educacionales anuncia el presupuesto 2013?",
            "Ayuda a distinguir montos, porcentajes y grupos beneficiarios mencionados.",
        )
    if "salud" in text or "auge" in text:
        return (
            "Que compromisos de salud y atencion publica aparecen financiados?",
            "Ubica recursos, programas y coberturas sanitarias descritas en el documento.",
        )
    if "seguridad ciudadana" in text or "carabineros" in text:
        return (
            "Que medidas de seguridad ciudadana se financian en el presupuesto?",
            "Permite seguir programas, instituciones y montos de seguridad mencionados.",
        )
    if "infraestructura" in text or "concesiones" in text or "vialidad" in text:
        return (
            "Que obras, conectividad o concesiones menciona el presupuesto?",
            "Permite ubicar las lineas de infraestructura que el texto declara financiar.",
        )
    if "innovacion" in text or "emprendimiento" in text:
        return (
            "Que recursos se orientan a innovacion y emprendimiento?",
            "Ayuda a revisar programas, montos y metas economicas mencionadas.",
        )
    if "informe" in text or "comision especial mixta" in text:
        return (
            "Que obligaciones de informacion y rendicion establece el articulado?",
            "Sirve para identificar plazos, destinatarios y antecedentes exigidos.",
        )
    return (
        f"Que afirma este fragmento sobre {_short_topic(anchor.label)}?",
        "La respuesta debe salir del fragmento citado, sin antecedentes externos.",
    )


def _claim_from_evidence(anchor: EvidenceAnchor) -> str:
    text = anchor.excerpt
    normalized = _normalize_text(text)
    if "deficit estructural" in normalized:
        detail = _sentence_containing(text, "deficit estructural")
    elif "educaci" in normalized:
        detail = _sentence_containing(text, "educaci")
    elif "salud" in normalized or "auge" in normalized:
        detail = _sentence_containing(text, "salud") or _sentence_containing(text, "auge")
    elif "seguridad ciudadana" in normalized:
        detail = _sentence_containing(text, "seguridad ciudadana")
    elif "infraestructura" in normalized or "concesiones" in normalized:
        detail = _sentence_containing(text, "infraestructura") or _sentence_containing(text, "concesiones")
    elif "innovacion" in normalized:
        detail = _sentence_containing(text, "innovacion")
    else:
        detail = _point_detail(text) or text
    detail = detail or _point_detail(text) or text
    return f"El documento senala que {detail.rstrip('.')}."


def _short_topic(value: str) -> str:
    text = " ".join(value.split())
    return text[:70].rstrip(" .") or "esta materia"


def _summary_opening(document: OfficialDocument) -> str:
    normalized_title = _normalize_text(document.title)
    if "presupuestos" in normalized_title and "2013" in normalized_title:
        return (
            "El documento presenta el mensaje presidencial que inicia el proyecto de Ley "
            "de Presupuestos del sector publico para 2013."
        )
    return _first_sentence(document.summary) or _first_sentence(document.sections[0].text if document.sections else "")


def _title_from_marker(marker: str) -> str:
    mapping = {
        "deficit estructural": "Regla fiscal y deficit",
        "seguridad ciudadana": "Seguridad ciudadana",
        "informe de ejecucion presupuestaria": "Informes de ejecucion presupuestaria",
        "innovacion": "Innovacion y emprendimiento",
        "infraestructura": "Infraestructura",
    }
    return mapping.get(marker, marker)


def _sentence_containing(text: str, needle: str) -> str:
    normalized_needle = _normalize_text(needle)
    return next(
        (
            sentence
            for sentence in _sentences(text)
            if normalized_needle in _normalize_text(sentence) and len(sentence) > 40
        ),
        "",
    )


def _normalize_text(text: str) -> str:
    replacements = {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "Á": "a",
        "É": "e",
        "Í": "i",
        "Ó": "o",
        "Ú": "u",
        "ñ": "n",
        "Ñ": "n",
    }
    normalized = "".join(replacements.get(char, char.lower()) for char in text)
    return " ".join(normalized.split())


def _first_sentence(text: str) -> str:
    sentences = _sentences(text)
    return sentences[0] if sentences else ""


def _sentences(text: str) -> list[str]:
    cleaned = " ".join(text.split())
    if not cleaned:
        return []
    parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÑ0-9])", cleaned) if part.strip()]
    return parts


def _excerpt(text: str, limit: int = 700) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3].rstrip() + "..."
