from __future__ import annotations

import reflex as rx

from datosenorden.application.public_deployment.sanitization import public_error

from datosenorden.maintenance.safe_access import _field
from datosenorden.web.app_services import get_citizen_dashboard
from reflex_app.helpers.routing import _search_href


class DashboardState(rx.State):
    dashboard_title: str = ""
    dashboard_summary: str = ""
    dashboard_budget_total: int = 0
    dashboard_budget_currency: str = "CLP"
    dashboard_contracts: int = 0
    dashboard_suppliers: int = 0
    dashboard_meetings: int = 0
    dashboard_authorities: int = 0
    dashboard_budget_rows: list[dict] = []
    dashboard_featured_entities: list[dict] = []
    dashboard_discovery_cases: list[dict] = []
    dashboard_error: str = ""
    dashboard_error_code: str = ""

    def load_dashboard(self) -> None:
        self.dashboard_error = ""
        try:
            data = get_citizen_dashboard()
            metrics = _field(data, "metrics", {})
            self.dashboard_title = str(_field(data, "title", ""))
            self.dashboard_summary = str(_field(data, "summary", ""))
            self.dashboard_budget_total = int(_field(metrics, "budget_total", 0) or 0)
            self.dashboard_budget_currency = str(_field(metrics, "budget_currency", "CLP"))
            self.dashboard_contracts = int(_field(metrics, "contracts", 0) or 0)
            self.dashboard_suppliers = int(_field(metrics, "suppliers", 0) or 0)
            self.dashboard_meetings = int(_field(metrics, "meetings", 0) or 0)
            self.dashboard_authorities = int(_field(metrics, "authorities", 0) or 0)
            self.dashboard_budget_rows = [
                {
                    **dict(row),
                    "years_text": str(row.get("fiscal_year", "")),
                }
                for row in _field(data, "budget_rows", [])
            ]
            self.dashboard_featured_entities = [
                {
                    **dict(row),
                    "datasets_text": " | ".join(str(item) for item in row.get("datasets", [])),
                }
                for row in _field(data, "featured_entities", [])
            ]
            self.dashboard_discovery_cases = [
                {
                    **dict(row),
                    "id_label": str(row.get("id", "")).replace("_", " "),
                    "concepts_text": " | ".join(str(item) for item in row.get("concepts", [])),
                    "sources_text": " | ".join(str(item) for item in row.get("suggested_sources", [])),
                    "search_href": _search_href(str(row.get("search_query", row.get("example_query", "")))),
                }
                for row in _field(data, "discovery_cases", [])
            ]
        except Exception as exc:  # noqa: BLE001
            self.dashboard_error_code, self.dashboard_error = public_error()
