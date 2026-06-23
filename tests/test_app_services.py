from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from types import SimpleNamespace

import datosenorden.web.app_services as app_services
from datosenorden.maintenance.cross_dataset_explorer import CrossDatasetConnection
from datosenorden.maintenance.cross_dataset_explorer import CrossDatasetOrganizationSummary
from datosenorden.maintenance.ecosystem_registry import ConceptNode
from datosenorden.maintenance.ecosystem_registry import EcosystemRegistry
from datosenorden.maintenance.ecosystem_registry import RoadmapGroup
from datosenorden.maintenance.ecosystem_registry import SourceCatalogEntry
from datosenorden.maintenance.dataset_registry import DatasetSummary
from datosenorden.maintenance.demo_pack import DemoDatasetStatus
from datosenorden.maintenance.demo_pack import DemoRepair
from datosenorden.maintenance.demo_pack import DemoStatusReport
from datosenorden.maintenance.entity_explorer import EntitySearchResult
from datosenorden.maintenance.investigation_view import InvestigationEvidenceGroup
from datosenorden.maintenance.investigation_view import InvestigationEvidenceLink
from datosenorden.maintenance.investigation_view import InvestigationLobbyItem
from datosenorden.maintenance.investigation_view import InvestigationMetrics
from datosenorden.maintenance.investigation_view import InvestigationProcurementItem
from datosenorden.maintenance.investigation_view import InvestigationRoleItem
from datosenorden.maintenance.investigation_view import InvestigationView
from datosenorden.maintenance.timeline_explorer import TimelineEvent


class _SessionContext:
    def __enter__(self):  # noqa: ANN001
        return object()

    def __exit__(self, exc_type, exc, tb):  # noqa: ANN001
        _ = (exc_type, exc, tb)
        return False


@dataclass(frozen=True)
class _EntitySummary:
    id: str
    entity_type: str
    name: str
    external_id: str | None = None


