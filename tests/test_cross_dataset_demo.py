from __future__ import annotations

import json
from types import SimpleNamespace
from uuid import UUID

import datosenorden.maintenance.cross_dataset_demo as cross_dataset_demo
import datosenorden.maintenance.cross_dataset_explorer as cross_dataset_explorer
from datosenorden.maintenance.cross_dataset_demo import DatasetOrganization
from datosenorden.maintenance.cross_dataset_demo import align_lobby_sample_to_existing_org
from datosenorden.maintenance.cross_dataset_demo import debug_cross_dataset_matches
from datosenorden.maintenance.cross_dataset_demo import render_cross_dataset_match_diagnostic_text
from datosenorden.maintenance.entity_matching import EntityMatchCandidate


ORGANIZATION_ID = UUID("11111111-1111-1111-1111-111111111111")


class _AlignmentSession:
    def __init__(self, organization_name: str = "SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO") -> None:
        self.organization = SimpleNamespace(
            id=ORGANIZATION_ID,
            entity_type="PUBLIC_ORGANIZATION",
            name=organization_name,
        )

    def scalar(self, statement):  # noqa: ANN001
        _ = statement
        return self.organization


def _sample_payload(organization_name: str = "SERVICIO DE SALUD ARAUCO") -> dict:
    return {
        "classification": "LOCAL_TEST_DATA",
        "official_status": "NOT_OFFICIAL_DATA",
        "dataset_name": "lobby-meeting-sample",
        "source_name": "DatosEnOrden Lobby Sample",
        "records": [
            {
                "external_id": "lobby-sample-2026-demo",
                "organization_name": organization_name,
                "counterparty_name": "MARLENE BEATRIZ FLORES PATINO",
                "counterparty_type": "COMPANY",
                "meeting_subject": "Presentacion de servicios",
                "meeting_date": "2026-03-15",
                "meeting_location": "Arauco, Chile",
                "source_url": "local://sample/lobby-meeting/lobby-sample-2026-demo",
                "source_dataset_name": "lobby-meeting-sample",
                "notes": "LOCAL_TEST_DATA / NOT_OFFICIAL_DATA sample.",
            }
        ],
    }


def test_debug_cross_dataset_matches_reports_no_lobby_records(monkeypatch) -> None:
    chilecompra_org = DatasetOrganization(
        entity_id=str(ORGANIZATION_ID),
        name="SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO",
        normalized_name="SERVICIO SALUD ARAUCO HOSPITAL ARAUCO",
        dataset="chilecompra",
    )
    monkeypatch.setattr(
        cross_dataset_demo,
        "_organizations_for_dataset",
        lambda session, dataset: (chilecompra_org,) if dataset == "chilecompra" else (),
    )

    diagnostic = debug_cross_dataset_matches(object())
    report = render_cross_dataset_match_diagnostic_text(diagnostic)

    assert diagnostic.shared_organization_ids == ()
    assert "No Lobby PUBLIC_ORGANIZATION records were found" in diagnostic.reason
    assert "chilecompra_organizations:" in report
    assert "lobby_organizations:" in report
    assert "normalized_name=SERVICIO SALUD ARAUCO HOSPITAL ARAUCO" in report


