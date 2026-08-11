from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from datosenorden.application.document_reading import context as document_context
from reflex_app.features.public_record import state as public_record_state
from reflex_app.features.public_record.state import PublicRecordState
from datosenorden.application.document_reading import service as document_reading_service
from datosenorden.application.search import service as search_service
from reflex_app.features.document_reading import state as document_reading_state
from reflex_app.features.document_reading.state import DocumentReadingState
from reflex_app.features.search import state as search_state
from reflex_app.features.search.state import SearchState
from reflex_app.helpers.routing import _investigation_href
from reflex_app.models.document import PDFHighlightTarget
from reflex_app.serialization.json_safe import to_json_safe


def _document_context_state() -> SimpleNamespace:
    state = SimpleNamespace(
        knowledge_selected_page=1,
        knowledge_selected_fragment_id="fragment-a",
        knowledge_selected_reference_label="",
        knowledge_selected_excerpt="",
        knowledge_selected_summary=[],
        knowledge_selected_questions=[],
        knowledge_selected_claims=[],
        knowledge_selected_evidence=[],
        knowledge_selected_connections=[],
        knowledge_fragment_contexts=[
            {
                "fragment_id": "fragment-a",
                "order": 1,
                "reference_label": "Página 1",
                "excerpt": "Primer fragmento",
                "summary": [],
                "questions": [],
                "claims": [],
                "evidence": [],
                "connections": [],
            },
            {
                "fragment_id": "fragment-b",
                "order": 5,
                "reference_label": "Página aproximada",
                "excerpt": "Segundo fragmento",
                "summary": [{"title": "Punto"}],
                "questions": [{"display_question": "Pregunta"}],
                "claims": [{"claim": "Afirmación"}],
                "evidence": [{"fragment_id": "fragment-b"}],
                "connections": [{"label": "Expediente"}],
            },
        ],
        knowledge_document_has_pdf=True,
        knowledge_document_pdf_page_href="",
        knowledge_pdf_highlight_target={},
        knowledge_selected_page_is_approximate=False,
        knowledge_pdf_location_notice="",
    )
    return state


def test_document_fallback_order_is_published_then_processing_then_demo(monkeypatch, tmp_path) -> None:
    view_path = tmp_path / "published" / "document_view.json"
    reading_path = tmp_path / "published" / "reading.json"
    processing_path = tmp_path / "processing" / "fragments.json"
    responses = {
        "view": [],
        "reading": [],
        "processing": [],
    }
    calls: list[Path] = []

    def load_view(path: Path) -> list[dict]:
        calls.append(path)
        return responses["view"]

    def load_fragments(path: Path) -> list[dict]:
        calls.append(path)
        if path == reading_path:
            return responses["reading"]
        assert path == processing_path
        return responses["processing"]

    monkeypatch.setattr(document_context, "load_document_view_blocks", load_view)
    monkeypatch.setattr(document_context, "load_document_fragments_from_file", load_fragments)

    kwargs = {
        "published_view_path": view_path,
        "published_reading_path": reading_path,
        "processing_fragments_path": processing_path,
    }
    responses["view"] = [{"fragment_id": "published-view", "text": "Vista publicada"}]
    assert document_context.load_document_fragments_with_source(fallback_fragments=[], **kwargs) == (
        responses["view"],
        str(view_path),
        False,
    )

    responses["view"] = []
    responses["reading"] = [{"fragment_id": "published-reading", "text": "Lectura publicada"}]
    assert document_context.load_document_fragments_with_source(fallback_fragments=[], **kwargs) == (
        responses["reading"],
        str(reading_path),
        False,
    )

    responses["reading"] = []
    responses["processing"] = [{"fragment_id": "processing", "text": "Procesado"}]
    assert document_context.load_document_fragments_with_source(fallback_fragments=[], **kwargs) == (
        responses["processing"],
        str(processing_path),
        True,
    )

    responses["processing"] = []
    demo_fragments = [{"fragment_id": "demo", "text": "Demo"}]
    assert document_context.load_document_fragments_with_source(fallback_fragments=demo_fragments, **kwargs) == (
        demo_fragments,
        "knowledge_demo_payload",
        True,
    )
    assert document_context.load_document_fragments_with_source(fallback_fragments=[], **kwargs) == ([], "", False)
    assert calls[0] == view_path

def test_pdf_locator_and_highlight_target_keep_current_honest_contract() -> None:
    target = PDFHighlightTarget("fragment-7", 3, "Texto citado")

    assert document_context.document_pdf_href("/document.pdf", 0) == "/document.pdf#page=1"
    assert document_context.document_pdf_href("/document.pdf", 7) == "/document.pdf#page=7"
    assert target.to_dict() == {
        "fragment_id": "fragment-7",
        "page": 3,
        "text_snippet": "Texto citado",
        "coordinates": None,
    }
    assert document_context.pdf_highlight_target("fragment-7", 0, "Texto citado") == {
        "fragment_id": "fragment-7",
        "page": 1,
        "text_snippet": "Texto citado",
        "coordinates": None,
    }
    json.dumps(target.to_dict())

