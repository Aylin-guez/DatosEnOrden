from __future__ import annotations

import reflex as rx

from datosenorden.application.public_deployment.sanitization import public_error
from datosenorden.application.public_collections import public_collection_counts
from datosenorden.application.public_explore import public_guided_categories, public_guided_questions
from datosenorden.application.real_expedient.public_facade import list_public_expedient_catalog
from datosenorden.db.session import SessionLocal

from datosenorden.application.search.service import (
    build_guided_journey,
    load_guided_options,
    run_workspace_search,
)
from reflex_app.helpers.routing import _investigation_href, _router_query_value, _search_href


def _guided_href(question_id: str, manual_query: str = "") -> str:
    from urllib.parse import quote_plus

    identifier = str(question_id or "").strip()
    if not identifier:
        return "/search"
    query = str(manual_query or "").strip()
    suffix = f"&q={quote_plus(query)}" if query else ""
    return f"/search?guided={quote_plus(identifier)}{suffix}"


def _reset_guided_journey(state: object) -> None:
    """Reset typed guided-response fields on Reflex state or lightweight test state."""
    state.guided_journey_title = ""
    state.guided_journey_description = ""
    state.guided_journey_summary = ""
    state.guided_journey_scope_copy = ""
    state.guided_journey_count_copy = ""
    state.guided_journey_status = ""
    state.guided_journey_entity_rows = []
    state.guided_journey_expedient_rows = []


