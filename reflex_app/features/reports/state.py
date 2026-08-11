from __future__ import annotations

import reflex as rx

from datosenorden.application.public_deployment.sanitization import public_error

from datosenorden.maintenance.safe_access import _field
from datosenorden.web.app_services import export_citizen_report_demo, get_citizen_report_demo, get_citizen_reports
from reflex_app.constants.demo import DEMO_INVESTIGATION_TARGET
from reflex_app.helpers.routing import _investigation_href
from reflex_app.serialization.json_safe import _json_dict, _json_list


class ReportsState(rx.State):
    citizen_reports: list[dict] = []
    citizen_report: dict = {}
    citizen_report_title: str = ""
    citizen_report_summary: str = ""
    citizen_report_subject: str = DEMO_INVESTIGATION_TARGET
    citizen_report_status: str = ""
    citizen_report_sources: list[str] = []
    citizen_report_sections: list[dict] = []
    citizen_report_evidence_refs: list[str] = []
    citizen_report_available: bool = False
    citizen_report_error: str = ""
    citizen_report_error_code: str = ""

    def load_reports(self) -> None:
        self.citizen_report_error = ""
        try:
            reports = _json_list(get_citizen_reports())
            demo = _json_dict(get_citizen_report_demo())
            self.citizen_reports = reports
            self.citizen_report = demo
            self.citizen_report_title = str(_field(demo, "title", ""))
            self.citizen_report_summary = str(_field(demo, "summary", ""))
            self.citizen_report_subject = str(_field(demo, "subject", DEMO_INVESTIGATION_TARGET))
            self.citizen_report_status = str(_field(demo, "current_status", "demo_read_only"))
            self.citizen_report_sources = [str(source) for source in _field(demo, "sources", [])]
            self.citizen_report_sections = [
                {
                    **dict(row),
                    "evidence_text": " | ".join(str(ref) for ref in row.get("evidence_refs", [])),
                }
                for row in _json_list(_field(demo, "sections", []))
            ]
            self.citizen_report_evidence_refs = [str(ref) for ref in _field(demo, "evidence_refs", [])]
            export_citizen_report_demo()
            self.citizen_report_available = False
        except Exception as exc:  # noqa: BLE001
            self.citizen_reports = []
            self.citizen_report = {}
            self.citizen_report_title = ""
            self.citizen_report_summary = ""
            self.citizen_report_subject = DEMO_INVESTIGATION_TARGET
            self.citizen_report_status = ""
            self.citizen_report_sources = []
            self.citizen_report_sections = []
            self.citizen_report_evidence_refs = []
            self.citizen_report_available = False
            self.citizen_report_error_code, self.citizen_report_error = public_error()

    def open_report_investigation(self):
        return rx.redirect(_investigation_href(self.citizen_report_subject or DEMO_INVESTIGATION_TARGET))
