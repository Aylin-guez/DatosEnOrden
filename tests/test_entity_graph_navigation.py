from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID

import datosenorden.maintenance.entity_explorer as entity_explorer
from datosenorden.maintenance.entity_explorer import EntityGraphNodeSummary
from datosenorden.maintenance.entity_explorer import EntityNavigationLink
from datosenorden.maintenance.entity_explorer import EntityNeighborSummary
from datosenorden.maintenance.entity_explorer import EntityRelationshipCount
from datosenorden.maintenance.entity_explorer import EntitySummary
from datosenorden.maintenance.entity_explorer import build_entity_graph
from datosenorden.maintenance.entity_explorer import get_entity_neighbors
from datosenorden.maintenance.entity_explorer import render_entity_graph_html
from datosenorden.maintenance.entity_explorer import render_entity_graph_text
from datosenorden.maintenance.entity_explorer import render_entity_neighbors_text
from datosenorden.maintenance.entity_explorer import render_relationship_summary_text
from datosenorden.maintenance.entity_explorer import summarize_relationship_counts


def _sample_entities() -> tuple[SimpleNamespace, SimpleNamespace, SimpleNamespace]:
    buyer = SimpleNamespace(
        id=UUID("11111111-1111-1111-1111-111111111111"),
        entity_type="PUBLIC_ORGANIZATION",
        name="Direccion de Compras y Contratacion Publica",
        external_id="buyer-1",
    )
    contract = SimpleNamespace(
        id=UUID("22222222-2222-2222-2222-222222222222"),
        entity_type="CONTRACT",
        name="Pasajes aereos",
        external_id="contract-1",
    )
    supplier = SimpleNamespace(
        id=UUID("33333333-3333-3333-3333-333333333333"),
        entity_type="COMPANY",
        name="SKY AIRLINE S.A.",
        external_id="supplier-1",
    )
    return buyer, contract, supplier


def _sample_relationships() -> list[SimpleNamespace]:
    buyer, contract, supplier = _sample_entities()
    return [
        SimpleNamespace(
            id=UUID("44444444-4444-4444-4444-444444444444"),
            relationship_type="ISSUES_PURCHASE_ORDER",
            source_entity_id=buyer.id,
            target_entity_id=contract.id,
            source_entity=buyer,
            target_entity=contract,
        ),
        SimpleNamespace(
            id=UUID("55555555-5555-5555-5555-555555555555"),
            relationship_type="RECEIVES_CONTRACT",
            source_entity_id=supplier.id,
            target_entity_id=contract.id,
            source_entity=supplier,
            target_entity=contract,
        ),
    ]


class _ScalarResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeSession:
    def __init__(self, entity: SimpleNamespace, relationships: list[SimpleNamespace], summary_rows=None):
        self._entity = entity
        self._relationships = relationships
        self._summary_rows = summary_rows or []

    def get(self, model, identity):  # noqa: ANN001
        if identity == self._entity.id:
            return self._entity
        for relationship in self._relationships:
            if identity == relationship.source_entity.id:
                return relationship.source_entity
            if identity == relationship.target_entity.id:
                return relationship.target_entity
        return None

    def scalars(self, statement):  # noqa: ANN001
        return _ScalarResult(self._relationships)

    def execute(self, statement):  # noqa: ANN001
        return _ScalarResult(self._summary_rows)


def test_get_entity_neighbors_returns_direct_neighbors(monkeypatch) -> None:
    buyer, _, _ = _sample_entities()
    session = _FakeSession(buyer, _sample_relationships())

    monkeypatch.setattr(
        entity_explorer,
        "_load_entity_relationships",
        lambda session, entity_id: [  # noqa: ARG005
            relationship
            for relationship in _sample_relationships()
            if relationship.source_entity_id == entity_id or relationship.target_entity_id == entity_id
        ],
    )
    neighbors = get_entity_neighbors(session, str(buyer.id))

    assert neighbors is not None
    assert len(neighbors) == 1
    neighbor = neighbors[0]
    assert neighbor.relationship_type == "ISSUES_PURCHASE_ORDER"
    assert neighbor.direction == "outgoing"
    assert neighbor.neighbor.entity_type == "CONTRACT"
    assert neighbor.profile_link.href == "profiles/22222222-2222-2222-2222-222222222222.html"


def test_build_entity_graph_traverses_without_cycles(monkeypatch) -> None:
    buyer, _, _ = _sample_entities()
    session = _FakeSession(buyer, _sample_relationships())

    monkeypatch.setattr(
        entity_explorer,
        "_load_entity_relationships",
        lambda session, entity_id: [  # noqa: ARG005
            relationship
            for relationship in _sample_relationships()
            if relationship.source_entity_id == entity_id or relationship.target_entity_id == entity_id
        ],
    )
    graph = build_entity_graph(session, str(buyer.id), depth=2)

    assert graph is not None
    assert graph.entity.entity_type == "PUBLIC_ORGANIZATION"
    assert len(graph.children) == 1
    contract_node = graph.children[0]
    assert contract_node.entity.entity_type == "CONTRACT"
    assert contract_node.via_relationship_type == "ISSUES_PURCHASE_ORDER"
    assert len(contract_node.children) == 1
    supplier_node = contract_node.children[0]
    assert supplier_node.entity.entity_type == "COMPANY"
    assert supplier_node.via_relationship_type == "RECEIVES_CONTRACT"
    assert supplier_node.children == ()


