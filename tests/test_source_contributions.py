from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID

import datosenorden.maintenance.source_contributions as source_contributions


class _SessionContext:
    def __enter__(self):  # noqa: ANN001
        return object()

    def __exit__(self, exc_type, exc, tb):  # noqa: ANN001
        _ = (exc_type, exc, tb)
        return False


def test_build_source_contributions_uses_dataset_metadata(monkeypatch) -> None:
    view = SimpleNamespace(
        profile=SimpleNamespace(
            entity=SimpleNamespace(id=UUID("11111111-1111-1111-1111-111111111111"), name="Entidad demo", entity_type="PUBLIC_ORGANIZATION"),
            relationships=(SimpleNamespace(),),
        ),
        evidence_groups=(
            SimpleNamespace(dataset="ChileCompra", links=(SimpleNamespace(), SimpleNamespace())),
        ),
        summary="Neutral summary.",
    )
    monkeypatch.setattr(source_contributions, "SessionLocal", lambda: _SessionContext())
    monkeypatch.setattr(source_contributions, "build_investigation_view", lambda session, entity_id: view)
    monkeypatch.setattr(
        source_contributions,
        "build_entity_comparison",
        lambda entity_id: {"datasets_present": ["ChileCompra", "SERVEL"], "coverage_summary": "Coverage."},
    )

    report = source_contributions.build_source_contributions(str(view.profile.entity.id))

    assert report["entity"]["name"] == "Entidad demo"
    assert len(report["sources"]) == 2
    assert report["sources"][0]["dataset"] in {"ChileCompra", "SERVEL"}
    assert report["sources"][0]["contributes"][0].startswith("- ")
    assert report["summary"] == "Coverage."
