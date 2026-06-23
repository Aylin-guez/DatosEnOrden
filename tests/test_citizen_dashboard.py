from __future__ import annotations

from types import SimpleNamespace

import datosenorden.maintenance.citizen_dashboard as citizen_dashboard


class _SessionContext:
    def __enter__(self):  # noqa: ANN001
        return object()

    def __exit__(self, exc_type, exc, tb):  # noqa: ANN001
        _ = (exc_type, exc, tb)
        return False


def test_build_citizen_dashboard_returns_local_metrics(monkeypatch) -> None:
    monkeypatch.setattr(citizen_dashboard, "SessionLocal", lambda: _SessionContext())
    monkeypatch.setattr(
        citizen_dashboard,
        "read_budget_summary",
        lambda session: (
            SimpleNamespace(organization_name="Entidad demo", budget_entity_name="Entidad demo", fiscal_year=2026, approved_budget=10, executed_budget=8, purchase_orders=2, suppliers=1, currency="CLP"),
        ),
    )
    monkeypatch.setattr(
        citizen_dashboard,
        "list_cross_dataset_organizations",
        lambda session: (
            SimpleNamespace(
                organization_id="11111111-1111-1111-1111-111111111111",
                organization_name="Entidad demo",
                datasets=("ChileCompra", "Lobby"),
                contracts=1,
                lobby_meetings=1,
                evidence=2,
                relationships=3,
            ),
        ),
    )
    monkeypatch.setattr(
        citizen_dashboard,
        "get_discovery_cases",
        lambda: {"cases": [{"id": "public_spending", "title": "Demo"}]},
    )

    dashboard = citizen_dashboard.build_citizen_dashboard()

    assert dashboard["metrics"]["budget_total"] == 8
    assert dashboard["metrics"]["contracts"] >= 0
    assert dashboard["featured_entities"][0]["organization_name"] == "Entidad demo"
    assert dashboard["discovery_cases"][0]["id"] == "public_spending"
