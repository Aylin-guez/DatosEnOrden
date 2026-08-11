from __future__ import annotations

from pathlib import Path

import reflex as rx

from datosenorden.application.document_reading.context import pdf_page_value
from datosenorden.application.document_reading.service import (
    DEMO_INVESTIGATION_TARGET,
    TOPIC_BUDGET_2013_TITLE,
    TOPIC_BUDGET_2013_TARGET,
    build_knowledge_payload,
    build_topic_payload,
    knowledge_error_payload,
    select_document_payload,
)
from datosenorden.web.app_services import get_investigation
from datosenorden.web.entity_engine import build_state_graph
from reflex_app.helpers.routing import _investigation_href, _router_query_value
from reflex_app.metadata.pages import _public_url
from datosenorden.application.public_deployment.sanitization import public_error


PUBLISHED_DOCUMENT_VIEW_PATH = Path("data") / "official_documents" / "published" / "senado-docto-9000-mensaje_mocion" / "document_view.json"
PUBLISHED_DOCUMENT_READING_PATH = Path("data") / "official_documents" / "published" / "senado-docto-9000-mensaje_mocion" / "reading.json"
PUBLISHED_DOCUMENT_PDF_PATH = Path("data") / "official_documents" / "published" / "senado-docto-9000-mensaje_mocion" / "document.pdf"
PUBLISHED_DOCUMENT_PDF_ASSET_PATH = Path("assets") / "official_documents" / "senado-docto-9000-mensaje_mocion" / "document.pdf"
PUBLISHED_DOCUMENT_PDF_PUBLIC_HREF = "/official_documents/senado-docto-9000-mensaje_mocion/document.pdf"
PROCESSING_DOCUMENT_FRAGMENTS_PATH = Path("data") / "official_documents" / "processing" / "senado-docto-9000-mensaje_mocion" / "fragments.json"


