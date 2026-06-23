from __future__ import annotations

from datosenorden.maintenance.discovery_cases import get_discovery_cases


def test_discovery_cases_expose_guided_neutral_examples() -> None:
    payload = get_discovery_cases()

    assert "cases" in payload
    ids = [case["id"] for case in payload["cases"]]
    assert "public_spending" in ids
    assert "public_roles" in ids
    assert payload["cases"][0]["cta"]
    forbidden_terms = ("accus", "irregular", "risk", "suspicious", "corrupt", "fraud")
    assert not any(term in str(payload).lower() for term in forbidden_terms)
