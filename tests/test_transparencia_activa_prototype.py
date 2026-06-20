from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID

from datosenorden.etl.core.contracts import EntityType
from datosenorden.etl.core.contracts import RelationshipType
from datosenorden.maintenance.transparencia_activa_prototype import (
    ORGANIZATION_HAS_PUBLIC_ROLE_PREDICATE,
    PERSON_HOLDS_PUBLIC_ROLE_PREDICATE,
    ROLE_BELONGS_TO_ORGANIZATION_PREDICATE,
    TransparenciaImportResult,
    TransparenciaSummary,
    TransparenciaSummaryRow,
    build_transparencia_sample_batch,
    load_transparencia_sample_payload,
    read_transparencia_summary,
    render_transparencia_import_result_text,
    render_transparencia_summary_text,
    transparencia_human_explanation,
)
import datosenorden.maintenance.transparencia_activa_prototype as transparencia


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


def _existing_org():
    return SimpleNamespace(
        id=UUID("11111111-1111-1111-1111-111111111111"),
        entity_type="PUBLIC_ORGANIZATION",
        name="DIVISION LOGISTICA DEL EJERCITO",
        external_id="chilecompra:buyer:division-logistica-ejercito",
        description="existing org aligned for local demo",
        normalized_key="division-logistica-ejercito",
        status="active",
        entity_metadata={"source": "chilecompra"},
    )


def test_load_transparencia_sample_payload_contains_local_markers() -> None:
    payload = load_transparencia_sample_payload()

    assert payload["classification"] == "LOCAL_TEST_DATA"
    assert payload["official_status"] == "NOT_OFFICIAL_DATA"
    assert payload["records"][0]["organization_name"] == "DIVISION LOGISTICA DEL EJERCITO"
    assert payload["records"][0]["person_name"] == "PERSONA DE MUESTRA TRANSPARENCIA"
    assert payload["records"][0]["source_dataset_name"] == "transparencia-activa-sample"


def test_build_transparencia_sample_batch_matches_org_and_creates_claims() -> None:
    payload = load_transparencia_sample_payload()
    session = _FakeSession([_existing_org()])

    batch = build_transparencia_sample_batch(session, payload)

    assert batch.raw_count == 1
    assert len(batch.entities) == 3
    assert batch.entities[0].entity_type == EntityType.PUBLIC_ORGANIZATION
    assert batch.entities[0].external_id == "chilecompra:buyer:division-logistica-ejercito"
    assert batch.entities[1].entity_type == EntityType.ROLE
    assert batch.entities[2].entity_type == EntityType.PERSON
    assert len(batch.evidence) == 3
    assert len(batch.claims) == 3
    assert {claim.predicate for claim in batch.claims} == {
        ORGANIZATION_HAS_PUBLIC_ROLE_PREDICATE,
        PERSON_HOLDS_PUBLIC_ROLE_PREDICATE,
        ROLE_BELONGS_TO_ORGANIZATION_PREDICATE,
    }
    assert len(batch.public_relationships) == 3
    assert {relationship.relationship_type for relationship in batch.public_relationships} == {
        RelationshipType.ORGANIZATION_HAS_PUBLIC_ROLE,
        RelationshipType.PERSON_HOLDS_PUBLIC_ROLE,
        RelationshipType.ROLE_BELONGS_TO_ORGANIZATION,
    }
    assert batch.public_relationships[0].metadata["match_method"] == "exact_normalized_match"
    assert batch.public_relationships[0].metadata["match_confidence"] == 1.0


def test_transparencia_sample_batch_has_stable_idempotency_keys() -> None:
    payload = load_transparencia_sample_payload()
    session = _FakeSession([_existing_org()])
    first_batch = build_transparencia_sample_batch(session, payload)
    second_batch = build_transparencia_sample_batch(session, payload)

    store = _IdempotencyStore()
    first_counts = store.apply(first_batch)
    second_counts = store.apply(second_batch)

    assert first_counts == {
        "source_records": 1,
        "entities": 3,
        "evidence": 3,
        "claims": 3,
        "relationship_public": 3,
    }
    assert second_counts == first_counts


