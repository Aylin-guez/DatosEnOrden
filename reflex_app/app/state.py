from __future__ import annotations

import reflex as rx

from datosenorden.application.public_deployment.sanitization import public_error

from reflex_app.helpers.routing import _search_href


class AppState(rx.State):
    """Cross-feature shell state and the documented Shell -> Search adapter."""

    error_message: str = ""
    header_search_open: bool = False
    header_search_query: str = ""
    sidebar_collapsed: bool = True

    def set_global_error(self, _message: str = "") -> None:
        _, self.error_message = public_error()

    def clear_global_error(self) -> None:
        self.error_message = ""

    def toggle_header_search(self) -> None:
        self.header_search_open = not self.header_search_open
        if not self.header_search_open:
            self.header_search_query = ""

    def toggle_sidebar(self) -> None:
        self.sidebar_collapsed = not self.sidebar_collapsed

    def set_header_search_query(self, value: str) -> None:
        self.header_search_query = value

    def submit_header_search(self):
        query = str(self.header_search_query or "").strip()
        if not query:
            self.header_search_open = False
            self.header_search_query = ""
            return None
        self.header_search_open = False
        self.header_search_query = ""
        return rx.redirect(_search_href(query))
