from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from types import SimpleNamespace
from uuid import UUID

import datosenorden.datasets as datasets
import datosenorden.maintenance.cross_dataset_explorer as cross_dataset_explorer
import datosenorden.maintenance.investigation_view as investigation_view
import datosenorden.maintenance.timeline_explorer as timeline_explorer
from datosenorden.maintenance.contraloria_prototype import (
    CONTROL_REPORT_HAS_OBSERVATION_PREDICATE,
    ORGANIZATION_HAS_CONTROL_REPORT_PREDICATE,
    ContraloriaSummary,
    ContraloriaSummaryRow,
    build_contraloria_sample_batch,
    load_contraloria_sample_payload,
    read_contraloria_summary,
    render_contraloria_summary_text,
)
from datosenorden.maintenance.explanations import graph_explanation_for_chain
from datosenorden.maintenance.explanations import relationship_explanation
from datosenorden.maintenance.municipalidades_prototype import (
    MUNICIPALITY_EXECUTES_PROJECT_PREDICATE,
    MUNICIPALITY_SPENDS_ON_PREDICATE,
    MunicipalidadesSummary,
    MunicipalidadesSummaryRow,
    build_municipalidades_sample_batch,
    load_municipalidades_sample_payload,
    read_municipalidades_summary,
    render_municipalidades_summary_text,
)
from datosenorden.maintenance.timeline_explorer import TimelineClaimRow


class _ScalarResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _BatchSession:
    def __init__(self, entity):
        self._entity = entity

    def get(self, model, identity):  # noqa: ANN001
        _ = model
        if identity == self._entity.id:
            return self._entity
        return None

    def scalar(self, statement):  # noqa: ANN001
        _ = statement
        return None

    def scalars(self, statement):  # noqa: ANN001
        _ = statement
        return _ScalarResult([])


@dataclass(frozen=True)
class _EntityRef:
    id: UUID
    entity_type: str
    name: str
    external_id: str
    description: str | None = None
    normalized_key: str | None = None
    status: str = "active"
    entity_metadata: dict[str, object] | None = None


def test_dataset_catalog_discovers_local_plugins() -> None:
    catalog = datasets.dataset_catalog()
    slugs = {definition.dataset_slug for definition in catalog}

    assert "contraloria" in slugs
    assert "municipalidades" in slugs
    assert "lobby" in slugs


def test_contraloria_sample_payload_contains_required_markers() -> None:
    payload = load_contraloria_sample_payload()

    assert payload["classification"] == "LOCAL_TEST_DATA"
    assert payload["official_status"] == "NOT_OFFICIAL_DATA"
    assert payload["records"][0]["organization_name"] == "DIVISION LOGISTICA DEL EJERCITO"
    assert "LOCAL_TEST_DATA / NOT_OFFICIAL_DATA" in payload["records"][0]["notes"]


def test_municipalidades_sample_payload_contains_required_markers() -> None:
    payload = load_municipalidades_sample_payload()

    assert payload["classification"] == "LOCAL_TEST_DATA"
    assert payload["official_status"] == "NOT_OFFICIAL_DATA"
    assert payload["records"][0]["municipality_name"] == "ILUSTRE MUNICIPALIDAD DE ARAUCO"
    assert "LOCAL_TEST_DATA / NOT_OFFICIAL_DATA" in payload["records"][0]["notes"]


def test_contraloria_sample_batch_is_idempotent(monkeypatch) -> None:
    payload = load_contraloria_sample_payload()
    candidate = SimpleNamespace(
        id=UUID("11111111-1111-1111-1111-111111111111"),
        entity_type="PUBLIC_ORGANIZATION",
        name="DIVISION LOGISTICA DEL EJERCITO",
        external_id="chilecompra:buyer:division-logistica-ejercito",
        description="existing org",
        normalized_key="division-logistica-del-ejercito",
        status="active",
        entity_metadata={"source": "chilecompra"},
        candidate_entity_id="11111111-1111-1111-1111-111111111111",
        candidate_name="DIVISION LOGISTICA DEL EJERCITO",
        match_method="exact_normalized_match",
        score=1.0,
    )
    session = _BatchSession(candidate)
    monkeypatch.setattr(
        "datosenorden.maintenance.contraloria_prototype.match_entity_candidates",
        lambda session, **kwargs: (candidate,),  # noqa: ARG005
    )

    first_batch = build_contraloria_sample_batch(session, payload)
    second_batch = build_contraloria_sample_batch(session, payload)

    store = _IdempotencyStore()
    assert store.apply(first_batch) == store.apply(second_batch)
    assert {claim.predicate for claim in first_batch.claims} == {
        ORGANIZATION_HAS_CONTROL_REPORT_PREDICATE,
        CONTROL_REPORT_HAS_OBSERVATION_PREDICATE,
    }


