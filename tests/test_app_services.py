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
from datosenorden.maintenance.investigation_view import InvestigationLegislativeVoteItem
from datosenorden.maintenance.investigation_view import InvestigationLobbyItem
from datosenorden.maintenance.investigation_view import InvestigationMetrics
from datosenorden.maintenance.investigation_view import InvestigationRegistryItem
from datosenorden.maintenance.investigation_view import InvestigationProcurementItem
from datosenorden.maintenance.investigation_view import InvestigationRoleItem
from datosenorden.maintenance.investigation_view import InvestigationSourceRecordItem
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
    monkeypatch.setattr(app_services, "enrich_public_ecosystem", lambda session, ecosystem: ecosystem)


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
        registry_items=(
            InvestigationRegistryItem(
                dataset="Registro Empresas",
                company="EMPRESA EJEMPLO SPA",
                person="Persona demo",
                relation="Representante",
                rut="76.123.456-7",
                status="Vigente",
                ownership_percentage="100",
                evidence_count=1,
                evidence_links=(
                    InvestigationEvidenceLink("Evidencia empresa", "https://example.test/empresa", None),
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


def _legislative_investigation_view() -> InvestigationView:
    entity = _EntitySummary(
        id="11111111-1111-1111-1111-111111111111",
        entity_type="PUBLIC_PROJECT",
        name="Boletin 8575-05",
        external_id="cl-congreso-boletin-8575-05",
    )
    evidence_link = InvestigationEvidenceLink(
        "Votacion camara-votacion-1 asociada al boletin 8575-05",
        "https://opendata.camara.cl/services/getVotacion_Detalle?prmVotacionID=1",
        date(2026, 1, 2),
    )
    timeline = SimpleNamespace(
        events=(
            TimelineEvent(
                event_date=date(2026, 1, 2),
                dataset="DATOS ABIERTOS LEGISLATIVOS",
                dataset_name="congreso-votaciones-boletin",
                title="Votacion asociada al boletin.",
                explanation="Fuente legislativa.",
                claim_id="22222222-2222-2222-2222-222222222222",
                predicate="LEGISLATIVE_BILL_HAS_VOTE",
                source_record_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                evidence_count=1,
                relationship_count=0,
            ),
        )
    )
    return InvestigationView(
        profile=SimpleNamespace(entity=entity, relationship_counts=(), direct_neighbors=()),
        entity_type_label="Proyecto legislativo / Boletin",
        summary="Vista legislativa minima.",
        dataset_badges=("Datos Abiertos Legislativos",),
        metrics=InvestigationMetrics(
            contracts=0,
            suppliers=0,
            lobby_meetings=0,
            public_roles=0,
            evidence=1,
            relationships=0,
        ),
        timeline=timeline,
        graph=None,
        graph_explanation="No hay grafo disponible para esta entidad.",
        procurement_items=(),
        lobby_items=(),
        registry_items=(),
        role_items=(),
        evidence_groups=(
            InvestigationEvidenceGroup(dataset="Datos Abiertos Legislativos", links=(evidence_link,)),
        ),
        explanation="No afirma causalidad.",
        source_records=(
            InvestigationSourceRecordItem(
                id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                external_id="camara-votacion-1",
                record_type="legislature:vote",
                source="Datos Abiertos Legislativos Congreso Nacional",
                dataset="Datos Abiertos Legislativos",
                official_url=evidence_link.url,
                retrieved_at="2026-01-02T00:00:00+00:00",
            ),
        ),
        legislative_vote_items=(
            InvestigationLegislativeVoteItem(
                dataset="Datos Abiertos Legislativos",
                vote_id="camara-votacion-1",
                date=date(2026, 1, 2),
                source="Datos Abiertos Legislativos",
                official_url=evidence_link.url,
                evidence_count=1,
                evidence_links=(evidence_link,),
            ),
        ),
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
        "registro_empresas",
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


def test_get_investigation_returns_minimal_legislative_bill_expediente(monkeypatch) -> None:
    _patch_session(monkeypatch)
    monkeypatch.setattr(
        app_services,
        "resolve_investigation_target",
        lambda value: {
            "found": True,
            "entity_id": "11111111-1111-1111-1111-111111111111",
            "entity_name": "Boletin 8575-05",
            "matched_by": "external_id",
        },
    )
    monkeypatch.setattr(app_services, "build_investigation_view", lambda session, entity_id: _legislative_investigation_view())

    investigation = app_services.get_investigation("cl-congreso-boletin-8575-05")

    assert investigation["found"] is True
    assert investigation["entity"]["name"] == "Boletin 8575-05"
    assert investigation["entity_type_label"] == "Proyecto legislativo / Boletin"
    assert investigation["official_source"] == "Datos Abiertos Legislativos"
    assert investigation["legislative"]["votes_found"] == 1
    assert investigation["legislative"]["source_records_count"] == 1
    assert investigation["compact_metrics"]["evidence_count"] == 1
    assert "Este expediente contiene votaciones oficiales asociadas al boletín" in investigation["knowledge"]["limitations"][0]


def test_get_investigation_existing_external_id_opens_internal_uuid(monkeypatch) -> None:
    internal_id = "11111111-1111-1111-1111-111111111111"
    captured: list[str] = []

    class _ExternalIdSession:
        def __enter__(self):  # noqa: ANN001
            return self

        def __exit__(self, exc_type, exc, tb):  # noqa: ANN001
            _ = (exc_type, exc, tb)
            return False

        def scalar(self, statement):  # noqa: ANN001
            _ = statement
            return internal_id

    monkeypatch.setattr(app_services, "SessionLocal", lambda: _ExternalIdSession())
    monkeypatch.setattr(
        app_services,
        "resolve_investigation_target",
        lambda value: {
            "found": True,
            "entity_id": "cl-congreso-boletin-8575-05",
            "entity_name": "Boletin 8575-05",
            "matched_by": "external_id",
        },
    )

    def build_view(session, entity_id):  # noqa: ANN001
        _ = session
        captured.append(entity_id)
        return _legislative_investigation_view()

    monkeypatch.setattr(app_services, "build_investigation_view", build_view)

    investigation = app_services.get_investigation("cl-congreso-boletin-8575-05")

    assert investigation["found"] is True
    assert captured == [internal_id]
    assert investigation["resolution"]["entity_id"] == internal_id

def test_get_investigation_unresolved_external_id_does_not_call_uuid_profile(monkeypatch) -> None:
    class _MissingExternalIdSession:
        def __enter__(self):  # noqa: ANN001
            return self

        def __exit__(self, exc_type, exc, tb):  # noqa: ANN001
            _ = (exc_type, exc, tb)
            return False

        def scalar(self, statement):  # noqa: ANN001
            _ = statement
            return None

    monkeypatch.setattr(app_services, "SessionLocal", lambda: _MissingExternalIdSession())
    monkeypatch.setattr(
        app_services,
        "resolve_investigation_target",
        lambda value: {"found": False, "entity_id": "", "warning": "No se encontro una entidad local."},
    )
    monkeypatch.setattr(
        app_services,
        "build_investigation_view",
        lambda session, entity_id: (_ for _ in ()).throw(AssertionError("profile lookup should not run")),
    )

    investigation = app_services.get_investigation("cl-congreso-boletin-8575-05")

    assert investigation["found"] is False
    assert investigation["entity_id"] == "cl-congreso-boletin-8575-05"
    assert "No se encontro" in investigation["warning"]

def test_get_guided_questions_returns_rule_based_questions() -> None:
    payload = app_services.get_guided_questions()

    assert any(question["id"] == "who_sells_to_this_body" for question in payload["questions"])
    assert any(category["id"] == "public_organizations" for category in payload["categories"])


def test_get_institution_profile_passthrough(monkeypatch) -> None:
    payload = {"entidad": {"nombre": "Entidad demo"}, "presupuesto": {"total": 0}, "contratos": []}
    monkeypatch.setattr(app_services, "build_institution_profile", lambda entity_name: payload)

    result = app_services.get_institution_profile("Entidad demo")

    assert result == payload


def test_get_citizen_dashboard_passthrough(monkeypatch) -> None:
    payload = {"metrics": {"budget_total": 0}, "featured_entities": []}
    monkeypatch.setattr(app_services, "build_citizen_dashboard", lambda: payload)

    result = app_services.get_citizen_dashboard()

    assert result == payload


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
    monkeypatch.setattr(
        app_services,
        "_resolve_canonical_expediente_target",
        lambda value: {
            "found": True,
            "canonical_entity_id": "1",
            "canonical_entity_name": "Demo",
            "canonical_entity_type": "PERSON",
            "is_record": False,
            "record_label": "Persona",
            "relation_to_original": "self",
        },
    )
    monkeypatch.setattr(app_services, "_get_record_context", lambda value: {"related_label": ""})

    result = app_services.search_workspace("demo")

    assert result["matches"][0]["canonical_entity_id"] == "1"
    assert result["matches"][0]["canonical_entity_name"] == "Demo"


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
        "build_public_dataset_summary",
        lambda session, datasets: {
            "datasets": [{**datasets[0], "health": "active"}, datasets[1]],
            "totals": {"active_datasets": 1},
        },
    )
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


def test_get_real_data_readiness_passthrough(monkeypatch) -> None:
    monkeypatch.setattr(
        app_services,
        "summarize_real_dataset_registry",
        lambda session: {"entries": [{"id": "chilecompra"}], "totals": {"ready": 1}},
    )

    result = app_services.get_real_data_readiness()

    assert result["totals"]["ready"] == 1
    assert result["entries"][0]["id"] == "chilecompra"


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


def test_get_discovery_cases_returns_guided_examples() -> None:
    payload = app_services.get_discovery_cases()

    assert "cases" in payload
    assert any(case["id"] == "public_spending" for case in payload["cases"])
    assert any(case["id"] == "public_roles" for case in payload["cases"])
    forbidden_terms = ("accus", "irregular", "risk", "suspicious", "corrupt", "fraud")
    assert not any(term in str(payload).lower() for term in forbidden_terms)


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


def test_source_population_enriches_lobby_surfaces(monkeypatch) -> None:
    _patch_session(monkeypatch)
    monkeypatch.setattr(
        "datosenorden.maintenance.ecosystem_registry.list_datasets",
        lambda session: (),
    )

    ecosystem = app_services.get_data_ecosystem()
    lobby = next(source for source in ecosystem["sources"] if source["slug"] == "lobby")
    search = app_services.search_workspace("MARLENE FLORES")
    topics = app_services.get_current_topics(limit=6)

    assert lobby["population_records"] == 1
    assert lobby["population_status_label"] == "muestra local controlada"
    assert not any(match["source_label"] == "InfoLobby" for match in search["matches"])
    assert any(topic["id"] == "pulse-infolobby-minimal-v1" for topic in topics)

def test_chilecompra_connector_feeds_core_surfaces(monkeypatch) -> None:
    _patch_session(monkeypatch)
    monkeypatch.setattr(
        "datosenorden.maintenance.ecosystem_registry.list_datasets",
        lambda session: (),
    )
    monkeypatch.setattr(app_services, "_search_workspace", lambda query: {"matches": []})
    monkeypatch.setattr(app_services, "_list_current_topics", lambda limit=3: [])

    connector = app_services._load_connector("chilecompra")
    ecosystem = app_services.get_data_ecosystem()
    search = app_services.search_workspace("ACME TECNOLOGIAS")
    topics = app_services.get_current_topics(limit=3)
    tracking = app_services.get_tracking_demo()
    chilecompra = next(source for source in ecosystem["sources"] if source["slug"] == "chilecompra")

    assert connector["produces"]["entities"] == ["Organismo", "Proveedor", "Empresa", "Contrato", "Compra"]
    assert connector["produces"]["relationships"] == ["ISSUES_PURCHASE_ORDER", "RECEIVES_CONTRACT"]
    assert chilecompra["connector_entities"] >= 5
    assert chilecompra["connector_relationships"] >= 6
    assert not any(match["source_label"] == "ChileCompra Connector" for match in search["matches"])
    assert any(topic["source"] == "ChileCompra Connector" for topic in topics)
    assert any(event["source"] == "ChileCompra Connector" for event in tracking["events"])


def test_infolobby_connector_feeds_core_surfaces(monkeypatch) -> None:
    _patch_session(monkeypatch)
    monkeypatch.setattr(
        "datosenorden.maintenance.ecosystem_registry.list_datasets",
        lambda session: (),
    )
    monkeypatch.setattr(app_services, "_search_workspace", lambda query: {"matches": []})
    monkeypatch.setattr(app_services, "_list_current_topics", lambda limit=3: [])

    connector = app_services._load_connector("infolobby")
    ecosystem = app_services.get_data_ecosystem()
    search = app_services.search_workspace("MARLENE FLORES")
    topics = app_services.get_current_topics(limit=4)
    tracking = app_services.get_tracking_demo()
    lobby = next(source for source in ecosystem["sources"] if source["slug"] == "lobby")

    assert connector["id"] == "lobby"
    assert connector["produces"]["entities"] == ["Organismo", "Persona", "Reuni\u00f3n"]
    assert connector["produces"]["relationships"] == ["ORGANIZATION_HELD_LOBBY_MEETING", "COUNTERPARTY_PARTICIPATED_IN_LOBBY"]
    assert connector["feeds"] == ["Buscar", "Expediente", "Pulso", "Fuentes", "Cronolog\u00eda", "Relaciones"]
    assert lobby["connector_entities"] == 3
    assert lobby["connector_relationships"] == 2
    assert lobby["connector_events"] == 1
    assert not any(match["source_label"] == "InfoLobby Connector" for match in search["matches"])
    assert not any(match["entity_name"] == "MARLENE BEATRIZ FLORES PATINO" for match in search["matches"])
    assert any(topic["source"] == "InfoLobby Connector" for topic in topics)
    assert any(event["source"] == "InfoLobby Connector" for event in tracking["events"])


def test_diario_oficial_connector_feeds_core_surfaces(monkeypatch) -> None:
    _patch_session(monkeypatch)
    monkeypatch.setattr(
        "datosenorden.maintenance.ecosystem_registry.list_datasets",
        lambda session: (),
    )
    monkeypatch.setattr(app_services, "_search_workspace", lambda query: {"matches": []})
    monkeypatch.setattr(app_services, "_list_current_topics", lambda limit=3: [])

    connector = app_services._load_connector("diario_oficial")
    ecosystem = app_services.get_data_ecosystem()
    search = app_services.search_workspace("Persona de Muestra Uno")
    topics = app_services.get_current_topics(limit=5)
    tracking = app_services.get_tracking_demo()
    diario = next(source for source in ecosystem["sources"] if source["slug"] == "diario_oficial")

    assert connector["id"] == "diario_oficial"
    assert connector["produces"]["entities"] == ["Organismo", "Persona", "Cargo", "Publicaci\u00f3n", "Documento"]
    assert connector["produces"]["relationships"] == ["OFFICIAL_PUBLICATION_REFERENCES_ENTITY", "PERSON_APPOINTED_TO_PUBLIC_OFFICE", "PUBLIC_OFFICE_BELONGS_TO_ORGANIZATION"]
    assert connector["feeds"] == ["Buscar", "Expediente", "Pulso", "Fuentes", "Cronolog\u00eda", "Relaciones"]
    assert diario["connector_entities"] == 4
    assert diario["connector_relationships"] == 3
    assert diario["connector_events"] == 1
    assert not any(match["source_label"] == "Diario Oficial Connector" for match in search["matches"])
    assert not any(match["entity_name"] == "Persona de Muestra Uno" for match in search["matches"])
    assert any(topic["source"] == "Diario Oficial Connector" for topic in topics)
    assert any(event["source"] == "Diario Oficial Connector" for event in tracking["events"])

