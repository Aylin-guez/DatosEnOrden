from pathlib import Path
from types import SimpleNamespace

import datosenorden.application.provenance.public_views as public_views
import datosenorden.application.provenance.service as provenance
from datosenorden.application.provenance.models import ProvenanceClass


def _row(**values):
    return SimpleNamespace(**values)


def test_public_metrics_count_only_usable_real_content(monkeypatch) -> None:
    real_record = _row(id="real", status="published")
    rejected_real = _row(id="rejected", status="rejected")
    demo_record = _row(id="demo", status="published")
    test_record = _row(id="test", status="published")
    unknown_record = _row(id="unknown", status="published")
    real_claim = _row(id="claim-real", source_record_id="real", status="published", subject_entity_id="supplier", object_entity_id=None, predicate="RECEIVES_CONTRACT")
    rejected_claim = _row(id="claim-rejected", source_record_id="rejected", status="published", subject_entity_id="rejected-supplier", object_entity_id=None, predicate="RECEIVES_CONTRACT")
    demo_claim = _row(id="claim-demo", source_record_id="demo", status="published", subject_entity_id="demo-supplier", object_entity_id=None, predicate="RECEIVES_CONTRACT")
    test_claim = _row(id="claim-test", source_record_id="test", status="published", subject_entity_id="test-supplier", object_entity_id=None, predicate="RECEIVES_CONTRACT")
    unknown_claim = _row(id="claim-unknown", source_record_id="unknown", status="published", subject_entity_id="unknown-supplier", object_entity_id=None, predicate="RECEIVES_CONTRACT")
    real_relationship = _row(id="relationship-real", claim_id="claim-real", status="published")
    rejected_relationship = _row(id="relationship-rejected", claim_id="claim-rejected", status="published")
    demo_relationship = _row(id="relationship-demo", claim_id="claim-demo", status="published")
    test_relationship = _row(id="relationship-test", claim_id="claim-test", status="published")
    unknown_relationship = _row(id="relationship-unknown", claim_id="claim-unknown", status="published")
    real_evidence = _row(id="evidence-real", source_record_id="real")
    entities = tuple(_row(id=item, entity_type="COMPANY") for item in ("supplier", "rejected-supplier", "demo-supplier", "test-supplier", "unknown-supplier"))
    records = (real_record, rejected_real, demo_record, test_record, unknown_record)
    claims = (real_claim, rejected_claim, demo_claim, test_claim, unknown_claim)
    relationships = (real_relationship, rejected_relationship, demo_relationship, test_relationship, unknown_relationship)
    decisions = {
        "real": ProvenanceClass.REAL,
        "rejected": ProvenanceClass.REAL,
        "demo": ProvenanceClass.DEMO,
        "test": ProvenanceClass.TEST,
        "unknown": ProvenanceClass.UNKNOWN,
    }
    monkeypatch.setattr(
        provenance,
        "_classified_content",
        lambda session: (
            (), records, (real_evidence,), claims, relationships, entities,
            {key: provenance._decision(provenance.PROVENANCE_MANIFEST[0]) if value is ProvenanceClass.REAL else provenance._unknown("record", key) for key, value in decisions.items()},
            {"evidence-real": provenance._decision(provenance.PROVENANCE_MANIFEST[0])},
            {"claim-real": ProvenanceClass.REAL, "claim-rejected": ProvenanceClass.REAL, "claim-demo": ProvenanceClass.DEMO, "claim-test": ProvenanceClass.TEST, "claim-unknown": ProvenanceClass.UNKNOWN},
            {"relationship-real": ProvenanceClass.REAL, "relationship-rejected": ProvenanceClass.REAL, "relationship-demo": ProvenanceClass.DEMO, "relationship-test": ProvenanceClass.TEST, "relationship-unknown": ProvenanceClass.UNKNOWN},
            {},
        ),
    )

    metrics = provenance.build_public_metric_projection(object())

    assert metrics == {
        "source_records": 1,
        "claims": 1,
        "evidences": 1,
        "relationships": 1,
        "entities": 1,
        "suppliers": 1,
        "contracts": 1,
        "meetings": 0,
        "authorities": 0,
        "documents": 1,
        "expedients": 0,
    }


def test_public_metric_authority_has_no_payload_marker_heuristic() -> None:
    source = Path(str(provenance.__file__)).read_text(encoding="utf-8")

    assert "_datosenorden_data_classification" not in source


def test_public_dataset_view_uses_only_provenance_metrics(monkeypatch) -> None:
    monkeypatch.setattr(
        public_views,
        "build_provenance_snapshot",
        lambda session: SimpleNamespace(source_metrics=({
            "source_label": "ChileCompra",
            "available_real_records": 1,
            "real_entities": 2,
            "real_claims": 3,
            "real_evidence": 4,
            "real_relationships": 5,
        },)),
    )
    monkeypatch.setattr(
        public_views,
        "build_public_metric_projection",
        lambda session: {
            "source_records": 1,
            "entities": 2,
            "claims": 3,
            "evidences": 4,
            "relationships": 5,
            "documents": 1,
            "expedients": 0,
        },
    )

    result = public_views.build_public_dataset_summary(
        object(),
        [{"name": "ChileCompra", "source_records": 99, "health": "active"}],
    )

    assert result["datasets"][0]["source_records"] == 1
    assert result["datasets"][0]["relationships"] == 5
    assert result["totals"]["active_datasets"] == 1


def test_public_ecosystem_marks_uningested_sources_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(
        public_views,
        "build_provenance_snapshot",
        lambda session: SimpleNamespace(source_metrics=()),
    )
    ecosystem = {"sources": [{"name": "InfoLobby", "status": "active"}]}

    result = public_views.enrich_public_ecosystem(object(), ecosystem)

    assert result["sources"][0]["real_available_records"] == 0
    assert result["sources"][0]["provenance_status"] == "UNKNOWN"
