from __future__ import annotations

from types import SimpleNamespace

from datosenorden.application import public_explore
from datosenorden.application import public_sources
from datosenorden.application.search.service import format_workspace_matches


def test_public_guidance_prefers_real_collection_titles(monkeypatch) -> None:
    rows = {
        "organisms": {"items": [{"title": "Organismo real"}]},
        "companies": {"items": [{"title": "Empresa real"}]},
        "contracts": {"items": [{"title": "Orden real"}]},
    }
    monkeypatch.setattr(public_explore, "public_collection", lambda _session, key: rows.get(key, {"items": []}))

    questions = public_explore.public_guided_questions(object())
    categories = public_explore.public_guided_categories(object())

    assert questions[0]["example_query"] == "Organismo real"
    assert questions[0]["example_authority"] == "REAL"
    assert next(row for row in categories if row["id"] == "procurement")["examples"] == ["Orden real"]
    assert all("Servicio de Salud Arauco" not in str(row) for row in [*questions, *categories])


def test_public_source_catalog_keeps_data_coverage_separate_from_connector_status(monkeypatch) -> None:
    metrics = [
        {
            "source_name": "Senado de Chile",
            "source_label": "Senado de Chile",
            "available_real_records": 2,
            "real_relationships": 0,
        },
        {
            "source_name": "ChileCompra API Mercado Publico",
            "source_label": "ChileCompra",
            "available_real_records": 7,
            "real_relationships": 14,
        },
    ]
    monkeypatch.setattr(public_sources, "build_provenance_snapshot", lambda _session: SimpleNamespace(source_metrics=metrics))

    class Session:
        def execute(self, _query):
            return [
                ("ChileCompra API Mercado Publico", "chilecompra:purchase_order"),
                ("Senado de Chile", "legislature:matter_observation"),
            ]

    catalog = public_sources.public_source_catalog(
        Session(),
        [{"name": "ChileCompra", "connector_status": "active_local_connector"}],
    )

    senate = next(row for row in catalog["sources"] if row["name"] == "Senado de Chile")
    chilecompra = next(row for row in catalog["sources"] if row["name"] == "ChileCompra")
    assert senate["coverage_status"] == "Datos disponibles"
    assert senate["connector_status"] == "Sin conector activo declarado"
    assert chilecompra["connector_status"] == "Conector activo local"
    assert catalog["connector_active_count"] == 1


def test_workspace_format_marks_demo_without_hiding_it_as_real() -> None:
    rows = format_workspace_matches(
        {
            "matches": [
                {
                    "entity_id": "demo-1",
                    "entity_name": "Ejemplo histórico",
                    "datasets": [],
                    "evidence_count": 0,
                    "relationship_count": 0,
                    "classification": "DEMO",
                }
            ]
        }
    )
    assert rows[0]["classification"] == "DEMO"
    assert rows[0]["source_hint"] == "Contenido DEMO (separado de datos incorporados)"
