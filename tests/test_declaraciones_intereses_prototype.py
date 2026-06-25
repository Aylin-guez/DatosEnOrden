from __future__ import annotations

from datosenorden.maintenance.declaraciones_intereses_prototype import DECLARATION_REFERENCES_COMPANY_PREDICATE
from datosenorden.maintenance.declaraciones_intereses_prototype import PERSON_HAS_DECLARATION_PREDICATE
from datosenorden.maintenance.declaraciones_intereses_prototype import build_declaraciones_intereses_sample_batch
from datosenorden.maintenance.declaraciones_intereses_prototype import load_declaraciones_intereses_sample_payload
from datosenorden.maintenance.declaraciones_intereses_prototype import render_declaraciones_intereses_summary_text


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


def test_declaraciones_intereses_sample_payload_is_marked_local() -> None:
    payload = load_declaraciones_intereses_sample_payload()

    assert payload["classification"] == "LOCAL_TEST_DATA"
    assert payload["official_status"] == "NOT_OFFICIAL_DATA"
    assert len(payload["records"]) == 2
    assert payload["records"][0]["person_name"] == "SOFIA RAMOS"


def test_declaraciones_intereses_batch_contains_neutral_graph_records() -> None:
    batch = build_declaraciones_intereses_sample_batch(_BatchSession(), load_declaraciones_intereses_sample_payload())

    assert batch.raw_count == 2
    assert len(batch.source_records) == 2
    assert len(batch.evidence) == 2
    assert any(claim.predicate == PERSON_HAS_DECLARATION_PREDICATE for claim in batch.claims)
    assert any(claim.predicate == DECLARATION_REFERENCES_COMPANY_PREDICATE for claim in batch.claims)
    assert all("risk" not in (evidence.excerpt or "").lower() for evidence in batch.evidence)


def test_declaraciones_intereses_summary_renderer_is_neutral() -> None:
    text = render_declaraciones_intereses_summary_text(
        type(
            "Summary",
            (),
            {
                "declarations": 0,
                "people": 0,
                "roles": 0,
                "companies": 0,
                "organizations": 0,
                "relationships": 0,
                "evidence": 0,
                "rows": (),
            },
        )()
    )

    assert "declaraciones_intereses_summary:" in text
    assert "risk" not in text.lower()
    assert "suspicious" not in text.lower()

