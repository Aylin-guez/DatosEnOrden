from __future__ import annotations

from pathlib import Path

from datosenorden.maintenance import citizen_reports
from datosenorden.web import app_services


def test_citizen_report_demo_is_local_neutral_and_connected() -> None:
    report = citizen_reports.build_citizen_report_demo()

    assert report.classification == citizen_reports.LOCAL_TEST_DATA
    assert report.official_status == citizen_reports.NOT_OFFICIAL_DATA
    assert report.related_expediente_target == citizen_reports.DEMO_ENTITY_NAME
    assert report.related_tracking_item_id
    assert len(report.sources) >= 5
    assert len(report.sections) >= 3
    assert all("irregularidad" not in section.title.lower() for section in report.sections)


def test_citizen_report_services_return_json_safe_demo() -> None:
    demo = app_services.get_citizen_report_demo()

    assert demo["id"] == citizen_reports.DEMO_CITIZEN_REPORT_ID
    assert demo["classification"] == citizen_reports.LOCAL_TEST_DATA
    assert demo["official_status"] == citizen_reports.NOT_OFFICIAL_DATA
    assert app_services.get_citizen_reports()[0]["id"] == citizen_reports.DEMO_CITIZEN_REPORT_ID
    assert app_services.get_citizen_report(citizen_reports.DEMO_CITIZEN_REPORT_ID)["sections"]
    assert app_services.get_citizen_report("missing") == {}


def test_export_citizen_report_demo_writes_html(tmp_path: Path) -> None:
    output = tmp_path / "citizen_report.html"

    path = citizen_reports.export_citizen_report_demo(output)
    html = output.read_text(encoding="utf-8")

    assert path == str(output)
    assert "Reporte ciudadano demo: Servicio de Salud Arauco" in html
    assert "LOCAL_TEST_DATA" in html
    assert "No afirma causalidad" in html