def test_read_transparencia_summary_aggregates_rows(monkeypatch) -> None:
    organization = _existing_org()
    role = SimpleNamespace(
        id=UUID("22222222-2222-2222-2222-222222222222"),
        name="Cargo de muestra Transparencia Activa - DIVISION LOGISTICA DEL EJERCITO (2026-01)",
    )
    person = SimpleNamespace(
        id=UUID("33333333-3333-3333-3333-333333333333"),
        name="PERSONA DE MUESTRA TRANSPARENCIA",
    )
    source_record = SimpleNamespace(id=UUID("44444444-4444-4444-4444-444444444444"))
    org_claim = SimpleNamespace(
        id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        subject_entity=organization,
        object_entity=role,
        source_record=source_record,
        predicate=ORGANIZATION_HAS_PUBLIC_ROLE_PREDICATE,
        object_value={"period": "2026-01", "unit_name": "Unidad de muestra"},
        confidence=1.0,
    )
    person_claim = SimpleNamespace(
        id=UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
        subject_entity=person,
        object_entity=role,
        predicate=PERSON_HOLDS_PUBLIC_ROLE_PREDICATE,
    )
    belongs_claim = SimpleNamespace(
        id=UUID("cccccccc-cccc-cccc-cccc-cccccccccccc"),
        predicate=ROLE_BELONGS_TO_ORGANIZATION_PREDICATE,
    )
    relationships = (
        _relationship("ORGANIZATION_HAS_PUBLIC_ROLE"),
        _relationship("PERSON_HOLDS_PUBLIC_ROLE"),
        _relationship("ROLE_BELONGS_TO_ORGANIZATION"),
    )
    monkeypatch.setattr(transparencia, "_load_organization_role_claims", lambda session: [org_claim])
    monkeypatch.setattr(transparencia, "_load_role_person_claim", lambda session, source_record_id: person_claim)
    monkeypatch.setattr(transparencia, "_load_role_organization_claim", lambda session, source_record_id: belongs_claim)
    monkeypatch.setattr(transparencia, "_load_transparencia_relationships", lambda session, source_record_id: relationships)
    monkeypatch.setattr(transparencia, "_count_evidence_for_claim_ids", lambda session, claim_ids: 3)

    summary = read_transparencia_summary(SimpleNamespace())

    assert summary.organizations == 1
    assert summary.people == 1
    assert summary.roles == 1
    assert summary.claims == 3
    assert summary.relationships == 3
    assert summary.evidence == 3
    assert summary.rows[0].organization_match_method == "exact_normalized_match"


def test_render_transparencia_summary_text_matches_contract() -> None:
    summary = TransparenciaSummary(
        organizations=1,
        people=1,
        roles=1,
        claims=3,
        relationships=3,
        evidence=3,
        rows=(
            TransparenciaSummaryRow(
                organization_id="11111111-1111-1111-1111-111111111111",
                organization_name="DIVISION LOGISTICA DEL EJERCITO",
                role_id="22222222-2222-2222-2222-222222222222",
                role_name="Cargo de muestra Transparencia Activa",
                person_id="33333333-3333-3333-3333-333333333333",
                person_name="PERSONA DE MUESTRA TRANSPARENCIA",
                period="2026-01",
                unit_name="Unidad de muestra",
                claims=(ORGANIZATION_HAS_PUBLIC_ROLE_PREDICATE,),
                relationships=("ORGANIZATION_HAS_PUBLIC_ROLE",),
                evidence=3,
                organization_match_method="exact_normalized_match",
                organization_match_confidence=1.0,
            ),
        ),
    )

    report = render_transparencia_summary_text(summary)

    assert "transparencia_summary:" in report
    assert "organizations=1" in report
    assert "people=1" in report
    assert "roles=1" in report
    assert "claims=3" in report
    assert "relationships=3" in report
    assert "evidence=3" in report
    assert "organization_match_method=exact_normalized_match" in report


def test_render_transparencia_import_result_text_formats_counts() -> None:
    report = render_transparencia_import_result_text(
        TransparenciaImportResult(
            source_records=1,
            claims=3,
            evidences=3,
            entities=3,
            relationship_public=3,
            organization_entity_id="11111111-1111-1111-1111-111111111111",
            organization_name="DIVISION LOGISTICA DEL EJERCITO",
            role_entity_id="22222222-2222-2222-2222-222222222222",
            role_name="Cargo de muestra Transparencia Activa",
            person_entity_id="33333333-3333-3333-3333-333333333333",
            person_name="PERSONA DE MUESTRA TRANSPARENCIA",
            organization_match_method="exact_normalized_match",
            organization_match_confidence=1.0,
        )
    )

    assert "transparencia_sample_loaded:" in report
    assert "relationship_public=3" in report
    assert "organization_name=DIVISION LOGISTICA DEL EJERCITO" in report
    assert "person_name=PERSONA DE MUESTRA TRANSPARENCIA" in report


def test_transparencia_human_explanation_is_neutral() -> None:
    report = transparencia_human_explanation()

    assert "Transparencia Activa muestra informacion administrativa" in report
    assert "datos de muestra, no datos oficiales" in report
    assert "No implica irregularidad" in report


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
            self.evidence.add((evidence.source_record.record_type, evidence.source_record.external_id, evidence.url))
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
        transparencia._stable_json_identity(claim.object_value)
        if hasattr(transparencia, "_stable_json_identity")
        else str(claim.object_value),
        (claim.source_record.record_type, claim.source_record.external_id),
    )


def _relationship(relationship_type: str):
    return SimpleNamespace(
        relationship_type=relationship_type,
        relationship_metadata={"match_method": "exact_normalized_match", "match_confidence": 1.0},
    )
