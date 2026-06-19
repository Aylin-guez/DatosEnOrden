from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID

from datosenorden.etl.core.contracts import EntityType
from datosenorden.etl.core.contracts import RelationshipType
from datosenorden.maintenance.dipres_prototype import BudgetSummaryRow
from datosenorden.maintenance.dipres_prototype import DIPRES_APPROVED_BUDGET_PREDICATE
from datosenorden.maintenance.dipres_prototype import DIPRES_EXECUTED_BUDGET_PREDICATE
from datosenorden.maintenance.dipres_prototype import DIPRES_MATCH_PREDICATE
from datosenorden.maintenance.dipres_prototype import DipresImportResult
from datosenorden.maintenance.dipres_prototype import build_dipres_sample_batch
from datosenorden.maintenance.dipres_prototype import load_dipres_sample_payload
from datosenorden.maintenance.dipres_prototype import read_budget_summary
from datosenorden.maintenance.dipres_prototype import render_budget_summary_text
from datosenorden.maintenance.dipres_prototype import render_dipres_import_result_text
import datosenorden.maintenance.dipres_prototype as dipres_prototype


class _ScalarResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeSession:
    def __init__(self, entities):
        self._entities = entities

    def scalars(self, statement):  # noqa: ANN001
        return _ScalarResult(self._entities)


def test_load_dipres_sample_payload_contains_markers() -> None:
    payload = load_dipres_sample_payload()

    assert payload["classification"] == "LOCAL_TEST_DATA"
    assert payload["official_status"] == "NOT_OFFICIAL_DATA"
    assert payload["records"][0]["service_name"] == "SERVICIO DE SALUD ARAUCO"
    assert payload["records"][0]["approved_budget"] == 1000000000
    assert payload["records"][0]["executed_budget"] == 950000000


def test_build_dipres_sample_batch_links_budget_to_existing_organization() -> None:
    candidate = SimpleNamespace(
        id=UUID("11111111-1111-1111-1111-111111111111"),
        entity_type="PUBLIC_ORGANIZATION",
        name="SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO",
        external_id="chilecompra:buyer:arauco",
        description="existing org",
        normalized_key="servicio-de-salud-arauco-hospital-de-arauco",
        status="active",
        entity_metadata={"source": "chilecompra"},
    )
    session = _FakeSession([candidate])
    payload = load_dipres_sample_payload()

    batch = build_dipres_sample_batch(session, payload)

    assert batch.raw_count == 1
    assert len(batch.entities) == 2
    assert batch.entities[0].entity_type == EntityType.BUDGET
    assert batch.entities[1].external_id == candidate.external_id
    assert batch.entities[1].name == candidate.name
    assert len(batch.claims) == 3
    assert {claim.predicate for claim in batch.claims} == {
        DIPRES_APPROVED_BUDGET_PREDICATE,
        DIPRES_EXECUTED_BUDGET_PREDICATE,
        DIPRES_MATCH_PREDICATE,
    }
    match_claim = next(claim for claim in batch.claims if claim.predicate == DIPRES_MATCH_PREDICATE)
    assert match_claim.object_entity is not None
    assert match_claim.object_entity.external_id == candidate.external_id
    assert match_claim.object_value["matching_method"] == "normalized_contains"
    assert match_claim.object_value["confidence"] >= 0.9
    assert len(batch.public_relationships) == 1
    assert batch.public_relationships[0].relationship_type == RelationshipType.BUDGET_ALLOCATED_TO
    assert batch.public_relationships[0].source_entity.entity_type == EntityType.BUDGET


def test_read_budget_summary_aggregates_counts(monkeypatch) -> None:
    budget_entity = SimpleNamespace(id=UUID("22222222-2222-2222-2222-222222222222"), name="DIPRES budget 2026 - SERVICIO DE SALUD ARAUCO")
    organization = SimpleNamespace(
        id=UUID("11111111-1111-1111-1111-111111111111"),
        name="SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO",
    )
    source_record = SimpleNamespace(id=UUID("33333333-3333-3333-3333-333333333333"))
    match_claim = SimpleNamespace(
        subject_entity=budget_entity,
        object_entity=organization,
        object_value={"matching_method": "normalized_contains", "confidence": 0.95},
        confidence=0.95,
        source_record=source_record,
    )
    approved_claim = SimpleNamespace(
        predicate=DIPRES_APPROVED_BUDGET_PREDICATE,
        object_value={"amount": 1000000000, "currency": "CLP", "fiscal_year": 2026},
    )
    executed_claim = SimpleNamespace(
        predicate=DIPRES_EXECUTED_BUDGET_PREDICATE,
        object_value={"amount": 950000000, "currency": "CLP", "fiscal_year": 2026},
    )
    session = SimpleNamespace()

    monkeypatch.setattr(dipres_prototype, "_load_budget_match_claims", lambda session: [match_claim])
    monkeypatch.setattr(
        dipres_prototype,
        "_load_budget_amount_claims",
        lambda session, source_record_id, organization_id: [approved_claim, executed_claim],  # noqa: ARG005
    )
    monkeypatch.setattr(dipres_prototype, "_count_purchase_orders_for_entity", lambda session, entity_id: 4)  # noqa: ARG005
    monkeypatch.setattr(dipres_prototype, "_count_suppliers_for_entity", lambda session, entity_id: 2)  # noqa: ARG005

    rows = read_budget_summary(session)

    assert rows == (
        BudgetSummaryRow(
            budget_entity_id=str(budget_entity.id),
            budget_entity_name=budget_entity.name,
            organization_id=str(organization.id),
            organization_name=organization.name,
            fiscal_year=2026,
            approved_budget=1000000000,
            executed_budget=950000000,
            purchase_orders=4,
            suppliers=2,
            match_method="normalized_contains",
            match_confidence=0.95,
            currency="CLP",
        ),
    )


def test_render_budget_summary_text_formats_rows() -> None:
    report = render_budget_summary_text(
        (
            BudgetSummaryRow(
                budget_entity_id="22222222-2222-2222-2222-222222222222",
                budget_entity_name="DIPRES budget 2026 - SERVICIO DE SALUD ARAUCO",
                organization_id="11111111-1111-1111-1111-111111111111",
                organization_name="SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO",
                fiscal_year=2026,
                approved_budget=1000000000,
                executed_budget=950000000,
                purchase_orders=4,
                suppliers=2,
                match_method="normalized_contains",
                match_confidence=0.95,
                currency="CLP",
            ),
        )
    )

    assert "budget_summary:" in report
    assert "organization:" in report
    assert "approved_budget=1000000000" in report
    assert "executed_budget=950000000" in report
    assert "purchase_orders=4" in report
    assert "suppliers=2" in report
    assert "match_method=normalized_contains" in report


def test_render_dipres_import_result_text_formats_counts() -> None:
    report = render_dipres_import_result_text(
        DipresImportResult(
            source_records=1,
            claims=3,
            evidences=3,
            entities=2,
            relationship_public=1,
            matched_entity_id="11111111-1111-1111-1111-111111111111",
            matched_entity_name="SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO",
            budget_entity_id="22222222-2222-2222-2222-222222222222",
            budget_entity_name="DIPRES budget 2026 - SERVICIO DE SALUD ARAUCO",
        )
    )

    assert "dipres_sample_loaded:" in report
    assert "source_records=1" in report
    assert "relationship_public=1" in report
    assert "matched_entity_name=SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO" in report
