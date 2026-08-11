from reflex_app.features.laboratory.state import LaboratoryState, REQUIRED_SECTIONS


def test_reading_gate_starts_locked_and_unlocks_after_required_sections():
    state = LaboratoryState()
    assert state.reading_complete is False
    assert state.participation_status == "LOCKED"
    state.visited_sections = list(REQUIRED_SECTIONS)
    state._recalculate_progress()
    assert state.reading_complete is True
    assert state.reading_progress == 100


def test_required_sections_are_approved_order():
    assert REQUIRED_SECTIONS == ("summary", "problem", "evidence", "claims", "hypotheses", "indicators", "sources", "relationships")
