from __future__ import annotations

from datosenorden.maintenance.diario_oficial_prototype import (
    DECREE_APPLIES_TO_ORGANIZATION_PREDICATE,
    DIARIO_SAMPLE_DATASET_NAME,
    PERSON_APPOINTED_TO_PUBLIC_OFFICE_PREDICATE,
    PERSON_RESIGNED_FROM_PUBLIC_OFFICE_PREDICATE,
    load_diario_oficial_sample_payload,
    build_diario_oficial_sample_batch,
    render_diario_oficial_summary_text,
)


class _ScalarResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _NullSession:
    def get(self, *args, **kwargs):  # noqa: ANN001
        _ = (args, kwargs)
        return None

    def scalar(self, *args, **kwargs):  # noqa: ANN001
        _ = (args, kwargs)
        return None

    def scalars(self, *args, **kwargs):  # noqa: ANN001
        _ = (args, kwargs)
        return _ScalarResult([])


def test_diario_oficial_sample_payload_contains_required_markers() -> None:
    payload = load_diario_oficial_sample_payload()

    assert payload["classification"] == "LOCAL_TEST_DATA"
    assert payload["official_status"] == "NOT_OFFICIAL_DATA"
    assert payload["records"][0]["person_name"] == "Persona de Muestra Uno"
    assert "local://sample/diario-oficial" in payload["records"][0]["source_url"]


def test_diario_oficial_sample_batch_uses_neutral_relationship_types() -> None:
    payload = load_diario_oficial_sample_payload()
    batch = build_diario_oficial_sample_batch(_NullSession(), payload)

    relationship_types = {relationship.relationship_type.value for relationship in batch.public_relationships}

    assert DIARIO_SAMPLE_DATASET_NAME == batch.dataset.name
    assert PERSON_APPOINTED_TO_PUBLIC_OFFICE_PREDICATE in {claim.predicate for claim in batch.claims}
    assert PERSON_RESIGNED_FROM_PUBLIC_OFFICE_PREDICATE in {claim.predicate for claim in batch.claims}
    assert DECREE_APPLIES_TO_ORGANIZATION_PREDICATE in {claim.predicate for claim in batch.claims}
    assert relationship_types >= {
        PERSON_APPOINTED_TO_PUBLIC_OFFICE_PREDICATE,
        PERSON_RESIGNED_FROM_PUBLIC_OFFICE_PREDICATE,
        DECREE_APPLIES_TO_ORGANIZATION_PREDICATE,
        "OFFICIAL_PUBLICATION_REFERENCES_ENTITY",
        "PUBLIC_OFFICE_BELONGS_TO_ORGANIZATION",
    }


def test_diario_oficial_summary_text_is_neutral() -> None:
    summary = render_diario_oficial_summary_text(
        type(
            "Summary",
            (),
            {
                "publications": 2,
                "people": 2,
                "offices": 2,
                "organizations": 2,
                "relationships": 5,
                "evidence": 8,
                "rows": (),
            },
        )()
    )

    assert "diario_oficial_summary:" in summary
    assert "publications=2" in summary
    forbidden_terms = ("accus", "irregular", "risk", "suspicious", "corrupt", "fraud")
    assert not any(term in summary.lower() for term in forbidden_terms)