def test_build_entity_graph_from_budget_root_shows_cross_dataset_chain(monkeypatch) -> None:
    budget = SimpleNamespace(
        id=UUID("66666666-6666-6666-6666-666666666666"),
        entity_type="BUDGET",
        name="DIPRES budget 2026 - SERVICIO DE SALUD ARAUCO",
        external_id="dipres-budget-2026-servicio-de-salud-arauco",
    )
    buyer, contract, supplier = _sample_entities()
    relationships = [
        SimpleNamespace(
            id=UUID("77777777-7777-7777-7777-777777777777"),
            relationship_type="BUDGET_ALLOCATED_TO",
            source_entity_id=budget.id,
            target_entity_id=buyer.id,
            source_entity=budget,
            target_entity=buyer,
        ),
        SimpleNamespace(
            id=UUID("44444444-4444-4444-4444-444444444444"),
            relationship_type="ISSUES_PURCHASE_ORDER",
            source_entity_id=buyer.id,
            target_entity_id=contract.id,
            source_entity=buyer,
            target_entity=contract,
        ),
        SimpleNamespace(
            id=UUID("55555555-5555-5555-5555-555555555555"),
            relationship_type="RECEIVES_CONTRACT",
            source_entity_id=supplier.id,
            target_entity_id=contract.id,
            source_entity=supplier,
            target_entity=contract,
        ),
    ]
    session = _FakeSession(budget, relationships)

    monkeypatch.setattr(
        entity_explorer,
        "_load_entity_relationships",
        lambda session, entity_id: [  # noqa: ARG005
            relationship
            for relationship in relationships
            if relationship.source_entity_id == entity_id or relationship.target_entity_id == entity_id
        ],
    )
    graph = build_entity_graph(session, str(budget.id), depth=3)

    assert graph is not None
    assert graph.entity.entity_type == "BUDGET"
    assert len(graph.children) == 1
    org_node = graph.children[0]
    assert org_node.entity.entity_type == "PUBLIC_ORGANIZATION"
    assert org_node.via_relationship_type == "BUDGET_ALLOCATED_TO"
    assert len(org_node.children) == 1
    contract_node = org_node.children[0]
    assert contract_node.entity.entity_type == "CONTRACT"
    assert contract_node.via_relationship_type == "ISSUES_PURCHASE_ORDER"
    assert len(contract_node.children) == 1
    supplier_node = contract_node.children[0]
    assert supplier_node.entity.entity_type == "COMPANY"
    assert supplier_node.via_relationship_type == "RECEIVES_CONTRACT"


def test_build_entity_graph_traverses_lobby_node_from_organization(monkeypatch) -> None:
    buyer, _, supplier = _sample_entities()
    lobby_meeting = SimpleNamespace(
        id=UUID("88888888-8888-8888-8888-888888888888"),
        entity_type="LOBBY_MEETING",
        name="Lobby meeting 2026-03-15 - Direccion de Compras / SKY AIRLINE S.A.",
        external_id="lobby-meeting-1",
    )
    relationships = [
        SimpleNamespace(
            id=UUID("99999999-9999-9999-9999-999999999999"),
            relationship_type="ORGANIZATION_HELD_LOBBY_MEETING",
            source_entity_id=buyer.id,
            target_entity_id=lobby_meeting.id,
            source_entity=buyer,
            target_entity=lobby_meeting,
        ),
        SimpleNamespace(
            id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
            relationship_type="COUNTERPARTY_PARTICIPATED_IN_LOBBY",
            source_entity_id=supplier.id,
            target_entity_id=lobby_meeting.id,
            source_entity=supplier,
            target_entity=lobby_meeting,
        ),
    ]
    session = _FakeSession(buyer, relationships)

    monkeypatch.setattr(
        entity_explorer,
        "_load_entity_relationships",
        lambda session, entity_id: [  # noqa: ARG005
            relationship
            for relationship in relationships
            if relationship.source_entity_id == entity_id or relationship.target_entity_id == entity_id
        ],
    )
    graph = build_entity_graph(session, str(buyer.id), depth=2)

    assert graph is not None
    assert graph.entity.entity_type == "PUBLIC_ORGANIZATION"
    lobby_node = graph.children[0]
    assert lobby_node.entity.entity_type == "LOBBY_MEETING"
    assert lobby_node.via_relationship_type == "ORGANIZATION_HELD_LOBBY_MEETING"
    counterparty_node = lobby_node.children[0]
    assert counterparty_node.entity.entity_type == "COMPANY"
    assert counterparty_node.via_relationship_type == "COUNTERPARTY_PARTICIPATED_IN_LOBBY"


