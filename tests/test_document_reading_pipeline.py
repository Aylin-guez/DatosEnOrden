from __future__ import annotations

from datosenorden.maintenance.knowledge_engine import DEMO_KNOWLEDGE_DOCUMENT_ID
from datosenorden.maintenance.knowledge_engine import DocumentSection
from datosenorden.maintenance.knowledge_engine import OfficialDocument
from datosenorden.studio.document_reading_pipeline import document_experience_to_dict
from datosenorden.studio.document_reading_pipeline import generate_document_experience
from datosenorden.studio.document_reading_pipeline import publish_document_experience


def test_generate_document_experience_returns_ui_ready_contract() -> None:
    experience = publish_document_experience(DEMO_KNOWLEDGE_DOCUMENT_ID)
    payload = document_experience_to_dict(experience)

    assert payload["document"]["id"] == DEMO_KNOWLEDGE_DOCUMENT_ID
    assert payload["pages"]
    assert payload["fragments"]
    assert payload["references"]
    assert payload["questions"]
    assert payload["key_points"]
    assert payload["claims"]
    assert payload["citizen_summary"]
    assert payload["connections"]["expediente"]
    assert payload["related_expediente"]
    assert payload["related_tracking"]
    assert payload["fragment_contexts"]
    assert payload["selected_context"]["fragment_id"] == payload["default_fragment_id"]


def test_document_experience_contains_reading_metrics_and_contexts() -> None:
    payload = document_experience_to_dict(publish_document_experience())
    metrics = {row["id"]: row["value"] for row in payload["metrics"]}

    assert metrics["fragments"] == len({row["fragment_id"] for row in payload["references"]})
    assert metrics["questions"] == len(payload["questions"])
    assert metrics["claims"] == len(payload["claims"])
    assert metrics["references"] == len(payload["references"])

    context = payload["fragment_contexts"][0]
    assert context["reference_label"].startswith("Pagina ")
    assert "summary" in context
    assert "questions" in context
    assert "claims" in context
    assert "evidence" in context
    assert context["connections"][0]["label"] == "Expediente"


def test_generate_document_experience_accepts_different_documents_without_ui_changes() -> None:
    document = OfficialDocument(
        id="document-b-demo",
        title="Documento B de prueba",
        source="Fuente local B",
        document_type="structured_demo",
        published_at="2026-06-01",
        official_url="local://document-b",
        summary="Documento B estructurado.",
        related_expediente_target="EXPEDIENTE B",
        related_tracking_item_id="tracking-b",
        related_citizen_report_id="report-b",
        public_source="Catalogo local",
        sections=(
            DocumentSection(id="intro", title="Introduccion", text="Este documento declara una medida local.", order=1, page=1, fragment_id="b-intro"),
            DocumentSection(id="detail", title="Detalle", text="El detalle permite revisar informacion especifica.", order=2, page=2, fragment_id="b-detail"),
        ),
    )

    payload = document_experience_to_dict(generate_document_experience(document))

    assert payload["document"]["id"] == "document-b-demo"
    assert [page["page"] for page in payload["pages"]] == [1, 2]
    assert payload["fragments"][0]["id"] == "b-intro"
    assert payload["related_tracking"] == "tracking-b"
    assert payload["selected_context"]["fragment_id"] == "b-intro"