class DocumentReadingState(rx.State):
    topic_view_mode: str = "lectura"
    knowledge_documents: list[dict] = []
    knowledge_document: dict = {}
    knowledge_title: str = ""
    knowledge_summary: str = ""
    knowledge_key_points: list[dict] = []
    knowledge_questions: list[dict] = []
    knowledge_claims: list[dict] = []
    knowledge_evidence: list[dict] = []
    knowledge_pages: list[dict] = []
    knowledge_fragments: list[dict] = []
    knowledge_document_paragraphs: list[dict] = []
    knowledge_document_source_reference: str = ""
    knowledge_document_source_is_fallback: bool = False
    knowledge_document_has_pdf: bool = False
    knowledge_document_pdf_reference: str = ""
    knowledge_document_pdf_href: str = ""
    knowledge_document_pdf_page_href: str = ""
    knowledge_citations: list[dict] = []
    knowledge_connections: list[dict] = []
    knowledge_notice: str = ""
    knowledge_expediente_target: str = DEMO_INVESTIGATION_TARGET
    knowledge_selected_page: int = 18
    knowledge_selected_fragment_id: str = ""
    knowledge_selected_reference_label: str = "Pagina 18"
    knowledge_selected_excerpt: str = ""
    knowledge_selected_summary: list[dict] = []
    knowledge_selected_questions: list[dict] = []
    knowledge_selected_claims: list[dict] = []
    knowledge_selected_evidence: list[dict] = []
    knowledge_selected_connections: list[dict] = []
    knowledge_pdf_highlight_target: dict = {}
    knowledge_selected_page_is_approximate: bool = False
    knowledge_pdf_location_notice: str = ""
    knowledge_fragment_contexts: list[dict] = []
    knowledge_fragment_count: int = 0
    knowledge_total_fragment_count: int = 0
    knowledge_question_count: int = 0
    knowledge_claim_count: int = 0
    knowledge_reference_count: int = 0
    knowledge_coverage_text: str = ""
    knowledge_reference_text: str = ""
    knowledge_share_path: str = ""
    knowledge_share_url: str = ""
    knowledge_share_title: str = ""
    knowledge_share_x_url: str = ""
    knowledge_share_whatsapp_url: str = ""
    knowledge_share_linkedin_url: str = ""
    knowledge_share_copy_script: str = ""
    knowledge_error: str = ""
    topic_title: str = TOPIC_BUDGET_2013_TITLE
    topic_status: str = ""
    topic_read_time: str = ""
    topic_document_count: int = 0
    topic_updated_at: str = ""
    topic_organizations_text: str = ""
    topic_official_document: dict = {}
    topic_proposes_rows: list[dict] = []
    topic_changes_rows: list[dict] = []
    topic_no_changes_rows: list[dict] = []
    topic_timeline_rows: list[dict] = []
    topic_evidence_rows: list[dict] = []
    topic_state_graph_rows: list[dict] = []
    topic_reading_rows: list[dict] = []
    topic_expediente_title: str = ""
    topic_expediente_summary: str = ""
    topic_expediente_metrics: str = ""
    topic_tracking_summary: str = ""
    topic_vote_summary: str = ""
    topic_vote_count: int = 0
    topic_status_rows: list[dict] = []
    topic_hero_answer_rows: list[dict] = []
    topic_original_url: str = ""

    def set_topic_view_mode(self, mode: str) -> None:
        self.topic_view_mode = mode

    def load_knowledge(self) -> None:
        self.knowledge_error = ""
        try:
            payload = build_knowledge_payload(
                requested_fragment_id=_router_query_value(self.router, "fragment_id"),
                requested_page=pdf_page_value(_router_query_value(self.router, "page")),
                published_view_path=PUBLISHED_DOCUMENT_VIEW_PATH,
                published_reading_path=PUBLISHED_DOCUMENT_READING_PATH,
                processing_fragments_path=PROCESSING_DOCUMENT_FRAGMENTS_PATH,
                pdf_asset_exists=PUBLISHED_DOCUMENT_PDF_ASSET_PATH.exists(),
                pdf_path=PUBLISHED_DOCUMENT_PDF_PATH,
                pdf_public_href=PUBLISHED_DOCUMENT_PDF_PUBLIC_HREF,
                public_url=_public_url,
            )
        except Exception:  # noqa: BLE001
            _, message = public_error()
            payload = knowledge_error_payload(message)
        for key, value in payload.items():
            setattr(self, key, value)

    def load_topic(self) -> None:
        load_knowledge = getattr(self, "load_knowledge", None)
        if callable(load_knowledge):
            load_knowledge()
        else:
            DocumentReadingState.load_knowledge.fn(self)
        investigation = dict(get_investigation(TOPIC_BUDGET_2013_TARGET) or {})
        try:
            topic_graph = build_state_graph(TOPIC_BUDGET_2013_TARGET).to_dict()
        except Exception:
            topic_graph = {}
        topic_payload = build_topic_payload(
            knowledge={
                name: getattr(self, name)
                for name in DocumentReadingState.vars
                if name.startswith("knowledge_") and hasattr(self, name)
            },
            investigation=investigation,
            graph=topic_graph,
        )
        for key, value in topic_payload.items():
            setattr(self, key, value)

    def open_knowledge_investigation(self):
        return rx.redirect(_investigation_href(self.knowledge_expediente_target or DEMO_INVESTIGATION_TARGET))

    def select_document_anchor(self, page: int, fragment_id: str) -> None:
        requested_page = pdf_page_value(page)
        if requested_page is not None:
            self.knowledge_selected_page = requested_page
        payload = select_document_payload(
            contexts=self.knowledge_fragment_contexts,
            fragment_id=str(fragment_id or ""),
            requested_page=requested_page,
            has_pdf=bool(getattr(self, "knowledge_document_has_pdf", False)),
            pdf_public_href=PUBLISHED_DOCUMENT_PDF_PUBLIC_HREF,
            public_url=_public_url,
        )
        for key, value in payload.items():
            setattr(self, key, value)
