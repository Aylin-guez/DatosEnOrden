from __future__ import annotations

import reflex as rx

from datosenorden.maintenance.safe_access import _field
from datosenorden.web.app_services import (
    export_investigation_report,
    get_dataset_summary,
    get_investigation,
    resolve_investigation_target,
)
from reflex_app.app.state import AppState
from reflex_app.constants.demo import DEMO_INVESTIGATION_TARGET
from reflex_app.serialization.json_safe import _json_dict


class DemoState(rx.State):
    demo_sources_ready: bool = False
    demo_investigation_ready: bool = False
    demo_report_ready: bool = False

    def load_demo(self):
        self.demo_sources_ready = False
        self.demo_investigation_ready = False
        self.demo_report_ready = False
        try:
            summary = get_dataset_summary()
            totals = _field(summary, "totals", {})
            self.demo_sources_ready = int(_field(totals, "datasets", 0) or 0) > 0 and int(_field(totals, "source_records", 0) or 0) > 0
            investigation = _json_dict(get_investigation(DEMO_INVESTIGATION_TARGET))
            metrics = _field(investigation, "compact_metrics", {})
            self.demo_investigation_ready = bool(_field(investigation, "found", False)) and int(_field(metrics, "evidence_count", 0) or 0) > 0
            resolved = _json_dict(resolve_investigation_target(DEMO_INVESTIGATION_TARGET))
            entity_id = str(_field(resolved, "entity_id", ""))
            if entity_id:
                export_investigation_report(entity_id)
                self.demo_report_ready = True
        except Exception:  # noqa: BLE001
            return AppState.set_global_error()
        return AppState.clear_global_error()
