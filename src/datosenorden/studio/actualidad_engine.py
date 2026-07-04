from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from datosenorden.maintenance.knowledge_engine import DEFAULT_SAMPLE_PATH
from datosenorden.maintenance.knowledge_engine import DEMO_KNOWLEDGE_DOCUMENT_ID
from datosenorden.studio.publication_engine import PublicationResult
from datosenorden.studio.publication_engine import artifact_to_dict
from datosenorden.studio.publication_engine import document_view_payload
from datosenorden.studio.publication_engine import publish_document


@dataclass(frozen=True)
class CurrentTopic:
    id: str
    slug: str
    title: str
    subtitle: str
    summary: str
    organization: str
    date: str
    status: str
    primary_document: dict[str, Any]
    related_expedientes: tuple[dict[str, str], ...]
    related_reports: tuple[dict[str, str], ...]
    related_tracking: tuple[dict[str, str], ...]
    main_questions: tuple[dict[str, Any], ...]
    key_points: tuple[dict[str, Any], ...]
    references: tuple[dict[str, Any], ...]
    tags: tuple[str, ...]
    published_at: str
    updated_at: str
    href: str
    artifacts: tuple[dict[str, Any], ...]


def build_current_topic(
    document_id: str = DEMO_KNOWLEDGE_DOCUMENT_ID,
    path: Path | str = DEFAULT_SAMPLE_PATH,
) -> CurrentTopic:
    publication = publish_document(document_id, path=path)
    return _topic_from_publication(publication)


def publish_current_topic(
    document_id: str = DEMO_KNOWLEDGE_DOCUMENT_ID,
    path: Path | str = DEFAULT_SAMPLE_PATH,
) -> dict[str, Any]:
    return current_topic_to_dict(build_current_topic(document_id, path=path))


def list_current_topics(limit: int = 3, path: Path | str = DEFAULT_SAMPLE_PATH) -> list[dict[str, Any]]:
    topics = [publish_current_topic(DEMO_KNOWLEDGE_DOCUMENT_ID, path=path)]
    return topics[: max(0, limit)]


def get_current_topic(slug: str, path: Path | str = DEFAULT_SAMPLE_PATH) -> dict[str, Any]:
    requested = str(slug or "").strip()
    return next((topic for topic in list_current_topics(path=path) if topic["slug"] == requested), {})


def current_topic_to_dict(topic: CurrentTopic) -> dict[str, Any]:
    return {
        "id": topic.id,
        "slug": topic.slug,
        "title": topic.title,
        "subtitle": topic.subtitle,
        "summary": topic.summary,
        "organization": topic.organization,
        "date": topic.date,
        "status": topic.status,
        "primary_document": dict(topic.primary_document),
        "related_expedientes": [dict(item) for item in topic.related_expedientes],
        "related_reports": [dict(item) for item in topic.related_reports],
        "related_tracking": [dict(item) for item in topic.related_tracking],
        "main_questions": [dict(item) for item in topic.main_questions],
        "key_points": [dict(item) for item in topic.key_points],
        "references": [dict(item) for item in topic.references],
        "tags": list(topic.tags),
        "published_at": topic.published_at,
        "updated_at": topic.updated_at,
        "href": topic.href,
        "artifacts": [dict(item) for item in topic.artifacts],
    }


def _topic_from_publication(publication: PublicationResult) -> CurrentTopic:
    experience = document_view_payload(publication)
    document = experience.get("document", {})
    document_id = str(document.get("id", publication.plan.document_id))
    title = _topic_title(str(document.get("title", "Documento oficial")))
    organization = str(document.get("source", "Documento oficial"))
    updated_at = str(document.get("published_at", "")) or date.today().isoformat()
    related_expediente = str(experience.get("related_expediente", ""))
    related_report = str(experience.get("related_report", ""))
    related_tracking = str(experience.get("related_tracking", ""))
    return CurrentTopic(
        id=f"current-topic-{document_id}",
        slug=_slug(title),
        title=title,
        subtitle="Tema oficial actualmente analizado por DatosEnOrden.",
        summary=str(experience.get("citizen_summary", "")),
        organization=organization,
        date=updated_at,
        status="Analizado",
        primary_document={
            "id": document_id,
            "title": str(document.get("title", "")),
            "href": "/official-document",
            "type": str(document.get("document_type", "Documento oficial")),
        },
        related_expedientes=_link_tuple("Expediente", related_expediente, f"/investigation?id={related_expediente}" if related_expediente else "/investigation"),
        related_reports=_link_tuple("Reporte ciudadano", related_report, "/reports"),
        related_tracking=_link_tuple("Seguimiento", related_tracking, "/tracking"),
        main_questions=tuple(dict(row) for row in experience.get("questions", [])[:3]),
        key_points=tuple(dict(row) for row in experience.get("key_points", [])[:3]),
        references=tuple(dict(row) for row in experience.get("references", [])[:4]),
        tags=("Documento oficial", "Lectura documentada", "Datos locales de prueba"),
        published_at=updated_at,
        updated_at=updated_at,
        href="/official-document",
        artifacts=tuple(artifact_to_dict(artifact) for artifact in publication.artifacts),
    )


def _link_tuple(label: str, target_id: str, href: str) -> tuple[dict[str, str], ...]:
    return ({"label": label, "target_id": str(target_id), "href": href},)


def _topic_title(document_title: str) -> str:
    cleaned = document_title.strip()
    if "fortalecimiento hospitalario" in cleaned.lower():
        return "Fortalecimiento Hospitalario Arauco"
    return cleaned or "Lectura documentada"


def _slug(value: str) -> str:
    allowed = []
    for char in value.lower():
        if char.isalnum():
            allowed.append(char)
        elif char.isspace() or char in "-_/":
            allowed.append("-")
    slug = "".join(allowed).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug or "lectura-documentada"
