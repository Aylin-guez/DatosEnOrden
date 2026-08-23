"""Reusable, human-readable public projection for a reviewed expedient.

The persistence model deliberately keeps references as immutable identifiers.  This
module is the application boundary that pairs that immutable narrative with safe
public labels supplied by a resolver.  It never needs to know an expedient id.
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import EpistemicClass, ExpedientStatus, StoredExpedient


@dataclass(frozen=True)
class CitizenEvidence:
    evidence_id: str
    title: str
    source_name: str
    official_url: str | None = None
    excerpt: str | None = None
    document_date: str | None = None

    @property
    def complete(self) -> bool:
        return bool(self.title and self.source_name and self.official_url)


@dataclass(frozen=True)
class CitizenTimelineEvent:
    date: str
    event_type: str
    text: str
    evidence_id: str | None = None


@dataclass(frozen=True)
class CitizenDocument:
    title: str
    institution: str
    document_type: str
    stage: str
    official_url: str | None = None
    date: str | None = None


@dataclass(frozen=True)
class CitizenQuestionAnswer:
    question: str
    answer: str


@dataclass(frozen=True)
class CitizenKnowledgeCutoff:
    substantive_through: str
    latest_administrative_record: str | None
    explanation: str


@dataclass(frozen=True)
class CitizenProjectionContext:
    expedient_type: str | None = None
    evidence: tuple[CitizenEvidence, ...] = ()
    timeline: tuple[CitizenTimelineEvent, ...] = ()
    actors: tuple[str, ...] = ()
    documents: tuple[CitizenDocument, ...] = ()
    sources: tuple[str, ...] = ()
    answers: tuple[CitizenQuestionAnswer, ...] = ()
    knowledge_cutoff: CitizenKnowledgeCutoff | None = None


def citizen_expedient_projection(
    expedient: StoredExpedient, context: CitizenProjectionContext
) -> dict[str, object]:
    """Project approved content without exposing opaque persistence identifiers."""
    specification = expedient.specification
    if specification.status is not ExpedientStatus.PUBLISHED:
        raise ValueError("only published expedients have a citizen projection")

    evidence_by_id = {item.evidence_id: item for item in context.evidence}
    facts, unknowns, limitations, open_questions = [], [], [], []
    sections: dict[str, list[dict[str, object]]] = {}
    for statement in specification.statements:
        item = {
            "statement": statement.text,
            "section": statement.section,
            "epistemic_class": statement.epistemic_class.value,
            "evidence": _evidence_for(statement.evidence_ids, evidence_by_id),
        }
        sections.setdefault(statement.section, []).append(item)
        if statement.epistemic_class is EpistemicClass.FACT:
            facts.append(item)
        elif statement.epistemic_class is EpistemicClass.OPEN_QUESTION:
            open_questions.append(item)
        elif statement.section == "limitations":
            limitations.append(item)
        else:
            unknowns.append(item)

    timeline = [
        {
            "date": item.date,
            "event_type": item.event_type,
            "text": item.text,
            "evidence": _one_evidence(item.evidence_id, evidence_by_id),
        }
        for item in sorted(context.timeline, key=lambda entry: (entry.date, entry.text))
    ]
    result: dict[str, object] = {
        "title": specification.title,
        "question": specification.question,
        "summary": specification.summary,
        "status": specification.status.value,
        "version": specification.version,
        "what_happened": facts,
        "what_we_know": facts,
        "what_is_missing": unknowns + open_questions,
        "what_we_cannot_conclude": limitations,
        "facts": facts,
        "unknowns": unknowns,
        "limitations": limitations,
        "open_questions": open_questions,
        "sections": {name: values for name, values in sections.items() if values},
    }
    if context.expedient_type:
        result["type"] = context.expedient_type
    if timeline:
        result["chronology"] = timeline
    if context.actors:
        result["actors"] = list(context.actors)
    if context.documents:
        result["documents"] = [_document(item) for item in context.documents]
    if context.sources:
        result["sources"] = list(context.sources)
    if context.answers:
        result["questions"] = [
            {"question": item.question, "answer": item.answer}
            for item in context.answers
        ]
    if context.knowledge_cutoff is not None:
        result["knowledge_cutoff"] = {
            "substantive_through": context.knowledge_cutoff.substantive_through,
            "latest_administrative_record": context.knowledge_cutoff.latest_administrative_record,
            "explanation": context.knowledge_cutoff.explanation,
        }
    return result


def _evidence_for(
    ids: tuple[str, ...], evidence: dict[str, CitizenEvidence]
) -> list[dict[str, object]]:
    return [_evidence(evidence[item]) for item in ids if item in evidence]


def _one_evidence(
    identifier: str | None, evidence: dict[str, CitizenEvidence]
) -> dict[str, object] | None:
    return _evidence(evidence[identifier]) if identifier and identifier in evidence else None


def _evidence(item: CitizenEvidence) -> dict[str, object]:
    return {
        "title": item.title,
        "source": item.source_name,
        "official_url": item.official_url,
        "excerpt": item.excerpt,
        "document_date": item.document_date,
        "can_view_evidence": item.complete,
    }


def _document(item: CitizenDocument) -> dict[str, object]:
    return {
        "title": item.title,
        "institution": item.institution,
        "type": item.document_type,
        "stage": item.stage,
        "official_url": item.official_url,
        "date": item.date,
    }
