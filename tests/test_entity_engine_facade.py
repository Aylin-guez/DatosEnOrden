from datosenorden.web import entity_engine


def _patch_entity_engine_services(monkeypatch) -> None:
    monkeypatch.setattr(
        entity_engine.app_services,
        "resolve_investigation_target",
        lambda target: {
            "found": True,
            "entity_id": "entity-1",
            "entity_name": "Servicio de Salud Arauco",
            "canonical": {"canonical_entity_name": "SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO"},
        },
    )
    monkeypatch.setattr(
        entity_engine.app_services,
        "get_investigation",
        lambda entity_id: {
            "found": True,
            "entity": {"id": entity_id, "name": "SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO", "external_id": "ssaah"},
            "entity_type_label": "Organismo",
            "narrative_summary": "Resumen ciudadano",
            "summary": "Resumen base",
            "compact_metrics": {"evidence_count": 4, "relationship_count": 5, "connected_entities": 3},
            "dataset_badges": ["ChileCompra", "DIPRES", "Lobby"],
            "connections": {
                "summary": "Conexion demo.",
                "relationship_cards": [
                    {"title": "ACME TECNOLOGIAS SPA", "type": "Proveedor", "source": "ChileCompra"},
                    {"title": "Servicio de Salud Concepcion", "type": "Organismo", "source": "DIPRES"},
                    {"title": "Marlene Flores", "type": "Persona", "source": "Lobby"},
                ],
                "direct_neighbors": [],
            },
            "contracts_compras": [
                {"id": "oc-1", "supplier": "ACME TECNOLOGIAS SPA", "dataset": "ChileCompra"},
                {"id": "oc-2", "supplier": "ACME TECNOLOGIAS SPA", "dataset": "ChileCompra"},
            ],
            "lobby": [{"id": "lob-1", "counterparty_name": "ACME TECNOLOGIAS SPA", "dataset": "Lobby"}],
            "transparencia": [{"title": "Directora", "type": "Cargo publico"}],
            "registro_empresas": [{"title": "ACME TECNOLOGIAS SPA", "type": "Empresa"}],
            "timeline": [{"id": "pub-1", "title": "Publicacion Diario Oficial", "source": "Diario Oficial"}],
            "evidence": [{"dataset": "ChileCompra", "links": [{"title": "OC"}]}],
            "knowledge": {"summary": "Conocimiento"},
        },
    )
    monkeypatch.setattr(
        entity_engine.app_services,
        "get_investigation_timeline",
        lambda entity_id: {"years": [{"year": "2026", "events": [{"id": "ev-1", "title": "Compra"}]}]},
    )
    monkeypatch.setattr(
        entity_engine.app_services,
        "get_source_trace",
        lambda entity_id: {"sources": [{"dataset": "ChileCompra"}, {"dataset": "Lobby"}]},
    )
    monkeypatch.setattr(
        entity_engine.app_services,
        "get_source_contributions",
        lambda entity_id: {"sources": [{"dataset": "ChileCompra", "facts": ["Compra"]}]},
    )
    monkeypatch.setattr(
        entity_engine.app_services,
        "get_knowledge_documents",
        lambda: [
            {
                "id": "doc-1",
                "title": "Servicio de Salud Arauco documento oficial",
                "summary": "Documento del expediente",
                "source": "Senado",
                "related_expediente_target": "Servicio de Salud Arauco",
            },
            {"id": "doc-2", "title": "Otro documento", "summary": "", "source": "Biblioteca"},
        ],
    )
    monkeypatch.setattr(
        entity_engine.app_services,
        "get_current_topics",
        lambda limit=10: [{"id": "topic-1", "title": "Nueva compra publica", "source": "ChileCompra Connector"}],
    )
    monkeypatch.setattr(
        entity_engine.app_services,
        "get_data_ecosystem",
        lambda: {
            "sources": [
                {"name": "ChileCompra", "slug": "chilecompra", "connector_status": "active", "connector_entities": 7, "connector_relationships": 6, "connector_events": 3},
                {"name": "Lobby", "slug": "lobby", "connector_status": "demo", "connector_entities": 3, "connector_relationships": 2, "connector_events": 1},
                {"name": "Diario Oficial", "slug": "diario_oficial", "connector_status": "demo", "connector_entities": 4, "connector_relationships": 3, "connector_events": 1},
            ]
        },
    )


