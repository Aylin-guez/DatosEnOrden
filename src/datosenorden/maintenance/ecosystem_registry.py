from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from datosenorden.maintenance.dataset_registry import list_datasets
from datosenorden.maintenance.source_plugins import get_source_plugins
from datosenorden.maintenance.source_plugins import plugin_concept_names
from datosenorden.maintenance.source_plugins import plugin_relationship_predicates
from datosenorden.maintenance.source_plugins import plugin_status_value


@dataclass(frozen=True)
class SourceCatalogEntry:
    name: str
    slug: str
    status: str
    category: str
    description: str
    coverage: str
    concepts: tuple[str, ...]
    relationships: tuple[str, ...]
    connects_with: tuple[str, ...]
    entities: tuple[str, ...]


@dataclass(frozen=True)
class ConceptNode:
    name: str
    coverage: str
    datasets: tuple[str, ...]
    description: str


@dataclass(frozen=True)
class RoadmapGroup:
    status: str
    title: str
    sources: tuple[str, ...]


@dataclass(frozen=True)
class EcosystemRegistry:
    sources: tuple[SourceCatalogEntry, ...]
    concepts: tuple[ConceptNode, ...]
    roadmap: tuple[RoadmapGroup, ...]


def build_ecosystem_registry(session: Session) -> EcosystemRegistry:
    loaded = {row.slug: row for row in list_datasets(session)}
    sources: list[SourceCatalogEntry] = []
    for plugin in get_source_plugins():
        summary = _loaded_summary_for_plugin(loaded, plugin.id)
        status = plugin_status_value(plugin)
        coverage = plugin.coverage.level
        if summary is not None and summary.health == "active":
            status = "active"
            coverage = "covered"
        elif summary is not None and summary.source_records:
            coverage = "partial"
        sources.append(
            SourceCatalogEntry(
                name=plugin.display_name,
                slug=plugin.id,
                status=status,
                category=plugin.category,
                description=plugin.description,
                coverage=coverage,
                concepts=plugin_concept_names(plugin),
                relationships=plugin_relationship_predicates(plugin),
                connects_with=tuple(
                    connected.display_name
                    for connected_id in plugin.compatible_source_ids
                    for connected in get_source_plugins()
                    if connected.id == connected_id
                ),
                entities=tuple(
                    entity_type
                    for concept in plugin.concepts
                    for entity_type in concept.entity_types
                ),
            )
        )
    return EcosystemRegistry(
        sources=tuple(sources),
        concepts=_concept_nodes(tuple(sources)),
        roadmap=_roadmap(tuple(sources)),
    )


def _loaded_summary_for_plugin(loaded: dict[str, object], plugin_id: str):  # noqa: ANN001
    aliases = {
        plugin_id,
        plugin_id.replace("_", "-"),
        plugin_id.replace("_activa", ""),
        "transparencia" if plugin_id == "transparencia_activa" else plugin_id,
        "diario-oficial" if plugin_id == "diario_oficial" else plugin_id,
        "registro_empresas" if plugin_id == "registro_empresas" else plugin_id,
    }
    for alias in aliases:
        if alias in loaded:
            return loaded[alias]
    return None


def sources_by_status(registry: EcosystemRegistry, status: str) -> tuple[SourceCatalogEntry, ...]:
    return tuple(source for source in registry.sources if source.status == status)


def coverage_groups(registry: EcosystemRegistry) -> dict[str, tuple[ConceptNode, ...]]:
    groups = {"covered": [], "partial": [], "future": []}
    for concept in registry.concepts:
        groups.setdefault(concept.coverage, []).append(concept)
    return {key: tuple(value) for key, value in groups.items()}


def _concept_nodes(sources: tuple[SourceCatalogEntry, ...]) -> tuple[ConceptNode, ...]:
    by_concept: dict[str, list[SourceCatalogEntry]] = {}
    for source in sources:
        for concept in source.concepts:
            by_concept.setdefault(concept, []).append(source)

    nodes: list[ConceptNode] = []
    for concept, concept_sources in sorted(by_concept.items()):
        coverage = _concept_coverage(concept_sources)
        datasets = tuple(source.name for source in concept_sources)
        nodes.append(
            ConceptNode(
                name=concept,
                coverage=coverage,
                datasets=datasets,
                description=f"Concepto alimentado por {', '.join(datasets)}.",
            )
        )
    return tuple(nodes)


def _concept_coverage(sources: list[SourceCatalogEntry]) -> str:
    statuses = {source.status for source in sources}
    if statuses and statuses <= {"planned"}:
        return "future"
    if "active" in statuses:
        return "covered"
    return "partial"


def _roadmap(sources: tuple[SourceCatalogEntry, ...]) -> tuple[RoadmapGroup, ...]:
    labels = {
        "active": "Fuentes implementadas",
        "prototype": "Fuentes en desarrollo",
        "planned": "Fuentes planificadas",
    }
    return tuple(
        RoadmapGroup(
            status=status,
            title=labels[status],
            sources=tuple(source.name for source in sources if source.status == status),
        )
        for status in ("active", "prototype", "planned")
    )
