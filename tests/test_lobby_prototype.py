from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from uuid import UUID

from datosenorden.etl.core.contracts import EntityType
from datosenorden.etl.core.contracts import RelationshipType
from datosenorden.maintenance.lobby_prototype import (
    COUNTERPARTY_PARTICIPATED_IN_LOBBY_PREDICATE,
    LOBBY_MEETING_ABOUT_SUBJECT_PREDICATE,
    ORGANIZATION_HELD_LOBBY_MEETING_PREDICATE,
    LobbyImportResult,
    LobbySummaryRow,
    build_lobby_sample_batch,
    load_lobby_sample_payload,
    read_lobby_summary,
    render_lobby_import_result_text,
    render_lobby_summary_text,
)
import datosenorden.maintenance.lobby_prototype as lobby_prototype


class _ScalarResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeSession:
    def __init__(self, entities):
        self._entities = entities

    def get(self, model, identity):  # noqa: ANN001
        for entity in self._entities:
            if entity.id == identity:
                return entity
        return None

    def scalars(self, statement):  # noqa: ANN001
        return _ScalarResult(self._entities)


def _existing_entities():
    return [
        SimpleNamespace(
            id=UUID("11111111-1111-1111-1111-111111111111"),
            entity_type="PUBLIC_ORGANIZATION",
            name="SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO",
            external_id="chilecompra:buyer:arauco",
            description="existing org",
            normalized_key="servicio-de-salud-arauco-hospital-de-arauco",
            status="active",
            entity_metadata={"source": "chilecompra"},
        ),
        SimpleNamespace(
            id=UUID("22222222-2222-2222-2222-222222222222"),
            entity_type="COMPANY",
            name="MARLENE BEATRIZ FLORES PATIÑO",
            external_id="chilecompra:supplier:marlene-flores",
            description="existing company",
            normalized_key="marlene-beatriz-flores-patino",
            status="active",
            entity_metadata={"source": "chilecompra"},
        ),
    ]


def test_load_lobby_sample_payload_contains_required_markers() -> None:
    payload = load_lobby_sample_payload()

    assert payload["classification"] == "LOCAL_TEST_DATA"
    assert payload["official_status"] == "NOT_OFFICIAL_DATA"
    assert payload["records"][0]["organization_name"] == "SERVICIO DE SALUD ARAUCO"
    assert payload["records"][0]["counterparty_name"] == "MARLENE BEATRIZ FLORES PATINO"
    assert payload["records"][0]["source_dataset_name"] == "lobby-meeting-sample"


def test_build_lobby_sample_batch_matches_existing_entities_and_creates_claims() -> None:
    payload = load_lobby_sample_payload()
    session = _FakeSession(_existing_entities())

    batch = build_lobby_sample_batch(session, payload)

    assert batch.raw_count == 1
    assert len(batch.entities) == 3
    assert batch.entities[0].entity_type == EntityType.LOBBY_MEETING
    assert batch.entities[1].external_id == "chilecompra:buyer:arauco"
    assert batch.entities[2].external_id == "chilecompra:supplier:marlene-flores"
    assert len(batch.evidence) == 3
    assert len(batch.claims) == 3
    assert {claim.predicate for claim in batch.claims} == {
        ORGANIZATION_HELD_LOBBY_MEETING_PREDICATE,
        COUNTERPARTY_PARTICIPATED_IN_LOBBY_PREDICATE,
        LOBBY_MEETING_ABOUT_SUBJECT_PREDICATE,
    }
    subject_claim = next(claim for claim in batch.claims if claim.predicate == LOBBY_MEETING_ABOUT_SUBJECT_PREDICATE)
    assert subject_claim.object_value["meeting_subject"].startswith("Presentacion de servicios")
    assert len(batch.public_relationships) == 2
    assert {relationship.relationship_type for relationship in batch.public_relationships} == {
        RelationshipType.ORGANIZATION_HELD_LOBBY_MEETING,
        RelationshipType.COUNTERPARTY_PARTICIPATED_IN_LOBBY,
    }
    org_relationship = next(
        relationship
        for relationship in batch.public_relationships
        if relationship.relationship_type == RelationshipType.ORGANIZATION_HELD_LOBBY_MEETING
    )
    assert org_relationship.metadata["match_method"] == "contains_normalized_match"
    assert org_relationship.metadata["match_confidence"] >= 0.9