def test_entity_engine_facade_delegates_to_web_services(monkeypatch) -> None:
    _patch_entity_engine_services(monkeypatch)
    engine = entity_engine.EntityEngine()

    assert engine.get_entity("arauco")["entity_id"] == "entity-1"
    assert engine.get_entity_summary("arauco")["summary"] == "Resumen ciudadano"
    assert engine.get_entity_timeline("arauco") == {"years": [{"year": "2026", "events": [{"id": "ev-1", "title": "Compra"}]}]}
    assert engine.get_entity_sources("arauco") == {"sources": [{"dataset": "ChileCompra"}, {"dataset": "Lobby"}]}
    assert engine.get_entity_documents("arauco") == [
        {
            "id": "doc-1",
            "title": "Servicio de Salud Arauco documento oficial",
            "summary": "Documento del expediente",
            "source": "Senado",
            "related_expediente_target": "Servicio de Salud Arauco",
        }
    ]
    assert engine.get_entity_events("arauco")["current_topics"] == [{"id": "topic-1", "title": "Nueva compra publica", "source": "ChileCompra Connector"}]
    assert engine.get_entity_relationships("arauco")["summary"] == "Conexion demo."
    assert engine.get_entity_knowledge("arauco") == {"summary": "Conocimiento"}


def test_build_entity_snapshot_groups_dossier_sections_and_coverage(monkeypatch) -> None:
    _patch_entity_engine_services(monkeypatch)

    snapshot = entity_engine.build_entity_snapshot("arauco")

    assert snapshot.found is True
    assert snapshot.entity["name"] == "SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO"
    assert "Servicio de Salud Arauco" in snapshot.aliases
    assert snapshot.contracts == snapshot.purchases
    assert len(snapshot.contracts) == 2
    assert snapshot.suppliers[0]["title"] == "ACME TECNOLOGIAS SPA"
    assert snapshot.people
    assert snapshot.companies
    assert snapshot.meetings[0]["counterparty_name"] == "ACME TECNOLOGIAS SPA"
    assert snapshot.documents[0]["id"] == "doc-1"
    assert snapshot.publications[0]["id"] == "pub-1"
    assert snapshot.evidence[0]["dataset"] == "ChileCompra"
    assert snapshot.relationships["summary"] == "Conexion demo."
    assert snapshot.timeline["years"][0]["events"][0]["id"] == "ev-1"
    assert snapshot.events["current_topics"][0]["id"] == "topic-1"
    assert snapshot.source_contributions["sources"][0]["dataset"] == "ChileCompra"
    assert {row["slug"] for row in snapshot.connectors} == {"chilecompra", "lobby", "diario_oficial"}

    coverage = {item.source: item.available for item in snapshot.coverage}
    assert coverage["ChileCompra"] is True
    assert coverage["Lobby"] is True
    assert coverage["DIPRES"] is True
    assert coverage["Diario Oficial"] is True
    assert coverage["Contralor\u00eda"] is False

    assert snapshot.statistics["contracts"] == 2
    assert snapshot.statistics["meetings"] == 1
    assert snapshot.statistics["documents"] == 1
    assert snapshot.statistics["timeline_events"] == 1
    assert any(insight.id == "recurrent_company" for insight in snapshot.insights)
    assert any(insight.id == "supplier_with_lobby" for insight in snapshot.insights)
    assert any(insight.id == "documented_timeline" for insight in snapshot.insights)
    assert any(insight.severity == "coverage" for insight in snapshot.insights)
    assert snapshot.to_dict()["coverage"][0]["source"] == "ChileCompra"


def test_entity_snapshot_handles_missing_entity(monkeypatch) -> None:
    monkeypatch.setattr(entity_engine.app_services, "resolve_investigation_target", lambda target: {"found": False, "entity_id": "", "entity_name": target})
    monkeypatch.setattr(entity_engine.app_services, "get_investigation", lambda entity_id: {"found": False, "entity_id": entity_id})
    monkeypatch.setattr(entity_engine.app_services, "get_knowledge_documents", lambda: [])
    monkeypatch.setattr(entity_engine.app_services, "get_current_topics", lambda limit=10: [])
    monkeypatch.setattr(entity_engine.app_services, "get_data_ecosystem", lambda: {"sources": []})

    snapshot = entity_engine.EntityEngine().build_entity_snapshot("missing")

    assert snapshot.found is False
    assert snapshot.overview["found"] is False
    assert snapshot.statistics["documents"] == 0
    assert all(item.available is False for item in snapshot.coverage)


