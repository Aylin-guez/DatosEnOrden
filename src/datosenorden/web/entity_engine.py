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


def build_entity_snapshot(target: str) -> EntitySnapshot:
    return get_default_entity_engine().build_entity_snapshot(target)


def get_entity_relationship_graph(target: str) -> dict[str, Any]:
    return get_default_entity_engine().get_entity_relationship_graph(target)


def get_default_entity_engine() -> EntityEngine:
    return EntityEngine()