def test_municipalidades_sample_batch_is_idempotent() -> None:
    payload = load_municipalidades_sample_payload()
    session = _BatchSession(
        _EntityRef(
            id=UUID("22222222-2222-2222-2222-222222222222"),
            entity_type="MUNICIPALITY",
            name="ILUSTRE MUNICIPALIDAD DE ARAUCO",
            external_id="municipalidades:municipality:municipalidades-2026-arauco-project-01",
        )
    )

    first_batch = build_municipalidades_sample_batch(session, payload)
    second_batch = build_municipalidades_sample_batch(session, payload)

    store = _IdempotencyStore()
    assert store.apply(first_batch) == store.apply(second_batch)
    assert {relationship.relationship_type for relationship in first_batch.public_relationships} == {
        MUNICIPALITY_EXECUTES_PROJECT_PREDICATE,
        MUNICIPALITY_SPENDS_ON_PREDICATE,
    }


def test_contraloria_summary_renders_neutral_text(monkeypatch) -> None:
    organization = SimpleNamespace(id=UUID("11111111-1111-1111-1111-111111111111"), name="DIVISION LOGISTICA DEL EJERCITO")
    report = SimpleNamespace(id=UUID("22222222-2222-2222-2222-222222222222"), name="Revision de control administrativo de muestra")
    observation = SimpleNamespace(id=UUID("33333333-3333-3333-3333-333333333333"), name="Observation 24-2026 - DIVISION LOGISTICA DEL EJERCITO")
    source_record = SimpleNamespace(id=UUID("44444444-4444-4444-4444-444444444444"))
    report_claim = SimpleNamespace(
        subject_entity=organization,
        object_entity=report,
        source_record=source_record,
        valid_from=date(2026, 4, 20),
        predicate=ORGANIZATION_HAS_CONTROL_REPORT_PREDICATE,
        confidence=1.0,
    )
    observation_claim = SimpleNamespace(
        subject_entity=observation,
        object_entity=None,
        source_record=source_record,
        valid_from=date(2026, 4, 21),
        predicate=CONTROL_REPORT_HAS_OBSERVATION_PREDICATE,
    )
    relationships = (
        SimpleNamespace(
            relationship_type=ORGANIZATION_HAS_CONTROL_REPORT_PREDICATE,
            relationship_metadata={"match_method": "exact_normalized_match", "match_confidence": 1.0},
        ),
        SimpleNamespace(
            relationship_type=CONTROL_REPORT_HAS_OBSERVATION_PREDICATE,
            relationship_metadata={},
        ),
    )
    monkeypatch.setattr(
        "datosenorden.maintenance.contraloria_prototype._load_report_claims",
        lambda session: [report_claim],
    )
    monkeypatch.setattr(
        "datosenorden.maintenance.contraloria_prototype._load_observation_claim",
        lambda session, source_record_id: observation_claim,
    )
    monkeypatch.setattr(
        "datosenorden.maintenance.contraloria_prototype._load_contraloria_relationships",
        lambda session, source_record_id: relationships,
    )
    monkeypatch.setattr(
        "datosenorden.maintenance.contraloria_prototype._count_evidence_for_source_record",
        lambda session, source_record_id: 2,
    )

    summary = read_contraloria_summary(object())

    assert summary.organizations == 1
    assert summary.reports == 1
    assert summary.observations == 1
    assert summary.claims == 2
    assert summary.relationships == 2
    assert summary.evidence == 2
    assert summary.rows[0].organization_name == organization.name
    assert summary.rows[0].report_name == report.name
    assert summary.rows[0].observation_name == observation.name
    assert summary.rows[0].claims == (
        ORGANIZATION_HAS_CONTROL_REPORT_PREDICATE,
        CONTROL_REPORT_HAS_OBSERVATION_PREDICATE,
    )
    assert summary.rows[0].relationships == (
        ORGANIZATION_HAS_CONTROL_REPORT_PREDICATE,
        CONTROL_REPORT_HAS_OBSERVATION_PREDICATE,
    )
    assert summary.rows[0].organization_match_method == "exact_normalized_match"
    assert summary.rows[0].organization_match_confidence == 1.0

    report_text = render_contraloria_summary_text(summary)
    assert "contraloria_summary:" in report_text
    assert "organization=DIVISION LOGISTICA DEL EJERCITO" in report_text
    assert "report=Revision de control administrativo de muestra" in report_text
    assert "observation=Observation 24-2026 - DIVISION LOGISTICA DEL EJERCITO" in report_text


