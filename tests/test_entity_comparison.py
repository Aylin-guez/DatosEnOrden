from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from uuid import UUID

import datosenorden.maintenance.entity_comparison as entity_comparison
import datosenorden.web.app_services as app_services


class _SessionContext:
    def __enter__(self):  # noqa: ANN001
        return object()

    def __exit__(self, exc_type, exc, tb):  # noqa: ANN001
        _ = (exc_type, exc, tb)
        return False


@dataclass(frozen=True)
class _ComparisonFixture:
    entity: SimpleNamespace
    claim_rows: tuple[tuple[SimpleNamespace, str], ...]
    relationship_rows: tuple[tuple[SimpleNamespace, str], ...]
    evidence_rows: tuple[tuple[SimpleNamespace, str], ...]


def test_build_entity_comparison_reports_one_dataset_neutrally(monkeypatch) -> None:
    fixture = _one_dataset_fixture()
    _patch_comparison_fixture(monkeypatch, fixture)

    report = entity_comparison.build_entity_comparison(str(fixture.entity.id))

    assert report["entity_name"] == fixture.entity.name
    assert report["entity_type"] == fixture.entity.entity_type
    assert report["datasets_present"] == ["ChileCompra"]
    assert report["dataset_facts"][0]["dataset"] == "ChileCompra"
    assert report["dataset_facts"][0]["headline"] == "ChileCompra records"
    assert any("procurement activity" in fact.lower() for fact in report["dataset_facts"][0]["facts"])
    assert report["consistency_observations"][0] == "This organization appears in ChileCompra records."
    assert report["consistency_observations"][1] == "This organization appears only in procurement records."
    assert "ChileCompra" in report["coverage_summary"]
    _assert_neutral(report)


def test_build_entity_comparison_reports_multiple_sources(monkeypatch) -> None:
    fixture = _multiple_sources_fixture()
    _patch_comparison_fixture(monkeypatch, fixture)

    report = entity_comparison.build_entity_comparison(str(fixture.entity.id))

    assert set(report["datasets_present"]) == {
        "ChileCompra",
        "Lobby",
        "Transparencia Activa",
        "Contraloria",
        "Municipalidades",
        "SERVEL",
    }
    assert report["dataset_facts"][0]["dataset"] in report["datasets_present"]
    assert any(
        obs == "The organization appears in procurement records, registered meetings, and transparency records."
        for obs in report["consistency_observations"]
    )
    assert "Contraloria records contain observations related to the organization." in report["consistency_observations"]
    assert "Municipal records reference the organization." in report["consistency_observations"]
    assert "6 public sources" in report["coverage_summary"]
    assert any(fact["dataset"] == "SERVEL" for fact in report["dataset_facts"])
    assert any(
        "elected authorities" in sentence.lower()
        for fact in report["dataset_facts"]
        for sentence in fact["facts"]
    )
    _assert_neutral(report)


def test_build_entity_comparison_uses_registry_labels_for_plugin_discovery(monkeypatch) -> None:
    fixture = _plugin_fixture()
    _patch_comparison_fixture(monkeypatch, fixture)

    monkeypatch.setattr(
        entity_comparison.datasets,
        "dataset_label_for_name",
        lambda dataset_name: "Custom Registry Label" if dataset_name == "custom-source-sample" else dataset_name,
    )

    report = entity_comparison.build_entity_comparison(str(fixture.entity.id))

    assert report["datasets_present"] == ["Custom Registry Label"]
    assert report["dataset_facts"][0]["headline"] == "Custom Registry Label records"
    assert "Custom Registry Label" in report["coverage_summary"]
    _assert_neutral(report)


def test_get_entity_comparison_passthrough(monkeypatch) -> None:
    payload = {
        "entity_name": "Demo entity",
        "entity_type": "PUBLIC_ORGANIZATION",
        "datasets_present": ["ChileCompra"],
        "dataset_facts": [],
        "consistency_observations": [],
        "coverage_summary": "Demo summary.",
    }
    monkeypatch.setattr(app_services, "build_entity_comparison", lambda entity_id: payload)

    result = app_services.get_entity_comparison("11111111-1111-1111-1111-111111111111")

    assert result == payload


def _patch_comparison_fixture(monkeypatch, fixture: _ComparisonFixture) -> None:
    monkeypatch.setattr(entity_comparison, "SessionLocal", lambda: _SessionContext())
    monkeypatch.setattr(entity_comparison, "_load_entity", lambda session, entity_id: fixture.entity)
    monkeypatch.setattr(entity_comparison, "_load_entity_claim_rows", lambda session, entity_id: fixture.claim_rows)
    monkeypatch.setattr(
        entity_comparison,
        "_load_entity_relationship_rows",
        lambda session, entity_id: fixture.relationship_rows,
    )
    monkeypatch.setattr(entity_comparison, "_load_entity_evidence_rows", lambda session, claim_ids: fixture.evidence_rows)


def _assert_neutral(report: dict[str, object]) -> None:
    text = _flatten(report).lower()
    bad_terms = (
        "accus",
        "accuse",
        "culp",
        "corrupt",
        "fraud",
        "illicit",
        "irregular",
        "risk",
        "suspicious",
        "wrongdo",
    )
    assert not any(term in text for term in bad_terms)


def _flatten(value: object) -> str:
    if isinstance(value, dict):
        return " ".join(_flatten(item) for item in value.values())
    if isinstance(value, list | tuple | set):
        return " ".join(_flatten(item) for item in value)
    return str(value)