def test_select_document_anchor_keeps_fragment_page_locator_and_approximation() -> None:
    state = _document_context_state()

    DocumentReadingState.select_document_anchor.fn(state, 0, "fragment-b")

    assert state.knowledge_selected_fragment_id == "fragment-b"
    assert state.knowledge_selected_page == 5
    assert state.knowledge_document_pdf_page_href.endswith("document.pdf#page=5")
    assert state.knowledge_pdf_highlight_target == {
        "fragment_id": "fragment-b",
        "page": 5,
        "text_snippet": "Segundo fragmento",
        "coordinates": None,
    }
    assert state.knowledge_selected_page_is_approximate is True
    assert state.knowledge_pdf_location_notice == document_context.PDF_LOCATION_APPROXIMATE_NOTICE
    assert state.knowledge_selected_summary == [{"title": "Punto"}]
    assert state.knowledge_selected_connections == [{"label": "Expediente"}]


def test_empty_knowledge_document_is_safe_with_mocked_services_and_no_pdf(monkeypatch, tmp_path) -> None:
    documents = Mock(return_value=[])
    demo = Mock(
        return_value={
            "document": {},
            "pages": [],
            "citations": [],
            "key_points": [],
            "citizen_questions": [],
            "claims": [],
            "references": [],
            "fragments": [],
            "fragment_contexts": [],
            "selected_context": {},
            "connections": {},
            "metrics": [],
            "document_coverage": {},
        }
    )
    state = SimpleNamespace(
        error_message="",
        router=SimpleNamespace(url=SimpleNamespace(query_parameters={}, raw_path="/knowledge")),
    )

    monkeypatch.setattr(document_reading_service, "get_knowledge_documents", documents)
    monkeypatch.setattr(document_reading_service, "get_knowledge_demo", demo)
    monkeypatch.setattr(
        document_reading_service,
        "load_document_fragments_with_source",
        Mock(return_value=([], "", False)),
    )
    monkeypatch.setattr(document_reading_state, "PUBLISHED_DOCUMENT_PDF_ASSET_PATH", tmp_path / "missing.pdf")

    DocumentReadingState.load_knowledge.fn(state)

    assert state.knowledge_error == ""
    assert state.knowledge_document_has_pdf is False
    assert state.knowledge_document_pdf_href == ""
    assert state.knowledge_document_paragraphs == []
    assert state.knowledge_fragments == []
    assert state.knowledge_selected_page >= 1


def test_search_query_results_and_canonical_navigation_use_service_contract(monkeypatch) -> None:
    workspace = Mock(
        return_value={
            "matches": [
                {
                    "id": "result-1",
                    "entity_id": "entity-1",
                    "entity_name": "Entidad",
                    "canonical_entity_id": "canonical-1",
                    "canonical_entity_name": "Entidad canónica",
                    "datasets": ["ChileCompra"],
                    "relationship_count": 1,
                    "evidence_count": 1,
                }
            ]
        }
    )
    state = SimpleNamespace(query="", guided_search_title="stale", search_error="")

    SearchState.set_query.fn(state, "Entidad")
    monkeypatch.setattr(search_service, "search_workspace", workspace)
    SearchState.run_search.fn(state)

    workspace.assert_called_once_with("Entidad")
    assert state.results == state.workspace_matches
    assert state.workspace_matches[0]["canonical_entity_id"] == "canonical-1"
    json.dumps(to_json_safe(state.workspace_matches))

    redirect = Mock(return_value="redirect-event")
    monkeypatch.setattr(search_service, "search_workspace", workspace)
    monkeypatch.setattr(search_state.rx, "redirect", redirect)
    assert SearchState.select_result.fn(state, "result-1") == "redirect-event"
    assert "canonical-1" in redirect.call_args.args[0]


def test_open_canonical_investigation_uses_resolved_target_without_database_access(monkeypatch) -> None:
    resolve = Mock(
        return_value={
            "canonical_entity_id": "canonical-1",
            "canonical_entity_name": "Entidad canónica",
        }
    )
    redirect = Mock(return_value="redirect-event")
    state = SimpleNamespace(
        selected_entity_id="",
        selected_entity_name="",
        last_valid_investigation_target="",
    )

    monkeypatch.setattr(public_record_state, "resolve_canonical_expediente_target", resolve)
    monkeypatch.setattr(public_record_state.rx, "redirect", redirect)

    assert PublicRecordState.open_canonical_investigation.fn(state, "input-entity") == "redirect-event"

    resolve.assert_called_once_with("input-entity")
    redirect.assert_called_once_with(_investigation_href("canonical-1"))
    assert state.selected_entity_id == "canonical-1"
    assert state.selected_entity_name == "Entidad canónica"
    assert state.last_valid_investigation_target == "canonical-1"