def test_render_entity_neighbors_text_lists_links() -> None:
    buyer, contract, _ = _sample_entities()
    neighbor = EntityNeighborSummary(
        relationship_id="44444444-4444-4444-4444-444444444444",
        relationship_type="ISSUES_PURCHASE_ORDER",
        direction="outgoing",
        neighbor=EntitySummary(
            id=str(contract.id),
            entity_type=contract.entity_type,
            name=contract.name,
            external_id=contract.external_id,
        ),
        source_entity=EntitySummary(
            id=str(buyer.id),
            entity_type=buyer.entity_type,
            name=buyer.name,
            external_id=buyer.external_id,
        ),
        target_entity=EntitySummary(
            id=str(contract.id),
            entity_type=contract.entity_type,
            name=contract.name,
            external_id=contract.external_id,
        ),
        profile_link=EntityNavigationLink(label="entity_profile", href="profiles/22222222-2222-2222-2222-222222222222.html"),
        graph_link=EntityNavigationLink(label="entity_graph", href="graph_exports/entity_22222222-2222-2222-2222-222222222222.html"),
    )

    report = render_entity_neighbors_text(
        EntitySummary(
            id=str(buyer.id),
            entity_type=buyer.entity_type,
            name=buyer.name,
            external_id=buyer.external_id,
        ),
        (neighbor,),
    )

    assert "entity:" in report
    assert "neighbors:" in report
    assert "relationship=ISSUES_PURCHASE_ORDER" in report
    assert "profile_link=profiles/22222222-2222-2222-2222-222222222222.html" in report


def test_render_entity_graph_text_contains_tree() -> None:
    buyer, _, _ = _sample_entities()
    graph = EntityGraphNodeSummary(
        entity=EntitySummary(
            id=str(buyer.id),
            entity_type=buyer.entity_type,
            name=buyer.name,
            external_id=buyer.external_id,
        ),
        via_relationship_type=None,
        via_direction=None,
        children=(
            EntityGraphNodeSummary(
                entity=EntitySummary(
                    id="22222222-2222-2222-2222-222222222222",
                    entity_type="CONTRACT",
                    name="Pasajes aereos",
                    external_id="contract-1",
                ),
                via_relationship_type="ISSUES_PURCHASE_ORDER",
                via_direction="outgoing",
                children=(),
            ),
        ),
    )

    report = render_entity_graph_text(graph, depth=1)

    assert "entity graph: depth=1" in report
    assert "PUBLIC_ORGANIZATION" in report
    assert "CONTRACT" in report
    assert "ISSUES_PURCHASE_ORDER" in report


def test_render_entity_graph_html_contains_nodes_and_relationships() -> None:
    buyer, _, _ = _sample_entities()
    graph = EntityGraphNodeSummary(
        entity=EntitySummary(
            id=str(buyer.id),
            entity_type=buyer.entity_type,
            name=buyer.name,
            external_id=buyer.external_id,
        ),
        via_relationship_type=None,
        via_direction=None,
        children=(
            EntityGraphNodeSummary(
                entity=EntitySummary(
                    id="22222222-2222-2222-2222-222222222222",
                    entity_type="CONTRACT",
                    name="Pasajes aereos",
                    external_id="contract-1",
                ),
                via_relationship_type="ISSUES_PURCHASE_ORDER",
                via_direction="outgoing",
                children=(),
            ),
        ),
    )

    html = render_entity_graph_html(graph, depth=1)

    assert "<!doctype html>" in html
    assert "PUBLIC_ORGANIZATION" in html
    assert "ISSUES_PURCHASE_ORDER" in html
    assert "¿Qué significa esto?" in html
    assert 'class="node root"' in html
    assert 'class="edge"' in html


def test_render_relationship_summary_text_orders_rows() -> None:
    report = render_relationship_summary_text(
        (
            EntityRelationshipCount(relationship_type="RECEIVES_CONTRACT", count=2),
            EntityRelationshipCount(relationship_type="ISSUES_PURCHASE_ORDER", count=5),
        )
    )

    assert "relationship_summary:" in report
    assert "RECEIVES_CONTRACT = 2" in report
    assert "ISSUES_PURCHASE_ORDER = 5" in report


def test_summarize_relationship_counts_formats_rows() -> None:
    session = _FakeSession(_sample_entities()[0], _sample_relationships(), summary_rows=[("ISSUES_PURCHASE_ORDER", 3), ("RECEIVES_CONTRACT", 2)])

    rows = summarize_relationship_counts(session)

    assert rows == (
        EntityRelationshipCount(relationship_type="ISSUES_PURCHASE_ORDER", count=3),
        EntityRelationshipCount(relationship_type="RECEIVES_CONTRACT", count=2),
    )