def test_municipalidades_summary_renders_neutral_text(monkeypatch) -> None:
    municipality = SimpleNamespace(id=UUID("55555555-5555-5555-5555-555555555555"), name="ILUSTRE MUNICIPALIDAD DE ARAUCO")
    project = SimpleNamespace(id=UUID("66666666-6666-6666-6666-666666666666"), name="Mejoramiento de plaza local de muestra")
    spending_item = SimpleNamespace(id=UUID("77777777-7777-7777-7777-777777777777"), name="Compra de materiales de mantencion")
    source_record = SimpleNamespace(id=UUID("88888888-8888-8888-8888-888888888888"))
    project_claim = SimpleNamespace(
        subject_entity=municipality,
        object_entity=project,
        source_record=source_record,
        valid_from=date(2026, 5, 1),
        predicate=MUNICIPALITY_EXECUTES_PROJECT_PREDICATE,
    )
    spending_claim = SimpleNamespace(
        subject_entity=municipality,
        object_entity=spending_item,
        source_record=source_record,
        valid_from=date(2026, 5, 1),
        predicate=MUNICIPALITY_SPENDS_ON_PREDICATE,
    )
    relationships = (
        SimpleNamespace(
            relationship_type=MUNICIPALITY_EXECUTES_PROJECT_PREDICATE,
            relationship_metadata={},
        ),
        SimpleNamespace(
            relationship_type=MUNICIPALITY_SPENDS_ON_PREDICATE,
            relationship_metadata={},
        ),
    )
    monkeypatch.setattr(
        "datosenorden.maintenance.municipalidades_prototype._load_project_claims",
        lambda session: [project_claim],
    )
    monkeypatch.setattr(
        "datosenorden.maintenance.municipalidades_prototype._load_spending_claim",
        lambda session, source_record_id: spending_claim,
    )
    monkeypatch.setattr(
        "datosenorden.maintenance.municipalidades_prototype._load_municipalidades_relationships",
        lambda session, source_record_id: relationships,
    )
    monkeypatch.setattr(
        "datosenorden.maintenance.municipalidades_prototype._count_evidence_for_source_record",
        lambda session, source_record_id: 2,
    )

    summary = read_municipalidades_summary(object())

    assert summary.municipalities == 1
    assert summary.projects == 1
    assert summary.spending_items == 1
    assert summary.claims == 2
    assert summary.relationships == 2
    assert summary.evidence == 2
    assert summary.rows[0].municipality_name == municipality.name
    assert summary.rows[0].project_name == project.name
    assert summary.rows[0].spending_item_name == spending_item.name
    assert summary.rows[0].claims == (
        MUNICIPALITY_EXECUTES_PROJECT_PREDICATE,
        MUNICIPALITY_SPENDS_ON_PREDICATE,
    )
    assert summary.rows[0].relationships == (
        MUNICIPALITY_EXECUTES_PROJECT_PREDICATE,
        MUNICIPALITY_SPENDS_ON_PREDICATE,
    )

    report_text = render_municipalidades_summary_text(summary)
    assert "municipalidades_summary:" in report_text
    assert "municipality=ILUSTRE MUNICIPALIDAD DE ARAUCO" in report_text
    assert "project=Mejoramiento de plaza local de muestra" in report_text


def test_cross_dataset_and_timeline_helpers_include_new_local_datasets() -> None:
    assert cross_dataset_explorer._dataset_group("contraloria-control-report-sample") == "contraloria"
    assert cross_dataset_explorer._dataset_group("municipalidades-project-sample") == "municipalidades"
    assert timeline_explorer._dataset_badge("contraloria-control-report-sample") == "CONTRALORIA"
    assert timeline_explorer._dataset_badge("municipalidades-project-sample") == "MUNICIPALIDADES"


def test_investigation_helpers_label_new_datasets_without_special_case() -> None:
    claims = (
        SimpleNamespace(
            source_record=SimpleNamespace(dataset=SimpleNamespace(name="contraloria-control-report-sample")),
            predicate=ORGANIZATION_HAS_CONTROL_REPORT_PREDICATE,
        ),
        SimpleNamespace(
            source_record=SimpleNamespace(dataset=SimpleNamespace(name="municipalidades-project-sample")),
            predicate=MUNICIPALITY_EXECUTES_PROJECT_PREDICATE,
        ),
    )
    badges = investigation_view._dataset_badges_for_claims(claims)  # noqa: SLF001

    assert badges == ("Contraloria", "Municipalidades")
    assert graph_explanation_for_chain(("PUBLIC_ORGANIZATION", "CONTROL_REPORT", "PUBLIC_OBSERVATION")).startswith(
        "El organismo aparece vinculado a un informe de control"
    )


def test_relationship_explanations_are_neutral() -> None:
    report = relationship_explanation("CONTROL_REPORT_HAS_OBSERVATION")
    assert "observaciones registradas" in report
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
