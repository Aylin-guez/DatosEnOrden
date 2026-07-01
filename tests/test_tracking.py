from __future__ import annotations

from datetime import date
from pathlib import Path

from datosenorden.maintenance import tracking
from datosenorden.web import app_services


def test_tracking_demo_has_local_markers_and_timeline() -> None:
    timeline = tracking.build_tracking_demo()

    assert timeline.item.classification == tracking.LOCAL_TEST_DATA
    assert timeline.item.official_status == tracking.NOT_OFFICIAL_DATA
    assert timeline.item.related_expediente_target == tracking.DEMO_ENTITY_NAME
    assert len(timeline.events) >= 7
    assert {event.status for event in timeline.events} >= {
        tracking.TrackingStatus.PROPOSED,
        tracking.TrackingStatus.PUBLISHED,
        tracking.TrackingStatus.PARTIALLY_IMPLEMENTED,
    }
    assert any("ChileCompra" in event.source for event in timeline.events)
    assert any(document.hash_sha256 for document in timeline.documents)


def test_tracking_services_return_json_safe_demo() -> None:
    demo = app_services.get_tracking_demo()

    assert demo["item"]["id"] == tracking.DEMO_TRACKING_ITEM_ID
    assert demo["item"]["current_status"] == "partially_implemented"
    assert demo["events"][0]["status"] == "proposed"
    assert app_services.get_tracking_items()[0]["id"] == tracking.DEMO_TRACKING_ITEM_ID
    assert app_services.get_tracking_item(tracking.DEMO_TRACKING_ITEM_ID)["events"]
    assert app_services.get_tracking_timeline(tracking.DEMO_TRACKING_ITEM_ID)["documents"]
    assert app_services.get_tracking_item("missing") == {}
    assert demo["overview"]["progress"]["total_events"] == len(demo["events"])
    assert demo["overview"]["history"]


def test_tracking_engine_derives_history_progress_coverage_and_alerts() -> None:
    timeline = tracking.build_tracking_demo()

    history = tracking.build_tracking_history(timeline)
    progress = tracking.calculate_tracking_progress(timeline)
    coverage = tracking.calculate_document_coverage(timeline)
    alerts = tracking.build_tracking_alerts(timeline, today=date(2026, 7, 1), stale_days=45)

    assert history[0].field == "status"
    assert progress.total_events == len(timeline.events)
    assert progress.documented_events == len(timeline.events)
    assert coverage.coverage_percent == 100
    assert coverage.missing_document_ids == ()
    assert any(alert.event_id == "evt-lobby" for alert in alerts)
    assert all("SACFI" not in alert.title for alert in alerts)


def test_export_tracking_demo_report_writes_html(tmp_path: Path) -> None:
    output = tmp_path / "tracking.html"

    path = tracking.export_tracking_demo_report(output)
    html = output.read_text(encoding="utf-8")

    assert path == str(output)
    assert "Programa / propuesta de fortalecimiento hospitalario Arauco" in html
    assert "LOCAL_TEST_DATA" in html
    assert "No afirma causalidad" in html or "No afirma causalidad".lower() in html.lower()
