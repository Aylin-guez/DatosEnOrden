from __future__ import annotations

from datosenorden.maintenance.knowledge_engine import DEMO_KNOWLEDGE_DOCUMENT_ID
from datosenorden.studio.actualidad_engine import build_current_topic
from datosenorden.studio.actualidad_engine import current_topic_to_dict
from datosenorden.studio.actualidad_engine import get_current_topic
from datosenorden.studio.actualidad_engine import list_current_topics
from datosenorden.studio.actualidad_engine import publish_current_topic
from datosenorden.web import app_services


def test_build_current_topic_uses_publication_artifacts() -> None:
    topic = build_current_topic(DEMO_KNOWLEDGE_DOCUMENT_ID)

    assert topic.id.startswith("current-topic-")
    assert topic.title == "Fortalecimiento Hospitalario Arauco"
    assert topic.status == "Analizado"
    assert topic.primary_document["href"] == "/official-document"
    assert topic.related_expedientes[0]["href"].startswith("/investigation")
    assert topic.related_reports[0]["href"] == "/reports"
    assert topic.related_tracking[0]["href"] == "/tracking"
    assert {artifact["surface"] for artifact in topic.artifacts} >= {"document_view", "library", "report"}


def test_publish_current_topic_is_serializable() -> None:
    payload = publish_current_topic(DEMO_KNOWLEDGE_DOCUMENT_ID)

    assert payload["slug"] == "fortalecimiento-hospitalario-arauco"
    assert payload["summary"]
    assert payload["main_questions"]
    assert payload["key_points"]
    assert payload["references"]
    assert payload["tags"] == ["Documento oficial", "Lectura documentada", "Datos locales de prueba"]


def test_list_and_get_current_topics() -> None:
    topics = list_current_topics(limit=3)

    assert 1 <= len(topics) <= 3
    found = get_current_topic(topics[0]["slug"])
    missing = get_current_topic("no-existe")
    assert found["id"] == topics[0]["id"]
    assert missing == {}


def test_app_services_expose_current_topics() -> None:
    topics = app_services.get_current_topics(limit=3)

    assert topics[0]["title"] == "Fortalecimiento Hospitalario Arauco"
    assert app_services.get_current_topic(topics[0]["slug"])["id"] == topics[0]["id"]
