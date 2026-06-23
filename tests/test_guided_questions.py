from __future__ import annotations

from datosenorden.maintenance.guided_questions import get_guided_questions


def test_guided_questions_expose_rule_based_entries() -> None:
    payload = get_guided_questions()

    assert any(question["id"] == "which_official_publications_exist" for question in payload["questions"])
    assert any(category["id"] == "suppliers" for category in payload["categories"])
    forbidden_terms = ("accus", "irregular", "risk", "suspicious", "corrupt", "fraud")
    assert not any(term in str(payload).lower() for term in forbidden_terms)