def test_build_lobby_sample_batch_can_create_local_fallback_entities() -> None:
    payload = load_lobby_sample_payload()
    session = _FakeSession([])

    batch = build_lobby_sample_batch(session, payload)

    assert batch.entities[1].external_id.startswith("lobby:local:public_organization:")
    assert batch.entities[2].external_id.startswith("lobby:local:company:")
    assert batch.public_relationships[0].metadata["match_method"] == "local_sample_no_existing_match"
    assert batch.public_relationships[0].metadata["match_confidence"] == 0.5


def test_lobby_sample_batch_has_stable_idempotency_keys_across_runs() -> None:
    payload = load_lobby_sample_payload()
    session = _FakeSession(_existing_entities())
    first_batch = build_lobby_sample_batch(session, payload)
    second_batch = build_lobby_sample_batch(session, payload)

    store = _IdempotencyStore()
    first_counts = store.apply(first_batch)
    second_counts = store.apply(second_batch)

    assert first_counts == {
        "source_records": 1,
        "entities": 3,
        "evidence": 3,
        "claims": 3,
        "relationship_public": 2,
    }
    assert second_counts == first_counts


def test_read_lobby_summary_aggregates_claims_relationships_and_matches(monkeypatch) -> None:
    meeting = SimpleNamespace(
        id=UUID("33333333-3333-3333-3333-333333333333"),
        name="Lobby meeting 2026-03-15 - SERVICIO DE SALUD ARAUCO / MARLENE BEATRIZ FLORES PATINO",
    )
    organization = _existing_entities()[0]
    counterparty = _existing_entities()[1]
    source_record = SimpleNamespace(id=UUID("44444444-4444-4444-4444-444444444444"))
    subject_claim = SimpleNamespace(
        subject_entity=meeting,
        source_record=source_record,
        object_value={"meeting_subject": "Presentacion de servicios"},
        valid_from=date(2026, 3, 15),
        predicate=LOBBY_MEETING_ABOUT_SUBJECT_PREDICATE,
    )
    organization_claim = SimpleNamespace(
        subject_entity=organization,
        predicate=ORGANIZATION_HELD_LOBBY_MEETING_PREDICATE,
        confidence=0.95,
    )
    counterparty_claim = SimpleNamespace(
        subject_entity=counterparty,
        predicate=COUNTERPARTY_PARTICIPATED_IN_LOBBY_PREDICATE,
        confidence=1.0,
    )
    relationships = (
        SimpleNamespace(
            relationship_type=ORGANIZATION_HELD_LOBBY_MEETING_PREDICATE,
            relationship_metadata={"match_method": "contains_normalized_match", "match_confidence": 0.95},
        ),
        SimpleNamespace(
            relationship_type=COUNTERPARTY_PARTICIPATED_IN_LOBBY_PREDICATE,
            relationship_metadata={"match_method": "exact_normalized_match", "match_confidence": 1.0},
        ),
    )
    session = SimpleNamespace()

    monkeypatch.setattr(lobby_prototype, "_load_lobby_subject_claims", lambda session: [subject_claim])
    monkeypatch.setattr(
        lobby_prototype,
        "_load_lobby_link_claim",
        lambda session, source_record_id, predicate: organization_claim
        if predicate == ORGANIZATION_HELD_LOBBY_MEETING_PREDICATE
        else counterparty_claim,
    )
    monkeypatch.setattr(lobby_prototype, "_load_lobby_relationships", lambda session, source_record_id: relationships)

    rows = read_lobby_summary(session)

    assert rows == (
        LobbySummaryRow(
            lobby_meeting_id=str(meeting.id),
            lobby_meeting_name=meeting.name,
            organization_id=str(organization.id),
            organization_name=organization.name,
            counterparty_id=str(counterparty.id),
            counterparty_name=counterparty.name,
            counterparty_type="COMPANY",
            meeting_subject="Presentacion de servicios",
            meeting_date=date(2026, 3, 15),
            claims=(
                ORGANIZATION_HELD_LOBBY_MEETING_PREDICATE,
                COUNTERPARTY_PARTICIPATED_IN_LOBBY_PREDICATE,
                LOBBY_MEETING_ABOUT_SUBJECT_PREDICATE,
            ),
            relationships=(
                COUNTERPARTY_PARTICIPATED_IN_LOBBY_PREDICATE,
                ORGANIZATION_HELD_LOBBY_MEETING_PREDICATE,
            ),
            organization_match_method="contains_normalized_match",
            organization_match_confidence=0.95,
            counterparty_match_method="exact_normalized_match",
            counterparty_match_confidence=1.0,
        ),
    )


