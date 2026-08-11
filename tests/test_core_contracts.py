from __future__ import annotations

from dataclasses import FrozenInstanceError
from dataclasses import fields
from datetime import UTC, datetime

from datosenorden.maintenance.entity_resolution import CanonicalEntity
from datosenorden.maintenance.entity_resolution import EntityAlias
from datosenorden.maintenance.entity_resolution import Identifier
from datosenorden.maintenance.entity_resolution import ResolutionResult
from datosenorden.studio.source_watcher import ChangeCandidate
from datosenorden.studio.source_watcher import ChangeType
from datosenorden.studio.state_events import StateEvent
from datosenorden.studio.state_events import StateEventImportance
from datosenorden.studio.state_events import StateEventType
from datosenorden.studio.state_events import state_event_from_dict
from datosenorden.studio.state_events import state_event_to_dict
from datosenorden.studio.topic_classifier import TopicClassification


def test_frozen_core_contract_field_layouts_remain_stable() -> None:
    assert tuple(field.name for field in fields(ChangeCandidate)) == (
        "source_id",
        "external_id",
        "title",
        "url",
        "detected_at",
        "change_type",
        "reason",
        "priority",
        "suggested_action",
    )
    assert tuple(field.name for field in fields(TopicClassification)) == (
        "category_id",
        "topic_id",
        "confidence",
        "reason",
    )
    assert tuple(field.name for field in fields(StateEvent)) == (
        "event_id",
        "topic_id",
        "category_id",
        "source_id",
        "source_url",
        "external_id",
        "title",
        "description",
        "detected_at",
        "importance",
        "event_type",
        "document_available",
        "evidence_available",
    )
    assert tuple(field.name for field in fields(ResolutionResult)) == (
        "found",
        "query",
        "confidence",
        "method",
        "entity",
        "matched_value",
        "reason",
    )


def test_change_candidate_is_frozen_and_hashable() -> None:
    candidate = ChangeCandidate(
        source_id="source-1",
        external_id="external-1",
        title="Cambio detectado",
        url="https://example.test/change",
        detected_at=datetime(2026, 7, 11, 12, 0, tzinfo=UTC),
        change_type=ChangeType.NEW,
        reason="mock",
        priority=90,
        suggested_action="import_record",
    )

    cache = {candidate: "ok"}

    assert cache[candidate] == "ok"
    try:
        candidate.title = "otro"  # type: ignore[misc]
    except FrozenInstanceError:
        pass
    else:  # pragma: no cover
        raise AssertionError("ChangeCandidate must remain frozen")


def test_state_event_roundtrip_preserves_contract_shape() -> None:
    event = StateEvent(
        event_id="evt-1",
        topic_id="topic-1",
        category_id="category-1",
        source_id="source-1",
        source_url="https://example.test/source",
        external_id="external-1",
        title="Evento detectado",
        description="Descripcion neutral del evento",
        detected_at=datetime(2026, 7, 11, 13, 30, tzinfo=UTC),
        importance=StateEventImportance.HIGH,
        event_type=StateEventType.NEW_DOCUMENT,
        document_available=True,
        evidence_available=False,
    )

    payload = state_event_to_dict(event)
    restored = state_event_from_dict(payload)

    assert payload["detected_at"] == "2026-07-11T13:30:00+00:00"
    assert payload["importance"] == "HIGH"
    assert payload["event_type"] == "NEW_DOCUMENT"
    assert restored == event


def test_resolution_result_to_dict_is_json_safe_with_and_without_entity() -> None:
    empty = ResolutionResult(False, "query", 0.0, "", reason="no_match")

    assert empty.to_dict()["entity"] is None
    assert empty.to_dict()["reason"] == "no_match"

    entity = CanonicalEntity(
        id="entity-1",
        canonical_name="Entity One",
        aliases=(EntityAlias("Alias One"),),
        identifiers=(Identifier("internal_code", "E-001"),),
        tags=("generic",),
        metadata={"scope": "core_candidate"},
    )
    resolved = ResolutionResult(True, "Alias One", 0.9, "alias", entity, "Alias One")
    payload = resolved.to_dict()

    assert payload["entity"]["id"] == "entity-1"
    assert payload["entity"]["aliases"][0]["value"] == "Alias One"
    assert payload["entity"]["identifiers"][0]["type"] == "internal_code"
    assert payload["matched_value"] == "Alias One"
