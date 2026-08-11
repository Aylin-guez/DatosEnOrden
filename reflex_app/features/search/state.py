from __future__ import annotations

import reflex as rx

from datosenorden.application.public_deployment.sanitization import public_error

from datosenorden.application.search.service import (
    build_guided_categories,
    build_guided_questions,
    load_guided_options,
    run_workspace_search,
)
from reflex_app.helpers.routing import _investigation_href, _router_query_value, _search_href


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
    search_error: str = ""
    search_error_code: str = ""

    def submit_main_search(self):
        query = str(self.query or "").strip()
        self.query = query
        return rx.redirect(_search_href(query))

    def load_discover(self) -> None:
        self.search_error = ""
        try:
            self._load_guided_rows()
            if self.guided_category_rows and not self.selected_guided_category_id:
                self._select_category_row(self.guided_category_rows[0])
        except Exception as exc:  # noqa: BLE001
            self.search_error_code, self.search_error = public_error()

    def load_search(self) -> None:
        self.search_error = ""
        self.results = []
        self.workspace_matches = []
        self.guided_search_title = ""
        self._clear_selected_category()
        try:
            self._load_guided_rows()
            query_value = _router_query_value(self.router, "q")
            if query_value:
                self.query = query_value
                self.guided_search_title = f"Alternativas para explorar: {query_value}"
                self.run_search()
            else:
                self.query = ""
        except Exception as exc:  # noqa: BLE001
            self.search_error_code, self.search_error = public_error()

    def set_query(self, value: str) -> None:
        self.query = value
        self.guided_search_title = ""

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

    def explore_guided_question(self, question_id: str, title: str, description: str, query: str) -> None:
        self.selected_guided_category_id = question_id
        self.selected_guided_category_title = title
        self.selected_guided_category_description = description
        self.selected_guided_category_examples = [query] if query else []
        self.selected_guided_category_sources = []
        self.selected_guided_category_query = query
        self.selected_guided_category_cta = "Buscar"
        self.selected_guided_category_href = _search_href(query)
        self.selected_guided_category_path = "Este recorrido mostrara opciones locales antes de abrir el expediente."
        self.guided_option_rows = load_guided_options(question_id)
        if query:
            self.query = query

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
        self.guided_question_rows = build_guided_questions()
        self.guided_category_rows = build_guided_categories()

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
