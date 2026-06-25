from __future__ import annotations

from dataclasses import dataclass

from datosenorden.db.session import SessionLocal
from datosenorden.maintenance.dataset_metadata import dataset_citizen_summary
from datosenorden.maintenance.dataset_metadata import dataset_metadata_for_name
from datosenorden.maintenance.entity_comparison import build_entity_comparison
from datosenorden.maintenance.entity_explorer import get_entity_profile
from datosenorden.maintenance.explanations import relationship_explanation
from datosenorden.maintenance.safe_access import _field


@dataclass(frozen=True)
class InvestigationGraphNode:
    id: str
    label: str
    category: str
    summary: str
    dataset: str | None = None


@dataclass(frozen=True)
class InvestigationGraphEdge:
    source: str
    target: str
    label: str
    meaning: str


def build_investigation_graph(entity_id: str) -> dict[str, object]:
    with SessionLocal() as session:
        profile = get_entity_profile(session, entity_id)

    if profile is None:
        return _empty_graph()

    comparison = build_entity_comparison(entity_id)
    datasets = tuple(str(dataset) for dataset in _field(comparison, "datasets_present", ()))
    nodes: list[InvestigationGraphNode] = [
        InvestigationGraphNode(
            id=f"entity:{profile.entity.id}",
            label=profile.entity.name,
            category="entity",
            summary=f"{profile.entity.name} is the entity at the center of this investigation.",
        )
    ]
    edges: list[InvestigationGraphEdge] = []

    for dataset in datasets:
        metadata = dataset_metadata_for_name(dataset)
        if metadata is None:
            continue
        node_id = f"dataset:{metadata.name}"
        nodes.append(
            InvestigationGraphNode(
                id=node_id,
                label=metadata.name,
                category="dataset",
                summary=dataset_citizen_summary(metadata.name),
                dataset=metadata.name,
            )
        )
        edges.append(
            InvestigationGraphEdge(
                source=node_id,
                target=nodes[0].id,
                label="records",
                meaning=metadata.citizen_summary,
            )
        )

    evidence_nodes: dict[str, str] = {}
    for evidence in profile.evidences:
        node_id = f"evidence:{evidence.id}"
        evidence_nodes[str(evidence.claim_id or evidence.id)] = node_id
        nodes.append(
            InvestigationGraphNode(
                id=node_id,
                label=evidence.title,
                category="evidence",
                summary="Supporting public evidence associated with this investigation.",
            )
        )

    for relationship in profile.relationships:
        node_id = f"relationship:{relationship.id}"
        relation_label = relationship_explanation(relationship.relationship_type)
        nodes.append(
            InvestigationGraphNode(
                id=node_id,
                label=relation_label,
                category="relationship",
                summary=f"Relationship record: {relationship.relationship_type}.",
            )
        )
        edges.append(
            InvestigationGraphEdge(
                source=nodes[0].id,
                target=node_id,
                label="relationship",
                meaning=relation_label,
            )
        )
        evidence_node_id = evidence_nodes.get(relationship.claim_id)
        if evidence_node_id is not None:
            edges.append(
                InvestigationGraphEdge(
                    source=node_id,
                    target=evidence_node_id,
                    label="evidence",
                    meaning="Supporting evidence for this relationship.",
                )
            )

    summary = (
        f"{profile.entity.name} connects {len(datasets)} datasets, "
        f"{len(profile.relationships)} relationships, and {len(profile.evidences)} evidence items."
    )
    return {
        "nodes": [
            {
                "id": node.id,
                "label": node.label,
                "category": node.category,
                "summary": node.summary,
                "dataset": node.dataset,
            }
            for node in nodes
        ],
        "edges": [
            {
                "source": edge.source,
                "target": edge.target,
                "label": edge.label,
                "meaning": edge.meaning,
            }
            for edge in edges
        ],
        "summary": summary,
    }


def _empty_graph() -> dict[str, object]:
    return {"nodes": [], "edges": [], "summary": "No public graph records were found for this entity."}
