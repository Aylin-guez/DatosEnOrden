from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from datosenorden.maintenance.knowledge_engine import DEFAULT_SAMPLE_PATH
from datosenorden.maintenance.knowledge_engine import DEMO_KNOWLEDGE_DOCUMENT_ID
from datosenorden.maintenance.knowledge_engine import KnowledgeDigest
from datosenorden.maintenance.knowledge_engine import OfficialDocument
from datosenorden.maintenance.knowledge_engine import build_knowledge_digest
from datosenorden.maintenance.knowledge_engine import official_document_to_dict


@dataclass(frozen=True)
class ReadingMetric:
    id: str
    label: str
    value: int


@dataclass(frozen=True)
class ReadingConnection:
    label: str
    href: str
    target_id: str


@dataclass(frozen=True)
class FragmentReadingContext:
    fragment_id: str
    page: int
    reference_label: str
    excerpt: str
    summary: tuple[dict[str, Any], ...]
    questions: tuple[dict[str, Any], ...]
    claims: tuple[dict[str, Any], ...]
    evidence: tuple[dict[str, Any], ...]
    connections: tuple[ReadingConnection, ...]


@dataclass(frozen=True)
class DocumentExperience:
    document: dict[str, Any]
    pages: tuple[dict[str, Any], ...]
    fragments: tuple[dict[str, Any], ...]
    references: tuple[dict[str, Any], ...]
    questions: tuple[dict[str, Any], ...]
    key_points: tuple[dict[str, Any], ...]
    claims: tuple[dict[str, Any], ...]
    citizen_summary: str
    connections: dict[str, str]
    related_expediente: str
    related_tracking: str
    related_report: str
    metrics: tuple[ReadingMetric, ...]
    fragment_contexts: tuple[FragmentReadingContext, ...]
    selected_context: FragmentReadingContext | None
    notice: str


def generate_document_experience(
    document: OfficialDocument | str = DEMO_KNOWLEDGE_DOCUMENT_ID,
    path: Path | str = DEFAULT_SAMPLE_PATH,
) -> DocumentExperience:
    """Generate a UI-ready documented reading from one structured document."""
    digest = build_knowledge_digest(document, path) if isinstance(document, str) else build_knowledge_digest(document)
    return _experience_from_digest(digest)


def publish_document_experience(
    document_id: str = DEMO_KNOWLEDGE_DOCUMENT_ID,
    path: Path | str = DEFAULT_SAMPLE_PATH,
) -> DocumentExperience:
    """Produce the complete navigable object for publication surfaces."""
    return generate_document_experience(document_id, path=path)


def document_experience_to_dict(experience: DocumentExperience) -> dict[str, Any]:
    selected_context = _context_to_dict(experience.selected_context) if experience.selected_context is not None else {}
    used_fragments = {
        str(reference.get("fragment_id", ""))
        for reference in experience.references
        if reference.get("fragment_id", "")
    }
    coverage = {
        "used_fragments": len(used_fragments),
        "total_fragments": len(experience.fragments),
        "references": len(experience.references),
        "label": f"Fragmentos utilizados: {len(used_fragments)} de {len(experience.fragments)}",
        "references_label": f"Referencias: {len(experience.references)}",
    }
    return {
        "document": dict(experience.document),
        "pages": [dict(page) for page in experience.pages],
        "fragments": [dict(fragment) for fragment in experience.fragments],
        "references": [dict(reference) for reference in experience.references],
        "anchors": [dict(reference) for reference in experience.references],
        "citations": [dict(reference) for reference in experience.references],
        "evidence": [dict(reference) for reference in experience.references],
        "questions": [dict(question) for question in experience.questions],
        "citizen_questions": [dict(question) for question in experience.questions],
        "key_points": [dict(point) for point in experience.key_points],
        "claims": [dict(claim) for claim in experience.claims],
        "citizen_summary": experience.citizen_summary,
        "connections": dict(experience.connections),
        "related_expediente": experience.related_expediente,
        "related_tracking": experience.related_tracking,
        "related_report": experience.related_report,
        "document_coverage": coverage,
        "metrics": [metric.__dict__ for metric in experience.metrics],
        "fragment_contexts": [_context_to_dict(context) for context in experience.fragment_contexts],
        "selected_context": selected_context,
        "default_page": int(selected_context.get("page", 1) or 1),
        "default_fragment_id": str(selected_context.get("fragment_id", "")),
        "notice": experience.notice,
    }


