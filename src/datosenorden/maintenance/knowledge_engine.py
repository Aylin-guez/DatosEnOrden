from __future__ import annotations

import json
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
            "Digest local de prueba. No representa datos oficiales, no afirma irregularidad "
            "y cada afirmacion debe revisarse contra la evidencia original."
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
            {**claim.__dict__, "evidence_ids": list(claim.evidence_ids)}
            for claim in digest.claims
        ],
        "evidence": [anchor.__dict__ for anchor in digest.evidence],
        "connections": dict(digest.connections),
        "notice": digest.notice,
    }


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
    section_titles = ", ".join(section.title for section in document.sections[:3])
    return (
        f"{document.title} es un documento local de demostracion asociado a {document.related_expediente_target}. "
        f"Resume informacion ya presente en metadata y secciones como {section_titles}. "
        "La lectura es neutral y sirve para orientar revision ciudadana con evidencia original."
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
    for index, section in enumerate(document.sections[:5], start=1):
        anchor = _anchor_for_section(evidence, section.id)
        points.append(
            KeyPoint(
                id=f"key-point-{index}",
                title=section.title,
                detail=_first_sentence(section.text) or document.summary,
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
    templates = (
        (
            "Que objetivo declara este documento?",
            "Ayuda a separar el proposito informado de interpretaciones externas.",
        ),
        (
            "Que fuente publica deberia revisarse antes de citarlo?",
            "Permite volver al registro original y no depender del resumen.",
        ),
        (
            "Con que expediente o seguimiento se conecta?",
            "Ayuda a navegar entre documento, historia del caso y reporte ciudadano.",
        ),
    )
    questions: list[CitizenQuestion] = []
    for index, (question, why) in enumerate(templates, start=1):
        anchor = evidence[min(index - 1, len(evidence) - 1)] if evidence else None
        questions.append(
            CitizenQuestion(
                id=f"citizen-question-{index}",
                question=question,
                why_it_matters=why,
                evidence_id=anchor.id if anchor is not None else "",
                document_id=document.id,
                page=anchor.page if anchor is not None else section.page,
                fragment_id=anchor.fragment_id if anchor is not None else _fragment_id(document, section),
                citation_id=anchor.citation_id if anchor is not None else "",
                reference_label=_reference_label(anchor),
            )
        )
    return tuple(questions)


def _build_claims(
    document: OfficialDocument,
    evidence: tuple[EvidenceAnchor, ...],
    citations: tuple[Citation, ...],
) -> tuple[KnowledgeClaim, ...]:
    evidence_ids = tuple(anchor.id for anchor in evidence)
    citation_ids = tuple(citation.id for citation in citations)
    first_evidence = evidence_ids[:1]
    return (
        KnowledgeClaim(
            id="claim-document-identity",
            claim=f"El documento demo se identifica como {document.title}.",
            evidence_ids=first_evidence,
            review_note="Revisar y verificar titulo, fuente y URL en el registro original antes de reutilizar.",
            citation_ids=citation_ids[:1],
        ),
        KnowledgeClaim(
            id="claim-related-expediente",
            claim=f"El documento se conecta al expediente {document.related_expediente_target}.",
            evidence_ids=evidence_ids[:2],
            review_note="La conexion es metadata local de prueba y debe revisarse con evidencia original.",
            citation_ids=citation_ids[:2],
        ),
        KnowledgeClaim(
            id="claim-public-source",
            claim=f"La fuente publica declarada para este digest es {document.public_source}.",
            evidence_ids=evidence_ids[-1:] if evidence_ids else (),
            review_note="No usar esta afirmacion como conclusion automatica; revisar la fuente original.",
            citation_ids=citation_ids[-1:] if citation_ids else (),
        ),
    )


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


def _first_sentence(text: str) -> str:
    cleaned = " ".join(text.split())
    if not cleaned:
        return ""
    first, separator, _rest = cleaned.partition(".")
    return first + separator if separator else cleaned


def _excerpt(text: str, limit: int = 220) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3].rstrip() + "..."
