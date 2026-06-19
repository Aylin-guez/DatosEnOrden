from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import sys

from datosenorden.maintenance.entity_explorer import EntityGraphNodeSummary
from datosenorden.maintenance.entity_explorer import EntityNavigationLink
from datosenorden.maintenance.entity_explorer import EntityNeighborSummary
from datosenorden.maintenance.entity_explorer import EntityProfile
from datosenorden.maintenance.entity_explorer import EntityRelationshipCount
from datosenorden.maintenance.entity_explorer import EntitySummary

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import entity_graph
import entity_neighbors
import export_entity_graph
import relationship_summary


def _session_manager(session):
    @contextmanager
    def _manager():
        yield session

    return _manager()


def _sample_profile() -> EntityProfile:
    root = EntitySummary(
        id="11111111-1111-1111-1111-111111111111",
        entity_type="PUBLIC_ORGANIZATION",
        name="Direccion de Compras y Contratacion Publica",
        external_id="buyer-1",
    )
    contract = EntitySummary(
        id="22222222-2222-2222-2222-222222222222",
        entity_type="CONTRACT",
        name="Pasajes aereos",
        external_id="contract-1",
    )
    neighbor = EntityNeighborSummary(
        relationship_id="44444444-4444-4444-4444-444444444444",
        relationship_type="ISSUES_PURCHASE_ORDER",
        direction="outgoing",
        neighbor=contract,
        source_entity=root,
        target_entity=contract,
        profile_link=EntityNavigationLink(label="entity_profile", href="profiles/22222222-2222-2222-2222-222222222222.html"),
        graph_link=EntityNavigationLink(label="entity_graph", href="graph_exports/entity_22222222-2222-2222-2222-222222222222.html"),
    )
    return EntityProfile(
        generated_at=datetime(2026, 6, 18, 12, 30, tzinfo=timezone.utc),
        entity=root,
        claims=(),
        relationships=(),
        evidences=(),
        related_entities=(contract,),
        direct_neighbors=(neighbor,),
        relationship_counts=(EntityRelationshipCount(relationship_type="ISSUES_PURCHASE_ORDER", count=1),),
        navigation_links=(
            EntityNavigationLink(label="profile_html", href="profiles/11111111-1111-1111-1111-111111111111.html"),
            EntityNavigationLink(label="graph_html", href="graph_exports/entity_11111111-1111-1111-1111-111111111111.html"),
        ),
    )


def _sample_graph() -> EntityGraphNodeSummary:
    root = EntitySummary(
        id="11111111-1111-1111-1111-111111111111",
        entity_type="PUBLIC_ORGANIZATION",
        name="Direccion de Compras y Contratacion Publica",
        external_id="buyer-1",
    )
    contract = EntitySummary(
        id="22222222-2222-2222-2222-222222222222",
        entity_type="CONTRACT",
        name="Pasajes aereos",
        external_id="contract-1",
    )
    supplier = EntitySummary(
        id="33333333-3333-3333-3333-333333333333",
        entity_type="COMPANY",
        name="SKY AIRLINE S.A.",
        external_id="supplier-1",
    )
    return EntityGraphNodeSummary(
        entity=root,
        via_relationship_type=None,
        via_direction=None,
        children=(
            EntityGraphNodeSummary(
                entity=contract,
                via_relationship_type="ISSUES_PURCHASE_ORDER",
                via_direction="outgoing",
                children=(
                    EntityGraphNodeSummary(
                        entity=supplier,
                        via_relationship_type="RECEIVES_CONTRACT",
                        via_direction="incoming",
                        children=(),
                    ),
                ),
            ),
        ),
    )


def test_entity_neighbors_script_prints_neighbors(monkeypatch, capsys) -> None:
    monkeypatch.setattr(entity_neighbors, "SessionLocal", lambda: _session_manager(object()))
    monkeypatch.setattr(entity_neighbors, "get_entity_profile", lambda session, entity_id: _sample_profile())

    exit_code = entity_neighbors.main(["--entity-id", "11111111-1111-1111-1111-111111111111"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "entity:" in captured.out
    assert "neighbors:" in captured.out
    assert "relationship=ISSUES_PURCHASE_ORDER" in captured.out
    assert captured.err == ""


def test_entity_graph_script_prints_tree(monkeypatch, capsys) -> None:
    monkeypatch.setattr(entity_graph, "SessionLocal", lambda: _session_manager(object()))
    monkeypatch.setattr(entity_graph, "build_entity_graph", lambda session, entity_id, depth=1: _sample_graph())

    exit_code = entity_graph.main(["--entity-id", "11111111-1111-1111-1111-111111111111", "--depth", "2"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "entity graph: depth=2" in captured.out
    assert "PUBLIC_ORGANIZATION" in captured.out
    assert "CONTRACT" in captured.out
    assert "COMPANY" in captured.out
    assert captured.err == ""


def test_export_entity_graph_script_writes_html(monkeypatch, tmp_path, capsys) -> None:
    output_path = tmp_path / "graph_exports" / "entity_11111111-1111-1111-1111-111111111111.html"
    monkeypatch.setattr(export_entity_graph, "GRAPH_EXPORTS_DIR", tmp_path / "graph_exports")
    monkeypatch.setattr(export_entity_graph, "SessionLocal", lambda: _session_manager(object()))
    monkeypatch.setattr(export_entity_graph, "build_entity_graph", lambda session, entity_id, depth=1: _sample_graph())

    exit_code = export_entity_graph.main(["--entity-id", "11111111-1111-1111-1111-111111111111"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert f"entity_graph_exported: path={output_path.as_posix()}" in captured.out
    html = output_path.read_text(encoding="utf-8")
    assert "PUBLIC_ORGANIZATION" in html
    assert "ISSUES_PURCHASE_ORDER" in html
    assert captured.err == ""


def test_relationship_summary_script_prints_counts(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        relationship_summary,
        "SessionLocal",
        lambda: _session_manager(object()),
    )
    monkeypatch.setattr(
        relationship_summary,
        "summarize_relationship_counts",
        lambda session: (
            EntityRelationshipCount(relationship_type="ISSUES_PURCHASE_ORDER", count=5),
            EntityRelationshipCount(relationship_type="RECEIVES_CONTRACT", count=3),
        ),
    )

    exit_code = relationship_summary.main([])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "relationship_summary:" in captured.out
    assert "ISSUES_PURCHASE_ORDER = 5" in captured.out
    assert "RECEIVES_CONTRACT = 3" in captured.out
    assert captured.err == ""
