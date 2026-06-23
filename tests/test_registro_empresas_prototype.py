from __future__ import annotations

from datosenorden.maintenance.registro_empresas_prototype import (
    COMPANY_MODIFIED_ON_PREDICATE,
    COMPANY_REGISTERED_ON_PREDICATE,
    PERSON_OWNS_COMPANY_PREDICATE,
    PERSON_REPRESENTS_COMPANY_PREDICATE,
    REGISTRO_SAMPLE_DATASET_NAME,
    build_registro_empresas_sample_batch,
    load_registro_empresas_sample_payload,
    render_registro_empresas_summary_text,
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


def test_registro_empresas_sample_payload_contains_required_markers() -> None:
    payload = load_registro_empresas_sample_payload()

    assert payload["classification"] == "LOCAL_TEST_DATA"
    assert payload["official_status"] == "NOT_OFFICIAL_DATA"
    assert payload["records"][0]["company_name"] == "ACME TECNOLOGIAS SPA"
    assert "local://sample/registro-empresas" in payload["records"][0]["source_url"]


def test_registro_empresas_sample_batch_uses_neutral_relationship_types() -> None:
    payload = load_registro_empresas_sample_payload()
    batch = build_registro_empresas_sample_batch(_NullSession(), payload)

    relationship_types = {relationship.relationship_type.value for relationship in batch.public_relationships}
    claim_predicates = {claim.predicate for claim in batch.claims}

    assert REGISTRO_SAMPLE_DATASET_NAME == batch.dataset.name
    assert PERSON_REPRESENTS_COMPANY_PREDICATE in claim_predicates
    assert PERSON_OWNS_COMPANY_PREDICATE in claim_predicates
    assert COMPANY_REGISTERED_ON_PREDICATE in claim_predicates
    assert COMPANY_MODIFIED_ON_PREDICATE in claim_predicates
    assert relationship_types >= {
        PERSON_REPRESENTS_COMPANY_PREDICATE,
        PERSON_OWNS_COMPANY_PREDICATE,
        COMPANY_REGISTERED_ON_PREDICATE,
        COMPANY_MODIFIED_ON_PREDICATE,
    }


def test_registro_empresas_summary_text_is_neutral() -> None:
    summary = render_registro_empresas_summary_text(
        type(
            "Summary",
            (),
            {
                "companies": 2,
                "people": 3,
                "representatives": 2,
                "owners": 3,
                "relationships": 6,
                "evidence": 6,
                "rows": (),
            },
        )()
    )

    assert "registro_empresas_summary:" in summary
    assert "companies=2" in summary
    forbidden_terms = ("accus", "irregular", "risk", "suspicious", "corrupt", "fraud")
    assert not any(term in summary.lower() for term in forbidden_terms)
