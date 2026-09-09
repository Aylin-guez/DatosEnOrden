from __future__ import annotations

import inspect
from pathlib import Path

from reflex_app.features.search import components as search_components
from reflex_app.features.search.state import SearchState


def test_explore_is_bounded_and_orders_catalog_before_guided_questions() -> None:
    source = inspect.getsource(search_components.guided_discovery_panel)
    assert source.index('"Expedientes disponibles"') < source.index('"Preguntas guiadas"')
    assert 'href="/expedientes"' in source
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
