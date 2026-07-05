from datosenorden.web import entity_engine


def test_entity_engine_facade_delegates_to_web_services(monkeypatch) -> None:
    calls = []

    monkeypatch.setattr(
        entity_engine.app_services,
        "resolve_investigation_target",
        lambda target: {"found": True, "entity_id": "entity-1", "entity_name": "Servicio de Salud Arauco"},
    )
    monkeypatch.setattr(
        entity_engine.app_services,
        "get_investigation",
        lambda entity_id: {
            "found": True,
            "entity": {"id": entity_id, "name": "Servicio de Salud Arauco"},
            "narrative_summary": "Resumen ciudadano",
            "compact_metrics": [{"label": "Compras", "value": "3"}],
            "dataset_badges": ["ChileCompra"],
            "connections": {"relationship_cards": [{"title": "Proveedor"}]},
            "knowledge": {"summary": "Conocimiento"},
        },
    )
    monkeypatch.setattr(
        entity_engine.app_services,
        "get_investigation_timeline",
        lambda entity_id: calls.append(("timeline", entity_id)) or {"years": []},
    )
    monkeypatch.setattr(
        entity_engine.app_services,
        "get_source_trace",
        lambda entity_id: calls.append(("sources", entity_id)) or {"sources": []},
    )
    monkeypatch.setattr(
        entity_engine.app_services,
        "get_knowledge_documents",
        lambda: [
            {"id": "doc-1", "title": "Servicio de Salud Arauco compra publica"},
            {"id": "doc-2", "title": "Otro documento"},
        ],
    )
    monkeypatch.setattr(
        entity_engine.app_services,
        "get_current_topics",
        lambda limit=10: [{"title": "Nueva compra publica"}],
    )

    engine = entity_engine.EntityEngine()

    assert engine.get_entity("arauco")["entity_id"] == "entity-1"
    assert engine.get_entity_summary("arauco")["summary"] == "Resumen ciudadano"
    assert engine.get_entity_timeline("arauco") == {"years": []}
    assert engine.get_entity_sources("arauco") == {"sources": []}
    assert engine.get_entity_documents("arauco") == [
        {"id": "doc-1", "title": "Servicio de Salud Arauco compra publica"}
    ]
    assert engine.get_entity_events("arauco")["current_topics"] == [{"title": "Nueva compra publica"}]
    assert engine.get_entity_relationships("arauco") == {"relationship_cards": [{"title": "Proveedor"}]}
    assert engine.get_entity_knowledge("arauco") == {"summary": "Conocimiento"}
    assert calls == [("timeline", "entity-1"), ("sources", "entity-1"), ("timeline", "entity-1")]
