from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import datosenorden.maintenance.investigation_report as investigation_report


class _SessionContext:
    def __enter__(self):  # noqa: ANN001
        return object()

    def __exit__(self, exc_type, exc, tb):  # noqa: ANN001
        _ = (exc_type, exc, tb)
        return False


def test_export_investigation_report_writes_html(monkeypatch, tmp_path) -> None:
    view = SimpleNamespace(
        profile=SimpleNamespace(
            entity=SimpleNamespace(id=UUID("11111111-1111-1111-1111-111111111111"), name="Entidad demo", entity_type="PUBLIC_ORGANIZATION"),
            relationships=(),
        ),
        summary="Neutral summary.",
        evidence_groups=(),
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(investigation_report, "SessionLocal", lambda: _SessionContext())
    monkeypatch.setattr(investigation_report, "build_investigation_view", lambda session, entity_id: view)
    monkeypatch.setattr(investigation_report, "build_investigation_story", lambda entity_id: {"summary": "Neutral summary."})
    monkeypatch.setattr(
        investigation_report,
        "build_source_trace",
        lambda entity_id: {"sources": [], "neutrality_notice": "This view is descriptive only.", "overlap_summary": "Coverage."},
    )
    monkeypatch.setattr(
        investigation_report,
        "build_investigation_graph",
        lambda entity_id: {"nodes": [], "edges": [], "summary": "Graph summary."},
    )
    monkeypatch.setattr(
        investigation_report,
        "build_investigation_timeline",
        lambda entity_id: {"entity": {"id": "", "name": "", "type": ""}, "years": [], "summary": "Timeline summary."},
    )
    monkeypatch.setattr(
        investigation_report,
        "build_source_contributions",
        lambda entity_id: {"sources": [], "summary": "Contribution summary."},
    )

    output = investigation_report.export_investigation_report(str(view.profile.entity.id))

    path = Path(output)
    assert path.exists()
    html = path.read_text(encoding="utf-8")
    assert "Investigation report: Entidad demo" in html
    assert "Source Contributions" in html
    assert "Timeline" in html
    assert "Relationships" in html
    assert "Evidence" in html


def test_export_investigation_report_handles_dict_views_and_links(monkeypatch, tmp_path) -> None:
    view = {
        "profile": {
            "entity": {
                "id": UUID("11111111-1111-1111-1111-111111111111"),
                "name": "Entidad demo",
                "entity_type": "PUBLIC_ORGANIZATION",
            },
            "relationships": (
                {
                    "relationship_type": "RELATES_TO",
                    "related_entity": {"name": "Entidad relacionada"},
                },
            ),
        },
        "summary": "Neutral summary.",
        "evidence_groups": (
            {
                "dataset": "ChileCompra",
                "links": (
                    {"title": "Evidencia dict", "url": "https://example.test/dict", "published_at": None},
                ),
            },
        ),
    }
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(investigation_report, "SessionLocal", lambda: _SessionContext())
    monkeypatch.setattr(investigation_report, "build_investigation_view", lambda session, entity_id: view)
    monkeypatch.setattr(investigation_report, "build_investigation_story", lambda entity_id: {"summary": "Neutral summary."})
    monkeypatch.setattr(
        investigation_report,
        "build_source_trace",
        lambda entity_id: {
            "sources": [
                {
                    "dataset": "ChileCompra",
                    "contribution": "Contribution.",
                    "evidence_count": 1,
                    "relationship_count": 1,
                    "facts": ["Fact one"],
                    "technical": ["claim_id=1"],
                }
            ],
            "neutrality_notice": "This view is descriptive only.",
            "overlap_summary": "Coverage.",
        },
    )
    monkeypatch.setattr(
        investigation_report,
        "build_investigation_graph",
        lambda entity_id: {"nodes": [{"label": "Node", "category": "dataset"}], "edges": [], "summary": "Graph summary."},
    )
    monkeypatch.setattr(
        investigation_report,
        "build_investigation_timeline",
        lambda entity_id: {"entity": {"id": "", "name": "", "type": ""}, "years": [], "summary": "Timeline summary."},
    )
    monkeypatch.setattr(
        investigation_report,
        "build_source_contributions",
        lambda entity_id: {"sources": [], "summary": "Contribution summary."},
    )

    output = investigation_report.export_investigation_report(str(view["profile"]["entity"]["id"]))

    path = Path(output)
    assert path.exists()
    html = path.read_text(encoding="utf-8")
    assert "Evidencia dict" in html
    assert "Entidad relacionada" in html