def _one_dataset_fixture() -> _ComparisonFixture:
    entity = _entity()
    source_record_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    claim1 = _claim("11111111-1111-1111-1111-111111111111", source_record_id, "ISSUES_PURCHASE_ORDER")
    claim2 = _claim("22222222-2222-2222-2222-222222222222", source_record_id, "RECEIVES_CONTRACT")
    relationship = _relationship("33333333-3333-3333-3333-333333333333", "RECEIVES_CONTRACT")
    evidence = _evidence("44444444-4444-4444-4444-444444444444")
    return _ComparisonFixture(
        entity=entity,
        claim_rows=(
            (claim1, "chilecompra-ordenes-compra"),
            (claim2, "chilecompra-licitaciones"),
        ),
        relationship_rows=((relationship, "chilecompra-ordenes-compra"),),
        evidence_rows=((evidence, "chilecompra-ordenes-compra"),),
    )


def _multiple_sources_fixture() -> _ComparisonFixture:
    entity = _entity()
    source_record_id = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    return _ComparisonFixture(
        entity=entity,
        claim_rows=(
            (_claim("11111111-1111-1111-1111-111111111111", source_record_id, "ISSUES_PURCHASE_ORDER"), "chilecompra-ordenes-compra"),
            (_claim("22222222-2222-2222-2222-222222222222", source_record_id, "ORGANIZATION_HELD_LOBBY_MEETING"), "lobby-meeting-sample"),
            (_claim("33333333-3333-3333-3333-333333333333", source_record_id, "ORGANIZATION_HAS_PUBLIC_ROLE"), "transparencia-activa-sample"),
            (_claim("44444444-4444-4444-4444-444444444444", source_record_id, "ORGANIZATION_HAS_CONTROL_REPORT"), "contraloria-control-report-sample"),
            (_claim("55555555-5555-5555-5555-555555555555", source_record_id, "MUNICIPALITY_EXECUTES_PROJECT"), "municipalidades-project-sample"),
            (_claim("66666666-6666-6666-6666-666666666666", source_record_id, "AUTHORITY_ELECTED_TO_OFFICE"), "servel-authorities-sample"),
        ),
        relationship_rows=(
            (_relationship("61111111-1111-1111-1111-111111111111", "ISSUES_PURCHASE_ORDER"), "chilecompra-ordenes-compra"),
            (_relationship("62222222-2222-2222-2222-222222222222", "ORGANIZATION_HELD_LOBBY_MEETING"), "lobby-meeting-sample"),
            (_relationship("63333333-3333-3333-3333-333333333333", "ORGANIZATION_HAS_PUBLIC_ROLE"), "transparencia-activa-sample"),
            (_relationship("64444444-4444-4444-4444-444444444444", "ORGANIZATION_HAS_CONTROL_REPORT"), "contraloria-control-report-sample"),
            (_relationship("65555555-5555-5555-5555-555555555555", "MUNICIPALITY_EXECUTES_PROJECT"), "municipalidades-project-sample"),
            (_relationship("66666666-6666-6666-6666-666666666667", "AUTHORITY_ELECTED_TO_OFFICE"), "servel-authorities-sample"),
        ),
        evidence_rows=(
            (_evidence("71111111-1111-1111-1111-111111111111"), "chilecompra-ordenes-compra"),
            (_evidence("72222222-2222-2222-2222-222222222222"), "lobby-meeting-sample"),
            (_evidence("73333333-3333-3333-3333-333333333333"), "transparencia-activa-sample"),
            (_evidence("74444444-4444-4444-4444-444444444444"), "contraloria-control-report-sample"),
            (_evidence("75555555-5555-5555-5555-555555555555"), "municipalidades-project-sample"),
            (_evidence("76666666-6666-6666-6666-666666666666"), "servel-authorities-sample"),
        ),
    )


def _plugin_fixture() -> _ComparisonFixture:
    entity = _entity(entity_id="99999999-9999-9999-9999-999999999999", name="Custom Organization")
    source_record_id = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
    claim = _claim("88888888-8888-8888-8888-888888888888", source_record_id, "CUSTOM_ACTIVITY")
    relationship = _relationship("77777777-7777-7777-7777-777777777777", "CUSTOM_ACTIVITY")
    evidence = _evidence("66666666-6666-6666-6666-666666666666")
    return _ComparisonFixture(
        entity=entity,
        claim_rows=((claim, "custom-source-sample"),),
        relationship_rows=((relationship, "custom-source-sample"),),
        evidence_rows=((evidence, "custom-source-sample"),),
    )


def _entity(
    *,
    entity_id: str = "12345678-1234-1234-1234-123456789012",
    name: str = "DIVISION LOGISTICA DEL EJERCITO",
    entity_type: str = "PUBLIC_ORGANIZATION",
) -> SimpleNamespace:
    return SimpleNamespace(id=UUID(entity_id), name=name, entity_type=entity_type)


def _claim(claim_id: str, source_record_id: UUID, predicate: str) -> SimpleNamespace:
    return SimpleNamespace(id=UUID(claim_id), source_record_id=source_record_id, predicate=predicate)


def _relationship(relationship_id: str, relationship_type: str) -> SimpleNamespace:
    return SimpleNamespace(id=UUID(relationship_id), relationship_type=relationship_type)


def _evidence(evidence_id: str) -> SimpleNamespace:
    return SimpleNamespace(id=UUID(evidence_id))
