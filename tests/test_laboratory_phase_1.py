from reflex_app.app.state import AppState
from reflex_app.features.laboratory.state import LaboratoryState
from datosenorden.application.laboratory.service import get_expedient, load_expedient_catalog


def test_public_fixture_and_models():
    expedient = get_expedient("EXP-001")
    assert expedient and expedient["id"] == "EXP-001"
    assert any(item["id"] == "HYP-001" for item in expedient["hypotheses"])
    assert "author" not in expedient
    assert all(ind["latest_value"] is None and ind["status"] == "PENDING_DATA" for ind in expedient["indicators"])
    assert load_expedient_catalog()[0]["id"] == "EXP-001"


def test_laboratory_state_is_independent_from_app_state():
    assert not {"catalog_rows", "expedient_id", "active_section", "visited_sections"} & set(AppState.__fields__)
    assert "visited_sections" in LaboratoryState.__fields__