def _experience_from_digest(digest: KnowledgeDigest) -> DocumentExperience:
    references = tuple(_reference_row(row) for row in digest.evidence)
    references_by_id = {str(row["id"]): row for row in references}
    key_points = tuple(_point_row(row.__dict__, references_by_id) for row in digest.key_points)
    questions = tuple(
        _question_row(row.__dict__, references_by_id, index)
        for index, row in enumerate(digest.citizen_questions, start=1)
    )
    claims = tuple(_claim_row(row.__dict__, references_by_id) for row in digest.claims)
    fragments = tuple(_fragment_row(row.__dict__, key_points, questions, claims) for row in digest.fragments)
    contexts = tuple(
        _fragment_context(fragment, key_points, questions, claims, references, digest.connections)
        for fragment in fragments
    )
    selected = contexts[0] if contexts else None
    return DocumentExperience(
        document=official_document_to_dict(digest.document),
        pages=tuple(page.__dict__ for page in digest.pages),
        fragments=fragments,
        references=references,
        questions=questions,
        key_points=key_points,
        claims=claims,
        citizen_summary=digest.citizen_summary,
        connections=dict(digest.connections),
        related_expediente=str(digest.connections.get("expediente", "")),
        related_tracking=str(digest.connections.get("seguimiento", "")),
        related_report=str(digest.connections.get("reporte_ciudadano", "")),
        metrics=_reading_metrics(fragments, questions, claims, references),
        fragment_contexts=contexts,
        selected_context=selected,
        notice=digest.notice,
    )


def _reference_row(row: Any) -> dict[str, Any]:
    data = row.__dict__ if hasattr(row, "__dict__") else dict(row)
    page = int(data.get("page", 1) or 1)
    return {
        **data,
        "page": page,
        "reference_label": str(data.get("reference_label", "")) or f"Pagina {page} - {data.get('label', '')}",
    }


