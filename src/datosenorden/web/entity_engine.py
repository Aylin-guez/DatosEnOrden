"""Entity facade over the existing web service layer.

This module owns no persistence, schema, ETL, or UI logic. It only composes
existing app_services responses into a single citizen-facing entity snapshot.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any
import unicodedata

from datosenorden.web import app_services


COVERAGE_SOURCES = (
    "ChileCompra",
    "Lobby",
    "InfoLobby",
    "Diario Oficial",
    "Contralor\u00eda",
    "DIPRES",
    "Congreso",
)


@dataclass(frozen=True)
class EntityCoverageItem:
    source: str
    available: bool
    reason: str


@dataclass(frozen=True)
class EntityInsight:
    id: str
    title: str
    detail: str
    severity: str = "info"


@dataclass(frozen=True)
class RelationshipGraphNode:
    id: str
    label: str
    node_type: str
    sources: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RelationshipGraphEdge:
    id: str
    source: str
    target: str
    relationship_type: str
    classification: str
    confidence: float
    evidence: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EntityRelationshipGraph:
    entity_id: str
    entity_label: str
    nodes: list[RelationshipGraphNode] = field(default_factory=list)
    edges: list[RelationshipGraphEdge] = field(default_factory=list)
    summary: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class StateGraphNode:
    id: str
    label: str
    node_type: str
    sources: list[str] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StateGraphEdge:
    id: str
    source: str
    target: str
    edge_type: str
    evidence: list[dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    source_connector: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StateGraph:
    entity_id: str
    entity_label: str
    nodes: list[StateGraphNode] = field(default_factory=list)
    edges: list[StateGraphEdge] = field(default_factory=list)
    summary: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EntitySnapshot:
    target: str
    found: bool
    entity: dict[str, Any]
    aliases: list[str] = field(default_factory=list)
    overview: dict[str, Any] = field(default_factory=dict)
    related_organizations: list[dict[str, Any]] = field(default_factory=list)
    people: list[dict[str, Any]] = field(default_factory=list)
    companies: list[dict[str, Any]] = field(default_factory=list)
    suppliers: list[dict[str, Any]] = field(default_factory=list)
    contracts: list[dict[str, Any]] = field(default_factory=list)
    purchases: list[dict[str, Any]] = field(default_factory=list)
    meetings: list[dict[str, Any]] = field(default_factory=list)
    documents: list[dict[str, Any]] = field(default_factory=list)
    publications: list[dict[str, Any]] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    relationships: dict[str, Any] = field(default_factory=dict)
    timeline: dict[str, Any] = field(default_factory=dict)
    events: dict[str, Any] = field(default_factory=dict)
    sources: dict[str, Any] = field(default_factory=dict)
    source_contributions: dict[str, Any] = field(default_factory=dict)
    connectors: list[dict[str, Any]] = field(default_factory=list)
    coverage: list[EntityCoverageItem] = field(default_factory=list)
    insights: list[EntityInsight] = field(default_factory=list)
    statistics: dict[str, int] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EntityEngine:
    """Facade that centralizes entity lookups without owning engine logic."""

    def get_entity(self, target: str) -> dict[str, Any]:
        return app_services.resolve_investigation_target(target)

    def build_entity_snapshot(self, target: str) -> EntitySnapshot:
        resolution = self.get_entity(target)
        entity_id = str(resolution.get("entity_id", target)) if resolution.get("found", False) else target
        investigation = app_services.get_investigation(entity_id)
        if not investigation.get("found", False) and entity_id != target:
            investigation = app_services.get_investigation(target)

        found = bool(investigation.get("found", False))
        resolved_entity_id = str(investigation.get("entity", {}).get("id") or entity_id)
        timeline = app_services.get_investigation_timeline(resolved_entity_id) if found else {}
        sources = app_services.get_source_trace(resolved_entity_id) if found else {"sources": []}
        source_contributions = app_services.get_source_contributions(resolved_entity_id) if found else {"sources": []}
        documents = self._documents_for_target(target, resolution)
        events = self._events_for_snapshot(timeline)
        ecosystem = app_services.get_data_ecosystem()
        connectors = self._connector_rows(ecosystem)
        coverage = self._coverage(investigation, sources, documents, events, connectors)

        contracts = _as_list(investigation.get("contracts_compras", []))
        meetings = _as_list(investigation.get("lobby", []))
        relationships = investigation.get("connections", {}) if isinstance(investigation.get("connections", {}), dict) else {}
        publications = self._publications(documents, investigation)
        evidence = _as_list(investigation.get("evidence", []))
        related_organizations = self._related_by_kind(relationships, ("organismo", "servicio", "ministerio", "hospital"))
        people = self._people(investigation, relationships)
        companies = self._companies(investigation, relationships)
        suppliers = self._suppliers(contracts, companies)
        statistics = self._statistics(
            investigation=investigation,
            relationships=relationships,
            contracts=contracts,
            meetings=meetings,
            documents=documents,
            publications=publications,
            evidence=evidence,
            sources=sources,
            events=events,
        )
        insights = self._insights(
            contracts=contracts,
            meetings=meetings,
            documents=documents,
            timeline=timeline,
            coverage=coverage,
            companies=companies,
            suppliers=suppliers,
            events=events,
        )

        return EntitySnapshot(
            target=target,
            found=found,
            entity=investigation.get("entity", resolution if isinstance(resolution, dict) else {}),
            aliases=self._aliases(resolution, investigation),
            overview=self._overview(investigation, resolution),
            related_organizations=related_organizations,
            people=people,
            companies=companies,
            suppliers=suppliers,
            contracts=contracts,
            purchases=contracts,
            meetings=meetings,
            documents=documents,
            publications=publications,
            evidence=evidence,
            relationships=relationships,
            timeline=timeline,
            events=events,
            sources=sources,
            source_contributions=source_contributions,
            connectors=connectors,
            coverage=coverage,
            insights=insights,
            statistics=statistics,
            raw={"resolution": resolution, "investigation": investigation},
        )

    def get_entity_overview(self, target: str) -> dict[str, Any]:
        return self.build_entity_snapshot(target).overview

    def get_entity_summary(self, target: str) -> dict[str, Any]:
        snapshot = self.build_entity_snapshot(target)
        return {
            "found": snapshot.found,
            "entity": snapshot.entity,
            "summary": snapshot.overview.get("summary", ""),
            "metrics": snapshot.overview.get("metrics", []),
            "datasets": snapshot.overview.get("datasets", []),
        }

    def get_entity_documents(self, target: str) -> list[dict[str, Any]]:
        return self.build_entity_snapshot(target).documents

    def get_entity_sources(self, target: str) -> dict[str, Any]:
        return self.build_entity_snapshot(target).sources

    def get_entity_relationships(self, target: str) -> dict[str, Any]:
        return self.build_entity_snapshot(target).relationships

    def get_entity_events(self, target: str) -> dict[str, Any]:
        return self.build_entity_snapshot(target).events

    def get_entity_statistics(self, target: str) -> dict[str, int]:
        return self.build_entity_snapshot(target).statistics

    def get_entity_relationship_graph(self, target: str) -> dict[str, Any]:
        return self.build_relationship_graph(self.build_entity_snapshot(target)).to_dict()

    def build_state_graph(self, target: str | EntitySnapshot) -> StateGraph:
        snapshot = target if isinstance(target, EntitySnapshot) else self.build_entity_snapshot(str(target))
        relationship_graph = self.build_relationship_graph(snapshot)
        nodes: dict[str, StateGraphNode] = {}
        edges: dict[str, StateGraphEdge] = {}

        for node in relationship_graph.nodes:
            self._add_state_node(
                nodes,
                node.id,
                node.label,
                _state_node_type(node.node_type, node.label),
                sources=node.sources,
                metadata={**node.metadata, "relationship_graph_node_type": node.node_type},
            )
        for edge in relationship_graph.edges:
            self._add_state_edge(
                edges,
                edge.source,
                edge.target,
                edge.relationship_type,
                edge.evidence,
                edge.confidence,
                _source_connector(edge.evidence, edge.metadata),
                {**edge.metadata, "classification": edge.classification},
            )

        main_id = relationship_graph.entity_id
        for source in snapshot.connectors:
            source_id = _node_id(f"source:{source.get('slug') or source.get('source')}")
            self._add_state_node(
                nodes,
                source_id,
                str(source.get("source") or source.get("slug") or "Fuente"),
                "Fuente",
                sources=[str(source.get("source") or source.get("slug") or "")],
                metadata=source,
            )
            self._add_state_edge(edges, source_id, main_id, "SOURCE_CONTRIBUTES_TO_ENTITY", [], 0.6, str(source.get("slug", "")), source)

        for purchase in snapshot.purchases:
            supplier = str(purchase.get("supplier") or purchase.get("supplier_name") or purchase.get("company_name") or "").strip()
            if supplier:
                supplier_id = _node_id(supplier)
                self._add_state_node(nodes, supplier_id, supplier, "Empresa", sources=_sources_from_row(purchase), evidence=_row_evidence(purchase, snapshot.evidence), metadata=purchase)
                self._add_state_edge(edges, supplier_id, main_id, "COMPANY_APPEARS_IN_PURCHASES", _row_evidence(purchase, snapshot.evidence), 0.82, _source_connector(_row_evidence(purchase, snapshot.evidence), purchase), purchase)

        for meeting in snapshot.meetings:
            counterparty = str(meeting.get("counterparty_name") or meeting.get("person_name") or meeting.get("company_name") or "").strip()
            if counterparty:
                counterparty_id = _node_id(counterparty)
                self._add_state_node(nodes, counterparty_id, counterparty, "Persona", sources=_sources_from_row(meeting), evidence=_row_evidence(meeting, snapshot.evidence), metadata=meeting)
                self._add_state_edge(edges, counterparty_id, main_id, "PERSON_APPEARS_IN_LOBBY_MEETING", _row_evidence(meeting, snapshot.evidence), 0.78, _source_connector(_row_evidence(meeting, snapshot.evidence), meeting), meeting)

        for publication in snapshot.publications:
            publication_id = _node_id(publication.get("id") or publication.get("title") or publication.get("name"))
            self._add_state_node(nodes, publication_id, str(publication.get("title") or publication.get("name") or "Publicacion"), "Publicacion", sources=_sources_from_row(publication), evidence=_row_evidence(publication, snapshot.evidence), metadata=publication)
            if _contains_any(publication, ("cargo", "nombramiento", "office", "role")):
                role_label = str(publication.get("office_name") or publication.get("role") or publication.get("title") or "Cargo mencionado")
                role_id = _node_id(role_label)
                self._add_state_node(nodes, role_id, role_label, "Cargo", sources=_sources_from_row(publication), evidence=_row_evidence(publication, snapshot.evidence), metadata=publication)
                self._add_state_edge(edges, publication_id, role_id, "PUBLICATION_REFERENCES_ROLE", _row_evidence(publication, snapshot.evidence), 0.76, _source_connector(_row_evidence(publication, snapshot.evidence), publication), publication)
                self._add_state_edge(edges, role_id, main_id, "ROLE_BELONGS_TO_ORGANIZATION", _row_evidence(publication, snapshot.evidence), 0.72, _source_connector(_row_evidence(publication, snapshot.evidence), publication), publication)

        for document in snapshot.documents:
            document_id = _node_id(document.get("id") or document.get("title") or document.get("name"))
            if _contains_any(document, ("ley", "law")):
                law_label = _law_label(document)
                law_id = _node_id(law_label)
                self._add_state_node(nodes, law_id, law_label, "Ley", sources=_sources_from_row(document), evidence=_row_evidence(document, snapshot.evidence), metadata=document)
                self._add_state_edge(edges, document_id, law_id, "DOCUMENT_CITES_LAW", _row_evidence(document, snapshot.evidence), 0.7, _source_connector(_row_evidence(document, snapshot.evidence), document), document)

        for event in snapshot.events.get("timeline_events", []) + snapshot.events.get("current_topics", []) if isinstance(snapshot.events, dict) else []:
            event_id = _node_id(event.get("id") or event.get("title") or event.get("name"))
            self._add_state_node(nodes, event_id, str(event.get("title") or event.get("name") or "Evento"), "Evento", sources=_sources_from_row(event), evidence=_row_evidence(event, snapshot.evidence), metadata=event)
            self._add_state_edge(edges, main_id, event_id, "EVENT_BELONGS_TO_DOSSIER", _row_evidence(event, snapshot.evidence), 0.74, _source_connector(_row_evidence(event, snapshot.evidence), event), event)

        summary = _state_graph_summary(nodes, edges)
        return StateGraph(entity_id=main_id, entity_label=relationship_graph.entity_label, nodes=list(nodes.values()), edges=list(edges.values()), summary=summary)

    def get_state_graph(self, target: str) -> dict[str, Any]:
        return self.build_state_graph(target).to_dict()

    def get_neighbors(self, graph_or_target: StateGraph | str, node_id: str) -> list[dict[str, Any]] | None:
        graph = self._coerce_state_graph(graph_or_target)
        node_ids = {node.id for node in graph.nodes}
        if node_id not in node_ids:
            return None
        neighbors = []
        for edge in graph.edges:
            other_id = edge.target if edge.source == node_id else edge.source if edge.target == node_id else ""
            if other_id:
                node = _state_node_by_id(graph, other_id)
                if node is not None:
                    neighbors.append({"node": asdict(node), "edge": asdict(edge)})
        return neighbors

    def get_connected_entities(self, graph_or_target: StateGraph | str, node_id: str) -> list[dict[str, Any]] | None:
        neighbors = self.get_neighbors(graph_or_target, node_id)
        if neighbors is None:
            return None
        return [item["node"] for item in neighbors if item["node"].get("node_type") not in {"Documento", "Fuente", "Evento"}]

    def get_documents_for_node(self, graph_or_target: StateGraph | str, node_id: str) -> list[dict[str, Any]] | None:
        return self._nodes_for_type(graph_or_target, node_id, {"Documento", "Publicacion", "Ley"})

    def get_events_for_node(self, graph_or_target: StateGraph | str, node_id: str) -> list[dict[str, Any]] | None:
        return self._nodes_for_type(graph_or_target, node_id, {"Evento"})

    def get_sources_for_node(self, graph_or_target: StateGraph | str, node_id: str) -> list[dict[str, Any]] | None:
        return self._nodes_for_type(graph_or_target, node_id, {"Fuente"})

    def get_shortest_path(self, graph_or_target: StateGraph | str, source_node_id: str, target_node_id: str) -> list[dict[str, Any]] | None:
        graph = self._coerce_state_graph(graph_or_target)
        node_ids = {node.id for node in graph.nodes}
        if source_node_id not in node_ids or target_node_id not in node_ids:
            return None
        if source_node_id == target_node_id:
            node = _state_node_by_id(graph, source_node_id)
            return [{"node": asdict(node), "edge": None}] if node is not None else None
        adjacency: dict[str, list[tuple[str, StateGraphEdge]]] = {}
        for edge in graph.edges:
            adjacency.setdefault(edge.source, []).append((edge.target, edge))
            adjacency.setdefault(edge.target, []).append((edge.source, edge))
        queue: list[tuple[str, list[tuple[str, StateGraphEdge | None]]]] = [(source_node_id, [(source_node_id, None)])]
        visited = {source_node_id}
        while queue:
            current, path = queue.pop(0)
            for next_id, edge in adjacency.get(current, []):
                if next_id in visited:
                    continue
                next_path = [*path, (next_id, edge)]
                if next_id == target_node_id:
                    result = []
                    for path_node_id, path_edge in next_path:
                        node = _state_node_by_id(graph, path_node_id)
                        result.append({"node": asdict(node) if node is not None else {"id": path_node_id}, "edge": asdict(path_edge) if path_edge is not None else None})
                    return result
                visited.add(next_id)
                queue.append((next_id, next_path))
        return None

    def build_relationship_graph(self, snapshot: EntitySnapshot) -> EntityRelationshipGraph:
        main_id = _node_id(snapshot.entity.get("id") or snapshot.target or "entity")
        main_label = str(snapshot.entity.get("name") or snapshot.overview.get("entity", {}).get("entity_name") or snapshot.target)
        nodes: dict[str, RelationshipGraphNode] = {
            main_id: RelationshipGraphNode(
                id=main_id,
                label=main_label,
                node_type=str(snapshot.entity.get("entity_type") or snapshot.overview.get("entity_type_label") or "entity"),
                sources=list(snapshot.overview.get("datasets", [])),
                metadata={"primary": True, "found": snapshot.found},
            )
        }
        edges: dict[str, RelationshipGraphEdge] = {}

        for row in snapshot.relationships.get("relationship_cards", []) if isinstance(snapshot.relationships, dict) else []:
            self._add_snapshot_relation(nodes, edges, main_id, row, "direct", "relationship_card", snapshot.evidence)
        for row in snapshot.relationships.get("direct_neighbors", []) if isinstance(snapshot.relationships, dict) else []:
            self._add_snapshot_relation(nodes, edges, main_id, row, "direct", "direct_neighbor", snapshot.evidence)

        for row in snapshot.related_organizations:
            self._add_snapshot_relation(nodes, edges, main_id, row, "direct", "related_organization", snapshot.evidence, relationship_type="RELATED_ORGANIZATION")
        for row in snapshot.people:
            self._add_snapshot_relation(nodes, edges, main_id, row, "secondary", "person", snapshot.evidence, relationship_type="RELATED_PERSON")
        for row in snapshot.companies:
            self._add_snapshot_relation(nodes, edges, main_id, row, "secondary", "company", snapshot.evidence, relationship_type="RELATED_COMPANY")
        for row in snapshot.suppliers:
            self._add_snapshot_relation(nodes, edges, main_id, row, "direct", "supplier", snapshot.evidence, relationship_type="HAS_SUPPLIER")

        for row in snapshot.purchases:
            purchase_node = self._add_row_node(nodes, row, fallback_type="purchase", fallback_label="Compra publica")
            evidence = _row_evidence(row, snapshot.evidence)
            self._add_edge(edges, main_id, purchase_node.id, "HAS_PURCHASE", "direct", evidence, row)
            supplier = str(row.get("supplier") or row.get("supplier_name") or row.get("company_name") or "").strip()
            if supplier:
                supplier_node = self._add_named_node(nodes, supplier, "supplier", row.get("dataset", "ChileCompra"))
                self._add_edge(edges, purchase_node.id, supplier_node.id, "PURCHASE_HAS_SUPPLIER", "direct", evidence, row)

        for row in snapshot.meetings:
            meeting_node = self._add_row_node(nodes, row, fallback_type="meeting", fallback_label="Reunion de lobby")
            evidence = _row_evidence(row, snapshot.evidence)
            self._add_edge(edges, main_id, meeting_node.id, "HAS_LOBBY_MEETING", "direct", evidence, row)
            counterparty = str(row.get("counterparty_name") or row.get("person_name") or row.get("company_name") or "").strip()
            if counterparty:
                counterparty_node = self._add_named_node(nodes, counterparty, "counterparty", row.get("dataset", "Lobby"))
                self._add_edge(edges, meeting_node.id, counterparty_node.id, "MEETING_HAS_COUNTERPARTY", "direct", evidence, row)

        for row in snapshot.documents:
            document_node = self._add_row_node(nodes, row, fallback_type="document", fallback_label="Documento")
            self._add_edge(edges, main_id, document_node.id, "MENTIONED_IN_DOCUMENT", "documental", _row_evidence(row, snapshot.evidence), row)
        for row in snapshot.publications:
            publication_node = self._add_row_node(nodes, row, fallback_type="publication", fallback_label="Publicacion oficial")
            self._add_edge(edges, main_id, publication_node.id, "MENTIONED_IN_PUBLICATION", "documental", _row_evidence(row, snapshot.evidence), row)

        for row in snapshot.events.get("timeline_events", []) if isinstance(snapshot.events, dict) else []:
            event_node = self._add_row_node(nodes, row, fallback_type="event", fallback_label="Evento")
            self._add_edge(edges, main_id, event_node.id, "HAS_TIMELINE_EVENT", "temporal", _row_evidence(row, snapshot.evidence), row)
        for row in snapshot.events.get("current_topics", []) if isinstance(snapshot.events, dict) else []:
            event_node = self._add_row_node(nodes, row, fallback_type="current_event", fallback_label="Evento reciente")
            self._add_edge(edges, main_id, event_node.id, "HAS_RECENT_EVENT", "temporal", _row_evidence(row, snapshot.evidence), row)

        summary = {
            "nodes": len(nodes),
            "edges": len(edges),
            "direct": sum(1 for edge in edges.values() if edge.classification == "direct"),
            "secondary": sum(1 for edge in edges.values() if edge.classification == "secondary"),
            "documental": sum(1 for edge in edges.values() if edge.classification == "documental"),
            "temporal": sum(1 for edge in edges.values() if edge.classification == "temporal"),
        }
        return EntityRelationshipGraph(entity_id=main_id, entity_label=main_label, nodes=list(nodes.values()), edges=list(edges.values()), summary=summary)

    def get_entity_timeline(self, target: str) -> dict[str, Any]:
        return self.build_entity_snapshot(target).timeline

    def get_entity_knowledge(self, target: str) -> dict[str, Any]:
        entity = self.get_entity(target)
        entity_id = str(entity.get("entity_id", target)) if entity.get("found", False) else target
        investigation = app_services.get_investigation(entity_id)
        return investigation.get("knowledge", {}) if investigation.get("found", False) else {}

    def _add_snapshot_relation(self, nodes: dict[str, RelationshipGraphNode], edges: dict[str, RelationshipGraphEdge], main_id: str, row: dict[str, Any], classification: str, source_kind: str, fallback_evidence: list[dict[str, Any]], relationship_type: str | None = None) -> None:
        node = self._add_row_node(nodes, row, fallback_type=str(row.get("type") or row.get("relationship_type") or "entity"), fallback_label="Entidad relacionada")
        relation = relationship_type or str(row.get("relationship_type") or row.get("predicate") or row.get("type") or "RELATED_TO")
        self._add_edge(edges, main_id, node.id, _constant_name(relation), classification, _row_evidence(row, fallback_evidence), {**row, "source_kind": source_kind})

    def _add_row_node(self, nodes: dict[str, RelationshipGraphNode], row: dict[str, Any], *, fallback_type: str, fallback_label: str) -> RelationshipGraphNode:
        label = str(row.get("title") or row.get("name") or row.get("entity_name") or row.get("label") or row.get("id") or fallback_label)
        node_id = _node_id(row.get("id") or row.get("entity_id") or row.get("target_id") or label)
        node = nodes.get(node_id)
        if node is not None:
            return node
        node = RelationshipGraphNode(
            id=node_id,
            label=label,
            node_type=str(row.get("type") or row.get("entity_type") or row.get("record_type") or fallback_type),
            sources=_sources_from_row(row),
            metadata={key: value for key, value in row.items() if key not in {"evidence", "evidence_links", "links"}},
        )
        nodes[node_id] = node
        return node

    def _add_named_node(self, nodes: dict[str, RelationshipGraphNode], label: str, node_type: str, source: Any = "") -> RelationshipGraphNode:
        node_id = _node_id(label)
        node = nodes.get(node_id)
        if node is not None:
            return node
        node = RelationshipGraphNode(id=node_id, label=label, node_type=node_type, sources=[str(source)] if source else [], metadata={})
        nodes[node_id] = node
        return node

    def _add_edge(self, edges: dict[str, RelationshipGraphEdge], source: str, target: str, relationship_type: str, classification: str, evidence: list[dict[str, Any]], metadata: dict[str, Any]) -> None:
        edge_id = f"{source}->{target}:{relationship_type}:{classification}"
        if edge_id in edges:
            return
        edges[edge_id] = RelationshipGraphEdge(
            id=edge_id,
            source=source,
            target=target,
            relationship_type=relationship_type,
            classification=classification,
            confidence=_confidence_from_evidence(evidence, classification),
            evidence=evidence,
            metadata={key: value for key, value in metadata.items() if key not in {"evidence", "evidence_links", "links"}},
        )

    def _coerce_state_graph(self, graph_or_target: StateGraph | str) -> StateGraph:
        return graph_or_target if isinstance(graph_or_target, StateGraph) else self.build_state_graph(str(graph_or_target))

    def _nodes_for_type(self, graph_or_target: StateGraph | str, node_id: str, node_types: set[str]) -> list[dict[str, Any]] | None:
        neighbors = self.get_neighbors(graph_or_target, node_id)
        if neighbors is None:
            return None
        return [item["node"] for item in neighbors if item["node"].get("node_type") in node_types]

    def _add_state_node(self, nodes: dict[str, StateGraphNode], node_id: str, label: str, node_type: str, *, sources: list[str] | None = None, evidence: list[dict[str, Any]] | None = None, metadata: dict[str, Any] | None = None) -> StateGraphNode:
        cleaned_id = _node_id(node_id)
        existing = nodes.get(cleaned_id)
        if existing is not None:
            merged_sources = list(dict.fromkeys([*existing.sources, *(sources or [])]))
            merged_evidence = _unique_dicts([*existing.evidence, *(evidence or [])], "id", limit=20)
            nodes[cleaned_id] = StateGraphNode(existing.id, existing.label, existing.node_type, merged_sources, merged_evidence, {**existing.metadata, **(metadata or {})})
            return nodes[cleaned_id]
        node = StateGraphNode(cleaned_id, label, node_type, list(dict.fromkeys(sources or [])), evidence or [], metadata or {})
        nodes[cleaned_id] = node
        return node

    def _add_state_edge(self, edges: dict[str, StateGraphEdge], source: str, target: str, edge_type: str, evidence: list[dict[str, Any]], confidence: float, source_connector: str, metadata: dict[str, Any]) -> None:
        source_id = _node_id(source)
        target_id = _node_id(target)
        edge_id = f"{source_id}->{target_id}:{edge_type}"
        if edge_id in edges:
            return
        edges[edge_id] = StateGraphEdge(edge_id, source_id, target_id, edge_type, evidence, confidence, source_connector, metadata)

    def _documents_for_target(self, target: str, resolution: dict[str, Any]) -> list[dict[str, Any]]:
        terms = {
            str(target).lower(),
            str(resolution.get("entity_id", "")).lower(),
            str(resolution.get("entity_name", "")).lower(),
        }
        return [document for document in app_services.get_knowledge_documents() if self._matches_terms(document, terms)]

    def _events_for_snapshot(self, timeline: dict[str, Any]) -> dict[str, Any]:
        return {
            "timeline": timeline,
            "current_topics": app_services.get_current_topics(limit=10),
            "timeline_events": self._timeline_events(timeline),
        }

    def _overview(self, investigation: dict[str, Any], resolution: dict[str, Any]) -> dict[str, Any]:
        return {
            "found": bool(investigation.get("found", False)),
            "entity": investigation.get("entity", resolution),
            "summary": investigation.get("narrative_summary") or investigation.get("summary", ""),
            "metrics": investigation.get("compact_metrics", []),
            "datasets": investigation.get("dataset_badges", []),
            "entity_type_label": investigation.get("entity_type_label", ""),
        }

    def _aliases(self, resolution: dict[str, Any], investigation: dict[str, Any]) -> list[str]:
        aliases: list[str] = []
        for key in ("entity_name", "canonical_entity_name", "original_entity_name"):
            value = str(resolution.get(key, "")).strip()
            if value:
                aliases.append(value)
        canonical = resolution.get("canonical", {})
        if isinstance(canonical, dict):
            for key in ("canonical_entity_name", "original_entity_name", "record_label"):
                value = str(canonical.get(key, "")).strip()
                if value:
                    aliases.append(value)
        entity = investigation.get("entity", {})
        if isinstance(entity, dict):
            for key in ("name", "external_id"):
                value = str(entity.get(key, "")).strip()
                if value:
                    aliases.append(value)
        return _unique_dicts([{"value": item} for item in aliases], "value", limit=12, values_only=True)

    def _publications(self, documents: list[dict[str, Any]], investigation: dict[str, Any]) -> list[dict[str, Any]]:
        publications = [doc for doc in documents if _contains_any(doc, ("diario", "publicacion", "publicaci\u00f3n", "publication"))]
        for row in _as_list(investigation.get("timeline", [])):
            if _contains_any(row, ("diario", "publicacion", "publicaci\u00f3n", "publication")):
                publications.append(row)
        return _unique_dicts(publications, "id", limit=20)

    def _related_by_kind(self, relationships: dict[str, Any], tokens: tuple[str, ...]) -> list[dict[str, Any]]:
        candidates = _as_list(relationships.get("relationship_cards", [])) + _as_list(relationships.get("direct_neighbors", []))
        return _unique_dicts([row for row in candidates if _contains_any(row, tokens)], "title", limit=20)

    def _people(self, investigation: dict[str, Any], relationships: dict[str, Any]) -> list[dict[str, Any]]:
        rows = self._related_by_kind(relationships, ("persona", "autoridad", "cargo"))
        for meeting in _as_list(investigation.get("lobby", [])):
            counterparty = str(meeting.get("counterparty_name", "") or meeting.get("person_name", "")).strip()
            if counterparty:
                rows.append({"title": counterparty, "source": "Lobby", "type": "Persona"})
        return _unique_dicts(rows, "title", limit=20)

    def _companies(self, investigation: dict[str, Any], relationships: dict[str, Any]) -> list[dict[str, Any]]:
        rows = self._related_by_kind(relationships, ("empresa", "proveedor", "company", "supplier"))
        rows.extend(_as_list(investigation.get("registro_empresas", [])))
        return _unique_dicts(rows, "title", limit=20)

    def _suppliers(self, contracts: list[dict[str, Any]], companies: list[dict[str, Any]]) -> list[dict[str, Any]]:
        rows = list(companies)
        for contract in contracts:
            supplier = str(contract.get("supplier", "") or contract.get("supplier_name", "") or contract.get("company_name", "")).strip()
            if supplier:
                rows.append({"title": supplier, "source": contract.get("dataset", "ChileCompra"), "type": "Proveedor"})
        return _unique_dicts(rows, "title", limit=20)

    def _statistics(self, *, investigation: dict[str, Any], relationships: dict[str, Any], contracts: list[dict[str, Any]], meetings: list[dict[str, Any]], documents: list[dict[str, Any]], publications: list[dict[str, Any]], evidence: list[dict[str, Any]], sources: dict[str, Any], events: dict[str, Any]) -> dict[str, int]:
        compact = investigation.get("compact_metrics", {}) if isinstance(investigation.get("compact_metrics", {}), dict) else {}
        return {
            "sources": len(investigation.get("dataset_badges", []) or sources.get("sources", [])),
            "relationships": int(compact.get("relationship_count", 0) or len(_as_list(relationships.get("relationship_cards", [])))),
            "evidence": int(compact.get("evidence_count", 0) or len(evidence)),
            "contracts": len(contracts),
            "purchases": len(contracts),
            "meetings": len(meetings),
            "documents": len(documents),
            "publications": len(publications),
            "timeline_events": len(events.get("timeline_events", [])),
            "current_events": len(events.get("current_topics", [])),
        }

    def _coverage(self, investigation: dict[str, Any], sources: dict[str, Any], documents: list[dict[str, Any]], events: dict[str, Any], connectors: list[dict[str, Any]]) -> list[EntityCoverageItem]:
        available_text = " ".join(
            [
                " ".join(str(item) for item in investigation.get("dataset_badges", [])),
                str(sources),
                str(documents),
                str(events),
                str(connectors),
            ]
        )
        normalized = _normalize(available_text)
        coverage: list[EntityCoverageItem] = []
        for source in COVERAGE_SOURCES:
            source_key = _normalize(source)
            aliases = {source_key}
            if source == "InfoLobby":
                aliases.update({"infolobby", "lobby connector"})
            if source == "Congreso":
                aliases.update({"datos abiertos legislativos", "senado", "camara", "congreso"})
            available = any(alias in normalized for alias in aliases)
            coverage.append(
                EntityCoverageItem(
                    source=source,
                    available=available,
                    reason="Informacion disponible en el expediente." if available else f"Informacion aun no disponible desde {source}.",
                )
            )
        return coverage

    def _connector_rows(self, ecosystem: dict[str, Any]) -> list[dict[str, Any]]:
        rows = []
        for source in _as_list(ecosystem.get("sources", [])):
            if source.get("connector_status"):
                rows.append(
                    {
                        "source": source.get("name", source.get("slug", "")),
                        "slug": source.get("slug", ""),
                        "status": source.get("connector_status", ""),
                        "entities": int(source.get("connector_entities", 0) or 0),
                        "relationships": int(source.get("connector_relationships", 0) or 0),
                        "events": int(source.get("connector_events", 0) or 0),
                    }
                )
        return rows

    def _insights(self, *, contracts: list[dict[str, Any]], meetings: list[dict[str, Any]], documents: list[dict[str, Any]], timeline: dict[str, Any], coverage: list[EntityCoverageItem], companies: list[dict[str, Any]], suppliers: list[dict[str, Any]], events: dict[str, Any]) -> list[EntityInsight]:
        insights: list[EntityInsight] = []
        supplier_counts: dict[str, int] = {}
        for contract in contracts:
            supplier = str(contract.get("supplier", "") or contract.get("supplier_name", "") or contract.get("company_name", "")).strip()
            if supplier:
                supplier_counts[supplier] = supplier_counts.get(supplier, 0) + 1
        if any(count > 1 for count in supplier_counts.values()):
            insights.append(EntityInsight("recurrent_company", "Empresa recurrente.", "Una empresa o proveedor aparece en multiples compras."))
        company_names = {_normalize(str(row.get("title", row.get("name", "")))) for row in companies + suppliers}
        meeting_text = _normalize(str(meetings))
        if meetings and any(name and name in meeting_text for name in company_names):
            insights.append(EntityInsight("supplier_with_lobby", "Proveedor con reuniones registradas.", "Una empresa relacionada tambien aparece en registros de lobby disponibles."))
        if documents and self._timeline_events(timeline):
            insights.append(EntityInsight("documented_timeline", "Respaldo documental y seguimiento historico.", "La entidad posee documentos y cronologia consultables."))
        if events.get("current_topics"):
            insights.append(EntityInsight("recent_events", "Eventos recientes disponibles.", "Pulso contiene eventos o actualizaciones relacionadas con fuentes del expediente."))
        for item in coverage:
            if not item.available:
                insights.append(EntityInsight(f"missing_{_normalize(item.source).replace(' ', '_')}", item.reason, "La cobertura marca esta fuente como pendiente.", "coverage"))
                break
        return insights

    @staticmethod
    def _timeline_events(timeline: dict[str, Any]) -> list[dict[str, Any]]:
        if isinstance(timeline.get("events"), list):
            return _as_list(timeline.get("events", []))
        events: list[dict[str, Any]] = []
        for year in _as_list(timeline.get("years", [])):
            events.extend(_as_list(year.get("events", [])))
        return events

    @staticmethod
    def _matches_terms(payload: dict[str, Any], terms: set[str]) -> bool:
        haystack = " ".join(str(payload.get(key, "")) for key in ("id", "title", "summary", "source", "source_label", "official_url", "related_expediente_target")).lower()
        return any(term and term in haystack for term in terms)


def _node_id(value: Any) -> str:
    normalized = _normalize(str(value or "node"))
    return normalized.replace(" ", "-") or "node"


def _constant_name(value: str) -> str:
    normalized = _normalize(value).upper().replace(" ", "_")
    return normalized or "RELATED_TO"


def _sources_from_row(row: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for key in ("source", "dataset", "dataset_name", "source_label"):
        value = row.get(key)
        if value:
            values.append(str(value))
    datasets = row.get("datasets")
    if isinstance(datasets, list):
        values.extend(str(item) for item in datasets if item)
    return list(dict.fromkeys(values))


def _row_evidence(row: dict[str, Any], fallback_evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    for key in ("evidence", "evidence_links", "links"):
        value = row.get(key)
        if isinstance(value, list):
            evidence.extend(item for item in value if isinstance(item, dict))
        elif isinstance(value, dict):
            evidence.append(value)
    evidence_ids = row.get("evidence_ids")
    if isinstance(evidence_ids, list):
        evidence.extend({"id": str(item)} for item in evidence_ids if item)
    if not evidence and fallback_evidence:
        row_source = _normalize(" ".join(_sources_from_row(row)))
        for group in fallback_evidence:
            if row_source and row_source in _normalize(str(group)):
                evidence.append(group)
    if not evidence and any(row.get(key) for key in ("source", "dataset", "url", "href", "id")):
        evidence.append({
            "source": row.get("source") or row.get("dataset") or row.get("source_label") or "snapshot",
            "id": row.get("id") or row.get("entity_id") or row.get("title") or row.get("name") or "snapshot-row",
            "label": row.get("title") or row.get("name") or row.get("label") or "Snapshot row",
            "url": row.get("url") or row.get("href") or row.get("source_url") or "",
        })
    return _unique_dicts(evidence, "id", limit=10)


def _confidence_from_evidence(evidence: list[dict[str, Any]], classification: str) -> float:
    if not evidence:
        return 0.35 if classification == "secondary" else 0.45
    source_count = len({str(item.get("source") or item.get("dataset") or item.get("id") or "") for item in evidence})
    base = {"direct": 0.72, "documental": 0.78, "temporal": 0.68, "secondary": 0.58}.get(classification, 0.55)
    score = base + min(len(evidence), 3) * 0.05 + min(source_count, 2) * 0.04
    return round(min(score, 0.95), 2)


def _as_list(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, tuple):
        return [item for item in value if isinstance(item, dict)]
    return []


def _contains_any(payload: dict[str, Any], tokens: tuple[str, ...]) -> bool:
    haystack = _normalize(str(payload))
    return any(_normalize(token) in haystack for token in tokens)


def _unique_dicts(rows: list[dict[str, Any]], key: str, *, limit: int = 20, values_only: bool = False):  # noqa: ANN201
    seen: set[str] = set()
    output = []
    for row in rows:
        value = str(row.get(key, "")).strip()
        if not value:
            value = str(row).strip()
        normalized = _normalize(value)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        output.append(value if values_only else row)
        if len(output) >= limit:
            break
    return output


def _normalize(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").strip().lower())
    text = "".join(character for character in text if not unicodedata.combining(character))
    return " ".join(text.replace("_", " ").replace("-", " ").split())


def _state_node_type(node_type: str, label: str = "") -> str:
    type_text = _normalize(node_type)
    label_text = _normalize(label)
    text = f"{type_text} {label_text}"
    if any(token in type_text for token in ("document", "documento")):
        return "Documento"
    if any(token in type_text for token in ("publicacion", "publication")):
        return "Publicacion"
    if any(token in type_text for token in ("evento", "event", "topic")):
        return "Evento"
    if any(token in type_text for token in ("fuente", "source", "connector")):
        return "Fuente"
    if any(token in type_text for token in ("ley", "law")):
        return "Ley"
    if any(token in type_text for token in ("compra", "purchase")):
        return "Compra"
    if any(token in type_text for token in ("contract", "contrato")):
        return "Contrato"
    if any(token in type_text for token in ("reunion", "meeting", "lobby")):
        return "Reunion"
    if any(token in type_text for token in ("cargo", "role", "office")):
        return "Cargo"
    if any(token in text for token in ("organismo", "organization", "hospital", "servicio", "ministerio")):
        return "Organismo"
    if any(token in text for token in ("persona", "person", "autoridad")):
        return "Persona"
    if any(token in text for token in ("empresa", "proveedor", "company", "supplier", "counterparty")):
        return "Empresa"
    return "Entidad"


def _source_connector(evidence: list[dict[str, Any]], metadata: dict[str, Any]) -> str:
    for item in evidence:
        for key in ("source", "dataset", "source_connector"):
            value = item.get(key)
            if value:
                return str(value)
    for key in ("source", "dataset", "source_label", "slug"):
        value = metadata.get(key)
        if value:
            return str(value)
    return ""


def _law_label(document: dict[str, Any]) -> str:
    for key in ("law", "law_title", "title", "name"):
        value = str(document.get(key, "")).strip()
        if value and _contains_any({"value": value}, ("ley", "law")):
            return value
    return "Ley citada"


def _state_node_by_id(graph: StateGraph, node_id: str) -> StateGraphNode | None:
    return next((node for node in graph.nodes if node.id == node_id), None)


def _state_graph_summary(nodes: dict[str, StateGraphNode], edges: dict[str, StateGraphEdge]) -> dict[str, int]:
    summary = {"nodes": len(nodes), "edges": len(edges)}
    for node_type in {node.node_type for node in nodes.values()}:
        summary[f"nodes_{_normalize(node_type).replace(' ', '_')}"] = sum(1 for node in nodes.values() if node.node_type == node_type)
    return summary


def build_entity_snapshot(target: str) -> EntitySnapshot:
    return get_default_entity_engine().build_entity_snapshot(target)


def get_entity_relationship_graph(target: str) -> dict[str, Any]:
    return get_default_entity_engine().get_entity_relationship_graph(target)


def build_state_graph(target: str) -> StateGraph:
    return get_default_entity_engine().build_state_graph(target)


def get_default_entity_engine() -> EntityEngine:
    return EntityEngine()
