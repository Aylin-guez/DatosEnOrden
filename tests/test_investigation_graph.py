from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID

import datosenorden.maintenance.investigation_graph as investigation_graph


class _SessionContext:
    def __enter__(self):  # noqa: ANN001
        return object()

    def __exit__(self, exc_type, exc, tb):  # noqa: ANN001
        _ = (exc_type, exc, tb)
        return False


def test_build_investigation_graph_returns_nodes_edges_and_summary(monkeypatch) -> None:
    profile = SimpleNamespace(
        entity=SimpleNamespace(id=UUID("11111111-1111-1111-1111-111111111111"), name="Entidad demo", entity_type="PUBLIC_ORGANIZATION"),
        evidences=(
            SimpleNamespace(id="e1", title="Evidencia 1", claim_id="r1"),
            SimpleNamespace(id="e2", title="Evidencia 2", claim_id="r2"),
        ),
        relationships=(
            SimpleNamespace(id="r1", relationship_type="ISSUES_PURCHASE_ORDER", claim_id="r1", related_entity=SimpleNamespace(name="Contrato demo")),
            SimpleNamespace(id="r2", relationship_type="AUTHORITY_ELECTED_TO_OFFICE", claim_id="r2", related_entity=SimpleNamespace(name="Autoridad demo")),
        ),
    )
    monkeypatch.setattr(investigation_graph, "SessionLocal", lambda: _SessionContext())
    monkeypatch.setattr(investigation_graph, "get_entity_profile", lambda session, entity_id: profile)
    monkeypatch.setattr(
        investigation_graph,
        "build_entity_comparison",
        lambda entity_id: {"datasets_present": ["ChileCompra", "SERVEL"]},
    )

    graph = investigation_graph.build_investigation_graph(str(profile.entity.id))

    assert graph["summary"].startswith("Entidad demo connects 2 datasets")
    assert any(node["category"] == "entity" for node in graph["nodes"])
    assert any(node["category"] == "dataset" for node in graph["nodes"])
    assert any(node["category"] == "relationship" for node in graph["nodes"])
    assert any(node["category"] == "evidence" for node in graph["nodes"])
    assert any(edge["label"] == "records" for edge in graph["edges"])
    assert any(edge["label"] == "evidence" for edge in graph["edges"])