def _point_row(row: dict[str, Any], references_by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    evidence = references_by_id.get(str(row.get("evidence_id", "")), {})
    page = int(row.get("page", evidence.get("page", 1)) or 1)
    return {
        **row,
        "page": page,
        "fragment_id": str(row.get("fragment_id", evidence.get("fragment_id", ""))),
        "reference_label": str(row.get("reference_label", evidence.get("reference_label", ""))) or f"Pagina {page}",
        "quoted_text": str(evidence.get("quoted_text", evidence.get("excerpt", ""))),
    }


def _question_row(row: dict[str, Any], references_by_id: dict[str, dict[str, Any]], index: int) -> dict[str, Any]:
    enriched = _point_row(row, references_by_id)
    enriched["display_question"] = str(row.get("question", ""))
    return enriched


def _claim_row(row: dict[str, Any], references_by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    evidence_ids = [str(ref) for ref in row.get("evidence_ids", [])]
    first_evidence = references_by_id.get(evidence_ids[0], {}) if evidence_ids else {}
    page = int(first_evidence.get("page", 1) or 1)
    return {
        **row,
        "evidence_ids": evidence_ids,
        "evidence_text": " | ".join(evidence_ids),
        "citation_text": " | ".join(str(ref) for ref in row.get("citation_ids", [])),
        "page": page,
        "fragment_id": str(first_evidence.get("fragment_id", "")),
        "reference_label": str(first_evidence.get("reference_label", "")) or f"Pagina {page}",
        "quoted_text": str(first_evidence.get("quoted_text", first_evidence.get("excerpt", ""))),
    }


def _fragment_row(
    row: dict[str, Any],
    key_points: tuple[dict[str, Any], ...],
    questions: tuple[dict[str, Any], ...],
    claims: tuple[dict[str, Any], ...],
) -> dict[str, Any]:
    fragment_id = str(row.get("id", ""))
    supports = []
    supports.extend(f"Punto importante: {item.get('title', '')}" for item in key_points if item.get("fragment_id") == fragment_id)
    supports.extend(f"Pregunta frecuente: {item.get('display_question', item.get('question', ''))}" for item in questions if item.get("fragment_id") == fragment_id)
    supports.extend(f"Resumen ciudadano: {item.get('claim', '')}" for item in claims if item.get("fragment_id") == fragment_id)
    supports = [item for item in supports if item.strip()]
    return {
        **row,
        "supports": supports,
        "supports_text": " | ".join(supports) if supports else "Sin afirmaciones destacadas para este fragmento.",
    }


def _fragment_context(
    fragment: dict[str, Any],
    key_points: tuple[dict[str, Any], ...],
    questions: tuple[dict[str, Any], ...],
    claims: tuple[dict[str, Any], ...],
    references: tuple[dict[str, Any], ...],
    connections: dict[str, str],
) -> FragmentReadingContext:
    fragment_id = str(fragment.get("id", ""))
    page = int(fragment.get("page", 1) or 1)
    related_references = tuple(row for row in references if str(row.get("fragment_id", "")) == fragment_id)
    excerpt = str(related_references[0].get("excerpt", "")) if related_references else str(fragment.get("text", ""))
    return FragmentReadingContext(
        fragment_id=fragment_id,
        page=page,
        reference_label=f"Pagina {page} - {fragment.get('section_title', '')}",
        excerpt=excerpt,
        summary=tuple(row for row in key_points if str(row.get("fragment_id", "")) == fragment_id),
        questions=tuple(row for row in questions if str(row.get("fragment_id", "")) == fragment_id),
        claims=tuple(row for row in claims if str(row.get("fragment_id", "")) == fragment_id),
        evidence=related_references,
        connections=_reading_connections(connections),
    )


def _reading_connections(connections: dict[str, str]) -> tuple[ReadingConnection, ...]:
    expediente = str(connections.get("expediente", ""))
    return (
        ReadingConnection("Expediente", f"/investigation?id={expediente}", expediente),
        ReadingConnection("Seguimiento", "/tracking", str(connections.get("seguimiento", ""))),
        ReadingConnection("Reporte ciudadano", "/reports", str(connections.get("reporte_ciudadano", ""))),
        ReadingConnection("Biblioteca", "/library", "library"),
    )


def _reading_metrics(
    fragments: tuple[dict[str, Any], ...],
    questions: tuple[dict[str, Any], ...],
    claims: tuple[dict[str, Any], ...],
    references: tuple[dict[str, Any], ...],
) -> tuple[ReadingMetric, ...]:
    used_fragments = {str(reference.get("fragment_id", "")) for reference in references if reference.get("fragment_id", "")}
    return (
        ReadingMetric("fragments", "fragmentos utilizados", len(used_fragments or fragments)),
        ReadingMetric("questions", "preguntas respondidas", len(questions)),
        ReadingMetric("claims", "afirmaciones verificables", len(claims)),
        ReadingMetric("references", "referencias documentales", len(references)),
    )


def _context_to_dict(context: FragmentReadingContext) -> dict[str, Any]:
    return {
        "fragment_id": context.fragment_id,
        "page": context.page,
        "reference_label": context.reference_label,
        "excerpt": context.excerpt,
        "summary": [dict(row) for row in context.summary],
        "questions": [dict(row) for row in context.questions],
        "claims": [dict(row) for row in context.claims],
        "evidence": [dict(row) for row in context.evidence],
        "connections": [connection.__dict__ for connection in context.connections],
    }