def test_relationship_discovery_graph_classifies_edges_and_confidence(monkeypatch) -> None:
    _patch_entity_engine_services(monkeypatch)

    graph = entity_engine.EntityEngine().get_entity_relationship_graph("arauco")

    assert graph["entity_label"] == "SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO"
    assert graph["summary"]["nodes"] >= 7
    assert graph["summary"]["direct"] >= 1
    assert graph["summary"]["secondary"] >= 1
    assert graph["summary"]["documental"] >= 1
    assert graph["summary"]["temporal"] >= 1

    edges = graph["edges"]
    classifications = {edge["classification"] for edge in edges}
    relationship_types = {edge["relationship_type"] for edge in edges}

    assert {"direct", "secondary", "documental", "temporal"}.issubset(classifications)
    assert "HAS_PURCHASE" in relationship_types
    assert "HAS_LOBBY_MEETING" in relationship_types
    assert "MENTIONED_IN_DOCUMENT" in relationship_types
    assert "HAS_TIMELINE_EVENT" in relationship_types
    assert all(0.0 < edge["confidence"] <= 0.95 for edge in edges)
    assert any(edge["evidence"] for edge in edges)
    assert any(node["label"] == "ACME TECNOLOGIAS SPA" for node in graph["nodes"])


def test_relationship_discovery_graph_can_be_built_from_snapshot(monkeypatch) -> None:
    _patch_entity_engine_services(monkeypatch)
    engine = entity_engine.EntityEngine()
    snapshot = engine.build_entity_snapshot("arauco")

    graph = engine.build_relationship_graph(snapshot)

    assert graph.entity_label == snapshot.entity["name"]
    assert graph.summary["edges"] == len(graph.edges)
    assert graph.to_dict()["edges"][0]["classification"] in {"direct", "secondary", "documental", "temporal"}


def test_state_graph_builds_navigable_state_model(monkeypatch) -> None:
    _patch_entity_engine_services(monkeypatch)
    engine = entity_engine.EntityEngine()
    snapshot = engine.build_entity_snapshot("arauco")

    graph = engine.build_state_graph(snapshot)
    graph_dict = graph.to_dict()
    main_id = graph.entity_id

    assert graph.entity_label == "SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO"
    assert graph.summary["nodes"] == len(graph.nodes)
    assert graph.summary["edges"] == len(graph.edges)
    assert {"Organismo", "Empresa", "Documento", "Evento", "Fuente"}.issubset({node.node_type for node in graph.nodes})
    assert any(edge.edge_type == "COMPANY_APPEARS_IN_PURCHASES" for edge in graph.edges)
    assert any(edge.edge_type == "EVENT_BELONGS_TO_DOSSIER" for edge in graph.edges)
    assert all(edge.source and edge.target and edge.edge_type for edge in graph.edges)
    assert all(edge.confidence >= 0 for edge in graph.edges)
    assert any(edge.source_connector for edge in graph.edges)
    assert graph_dict["nodes"][0]["id"]

    neighbors = engine.get_neighbors(graph, main_id)
    assert neighbors is not None
    assert any(item["node"]["node_type"] == "Empresa" for item in neighbors)

    connected = engine.get_connected_entities(graph, main_id)
    assert connected is not None
    assert any(node["label"] == "ACME TECNOLOGIAS SPA" for node in connected)

    documents = engine.get_documents_for_node(graph, main_id)
    assert documents is not None
    assert any(node["node_type"] in {"Documento", "Publicacion"} for node in documents)

    events = engine.get_events_for_node(graph, main_id)
    assert events is not None
    assert any(node["node_type"] == "Evento" for node in events)

    sources = engine.get_sources_for_node(graph, main_id)
    assert sources is not None
    assert any(node["node_type"] == "Fuente" for node in sources)


def test_state_graph_shortest_path_and_missing_nodes(monkeypatch) -> None:
    _patch_entity_engine_services(monkeypatch)
    engine = entity_engine.EntityEngine()
    graph = engine.build_state_graph("arauco")

    path = engine.get_shortest_path(graph, graph.entity_id, "acme-tecnologias-spa")

    assert path is not None
    assert path[0]["node"]["id"] == graph.entity_id
    assert path[-1]["node"]["id"] == "acme-tecnologias-spa"
    assert engine.get_neighbors(graph, "missing-node") is None
    assert engine.get_documents_for_node(graph, "missing-node") is None
    assert engine.get_shortest_path(graph, graph.entity_id, "missing-node") is None


def test_state_graph_module_wrapper_returns_state_graph(monkeypatch) -> None:
    _patch_entity_engine_services(monkeypatch)

    graph = entity_engine.build_state_graph("arauco")

    assert isinstance(graph, entity_engine.StateGraph)
    assert graph.summary["nodes"] >= 1