def test_render_lobby_summary_text_formats_rows() -> None:
    row = LobbySummaryRow(
        lobby_meeting_id="33333333-3333-3333-3333-333333333333",
        lobby_meeting_name="Lobby meeting 2026-03-15",
        organization_id="11111111-1111-1111-1111-111111111111",
        organization_name="SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO",
        counterparty_id="22222222-2222-2222-2222-222222222222",
        counterparty_name="MARLENE BEATRIZ FLORES PATIÑO",
        counterparty_type="COMPANY",
        meeting_subject="Presentacion de servicios",
        meeting_date=date(2026, 3, 15),
        claims=(
            ORGANIZATION_HELD_LOBBY_MEETING_PREDICATE,
            COUNTERPARTY_PARTICIPATED_IN_LOBBY_PREDICATE,
            LOBBY_MEETING_ABOUT_SUBJECT_PREDICATE,
        ),
        relationships=(
            ORGANIZATION_HELD_LOBBY_MEETING_PREDICATE,
            COUNTERPARTY_PARTICIPATED_IN_LOBBY_PREDICATE,
        ),
        organization_match_method="contains_normalized_match",
        organization_match_confidence=0.95,
        counterparty_match_method="exact_normalized_match",
        counterparty_match_confidence=1.0,
    )

    report = render_lobby_summary_text((row,))

    assert "lobby_summary:" in report
    assert "organization:" in report
    assert "counterparty:" in report
    assert "claims:" in report
    assert "relationships:" in report
    assert "matched_entities:" in report
    assert "organization_match_method=contains_normalized_match" in report


def test_read_lobby_summary_renders_unique_relationships(monkeypatch) -> None:
    meeting = SimpleNamespace(
        id=UUID("33333333-3333-3333-3333-333333333333"),
        name="Lobby meeting 2026-03-15 - SERVICIO DE SALUD ARAUCO / MARLENE BEATRIZ FLORES PATINO",
    )
    organization = _existing_entities()[0]
    counterparty = _existing_entities()[1]
    source_record = SimpleNamespace(id=UUID("44444444-4444-4444-4444-444444444444"))
    subject_claim = SimpleNamespace(
        subject_entity=meeting,
        source_record=source_record,
        object_value={"meeting_subject": "Presentacion de servicios"},
        valid_from=date(2026, 3, 15),
        predicate=LOBBY_MEETING_ABOUT_SUBJECT_PREDICATE,
    )
    organization_claim = SimpleNamespace(
        subject_entity=organization,
        predicate=ORGANIZATION_HELD_LOBBY_MEETING_PREDICATE,
        confidence=0.95,
    )
    counterparty_claim = SimpleNamespace(
        subject_entity=counterparty,
        predicate=COUNTERPARTY_PARTICIPATED_IN_LOBBY_PREDICATE,
        confidence=1.0,
    )
    duplicate_relationships = (
        _relationship(organization.id, meeting.id, ORGANIZATION_HELD_LOBBY_MEETING_PREDICATE),
        _relationship(organization.id, meeting.id, ORGANIZATION_HELD_LOBBY_MEETING_PREDICATE),
        _relationship(counterparty.id, meeting.id, COUNTERPARTY_PARTICIPATED_IN_LOBBY_PREDICATE),
        _relationship(counterparty.id, meeting.id, COUNTERPARTY_PARTICIPATED_IN_LOBBY_PREDICATE),
    )
    session = SimpleNamespace()

    monkeypatch.setattr(lobby_prototype, "_load_lobby_subject_claims", lambda session: [subject_claim, subject_claim])
    monkeypatch.setattr(
        lobby_prototype,
        "_load_lobby_link_claim",
        lambda session, source_record_id, predicate: organization_claim
        if predicate == ORGANIZATION_HELD_LOBBY_MEETING_PREDICATE
        else counterparty_claim,
    )
    monkeypatch.setattr(
        lobby_prototype,
        "_load_lobby_relationships",
        lambda session, source_record_id: duplicate_relationships,
    )

    rows = read_lobby_summary(session)

    assert len(rows) == 1
    assert rows[0].relationships == (
        COUNTERPARTY_PARTICIPATED_IN_LOBBY_PREDICATE,
        ORGANIZATION_HELD_LOBBY_MEETING_PREDICATE,
    )


