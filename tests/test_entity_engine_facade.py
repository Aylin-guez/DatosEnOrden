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
    assert {row["slug"] for row in snapshot.connectors} == {"chilecompra", "lobby"}

    coverage = {item.source: item.available for item in snapshot.coverage}
    assert coverage["ChileCompra"] is True
    assert coverage["Lobby"] is True
    assert coverage["DIPRES"] is True
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
