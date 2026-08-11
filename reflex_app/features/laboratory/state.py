from __future__ import annotations

import reflex as rx

from datosenorden.application.laboratory.service import get_expedient, load_expedient_catalog
from datosenorden.application.public_deployment.sanitization import public_error
from reflex_app.helpers.routing import _router_query_value


REQUIRED_SECTIONS = ("summary", "problem", "evidence", "claims", "hypotheses", "indicators", "sources", "relationships")


class LaboratoryState(rx.State):
    catalog_rows: list[dict] = []
    requested_expedient_id: str = ""
    expedient_id: str = ""
    expedient_title: str = ""
    expedient_summary: str = ""
    expedient_status: str = ""
    expedient_scope: str = ""
    expedient_territory: str = ""
    expedient_period: str = ""
    expedient_updated_at: str = ""
    problem_title: str = ""
    problem_description: str = ""
    problem_scope: str = ""
    problem_affected_population: str = ""
    problem_territory: str = ""
    problem_period: str = ""
    problem_status: str = ""
    sections: list[dict] = []
    hypotheses: list[dict] = []
    evidence_items: list[dict] = []
    claims: list[dict] = []
    indicators: list[dict] = []
    sources: list[dict] = []
    relationships: list[dict] = []
    open_questions_summary: str = ""
    participation_status: str = "LOCKED"
    active_section: str = "summary"
    visited_sections: list[str] = []
    reading_progress: int = 0
    reading_complete: bool = False
    load_status: str = "idle"
    error_message: str = ""
    public_error_code: str = ""

    def load_catalog(self) -> None:
        self.load_status = "loading"
        self.error_message = ""
        try:
            self.catalog_rows = load_expedient_catalog()
            self.load_status = "loaded" if self.catalog_rows else "empty"
        except Exception:  # noqa: BLE001
            self.catalog_rows = []
            self.load_status = "error"
            self.public_error_code, self.error_message = public_error()

    def load_expedient(self) -> None:
        self.load_status = "loading"
        self.error_message = ""
        requested = _router_query_value(self.router, "id") or "EXP-001"
        self.requested_expedient_id = requested
        try:
            payload = get_expedient(requested)
            if not payload:
                self._clear_expedient()
                self.load_status = "not_found"
                return
            self.expedient_id = str(payload["id"])
            self.expedient_title = str(payload["title"])
            self.expedient_summary = str(payload["summary"])
            self.expedient_status = str(payload["status"])
            self.expedient_scope = str(payload["scope"])
            self.expedient_territory = str(payload["territory"])
            self.expedient_period = str(payload["period"])
            self.expedient_updated_at = str(payload["updated_at"])
            problem = payload["problem"]
            self.problem_title = str(problem["title"])
            self.problem_description = str(problem["description"])
            self.problem_scope = str(problem["scope"])
            self.problem_affected_population = str(problem["affected_population"])
            self.problem_territory = str(problem["territory"])
            self.problem_period = str(problem["period"])
            self.problem_status = str(problem["status"])
            self.sections = payload["sections"]
            self.hypotheses = payload["hypotheses"]
            self.evidence_items = payload["evidence_items"]
            self.claims = payload["claims"]
            self.indicators = payload["indicators"]
            self.sources = payload["sources"]
            self.relationships = payload["relationships"]
            self.open_questions_summary = str(payload["open_questions_summary"])
            self.participation_status = str(payload["participation_status"])
            self.active_section = "summary"
            self.visited_sections = ["summary"]
            self._recalculate_progress()
            self.load_status = "loaded"
        except Exception:  # noqa: BLE001
            self._clear_expedient()
            self.load_status = "error"
            self.public_error_code, self.error_message = public_error()

    def set_active_section(self, section_id: str) -> None:
        section = str(section_id or "").strip()
        allowed = {row["id"] for row in self.sections}
        if section not in allowed:
            return
        self.active_section = section
        if section in REQUIRED_SECTIONS and section not in self.visited_sections:
            self.visited_sections = [*self.visited_sections, section]
        self._recalculate_progress()

    def _recalculate_progress(self) -> None:
        visited = set(self.visited_sections)
        completed = len(visited.intersection(REQUIRED_SECTIONS))
        self.reading_progress = int((completed / len(REQUIRED_SECTIONS)) * 100)
        self.reading_complete = completed == len(REQUIRED_SECTIONS)

    def _clear_expedient(self) -> None:
        self.expedient_id = ""
        self.expedient_title = ""
        self.expedient_summary = ""
        self.sections = []
        self.hypotheses = []
        self.evidence_items = []
        self.claims = []
        self.indicators = []
        self.sources = []
        self.relationships = []
        self.visited_sections = []
        self.reading_progress = 0
        self.reading_complete = False
