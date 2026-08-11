from __future__ import annotations

import reflex as rx

from datosenorden.web.app_services import (
    get_cross_dataset_connections,
    get_current_topics,
    get_dataset_summary,
    get_demo_status,
)
from reflex_app.app.state import AppState
from reflex_app.helpers.document import _format_chilean_date
from reflex_app.serialization.json_safe import _json_list


class PulseState(rx.State):
    dataset_rows: list[dict] = []
    connection_rows: list[dict] = []
    current_topic_rows: list[dict] = []
    demo_missing: list[str] = []
    total_datasets: int = 0
    active_datasets: int = 0
    total_claims: int = 0
    total_relationships: int = 0

    def load_home(self):
        try:
            summary = get_dataset_summary()
            totals = summary.get("totals", {})
            self.dataset_rows = summary.get("datasets", [])
            self.connection_rows = [
                {
                    **row,
                    "datasets_text": " | ".join(row.get("datasets", [])),
                }
                for row in get_cross_dataset_connections()
            ]
            self.current_topic_rows = [
                {
                    **row,
                    "updated_at": _format_chilean_date(row.get("updated_at", "")),
                }
                for row in _json_list(get_current_topics(limit=3))
            ]
            demo_status = get_demo_status()
            self.demo_missing = [item.get("label", "") for item in demo_status.get("missing", [])]
            self.total_datasets = int(totals.get("datasets", 0))
            self.active_datasets = int(totals.get("active_datasets", 0))
            self.total_claims = int(totals.get("claims", 0))
            self.total_relationships = int(totals.get("relationships", 0))
        except Exception:  # noqa: BLE001
            return AppState.set_global_error()
        return AppState.clear_global_error()