def test_debug_cross_dataset_matches_reports_candidate_without_shared_entity(monkeypatch) -> None:
    chilecompra_org = DatasetOrganization(
        entity_id=str(ORGANIZATION_ID),
        name="SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO",
        normalized_name="SERVICIO SALUD ARAUCO HOSPITAL ARAUCO",
        dataset="chilecompra",
    )
    lobby_org = DatasetOrganization(
        entity_id="22222222-2222-2222-2222-222222222222",
        name="SERVICIO DE SALUD ARAUCO",
        normalized_name="SERVICIO SALUD ARAUCO",
        dataset="lobby",
    )
    candidate = EntityMatchCandidate(
        candidate_entity_id=str(ORGANIZATION_ID),
        candidate_name=chilecompra_org.name,
        entity_type="PUBLIC_ORGANIZATION",
        score=0.95,
        match_method="contains_normalized_match",
        explanation="One normalized name contains the other.",
    )
    monkeypatch.setattr(
        cross_dataset_demo,
        "_organizations_for_dataset",
        lambda session, dataset: (chilecompra_org,) if dataset == "chilecompra" else (lobby_org,),
    )
    monkeypatch.setattr(cross_dataset_demo, "match_entity_candidates", lambda session, **kwargs: (candidate,))

    diagnostic = debug_cross_dataset_matches(object())
    report = render_cross_dataset_match_diagnostic_text(diagnostic)

    assert diagnostic.shared_organization_ids == ()
    assert "candidate ChileCompra matches" in diagnostic.reason
    assert "closest_candidate_matches:" in report
    assert "candidate_name=SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO" in report
    assert "match_method=contains_normalized_match" in report


def test_align_lobby_sample_to_existing_org_updates_only_local_sample(tmp_path) -> None:
    sample_path = tmp_path / "lobby_meeting_sample.json"
    sample_path.write_text(json.dumps(_sample_payload(), indent=2), encoding="utf-8")

    result = align_lobby_sample_to_existing_org(_AlignmentSession(), sample_path=sample_path)
    payload = json.loads(sample_path.read_text(encoding="utf-8"))

    assert result.changed is True
    assert result.organization_name == "SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO"
    assert payload["classification"] == "LOCAL_TEST_DATA"
    assert payload["official_status"] == "NOT_OFFICIAL_DATA"
    assert payload["records"][0]["organization_name"] == "SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO"
    assert "LOCAL_TEST_DATA / NOT_OFFICIAL_DATA sample aligned" in payload["records"][0]["notes"]


def test_align_lobby_sample_to_existing_org_is_idempotent(tmp_path) -> None:
    sample_path = tmp_path / "lobby_meeting_sample.json"
    payload = _sample_payload("SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO")
    sample_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    first = align_lobby_sample_to_existing_org(_AlignmentSession(), sample_path=sample_path)
    first_content = sample_path.read_text(encoding="utf-8")
    second = align_lobby_sample_to_existing_org(_AlignmentSession(), sample_path=sample_path)
    second_content = sample_path.read_text(encoding="utf-8")

    assert first.changed is False
    assert second.changed is False
    assert first_content == second_content


def test_cross_dataset_summary_detects_shared_organization_after_aligned_sample(monkeypatch) -> None:
    monkeypatch.setattr(cross_dataset_explorer, "_organization_ids_in_multiple_datasets", lambda session: (ORGANIZATION_ID,))
    monkeypatch.setattr(cross_dataset_explorer, "_datasets_for_entity", lambda session, entity_id: {"chilecompra", "lobby"})
    monkeypatch.setattr(cross_dataset_explorer, "_claim_ids_for_entity", lambda session, entity_id: ())
    monkeypatch.setattr(
        cross_dataset_explorer,
        "_count_distinct_claim_objects",
        lambda session, entity_id, predicate, dataset_group: 4 if dataset_group == "chilecompra" else 1,
    )
    monkeypatch.setattr(cross_dataset_explorer, "_count_evidence", lambda session, entity_id, claim_ids: 5)
    monkeypatch.setattr(cross_dataset_explorer, "_count_relationships", lambda session, entity_id, claim_ids: 6)
    monkeypatch.setattr(cross_dataset_explorer, "_lobby_connections", lambda session, entity_id: ())
    monkeypatch.setattr(cross_dataset_explorer, "_procurement_connections", lambda session, entity_id: ())
    session = SimpleNamespace(get=lambda model, identity: SimpleNamespace(id=ORGANIZATION_ID, name="SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO"))

    rows = cross_dataset_explorer.list_cross_dataset_organizations(session)

    assert len(rows) == 1
    assert rows[0].organization_name == "SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO"
    assert rows[0].datasets == ("chilecompra", "lobby")
