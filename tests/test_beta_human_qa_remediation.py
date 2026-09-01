from __future__ import annotations

import inspect
from pathlib import Path

import datosenorden.maintenance.search_workspace as workspace
from reflex_app.features.search import components as search_components
from reflex_app.features.search.state import SearchState


def test_available_catalog_title_terms_are_searchable_with_provenance(monkeypatch) -> None:
    catalog = [
        {
            "id": "EXP-001",
            "title": "Trabajo flexible, protección social e infraestructura pública de confianza",
            "summary": "Hipótesis de laboratorio.",
            "question": "¿Cómo cambia el trabajo?",
            "provenance_class": "DEMO",
            "sources": [],
        },
        {
            "id": "EXP-REAL-RECONSTRUCCION",
            "title": "Para la reconstrucción nacional y el desarrollo económico y social",
            "summary": "Expediente legislativo público.",
            "question": "Reconstrucción nacional.",
            "provenance_class": "REAL",
            "sources": ["Congreso"],
        },
        {
            "id": "EXP-REAL-DATA-PROTECTION-21719",
            "title": "Ley 21.719 sobre protección de datos personales",
            "summary": "Expediente legislativo público.",
            "question": "¿Qué establece la Ley 21.719?",
            "provenance_class": "REAL",
            "sources": ["Congreso"],
        },
        {
            "id": "EXP-REAL-CYBERSECURITY-21663",
            "title": "Ley 21.663 Marco de Ciberseguridad",
            "summary": "Incluye la Agencia Nacional de Ciberseguridad (ANCI).",
            "question": "¿Qué establece la Ley 21.663?",
            "provenance_class": "REAL",
            "sources": ["Congreso"],
        },
    ]
    monkeypatch.setattr(workspace, "list_public_expedient_catalog", lambda: catalog)

    trabajo = workspace._catalog_expedient_matches("trabajo")
    reconstruction_plain = workspace._catalog_expedient_matches("reconstruccion")
    reconstruction_accented = workspace._catalog_expedient_matches("reconstrucción")
    data_protection = workspace._catalog_expedient_matches("Ley 21.719")
    cybersecurity = workspace._catalog_expedient_matches("Ley 21.663")
    anci = workspace._catalog_expedient_matches("ANCI")
    absent = workspace._catalog_expedient_matches("término ciudadano inexistente")

    assert [(row.entity_id, row.classification) for row in trabajo] == [("EXP-001", "DEMO")]
    assert [row.entity_id for row in reconstruction_plain] == ["EXP-REAL-RECONSTRUCCION"]
    assert [row.entity_id for row in reconstruction_accented] == ["EXP-REAL-RECONSTRUCCION"]
    assert [row.entity_id for row in data_protection] == ["EXP-REAL-DATA-PROTECTION-21719"]
    assert [row.entity_id for row in cybersecurity] == ["EXP-REAL-CYBERSECURITY-21663"]
    assert [row.entity_id for row in anci] == ["EXP-REAL-CYBERSECURITY-21663"]
    assert absent == ()


def test_explore_is_bounded_and_orders_catalog_before_guided_questions() -> None:
    source = inspect.getsource(search_components.guided_discovery_panel)
    assert source.index('"Expedientes disponibles"') < source.index('"Preguntas guiadas"')
    assert 'href="/laboratory"' in source
    state_source = inspect.getsource(SearchState._load_public_expedients)
    assert "][:4]" in state_source


def test_public_reflex_configuration_disables_framework_badge() -> None:
    source = Path("rxconfig.py").read_text(encoding="utf-8")
    assert "show_built_with_reflex=False" in source


def test_public_spanish_source_and_canonical_labels_remain_utf8() -> None:
    registry = Path("src/datosenorden/application/canonical_entity_identity/registry.py").read_text(encoding="utf-8")
    for value in (
        "División Logística del Ejército",
        "Dirección de Educación Pública",
        "Félix Bulnes",
    ):
        assert value in registry
    assert "Direcci?n" not in registry
    assert "F?lix" not in registry
