from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from datosenorden.maintenance.knowledge_engine import DEFAULT_SAMPLE_PATH
from datosenorden.maintenance.knowledge_engine import DEMO_KNOWLEDGE_DOCUMENT_ID
from datosenorden.maintenance.knowledge_engine import OfficialDocument
from datosenorden.studio.document_reading_pipeline import document_experience_to_dict
from datosenorden.studio.document_reading_pipeline import publish_document_experience


@dataclass(frozen=True)
class PublicationPlan:
    document_id: str
    publish_library: bool = True
    publish_report: bool = True
    publish_investigation: bool = True
    publish_tracking: bool = True
    publish_search: bool = True
    publish_document_view: bool = True
    publish_news: bool = False
    publish_dashboard: bool = False
    publish_pdf_export: bool = False
    publish_public_api: bool = False
    publish_rss: bool = False
    publish_newsletter: bool = False
    publish_public_dataset: bool = False
    publish_embeddable_widgets: bool = False


@dataclass(frozen=True)
class PublicationArtifact:
    surface: str
    should_publish: bool
    document_id: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class PublicationResult:
    plan: PublicationPlan
    artifacts: tuple[PublicationArtifact, ...]


def build_publication_plan(document: OfficialDocument | str = DEMO_KNOWLEDGE_DOCUMENT_ID) -> PublicationPlan:
    document_id = document.id if isinstance(document, OfficialDocument) else str(document)
    return PublicationPlan(document_id=document_id)


def publish_document(
    document: OfficialDocument | str = DEMO_KNOWLEDGE_DOCUMENT_ID,
    path: Path | str = DEFAULT_SAMPLE_PATH,
) -> PublicationResult:
    plan = build_publication_plan(document)
    experience = document_experience_to_dict(publish_document_experience(plan.document_id, path=path))
    artifacts = tuple(
        artifact
        for artifact in (
            publish_library(plan, experience),
            publish_report(plan, experience),
            publish_investigation(plan, experience),
            publish_tracking(plan, experience),
            publish_search(plan, experience),
            publish_document_view(plan, experience),
            publish_news(plan, experience),
        )
        if artifact.should_publish
    )
    return PublicationResult(plan=plan, artifacts=artifacts)


def publication_result_to_dict(result: PublicationResult) -> dict[str, Any]:
    return {
        "plan": result.plan.__dict__,
        "artifacts": [artifact_to_dict(artifact) for artifact in result.artifacts],
    }


def artifact_to_dict(artifact: PublicationArtifact) -> dict[str, Any]:
    return {
        "surface": artifact.surface,
        "should_publish": artifact.should_publish,
        "document_id": artifact.document_id,
        "payload": artifact.payload,
    }


def document_view_payload(result: PublicationResult) -> dict[str, Any]:
    artifact = next((row for row in result.artifacts if row.surface == "document_view"), None)
    return dict(artifact.payload) if artifact is not None else {}


def publish_library(plan: PublicationPlan, experience: dict[str, Any]) -> PublicationArtifact:
    return PublicationArtifact(
        surface="library",
        should_publish=plan.publish_library,
        document_id=plan.document_id,
        payload={
            "document": experience.get("document", {}),
            "citizen_summary": experience.get("citizen_summary", ""),
            "references": experience.get("references", []),
            "href": "/library",
        },
    )


def publish_report(plan: PublicationPlan, experience: dict[str, Any]) -> PublicationArtifact:
    return PublicationArtifact(
        surface="report",
        should_publish=plan.publish_report,
        document_id=plan.document_id,
        payload={
            "related_report": experience.get("related_report", ""),
            "summary": experience.get("citizen_summary", ""),
            "href": "/reports",
        },
    )


def publish_investigation(plan: PublicationPlan, experience: dict[str, Any]) -> PublicationArtifact:
    related = str(experience.get("related_expediente", ""))
    return PublicationArtifact(
        surface="investigation",
        should_publish=plan.publish_investigation,
        document_id=plan.document_id,
        payload={
            "related_expediente": related,
            "href": f"/investigation?id={related}" if related else "/investigation",
        },
    )


def publish_tracking(plan: PublicationPlan, experience: dict[str, Any]) -> PublicationArtifact:
    return PublicationArtifact(
        surface="tracking",
        should_publish=plan.publish_tracking,
        document_id=plan.document_id,
        payload={
            "related_tracking": experience.get("related_tracking", ""),
            "href": "/tracking",
        },
    )


def publish_search(plan: PublicationPlan, experience: dict[str, Any]) -> PublicationArtifact:
    document = experience.get("document", {})
    return PublicationArtifact(
        surface="search",
        should_publish=plan.publish_search,
        document_id=plan.document_id,
        payload={
            "title": document.get("title", ""),
            "document_id": plan.document_id,
            "keywords": _search_keywords(experience),
            "href": "/search",
        },
    )


def publish_document_view(plan: PublicationPlan, experience: dict[str, Any]) -> PublicationArtifact:
    return PublicationArtifact(
        surface="document_view",
        should_publish=plan.publish_document_view,
        document_id=plan.document_id,
        payload=experience,
    )


def publish_news(plan: PublicationPlan, experience: dict[str, Any]) -> PublicationArtifact:
    return PublicationArtifact(
        surface="news",
        should_publish=plan.publish_news,
        document_id=plan.document_id,
        payload={
            "status": "planned",
            "source_document_id": plan.document_id,
            "summary": experience.get("citizen_summary", ""),
        },
    )


def _search_keywords(experience: dict[str, Any]) -> list[str]:
    document = experience.get("document", {})
    values = [
        document.get("title", ""),
        document.get("source", ""),
        experience.get("related_expediente", ""),
        experience.get("related_tracking", ""),
    ]
    values.extend(str(point.get("title", "")) for point in experience.get("key_points", []))
    return [value for value in (str(item).strip() for item in values) if value]
