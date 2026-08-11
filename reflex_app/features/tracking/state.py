from __future__ import annotations

import reflex as rx

from datosenorden.application.public_deployment.sanitization import public_error

from datosenorden.maintenance.safe_access import _field
from datosenorden.web.app_services import get_tracking_demo, get_tracking_items
from reflex_app.constants.demo import DEMO_INVESTIGATION_TARGET
from reflex_app.helpers.routing import _investigation_href
from reflex_app.serialization.json_safe import _json_dict, _json_list


def _display_label(value: object) -> str:
    text = str(value or "").replace("_", " ").strip().lower()
    return text.capitalize() if text else ""


class TrackingState(rx.State):
    tracking_items: list[dict] = []
    tracking_item: dict = {}
    tracking_title: str = ""
    tracking_summary: str = ""
    tracking_current_status: str = ""
    tracking_expediente_target: str = DEMO_INVESTIGATION_TARGET
    tracking_events: list[dict] = []
    tracking_documents: list[dict] = []
    tracking_evidence: list[dict] = []
    tracking_follow_targets: list[dict] = []
    tracking_related_sources: list[str] = []
    tracking_status_label: str = ""
    tracking_error: str = ""
    tracking_error_code: str = ""

    def load_tracking(self) -> None:
        self.tracking_error = ""
        try:
            items = _json_list(get_tracking_items())
            demo = _json_dict(get_tracking_demo())
            item = _json_dict(demo.get("item", {}))
            self.tracking_items = items
            self.tracking_item = item
            self.tracking_title = str(_field(item, "title", ""))
            self.tracking_summary = str(_field(item, "summary", ""))
            self.tracking_current_status = str(_field(item, "current_status", "unknown"))
            self.tracking_expediente_target = str(_field(item, "related_expediente_target", DEMO_INVESTIGATION_TARGET))
            self.tracking_events = _json_list(demo.get("events", []))
            self.tracking_documents = _json_list(demo.get("documents", []))
            self.tracking_evidence = _json_list(demo.get("evidence", []))
            self.tracking_follow_targets = _json_list(demo.get("follow_targets", []))
            self.tracking_related_sources = [str(source) for source in _field(item, "related_sources", [])]
            self.tracking_status_label = _display_label(str(_field(item, "current_status", "unknown")).upper())
        except Exception as exc:  # noqa: BLE001
            self.tracking_items = []
            self.tracking_item = {}
            self.tracking_title = ""
            self.tracking_summary = ""
            self.tracking_current_status = ""
            self.tracking_expediente_target = DEMO_INVESTIGATION_TARGET
            self.tracking_events = []
            self.tracking_documents = []
            self.tracking_evidence = []
            self.tracking_follow_targets = []
            self.tracking_related_sources = []
            self.tracking_status_label = ""
            self.tracking_error_code, self.tracking_error = public_error()

    def open_tracking_investigation(self):
        return rx.redirect(_investigation_href(self.tracking_expediente_target or DEMO_INVESTIGATION_TARGET))
