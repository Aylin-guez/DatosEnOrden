from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import sys

from datosenorden.maintenance.human_readable import DatasetExplanation
from datosenorden.maintenance.human_readable import EntityExplanation
from datosenorden.maintenance.human_readable import GraphExplanation

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import explain_dataset
import explain_entity
import explain_graph


def _session_manager(session):
    @contextmanager
    def _manager():
        yield session

    return _manager()


def test_explain_entity_script_prints_plain_language(monkeypatch, capsys) -> None:
    monkeypatch.setattr(explain_entity, "SessionLocal", lambda: _session_manager(object()))
    monkeypatch.setattr(
        explain_entity,
        "explain_entity",
        lambda session, entity_id: EntityExplanation(  # noqa: ARG005
            entity_id=entity_id,
            entity_name="Servicio de Salud Arauco",
            entity_type="PUBLIC_ORGANIZATION",
            public_contracts=4,
            suppliers=3,
            source_names=("ChileCompra",),
        ),
    )

    exit_code = explain_entity.main(["--entity-id", "11111111-1111-1111-1111-111111111111"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Este organismo aparece en 4 contratos públicos." in captured.out
    assert "Se relaciona con 3 proveedores." in captured.out
    assert "La información proviene de ChileCompra." in captured.out
    assert "¿Qué significa esto?" in captured.out
    assert captured.err == ""


def test_explain_dataset_script_prints_plain_language(monkeypatch, capsys) -> None:
    monkeypatch.setattr(explain_dataset, "SessionLocal", lambda: _session_manager(object()))
    monkeypatch.setattr(
        explain_dataset,
        "get_dataset_details",
        lambda session, slug: object(),  # noqa: ARG005
    )
    monkeypatch.setattr(
        explain_dataset,
        "explain_dataset",
        lambda details: DatasetExplanation(
            name="ChileCompra",
            summary="ChileCompra contiene información de compras públicas.",
            contracts=5,
            organizations=2,
            suppliers=3,
        ),
    )

    exit_code = explain_dataset.main(["--dataset", "chilecompra"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "ChileCompra contiene información de compras públicas." in captured.out
    assert "* 5 contratos" in captured.out
    assert "* 2 organismos" in captured.out
    assert "¿Qué significa esto?" in captured.out
    assert "Afirmación verificable" in captured.out
    assert captured.err == ""


def test_explain_graph_script_prints_path_and_meaning(monkeypatch, capsys) -> None:
    monkeypatch.setattr(explain_graph, "SessionLocal", lambda: _session_manager(object()))
    monkeypatch.setattr(explain_graph, "build_entity_graph", lambda session, entity_id, depth=3: object())  # noqa: ARG005
    monkeypatch.setattr(
        explain_graph,
        "explain_graph",
        lambda graph: GraphExplanation(
            labels=("Presupuesto", "Organización", "Contrato", "Proveedor"),
            meaning="El organismo recibió una asignación presupuestaria y emitió órdenes de compra a proveedores.",
        ),
    )

    exit_code = explain_graph.main(["--entity-id", "11111111-1111-1111-1111-111111111111"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Este gráfico muestra cómo se conectan las fuentes públicas." in captured.out
    assert "→ Organización" in captured.out
    assert "Esto significa:" in captured.out
    assert "asignación presupuestaria" in captured.out
    assert captured.err == ""
