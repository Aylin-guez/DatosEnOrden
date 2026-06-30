from __future__ import annotations

from datosenorden.maintenance.dataset_registry import DatasetSummary
from datosenorden.maintenance.ecosystem_registry import build_ecosystem_registry
from datosenorden.maintenance.ecosystem_registry import coverage_groups
from datosenorden.maintenance.ecosystem_registry import sources_by_status


def test_ecosystem_registry_groups_sources_concepts_and_roadmap(monkeypatch) -> None:
    monkeypatch.setattr(
        "datosenorden.maintenance.ecosystem_registry.list_datasets",
        lambda session: (
            DatasetSummary("chilecompra", "ChileCompra", 10, 20, 30, 40, 50, "active", False),
            DatasetSummary("lobby", "Lobby", 3, 4, 5, 6, 7, "partially_loaded", False),
        ),
    )

    registry = build_ecosystem_registry(object())

    active = sources_by_status(registry, "active")
    prototype = sources_by_status(registry, "prototype")
    coverage = coverage_groups(registry)

    assert any(source.name == "ChileCompra" for source in active)
    assert any(source.name == "Lobby" for source in prototype)
    assert any(source.name == "Diario Oficial" for source in prototype)
    assert any(source.name == "Registro Empresas" for source in prototype)
    assert any(source.name == "Declaraciones de Intereses" for source in prototype)
    assert any(source.slug == "sanciones_procedimientos" for source in prototype)
    assert any(concept.name == "Contrato" for concept in coverage["covered"])
    assert any(concept.name == "Reunion" for concept in coverage["partial"])
    assert registry.roadmap[0].title == "Fuentes implementadas"
    assert "ChileCompra" in registry.roadmap[0].sources
