from __future__ import annotations

from datosenorden.maintenance.knowledge_engine import DEMO_KNOWLEDGE_DOCUMENT_ID
from datosenorden.studio.publication_engine import build_publication_plan
from datosenorden.studio.publication_engine import document_view_payload
from datosenorden.studio.publication_engine import publication_result_to_dict
from datosenorden.studio.publication_engine import publish_document
from datosenorden.studio.publication_engine import publish_news


def test_build_publication_plan_enables_current_public_surfaces() -> None:
    plan = build_publication_plan(DEMO_KNOWLEDGE_DOCUMENT_ID)

    assert plan.document_id == DEMO_KNOWLEDGE_DOCUMENT_ID
    assert plan.publish_library is True
    assert plan.publish_report is True
    assert plan.publish_investigation is True
    assert plan.publish_tracking is True
    assert plan.publish_search is True
    assert plan.publish_document_view is True
    assert plan.publish_news is False


def test_publish_document_returns_active_publication_artifacts() -> None:
    result = publish_document(DEMO_KNOWLEDGE_DOCUMENT_ID)
    surfaces = {artifact.surface for artifact in result.artifacts}

    assert surfaces == {"library", "report", "investigation", "tracking", "search", "document_view"}
    payload = publication_result_to_dict(result)
    assert payload["plan"]["document_id"] == DEMO_KNOWLEDGE_DOCUMENT_ID
    assert len(payload["artifacts"]) == 6
    assert all(artifact["should_publish"] for artifact in payload["artifacts"])


def test_document_view_payload_reuses_reading_pipeline_contract() -> None:
    payload = document_view_payload(publish_document(DEMO_KNOWLEDGE_DOCUMENT_ID))

    assert payload["document"]["id"] == DEMO_KNOWLEDGE_DOCUMENT_ID
    assert payload["pages"]
    assert payload["fragments"]
    assert payload["references"]
    assert payload["fragment_contexts"]
    assert payload["selected_context"]["fragment_id"] == payload["default_fragment_id"]


def test_news_artifact_is_planned_but_disabled_by_default() -> None:
    result = publish_document(DEMO_KNOWLEDGE_DOCUMENT_ID)
    assert "news" not in {artifact.surface for artifact in result.artifacts}

    artifact = publish_news(result.plan, document_view_payload(result))
    assert artifact.surface == "news"
    assert artifact.should_publish is False
    assert artifact.payload["status"] == "planned"
