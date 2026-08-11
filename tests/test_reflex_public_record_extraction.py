from __future__ import annotations

import ast
from pathlib import Path

from reflex.page import DECORATED_PAGES

from reflex_app.app.state import AppState
from reflex_app.features.public_record import pages as public_record_pages
from reflex_app.features.public_record.state import PublicRecordState


ROOT = Path(__file__).resolve().parents[1]
MONOLITH = ROOT / "reflex_app" / "reflex_app.py"

PUBLIC_RECORD_FIELDS = {
    "selected_entity_id",
    "selected_entity_name",
    "entity_name",
    "entity_summary",
    "dataset_badges",
    "evidence_count",
    "relationship_count",
    "relationship_rows",
    "evidence_rows",
    "state_graph_connection_rows",
    "timeline_rows",
    "source_trace_sources",
    "report_available",
    "investigation_status",
    "investigation_loading",
}

PUBLIC_RECORD_HANDLERS = {
    "open_investigation",
    "open_canonical_investigation",
    "load_investigation",
}


def _registered_pages() -> dict[str, tuple[object, dict]]:
    return {kwargs["route"]: (page, kwargs) for page, kwargs in DECORATED_PAGES["reflex_app"]}


def test_public_record_state_is_single_source_for_investigation_fields() -> None:
    for field in PUBLIC_RECORD_FIELDS:
        assert field in PublicRecordState.vars
        assert field not in AppState.vars

    for handler in PUBLIC_RECORD_HANDLERS:
        assert handler in PublicRecordState.event_handlers
        assert handler not in AppState.event_handlers


def test_investigation_route_is_registered_from_public_record_feature() -> None:
    registered = _registered_pages()

    assert len(registered) == 21
    assert registered["/investigation"][0] is public_record_pages.investigation
    assert registered["/investigation"][1]["on_load"].fn is PublicRecordState.load_investigation.fn
    assert registered["/investigation"][1]["title"] == "Expediente - DatosEnOrden"


def test_legacy_appstate_adapters_were_removed_without_owning_fields() -> None:
    source = MONOLITH.read_text(encoding="utf-8")

    assert "def load_investigation" not in source
    assert "def open_canonical_investigation" not in source
    assert "selected_entity_id: str" not in source
    assert "relationship_rows: list[dict]" not in source


def test_public_record_components_use_feature_state() -> None:
    source = (ROOT / "reflex_app" / "features" / "public_record" / "components.py").read_text(encoding="utf-8")

    assert "PublicRecordState.citizen_summary" in source
    assert "PublicRecordState.relationship_rows" in source
    assert "PublicRecordState.state_graph_connection_rows" in source
    assert "AppState.selected_entity_id" not in source


def test_public_record_does_not_own_laboratory() -> None:
    laboratory = ROOT / "reflex_app" / "features" / "laboratory"
    for path in laboratory.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        assert [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
            and node.module
            and node.module.startswith("reflex_app.features.public_record")
        ] == []