def _patch_session(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(app_services, "SessionLocal", lambda: _SessionContext())


def _investigation_view() -> InvestigationView:
    entity = _EntitySummary(
        id="11111111-1111-1111-1111-111111111111",
        entity_type="PUBLIC_ORGANIZATION",
        name="DIVISION LOGISTICA DEL EJERCITO",
        external_id="buyer-1",
    )
    timeline = SimpleNamespace(
        events=(
            TimelineEvent(
                event_date=date(2026, 3, 15),
                dataset="LOBBY",
                dataset_name="lobby-meeting-sample",
                title="Lobby meeting",
                explanation="Registro de reunion de lobby asociado a la entidad.",
                claim_id="22222222-2222-2222-2222-222222222222",
                predicate="ORGANIZATION_HELD_LOBBY_MEETING",
                source_record_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                evidence_count=1,
                relationship_count=1,
            ),
        )
    )
    graph = SimpleNamespace(
        entity=entity,
        via_relationship_type=None,
        via_direction=None,
        children=(),
    )
    return InvestigationView(
        profile=SimpleNamespace(
            entity=entity,
            relationship_counts=(),
            direct_neighbors=(),
        ),
        entity_type_label="Organismo",
        summary="Vista demo de muestra.",
        dataset_badges=("ChileCompra", "Lobby", "Transparencia"),
        metrics=InvestigationMetrics(
            contracts=1,
            suppliers=1,
            lobby_meetings=1,
            public_roles=1,
            evidence=3,
            relationships=4,
        ),
        timeline=timeline,
        graph=graph,
        graph_explanation="Resumen neutral de conexiones.",
        procurement_items=(
            InvestigationProcurementItem(
                dataset="ChileCompra",
                contract_name="Orden de compra demo",
                supplier="EMPRESA EJEMPLO SPA",
                evidence_count=1,
                evidence_links=(
                    InvestigationEvidenceLink("Evidencia compra", "https://example.test/compra", date(2026, 1, 1)),
                ),
            ),
        ),
        lobby_items=(
            InvestigationLobbyItem(
                dataset="Lobby",
                date=date(2026, 3, 15),
                organization="DIVISION LOGISTICA DEL EJERCITO",
                counterparty="Persona demo",
                subject="Materia demo",
                evidence_count=1,
                evidence_links=(
                    InvestigationEvidenceLink("Evidencia lobby", "https://example.test/lobby", None),
                ),
            ),
        ),
        role_items=(
            InvestigationRoleItem(
                dataset="Transparencia",
                holder="Persona demo",
                role_title="Cargo demo",
                period="2026",
                evidence_count=1,
                evidence_links=(
                    InvestigationEvidenceLink("Evidencia rol", "https://example.test/rol", None),
                ),
            ),
        ),
        evidence_groups=(
            InvestigationEvidenceGroup(
                dataset="ChileCompra",
                links=(InvestigationEvidenceLink("Evidencia compra", "https://example.test/compra", date(2026, 1, 1)),),
            ),
        ),
        explanation="No afirma causalidad, irregularidad ni intencion.",
    )


def test_search_entities_handles_empty_query(monkeypatch) -> None:
    _patch_session(monkeypatch)

    assert app_services.search_entities("") == []


def test_search_entities_returns_json_like_values_for_non_empty_query(monkeypatch) -> None:
    _patch_session(monkeypatch)
    buyer = EntitySearchResult(
        id="11111111-1111-1111-1111-111111111111",
        entity_type="PUBLIC_ORGANIZATION",
        name="DIVISION LOGISTICA DEL EJERCITO",
        external_id="buyer-1",
        purchase_orders=4,
        claims=8,
        relationships=6,
    )
    supplier = EntitySearchResult(
        id="22222222-2222-2222-2222-222222222222",
        entity_type="COMPANY",
        name="EMPRESA EJEMPLO SPA",
        external_id=None,
        purchase_orders=2,
        claims=3,
        relationships=2,
    )
    monkeypatch.setattr(app_services, "search_buyers", lambda session, query, limit=10: (buyer,))
    monkeypatch.setattr(app_services, "search_suppliers", lambda session, query, limit=10: (supplier,))

    results = app_services.search_entities("division", limit=10)

    assert results == [
        {
            "id": buyer.id,
            "entity_type": "PUBLIC_ORGANIZATION",
            "entity_type_label": "Organismo publico",
            "name": "DIVISION LOGISTICA DEL EJERCITO",
            "external_id": "buyer-1",
            "purchase_orders": 4,
            "claims": 8,
            "relationships": 6,
            "datasets_involved": [],
            "explanation": "Entidad encontrada en la base local con registros publicos cargados, 8 afirmaciones y 6 relaciones navegables.",
            "technical_details": {
                "entity_id": buyer.id,
                "external_id": "buyer-1",
            },
        },
        {
            "id": supplier.id,
            "entity_type": "COMPANY",
            "entity_type_label": "Empresa",
            "name": "EMPRESA EJEMPLO SPA",
            "external_id": None,
            "purchase_orders": 2,
            "claims": 3,
            "relationships": 2,
            "datasets_involved": [],
            "explanation": "Entidad encontrada en la base local con registros publicos cargados, 3 afirmaciones y 2 relaciones navegables.",
            "technical_details": {
                "entity_id": supplier.id,
                "external_id": None,
            },
        },
    ]


def test_entity_type_label_includes_servel_period() -> None:
    assert app_services._entity_type_label("ELECTORAL_PERIOD") == "Periodo electoral"


def test_get_investigation_returns_expected_top_level_sections_for_demo_entity(monkeypatch) -> None:
    _patch_session(monkeypatch)
    monkeypatch.setattr(app_services, "build_investigation_view", lambda session, entity_id: _investigation_view())

    investigation = app_services.get_investigation("11111111-1111-1111-1111-111111111111")

    assert investigation["found"] is True
    assert investigation["entity"]["name"] == "DIVISION LOGISTICA DEL EJERCITO"
    assert set(investigation) >= {
        "entity",
        "dataset_badges",
        "key_metrics",
        "compact_metrics",
        "narrative_summary",
        "timeline",
        "connections",
        "contracts_compras",
        "lobby",
        "transparencia",
        "evidence",
        "neutral_explanation",
    }
    assert investigation["key_metrics"]["contracts"] == 1
    assert investigation["compact_metrics"] == {
        "datasets_involved": 3,
        "evidence_count": 3,
        "connected_entities": 0,
        "relationship_count": 4,
    }
    assert "Esto no afirma causalidad" in investigation["narrative_summary"]
    assert investigation["timeline"][0]["event_date"] == "2026-03-15"
    assert investigation["evidence"][0]["links"][0]["title"] == "Evidencia compra"
    assert investigation["evidence"][0]["links"][0]["published_at"] == "2026-01-01"
    assert "technical_details" in investigation


def test_get_source_trace_passthrough(monkeypatch) -> None:
    payload = {
        "entity": {"id": "11111111-1111-1111-1111-111111111111", "name": "Demo entity", "type": "PUBLIC_ORGANIZATION"},
        "sources": [],
        "connections": [],
        "overlap_summary": "Demo trace.",
        "neutrality_notice": "Neutral.",
    }
    monkeypatch.setattr(app_services, "build_source_trace", lambda entity_id: payload)

    result = app_services.get_source_trace("11111111-1111-1111-1111-111111111111")

    assert result == payload


def test_get_data_ecosystem_jsonifies_registry(monkeypatch) -> None:
    _patch_session(monkeypatch)
    registry = EcosystemRegistry(
        sources=(
            SourceCatalogEntry(
                name="ChileCompra",
                slug="chilecompra",
                status="active",
                category="procurement",
                description="Compras publicas.",
                coverage="covered",
                concepts=("Compra", "Proveedor"),
                relationships=("ISSUES_PURCHASE_ORDER",),
                connects_with=("Lobby", "Transparencia"),
                entities=("Organismo", "Empresa"),
            ),
        ),
        concepts=(
            ConceptNode(
                name="Compra",
                coverage="covered",
                datasets=("ChileCompra",),
                description="Compra cubierto por ChileCompra.",
            ),
        ),
        roadmap=(
            RoadmapGroup(
                status="planned",
                title="Fuentes planificadas",
                sources=("Declaraciones de intereses",),
            ),
        ),
    )
    monkeypatch.setattr(app_services, "build_ecosystem_registry", lambda session: registry)

    ecosystem = app_services.get_data_ecosystem()

    assert ecosystem["sources"][0]["connects_with"] == ["Lobby", "Transparencia"]
    assert ecosystem["sources"][0]["concepts"] == ["Compra", "Proveedor"]
    assert ecosystem["concepts"][0]["datasets"] == ["ChileCompra"]
    assert ecosystem["roadmap"][0]["sources"] == ["Declaraciones de intereses"]


def test_get_investigation_markdown_passthrough(monkeypatch) -> None:
    monkeypatch.setattr(app_services, "export_investigation_markdown", lambda entity_id: "# Demo\n")

    result = app_services.get_investigation_markdown("11111111-1111-1111-1111-111111111111")

    assert result == "# Demo\n"


def test_search_workspace_passthrough(monkeypatch) -> None:
    payload = {"matches": [{"entity_id": "1", "entity_name": "Demo", "entity_type": "PERSON", "datasets": ["SERVEL"], "evidence_count": 1, "relationship_count": 2}]}
    monkeypatch.setattr(app_services, "_search_workspace", lambda query: payload)

    result = app_services.search_workspace("demo")

    assert result == payload


def test_get_investigation_graph_passthrough(monkeypatch) -> None:
    payload = {"nodes": [], "edges": [], "summary": "Graph."}
    monkeypatch.setattr(app_services, "build_investigation_graph", lambda entity_id: payload)

    result = app_services.get_investigation_graph("11111111-1111-1111-1111-111111111111")

    assert result == payload


def test_get_investigation_timeline_passthrough(monkeypatch) -> None:
    payload = {"entity": {"id": "1", "name": "Demo", "type": "PERSON"}, "years": [], "summary": "Timeline."}
    monkeypatch.setattr(app_services, "build_investigation_timeline", lambda entity_id: payload)

    result = app_services.get_investigation_timeline("11111111-1111-1111-1111-111111111111")

    assert result == payload


def test_get_source_contributions_passthrough(monkeypatch) -> None:
    payload = {"entity": {"id": "1", "name": "Demo", "type": "PERSON"}, "sources": [], "summary": "Sources."}
    monkeypatch.setattr(app_services, "build_source_contributions", lambda entity_id: payload)

    result = app_services.get_source_contributions("11111111-1111-1111-1111-111111111111")

    assert result == payload


def test_export_investigation_report_passthrough(monkeypatch) -> None:
    monkeypatch.setattr(app_services, "_export_investigation_report", lambda entity_id: "reports/investigation_demo.html")

    result = app_services.export_investigation_report("11111111-1111-1111-1111-111111111111")

    assert result == "reports/investigation_demo.html"


def test_dataset_summary_includes_active_datasets(monkeypatch) -> None:
    _patch_session(monkeypatch)
    monkeypatch.setattr(
        app_services,
        "list_datasets",
        lambda session: (
            DatasetSummary("chilecompra", "ChileCompra", 1, 2, 3, 4, 5, "active", False),
            DatasetSummary("servel", "SERVEL", 0, 0, 0, 0, 0, "empty", True),
        ),
    )

    summary = app_services.get_dataset_summary()

    assert summary["totals"]["active_datasets"] == 1
    assert summary["datasets"][0]["name"] == "ChileCompra"
    assert summary["datasets"][0]["health"] == "active"


def test_get_data_ecosystem_returns_registry_payload(monkeypatch) -> None:
    _patch_session(monkeypatch)
    monkeypatch.setattr(
        "datosenorden.maintenance.ecosystem_registry.list_datasets",
        lambda session: (
            DatasetSummary("chilecompra", "ChileCompra", 1, 2, 3, 4, 5, "active", False),
        ),
    )

    ecosystem = app_services.get_data_ecosystem()

    assert ecosystem["sources"][0]["name"] == "ChileCompra"
    assert ecosystem["sources"][0]["status"] == "active"
    assert any(node["name"] == "Contrato" for node in ecosystem["concepts"])
    assert ecosystem["roadmap"][0]["title"] == "Fuentes implementadas"


def test_cross_dataset_connections_include_shared_organizations(monkeypatch) -> None:
    _patch_session(monkeypatch)
    row = CrossDatasetOrganizationSummary(
        organization_id="11111111-1111-1111-1111-111111111111",
        organization_name="DIVISION LOGISTICA DEL EJERCITO",
        datasets=("chilecompra", "lobby", "transparencia"),
        contracts=1,
        lobby_meetings=1,
        evidence=2,
        relationships=3,
        lobby_connections=(
            CrossDatasetConnection(
                entity_id="22222222-2222-2222-2222-222222222222",
                entity_type="PERSON",
                name="Persona demo",
                relationship_type="COUNTERPARTY_PARTICIPATED_IN_LOBBY",
            ),
        ),
        procurement_connections=(),
        explanation="Shared organization from loaded demo data.",
    )
    monkeypatch.setattr(app_services, "list_cross_dataset_organizations", lambda session: (row,))

    connections = app_services.get_cross_dataset_connections()

    assert connections[0]["organization_name"] == "DIVISION LOGISTICA DEL EJERCITO"
    assert "lobby" in connections[0]["datasets"]
    assert connections[0]["lobby_connections"][0]["name"] == "Persona demo"


def test_demo_status_returns_ready_and_missing_information_without_crashing(monkeypatch) -> None:
    _patch_session(monkeypatch)
    report = DemoStatusReport(
        database_connected=True,
        required_datasets_loaded=False,
        dataset_statuses=(DemoDatasetStatus("lobby", "Lobby sample", False, "empty"),),
        cross_dataset_organization=None,
        timeline_entity="DIVISION LOGISTICA DEL EJERCITO",
        streamlit_app_available=True,
        repairs=(DemoRepair("Lobby sample.", ("python scripts/load_lobby_sample.py",)),),
    )
    monkeypatch.setattr(app_services, "build_demo_status", lambda session: report)

    status = app_services.get_demo_status()

    assert status["ready"] is False
    assert status["database_connected"] is True
    assert status["dataset_statuses"][0]["slug"] == "lobby"
    assert status["missing"][0]["commands"] == ["python scripts/load_lobby_sample.py"]


def test_demo_status_reports_database_failure_without_crashing(monkeypatch) -> None:
    class _BrokenSession:
        def __enter__(self):  # noqa: ANN001
            raise RuntimeError("database unavailable")

        def __exit__(self, exc_type, exc, tb):  # noqa: ANN001
            _ = (exc_type, exc, tb)
            return False

    monkeypatch.setattr(app_services, "SessionLocal", lambda: _BrokenSession())

    status = app_services.get_demo_status()

    assert status["ready"] is False
    assert status["database_connected"] is False
    assert status["missing"][0]["label"] == "PostgreSQL connection."
    assert "database unavailable" in status["error"]