def test_render_lobby_import_result_text_formats_counts() -> None:
    report = render_lobby_import_result_text(
        LobbyImportResult(
            source_records=1,
            claims=3,
            evidences=3,
            entities=3,
            relationship_public=2,
            organization_entity_id="11111111-1111-1111-1111-111111111111",
            organization_name="SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO",
            counterparty_entity_id="22222222-2222-2222-2222-222222222222",
            counterparty_name="MARLENE BEATRIZ FLORES PATIÑO",
            lobby_meeting_entity_id="33333333-3333-3333-3333-333333333333",
            lobby_meeting_name="Lobby meeting 2026-03-15",
        )
    )

    assert "lobby_sample_loaded:" in report
    assert "claims=3" in report
    assert "relationship_public=2" in report
    assert "counterparty_name=" in report


class _IdempotencyStore:
    def __init__(self) -> None:
        self.source_records: set[tuple[str, str]] = set()
        self.entities: set[tuple[str, str]] = set()
        self.evidence: set[tuple[str, str, str]] = set()
        self.claims: set[tuple] = set()
        self.relationships: set[tuple] = set()

    def apply(self, batch) -> dict[str, int]:  # noqa: ANN001
        for source_record in batch.source_records:
            self.source_records.add((source_record.record_type, source_record.external_id))
        for entity in batch.entities:
            self.entities.add((entity.entity_type.value, entity.external_id))
        for evidence in batch.evidence:
            self.evidence.add(
                (
                    evidence.source_record.record_type,
                    evidence.source_record.external_id,
                    evidence.url,
                )
            )
        for claim in batch.claims:
            self.claims.add(_claim_key(claim))
        for relationship in batch.public_relationships:
            self.relationships.add(
                (
                    (relationship.source_entity.entity_type.value, relationship.source_entity.external_id),
                    (relationship.target_entity.entity_type.value, relationship.target_entity.external_id),
                    relationship.relationship_type.value,
                    _claim_key(relationship.claim),
                )
            )
        return {
            "source_records": len(self.source_records),
            "entities": len(self.entities),
            "evidence": len(self.evidence),
            "claims": len(self.claims),
            "relationship_public": len(self.relationships),
        }


def _claim_key(claim) -> tuple:  # noqa: ANN001
    object_entity_key = None
    if claim.object_entity is not None:
        object_entity_key = (claim.object_entity.entity_type.value, claim.object_entity.external_id)
    return (
        (claim.subject_entity.entity_type.value, claim.subject_entity.external_id),
        claim.predicate,
        object_entity_key,
        lobby_prototype._stable_json_identity(claim.object_value),
        (claim.source_record.record_type, claim.source_record.external_id),
    )


def _relationship(source_id: UUID, target_id: UUID, relationship_type: str):
    return SimpleNamespace(
        source_entity_id=source_id,
        target_entity_id=target_id,
        relationship_type=relationship_type,
        relationship_metadata={"match_method": "exact_normalized_match", "match_confidence": 1.0},
    )
