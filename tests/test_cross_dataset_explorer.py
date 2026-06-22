from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID

import datosenorden.maintenance.cross_dataset_explorer as cross_dataset_explorer
from datosenorden.maintenance.cross_dataset_explorer import CrossDatasetConnection
from datosenorden.maintenance.cross_dataset_explorer import CrossDatasetOrganizationSummary
from datosenorden.maintenance.cross_dataset_explorer import citizen_friendly_explanation
from datosenorden.maintenance.cross_dataset_explorer import get_cross_dataset_organization_summary
from datosenorden.maintenance.cross_dataset_explorer import render_cross_dataset_connections_text
from datosenorden.maintenance.cross_dataset_explorer import render_cross_dataset_summary_text


ORGANIZATION_ID = UUID("11111111-1111-1111-1111-111111111111")


class _FakeSession:
    def get(self, model, identity):  # noqa: ANN001
        _ = model
        if identity == ORGANIZATION_ID:
            return SimpleNamespace(
                id=ORGANIZATION_ID,
                entity_type="PUBLIC_ORGANIZATION",
                name="SERVICIO DE SALUD ARAUCO",
            )
        return None


def _summary() -> CrossDatasetOrganizationSummary:
    return CrossDatasetOrganizationSummary(
        organization_id=str(ORGANIZATION_ID),
        organization_name="SERVICIO DE SALUD ARAUCO",
        datasets=("chilecompra", "lobby"),
        contracts=4,
        lobby_meetings=1,
        evidence=5,
        relationships=6,
        lobby_connections=(
            CrossDatasetConnection(
                entity_id="22222222-2222-2222-2222-222222222222",
                entity_type="COMPANY",
                name="MARLENE FLORES PATINO",
                relationship_type="COUNTERPARTY_PARTICIPATED_IN_LOBBY",
            ),
        ),
        procurement_connections=(
            CrossDatasetConnection(
                entity_id="33333333-3333-3333-3333-333333333333",
                entity_type="COMPANY",
                name="SKY AIRLINE S.A.",
                relationship_type="RECEIVES_CONTRACT",
            ),
        ),
        explanation=citizen_friendly_explanation(),
    )


def test_get_cross_dataset_organization_summary_uses_stored_claims_and_relationships(monkeypatch) -> None:
    session = _FakeSession()
    monkeypatch.setattr(cross_dataset_explorer, "_datasets_for_entity", lambda session, entity_id: {"chilecompra", "lobby"})
    monkeypatch.setattr(cross_dataset_explorer, "_claim_ids_for_entity", lambda session, entity_id: (UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),))
    monkeypatch.setattr(
        cross_dataset_explorer,
        "_count_distinct_claim_objects",
        lambda session, entity_id, predicate, dataset_group: 4 if dataset_group == "chilecompra" else 1,
    )
    monkeypatch.setattr(cross_dataset_explorer, "_count_evidence", lambda session, entity_id, claim_ids: 5)
    monkeypatch.setattr(cross_dataset_explorer, "_count_relationships", lambda session, entity_id, claim_ids: 6)
    monkeypatch.setattr(cross_dataset_explorer, "_lobby_connections", lambda session, entity_id: _summary().lobby_connections)
    monkeypatch.setattr(cross_dataset_explorer, "_procurement_connections", lambda session, entity_id: _summary().procurement_connections)

    row = get_cross_dataset_organization_summary(session, str(ORGANIZATION_ID))

    assert row is not None
    assert row.organization_name == "SERVICIO DE SALUD ARAUCO"
    assert row.datasets == ("chilecompra", "lobby")
    assert row.contracts == 4
    assert row.lobby_meetings == 1
    assert row.evidence == 5
    assert row.relationships == 6
    assert row.lobby_connections[0].name == "MARLENE FLORES PATINO"
    assert row.procurement_connections[0].name == "SKY AIRLINE S.A."


def test_get_cross_dataset_organization_summary_returns_none_for_single_dataset(monkeypatch) -> None:
    monkeypatch.setattr(cross_dataset_explorer, "_datasets_for_entity", lambda session, entity_id: {"chilecompra"})

    row = get_cross_dataset_organization_summary(_FakeSession(), str(ORGANIZATION_ID))

    assert row is None


