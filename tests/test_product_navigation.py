from __future__ import annotations

import pytest

from datosenorden.maintenance.product_navigation import get_guided_discovery_options
from datosenorden.maintenance.product_navigation import resolve_canonical_expediente_target


MAIN_NAME = "SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO"


def _main_or_skip() -> dict:
    result = resolve_canonical_expediente_target(MAIN_NAME)
    if not result.get("found"):
        pytest.skip("complete MVP demo is not loaded")
    return result


def test_canonical_resolver_direct_organization() -> None:
    result = _main_or_skip()

    assert result["canonical_entity_name"] == MAIN_NAME
    assert result["original_entity_type"] == "PUBLIC_ORGANIZATION"
    assert result["relation_to_original"] == "self"


def test_canonical_resolver_budget_to_organization() -> None:
    _main_or_skip()
    options = get_guided_discovery_options("budgets")
    if not options:
        pytest.skip("budget demo records are not loaded")

    result = resolve_canonical_expediente_target(options[0]["entity_id"])

    assert result["is_record"] is True
    assert result["original_entity_type"] == "BUDGET"
    assert result["canonical_entity_name"] == MAIN_NAME


def test_canonical_resolver_purchase_contract_to_organization() -> None:
    _main_or_skip()
    options = get_guided_discovery_options("procurement")
    if not options:
        pytest.skip("procurement demo records are not loaded")

    result = resolve_canonical_expediente_target(options[0]["entity_id"])

    assert result["is_record"] is True
    assert result["original_entity_type"] in {"CONTRACT", "PURCHASE_ORDER"}
    assert result["canonical_entity_name"] == MAIN_NAME


def test_canonical_resolver_meeting_to_organization_or_person() -> None:
    _main_or_skip()
    options = get_guided_discovery_options("meetings")
    if not options:
        pytest.skip("meeting demo records are not loaded")

    result = resolve_canonical_expediente_target(options[0]["entity_id"])

    assert result["is_record"] is True
    assert result["original_entity_type"] == "LOBBY_MEETING"
    assert result["canonical_entity_type"] in {"PUBLIC_ORGANIZATION", "PERSON", "COMPANY"}


def test_guided_discovery_options_return_demo_entities() -> None:
    _main_or_skip()

    for category in ("public_organizations", "suppliers", "authorities", "budgets", "procurement", "meetings"):
        assert get_guided_discovery_options(category), category
