from __future__ import annotations

from datosenorden.maintenance.human_readable import DatasetExplanation
from datosenorden.maintenance.human_readable import EntityExplanation
from datosenorden.maintenance.human_readable import GraphExplanation
from datosenorden.maintenance.human_readable import entity_type_label
from datosenorden.maintenance.human_readable import human_label
from datosenorden.maintenance.human_readable import render_dataset_explanation_text
from datosenorden.maintenance.human_readable import render_entity_explanation_text
from datosenorden.maintenance.human_readable import render_graph_explanation_text


def test_human_label_maps_technical_names() -> None:
    assert human_label("source_record") == "Fuente"
    assert human_label("claim") == "Afirmación verificable"
    assert human_label("relationship_public") == "Relación pública"
    assert human_label("entity") == "Entidad"
    assert human_label("custom_value") == "Custom Value"


def test_entity_type_label_uses_plain_language() -> None:
    assert entity_type_label("PUBLIC_ORGANIZATION") == "organismo público"
    assert entity_type_label("COMPANY") == "proveedor"
    assert entity_type_label("CONTRACT") == "contrato"
    assert entity_type_label("LOBBY_MEETING") == "reunión de lobby"


def test_render_entity_explanation_text_formats_plain_language() -> None:
    report = render_entity_explanation_text(
        EntityExplanation(
            entity_id="11111111-1111-1111-1111-111111111111",
            entity_name="Servicio de Salud Arauco",
            entity_type="PUBLIC_ORGANIZATION",
            public_contracts=4,
            suppliers=3,
            source_names=("ChileCompra",),
        )
    )

    assert "Este organismo aparece en 4 contratos públicos." in report
    assert "Se relaciona con 3 proveedores." in report
    assert "La información proviene de ChileCompra." in report
    assert "¿Qué significa esto?" in report
    assert "Afirmación verificable" in report


def test_render_dataset_explanation_text_formats_counts() -> None:
    report = render_dataset_explanation_text(
        DatasetExplanation(
            name="ChileCompra",
            summary="ChileCompra contiene información de compras públicas.",
            contracts=5,
            organizations=2,
            suppliers=3,
        )
    )

    assert "ChileCompra contiene información de compras públicas." in report
    assert "* 5 contratos" in report
    assert "* 2 organismos" in report
    assert "* 3 proveedores" in report
    assert "¿Qué significa esto?" in report
    assert "Fuente" in report


def test_render_graph_explanation_text_formats_path_and_meaning() -> None:
    report = render_graph_explanation_text(
        GraphExplanation(
            labels=("Presupuesto", "Organización", "Contrato", "Proveedor"),
            meaning="El organismo recibió una asignación presupuestaria y emitió órdenes de compra a proveedores.",
        )
    )

    assert "Este gráfico muestra cómo se conectan las fuentes públicas." in report
    assert "Presupuesto" in report
    assert "→ Organización" in report
    assert "→ Contrato" in report
    assert "→ Proveedor" in report
    assert "Esto significa:" in report
    assert "asignación presupuestaria" in report


def test_render_graph_explanation_text_handles_lobby_neutrally() -> None:
    report = render_graph_explanation_text(
        GraphExplanation(
            labels=("Organismo", "Reunión de lobby", "Proveedor"),
            meaning=(
                "Esta reunión de lobby conecta un organismo público con una contraparte registrada. "
                "La relación no implica irregularidad; solo muestra una reunión registrada o de muestra."
            ),
        )
    )

    assert "Reunión de lobby" in report
    assert "contraparte registrada" in report
    assert "no implica irregularidad" in report