def test_render_cross_dataset_summary_text_matches_cli_contract() -> None:
    report = render_cross_dataset_summary_text((_summary(),))

    assert "cross_dataset_summary:" in report
    assert "organizations_in_multiple_datasets:\n1" in report
    assert "organization:\nSERVICIO DE SALUD ARAUCO" in report
    assert "* ChileCompra" in report
    assert "* Lobby" in report
    assert "lobby_meetings:\n1" in report
    assert "contracts:\n4" in report
    assert "relationships:\n6" in report
    assert "evidence:\n5" in report


def test_cross_dataset_summary_can_include_transparencia(monkeypatch) -> None:
    session = _FakeSession()
    monkeypatch.setattr(
        cross_dataset_explorer,
        "_datasets_for_entity",
        lambda session, entity_id: {"chilecompra", "lobby", "transparencia"},
    )
    monkeypatch.setattr(cross_dataset_explorer, "_claim_ids_for_entity", lambda session, entity_id: ())
    monkeypatch.setattr(
        cross_dataset_explorer,
        "_count_distinct_claim_objects",
        lambda session, entity_id, predicate, dataset_group: 4 if dataset_group == "chilecompra" else 1,
    )
    monkeypatch.setattr(cross_dataset_explorer, "_count_evidence", lambda session, entity_id, claim_ids: 8)
    monkeypatch.setattr(cross_dataset_explorer, "_count_relationships", lambda session, entity_id, claim_ids: 9)
    monkeypatch.setattr(cross_dataset_explorer, "_lobby_connections", lambda session, entity_id: ())
    monkeypatch.setattr(cross_dataset_explorer, "_procurement_connections", lambda session, entity_id: ())

    row = get_cross_dataset_organization_summary(session, str(ORGANIZATION_ID))

    assert row is not None
    assert row.datasets == ("chilecompra", "lobby", "transparencia")
    report = render_cross_dataset_summary_text((row,))
    assert "* Transparencia Activa" in report


def test_cross_dataset_group_recognizes_servel_sample() -> None:
    assert cross_dataset_explorer._dataset_group("servel-authorities-sample") == "servel"
    report = citizen_friendly_explanation()
    assert "elected authority records" in report


def test_render_cross_dataset_connections_text_is_neutral() -> None:
    report = render_cross_dataset_connections_text(_summary())

    assert "Lobby connections:" in report
    assert "* MARLENE FLORES PATINO" in report
    assert "Procurement connections:" in report
    assert "* SKY AIRLINE S.A." in report
    assert "does not imply any relationship beyond the available public information" in report
    forbidden_terms = ("suspicious", "irregular", "conflict", "influence", "corruption", "risk")
    assert not any(term in report.lower() for term in forbidden_terms)


def test_count_evidence_deduplicates_claim_source_record_and_relationship_evidence(monkeypatch) -> None:
    direct_claim = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    lobby_counterparty_claim = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    procurement_supplier_claim = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
    chilecompra_evidence = UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
    lobby_evidence = UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")
    shared_evidence = UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")
    source_record = UUID("99999999-9999-9999-9999-999999999999")

    monkeypatch.setattr(
        cross_dataset_explorer,
        "_cross_dataset_claim_ids",
        lambda session, entity_id, claim_ids: (direct_claim, lobby_counterparty_claim, procurement_supplier_claim),
    )
    monkeypatch.setattr(
        cross_dataset_explorer,
        "_source_record_ids_for_claims",
        lambda session, claim_ids: (source_record,),
    )
    monkeypatch.setattr(
        cross_dataset_explorer,
        "_claim_evidence_ids",
        lambda session, claim_ids: (chilecompra_evidence, shared_evidence),
    )
    monkeypatch.setattr(
        cross_dataset_explorer,
        "_evidence_ids_for_claims",
        lambda session, claim_ids: (lobby_evidence, shared_evidence),
    )
    monkeypatch.setattr(
        cross_dataset_explorer,
        "_evidence_ids_for_source_records",
        lambda session, source_record_ids: (chilecompra_evidence, shared_evidence),
    )

    count = cross_dataset_explorer._count_evidence(_FakeSession(), ORGANIZATION_ID, (direct_claim,))

    assert count == 3
