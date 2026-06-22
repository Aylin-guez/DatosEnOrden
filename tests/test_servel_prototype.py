from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from types import SimpleNamespace
from uuid import UUID

from datosenorden.maintenance.servel_prototype import AUTHORITY_ELECTED_TO_OFFICE_PREDICATE
from datosenorden.maintenance.servel_prototype import AUTHORITY_HAS_ELECTORAL_PERIOD_PREDICATE
from datosenorden.maintenance.servel_prototype import AUTHORITY_REPRESENTS_TERRITORY_PREDICATE
from datosenorden.maintenance.servel_prototype import OFFICE_BELONGS_TO_MUNICIPALITY_PREDICATE
from datosenorden.maintenance.servel_prototype import ServelSummary
from datosenorden.maintenance.servel_prototype import ServelSummaryRow
from datosenorden.maintenance.servel_prototype import build_servel_sample_batch
from datosenorden.maintenance.servel_prototype import load_servel_sample_payload
from datosenorden.maintenance.servel_prototype import read_servel_summary
from datosenorden.maintenance.servel_prototype import render_servel_summary_text


class _ScalarResult:
    def all(self):
        return []


class _BatchSession:
    def get(self, model, identity):  # noqa: ANN001
        _ = (model, identity)
        return None

    def scalar(self, statement):  # noqa: ANN001
        _ = statement
        return None

    def scalars(self, statement):  # noqa: ANN001
        _ = statement
        return _ScalarResult()


@dataclass(frozen=True)
class _ClaimRef:
    subject_entity: SimpleNamespace
    object_entity: SimpleNamespace
    source_record: SimpleNamespace
    predicate: str
    object_value: dict[str, str]
    valid_from: date | None = None


def test_servel_sample_payload_contains_required_markers() -> None:
    payload = load_servel_sample_payload()

    assert payload["classification"] == "LOCAL_TEST_DATA"
    assert payload["official_status"] == "NOT_OFFICIAL_DATA"
    assert len(payload["records"]) == 2
    assert payload["records"][0]["authority_name"] == "Autoridad Electa de Muestra Uno"


def test_servel_sample_batch_is_idempotent() -> None:
    payload = load_servel_sample_payload()
    session = _BatchSession()

    first_batch = build_servel_sample_batch(session, payload)
    second_batch = build_servel_sample_batch(session, payload)

    store = _IdempotencyStore()
    assert store.apply(first_batch) == store.apply(second_batch)


def test_read_servel_summary_and_renderer_are_neutral(monkeypatch) -> None:
    authority = SimpleNamespace(id=UUID("11111111-1111-1111-1111-111111111111"), name="Autoridad Electa de Muestra Uno")
    office = SimpleNamespace(id=UUID("22222222-2222-2222-2222-222222222222"), name="Alcaldia de muestra")
    territory = SimpleNamespace(id=UUID("33333333-3333-3333-3333-333333333333"), name="Municipalidad de Arauco")
    period = SimpleNamespace(id=UUID("44444444-4444-4444-4444-444444444444"), name="Periodo electoral 2024-2028")
    source_record = SimpleNamespace(id=UUID("55555555-5555-5555-5555-555555555555"))

    authority_claim = _ClaimRef(
        subject_entity=authority,
        object_entity=office,
        source_record=source_record,
        predicate=AUTHORITY_ELECTED_TO_OFFICE_PREDICATE,
        object_value={"period_label": "Periodo electoral 2024-2028"},
        valid_from=date(2024, 12, 6),
    )
    territory_claim = _ClaimRef(
        subject_entity=authority,
        object_entity=territory,
        source_record=source_record,
        predicate=AUTHORITY_REPRESENTS_TERRITORY_PREDICATE,
        object_value={"territory_name": "Comuna de Arauco"},
        valid_from=date(2024, 12, 6),
    )
    period_claim = _ClaimRef(
        subject_entity=authority,
        object_entity=period,
        source_record=source_record,
        predicate=AUTHORITY_HAS_ELECTORAL_PERIOD_PREDICATE,
        object_value={
            "period_label": "Periodo electoral 2024-2028",
            "period_start": "2024-12-06",
            "period_end": "2028-12-05",
        },
        valid_from=date(2024, 12, 6),
    )
    office_claim = _ClaimRef(
        subject_entity=office,
        object_entity=territory,
        source_record=source_record,
        predicate=OFFICE_BELONGS_TO_MUNICIPALITY_PREDICATE,
        object_value={"municipality_name": "Municipalidad de Arauco"},
        valid_from=date(2024, 12, 6),
    )

    monkeypatch.setattr(
        "datosenorden.maintenance.servel_prototype._load_servel_authority_claims",
        lambda session: [authority_claim],
    )
    monkeypatch.setattr(
        "datosenorden.maintenance.servel_prototype._load_claim",
        lambda session, source_record_id, predicate: {
            AUTHORITY_REPRESENTS_TERRITORY_PREDICATE: territory_claim,
            AUTHORITY_HAS_ELECTORAL_PERIOD_PREDICATE: period_claim,
            OFFICE_BELONGS_TO_MUNICIPALITY_PREDICATE: office_claim,
        }.get(predicate),
    )
    monkeypatch.setattr(
        "datosenorden.maintenance.servel_prototype._load_servel_relationships",
        lambda session, source_record_id: (
            SimpleNamespace(relationship_type=AUTHORITY_ELECTED_TO_OFFICE_PREDICATE),
            SimpleNamespace(relationship_type=AUTHORITY_REPRESENTS_TERRITORY_PREDICATE),
            SimpleNamespace(relationship_type=OFFICE_BELONGS_TO_MUNICIPALITY_PREDICATE),
            SimpleNamespace(relationship_type=AUTHORITY_HAS_ELECTORAL_PERIOD_PREDICATE),
        ),
    )
    monkeypatch.setattr(
        "datosenorden.maintenance.servel_prototype._count_evidence_for_source_record",
        lambda session, source_record_id: 4,
    )

    summary = read_servel_summary(object())

    assert summary.authorities == 1
    assert summary.offices == 1
    assert summary.territories == 1
    assert summary.periods == 1
    assert summary.relationships == 4
    assert summary.evidence == 4
    assert summary.rows[0].authority_name == "Autoridad Electa de Muestra Uno"

    report = render_servel_summary_text(summary)
    assert "servel_summary:" in report
    assert "authority=Autoridad Electa de Muestra Uno" in report
    assert "period=Periodo electoral 2024-2028" in report
    forbidden_terms = ("suspicious", "irregular", "conflict", "influence", "corruption", "risk")
    assert not any(term in report.lower() for term in forbidden_terms)


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
        _stable_json_identity(claim.object_value),
        (claim.source_record.record_type, claim.source_record.external_id),
    )


def _stable_json_identity(value) -> str:  # noqa: ANN001
    import json

    if value is None:
        return ""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