class SearchState(rx.State):
    query: str = ""
    results: list[dict] = []
    workspace_matches: list[dict] = []
    guided_search_title: str = ""
    guided_question_rows: list[dict] = []
    guided_category_rows: list[dict] = []
    selected_guided_category_id: str = ""
    selected_guided_category_title: str = ""
    selected_guided_category_description: str = ""
    selected_guided_category_examples: list[str] = []
    selected_guided_category_sources: list[str] = []
    selected_guided_category_query: str = ""
    selected_guided_category_cta: str = ""
    selected_guided_category_href: str = "/search"
    selected_guided_category_path: str = ""
    guided_option_rows: list[dict] = []
    guided_question_active: bool = False
    manual_result_active: bool = False
    guided_journey_title: str = ""
    guided_journey_description: str = ""
    guided_journey_summary: str = ""
    guided_journey_scope_copy: str = ""
    guided_journey_count_copy: str = ""
    guided_journey_status: str = ""
    guided_journey_entity_rows: list[dict] = []
    guided_journey_expedient_rows: list[dict] = []
    investigation_topic_rows: list[dict] = []
    public_expedient_rows: list[dict] = []
    search_error: str = ""
    search_error_code: str = ""

    def submit_main_search(self):
        query = str(self.query or "").strip()
        self.query = query
        return rx.redirect(_search_href(query))

    def load_discover(self) -> None:
        self.search_error = ""
        self.guided_question_active = False
        self.manual_result_active = False
        _reset_guided_journey(self)
        try:
            self._load_guided_rows()
            self._load_collection_counts()
            self._load_public_expedients()
            if self.guided_category_rows and not self.selected_guided_category_id:
                self._select_category_row(self.guided_category_rows[0])
        except Exception as exc:  # noqa: BLE001
            self.search_error_code, self.search_error = public_error()

    def load_search(self) -> None:
        self.search_error = ""
        self.results = []
        self.workspace_matches = []
        self.guided_search_title = ""
        self.guided_question_active = False
        self.manual_result_active = False
        _reset_guided_journey(self)
        self._clear_selected_category()
        try:
            self._load_guided_rows()
            self._load_collection_counts()
            self._load_public_expedients()
            guided_id = _router_query_value(self.router, "guided")
            query_value = _router_query_value(self.router, "q")
            if guided_id:
                row = next((item for item in self.guided_question_rows if item.get("id") == guided_id), {})
                if row:
                    self._activate_guided_question(row)
                if query_value:
                    self.query = query_value
            elif query_value:
                self.query = query_value
                self.manual_result_active = True
                self.run_search()
            else:
                self.query = ""
        except Exception as exc:  # noqa: BLE001
            self.search_error_code, self.search_error = public_error()

    def set_query(self, value: str) -> None:
        self.query = value
        self.guided_search_title = ""
        self.guided_question_active = False
        self.manual_result_active = False
        _reset_guided_journey(self)

    def run_search(self) -> None:
        self.search_error = ""
        try:
            self.workspace_matches = run_workspace_search(self.query)
            self.results = self.workspace_matches
        except Exception as exc:  # noqa: BLE001
            self.results = []
            self.workspace_matches = []
            self.search_error_code, self.search_error = public_error()

    def explore_discovery_case(self, case_id: str, example_query: str, title: str):
        query = str(example_query or case_id or "").strip()
        self.query = query
        self.guided_search_title = f"Alternativas para explorar: {title}" if title else "Alternativas para explorar"
        return rx.redirect(_search_href(query))

    def explore_guided_question(self, question_id: str, title: str, description: str, query: str):
        _ = (title, description, query)
        return rx.redirect(_guided_href(question_id, self.query))

    def explore_another_question(self) -> None:
        """Restore guided entry without discarding a manual query or its results."""
        return rx.redirect(_search_href(self.query))

    def return_to_explore(self):
        return rx.redirect("/search")

    def select_guided_category(self, category_id: str) -> None:
        self.selected_guided_category_id = category_id
        match = next((row for row in self.guided_category_rows if row.get("id") == category_id), {})
        self._select_category_row(match)
        if self.selected_guided_category_query:
            self.query = self.selected_guided_category_query
            self.guided_search_title = (
                f"Explorando {self.selected_guided_category_title}"
                if self.selected_guided_category_title
                else ""
            )

    def select_result(self, entity_id: str):
        match = next((row for row in self.results if row.get("id") == entity_id), {})
        target = str(match.get("canonical_entity_id", entity_id))
        name = str(match.get("canonical_entity_name", match.get("name", "")))
        return rx.redirect(_investigation_href(target or name))

    def _load_guided_rows(self) -> None:
        with SessionLocal() as session:
            self.guided_question_rows = public_guided_questions(session)
            self.guided_category_rows = public_guided_categories(session)

    def _load_collection_counts(self) -> None:
        from reflex_app.models.investigation import INVESTIGATION_TOPICS

        with SessionLocal() as session:
            counts = public_collection_counts(session)
        rows: list[dict] = []
        for topic in INVESTIGATION_TOPICS:
            row = dict(topic)
            key = str(row.get("collection_key", ""))
            if key:
                row["count"] = counts.get(key, 0)
                row["count_text"] = f"{row['count']} incorporados" if row["count"] else "Sin información incorporada todavía"
            else:
                row["count"] = 0
                row["count_text"] = "Sin información incorporada todavía"
            rows.append(row)
        self.investigation_topic_rows = rows

    def _load_public_expedients(self) -> None:
        self.public_expedient_rows = [
            row for row in list_public_expedient_catalog()
            if row.get("provenance_class") == "REAL"
        ]

    def _clear_selected_category(self) -> None:
        self.selected_guided_category_id = ""
        self.selected_guided_category_title = ""
        self.selected_guided_category_description = ""
        self.selected_guided_category_examples = []
        self.selected_guided_category_sources = []
        self.selected_guided_category_query = ""
        self.selected_guided_category_cta = ""
        self.selected_guided_category_href = "/search"
        self.selected_guided_category_path = ""
        self.guided_option_rows = []

    def _activate_guided_question(self, row: dict) -> None:
        question_id = str(row.get("id", ""))
        title = str(row.get("title", ""))
        description = str(row.get("description", ""))
        query = str(row.get("search_query", row.get("example_query", "")))
        self.guided_question_active = True
        self.selected_guided_category_id = question_id
        self.selected_guided_category_title = title
        self.selected_guided_category_description = description
        self.selected_guided_category_examples = [query] if query else []
        self.selected_guided_category_sources = []
        self.selected_guided_category_query = query
        self.selected_guided_category_cta = "Ver resultados"
        self.selected_guided_category_href = _guided_href(question_id)
        self.selected_guided_category_path = "Este recorrido muestra información disponible y lecturas ciudadanas relacionadas."
        self.guided_option_rows = []
        journey = build_guided_journey(question_id, title, description, query)
        self.guided_journey_title = str(journey["title"])
        self.guided_journey_description = str(journey["description"])
        self.guided_journey_summary = str(journey["summary"])
        self.guided_journey_scope_copy = str(journey["scope_copy"])
        self.guided_journey_count_copy = str(journey["count_copy"])
        self.guided_journey_status = str(journey["status"])
        self.guided_journey_entity_rows = list(journey["entity_rows"])
        self.guided_journey_expedient_rows = list(journey["expedient_rows"])

    def _select_category_row(self, row: dict) -> None:
        category_id = str(row.get("id", ""))
        self.selected_guided_category_id = category_id
        self.selected_guided_category_title = str(row.get("title", ""))
        self.selected_guided_category_description = str(row.get("description", ""))
        self.selected_guided_category_examples = [str(item) for item in row.get("examples", [])]
        self.selected_guided_category_sources = [str(item) for item in row.get("suggested_sources", [])]
        self.selected_guided_category_query = str(row.get("search_query", ""))
        self.selected_guided_category_cta = str(row.get("cta", ""))
        self.selected_guided_category_href = _search_href(self.selected_guided_category_query)
        self.selected_guided_category_path = str(row.get("path_text", ""))
        self.guided_option_rows = load_guided_options(category_id) if category_id else []
