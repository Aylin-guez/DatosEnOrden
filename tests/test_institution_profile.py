from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from uuid import UUID

import datosenorden.maintenance.institution_profile as institution_profile


class _SessionContext:
    def __enter__(self):  # noqa: ANN001
        return object()

    def __exit__(self, exc_type, exc, tb):  # noqa: ANN001
        _ = (exc_type, exc, tb)
        return False


def test_build_institution_profile_combines_multiple_sections(monkeypatch) -> None:
    entity = SimpleNamespace(id=UUID("11111111-1111-1111-1111-111111111111"), name="Entidad demo", entity_type="PUBLIC_ORGANIZATION")
    view = SimpleNamespace(
        profile=SimpleNamespace(entity=entity, direct_neighbors=()),
        procurement_items=(SimpleNamespace(dataset="ChileCompra", contract_name="Contrato demo", supplier="Proveedor demo", evidence_count=1, evidence_links=()),),
        lobby_items=(SimpleNamespace(dataset="Lobby", date=date(2026, 3, 15), organization="Entidad demo", counterparty="Persona demo", subject="Tema demo", evidence_count=1, evidence_links=()),),
        role_items=(SimpleNamespace(dataset="Transparencia", holder="Persona demo", role_title="Cargo demo", period="2026", evidence_count=1, evidence_links=()),),
        evidence_groups=(SimpleNamespace(dataset="ChileCompra", links=(SimpleNamespace(title="Evidencia demo", url="https://example.test", published_at=date(2026, 1, 1)),)),),
    )
    timeline = SimpleNamespace(
        events=(
            SimpleNamespace(
                dataset="Diario Oficial",
                dataset_name="diario-oficial-sample",
                title="Publicacion oficial demo",
                explanation="Publicacion demo.",
                event_date=date(2026, 1, 1),
                predicate="OFFICIAL_PUBLICATION_REFERENCES_ENTITY",
            ),
        )
    )
    budget_rows = [
        {
            "organization_name": "Entidad demo",
            "budget_entity_name": "Entidad demo",
            "fiscal_year": 2026,
            "approved_budget": 10,
            "executed_budget": 8,
            "purchase_orders": 2,
            "suppliers": 1,
            "currency": "CLP",
        }
    ]

    monkeypatch.setattr(institution_profile, "SessionLocal", lambda: _SessionContext())
    monkeypatch.setattr(institution_profile, "_find_entity", lambda session, name: entity)
    monkeypatch.setattr(institution_profile, "build_investigation_view", lambda session, entity_id: view)
    monkeypatch.setattr(institution_profile, "build_entity_comparison", lambda entity_id: {"datasets_present": ["ChileCompra", "Diario Oficial"]})
    monkeypatch.setattr(institution_profile, "build_investigation_story", lambda entity_id: {"summary": "Resumen demo", "key_findings": ["Hallazgo demo"], "sources_consulted": ["ChileCompra"]})
    monkeypatch.setattr(institution_profile, "build_source_trace", lambda entity_id: {"connections": [{"from_source": "ChileCompra", "to_entity": "Entidad demo", "meaning": "Compra", "evidence_count": 1}]})
    monkeypatch.setattr(institution_profile, "build_entity_timeline", lambda session, entity_id: timeline)
    monkeypatch.setattr(institution_profile, "read_budget_summary", lambda session: tuple(SimpleNamespace(**row) for row in budget_rows))

    profile = institution_profile.build_institution_profile("Entidad demo")

    assert profile["entidad"]["nombre"] == "Entidad demo"
    assert profile["presupuesto"]["total"] == 8
    assert profile["contratos"][0]["contract_name"] == "Contrato demo"
    assert profile["reuniones"][0]["subject"] == "Tema demo"
    assert profile["autoridades"][0]["role_title"] == "Cargo demo"
    assert profile["publicaciones"][0]["label"] == "Publicacion oficial demo"
    assert profile["evidencia"][0]["title"] == "Evidencia demo"
    assert profile["relaciones"][0]["meaning"] == "Compra"


def test_build_institution_profile_handles_empty_matches(monkeypatch) -> None:
    monkeypatch.setattr(institution_profile, "SessionLocal", lambda: _SessionContext())
    monkeypatch.setattr(institution_profile, "_find_entity", lambda session, name: None)

    profile = institution_profile.build_institution_profile("Entidad desconocida")

    assert profile["entidad"]["nombre"] == "Entidad desconocida"
    assert profile["contratos"] == []
    assert profile["reuniones"] == []
    assert profile["autoridades"] == []
