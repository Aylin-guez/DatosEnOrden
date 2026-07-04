from __future__ import annotations

from pathlib import Path

from datosenorden.maintenance import knowledge_engine
from datosenorden.web import app_services


def test_load_official_documents_from_local_sample() -> None:
    documents = knowledge_engine.load_official_documents()

    assert len(documents) == 1
    document = documents[0]
    assert document.id == knowledge_engine.DEMO_KNOWLEDGE_DOCUMENT_ID
    assert document.classification == knowledge_engine.LOCAL_TEST_DATA
    assert document.official_status == knowledge_engine.NOT_OFFICIAL_DATA
    assert document.related_expediente_target == knowledge_engine.DEMO_ENTITY_NAME
    assert len(document.sections) >= 4


def test_build_knowledge_digest_creates_rule_based_outputs() -> None:
    digest = knowledge_engine.build_knowledge_demo()

    assert "no agrega antecedentes externos" in digest.citizen_summary
    assert len(digest.key_points) >= 4
    assert len(digest.citizen_questions) >= 3
    assert len(digest.claims) >= 3
    assert len(digest.evidence) == len(digest.document.sections)
    assert digest.connections["expediente"] == knowledge_engine.DEMO_ENTITY_NAME
    assert digest.connections["seguimiento"] == knowledge_engine.DEMO_TRACKING_ITEM_ID
    assert digest.connections["reporte_ciudadano"] == knowledge_engine.DEMO_CITIZEN_REPORT_ID
    assert "irregularidad" in digest.notice


def test_claims_are_verifiable_and_linked_to_evidence() -> None:
    digest = knowledge_engine.build_knowledge_demo()
    evidence_ids = {anchor.id for anchor in digest.evidence}

    for claim in digest.claims:
        assert claim.evidence_ids
        assert set(claim.evidence_ids) <= evidence_ids
        assert "revis" in claim.review_note.lower()
        assert "riesgo" not in claim.claim.lower()


def test_knowledge_services_return_json_safe_payloads(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(app_services, "REAL_DOCUMENT_PUBLICATION_PATH", tmp_path / "missing-publication.json")

    demo = app_services.get_knowledge_demo()
    documents = app_services.get_knowledge_documents()
    digest = app_services.get_knowledge_digest(knowledge_engine.DEMO_KNOWLEDGE_DOCUMENT_ID)

    assert demo["document"]["id"] == knowledge_engine.DEMO_KNOWLEDGE_DOCUMENT_ID
    assert documents[0]["id"] == knowledge_engine.DEMO_KNOWLEDGE_DOCUMENT_ID
    assert digest["claims"][0]["evidence_ids"]
    assert app_services.get_knowledge_digest("missing") == {}


def test_export_knowledge_demo_report_writes_html(tmp_path: Path) -> None:
    output = tmp_path / "knowledge.html"

    path = knowledge_engine.export_knowledge_demo_report(output)
    html = output.read_text(encoding="utf-8")

    assert path == str(output)
    assert "Ficha local de demostracion" in html
    assert "LOCAL_TEST_DATA" in html
    assert "Claims verificables" in html
    assert "no afirma irregularidad" in html.lower()


def test_document_experience_contract_links_summary_to_fragments() -> None:
    digest = knowledge_engine.build_knowledge_demo()

    assert digest.document_reference.document_id == digest.document.id
    assert {page.page for page in digest.pages} == {18, 19, 20, 21}
    assert len(digest.fragments) == len(digest.document.sections)
    assert len(digest.anchors) == len(digest.fragments)
    assert len(digest.citations) == len(digest.fragments)

    fragment_ids = {fragment.id for fragment in digest.fragments}
    citation_ids = {citation.id for citation in digest.citations}
    for point in digest.key_points:
        assert point.document_id == digest.document.id
        assert point.page >= 1
        assert point.fragment_id in fragment_ids
        assert point.citation_id in citation_ids
        assert point.reference_label.startswith("Pagina ")

    for question in digest.citizen_questions:
        assert question.fragment_id in fragment_ids
        assert question.reference_label.startswith("Pagina ")

    for claim in digest.claims:
        assert claim.citation_ids
        assert set(claim.citation_ids) <= citation_ids


def test_knowledge_payload_exposes_viewer_references(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(app_services, "REAL_DOCUMENT_PUBLICATION_PATH", tmp_path / "missing-publication.json")

    payload = app_services.get_knowledge_demo()

    assert payload["pages"][0]["page"] == 18
    assert payload["fragments"][0]["id"] == "frag-metadata-declarada"
    assert payload["anchors"][0]["fragment_id"] == "frag-metadata-declarada"
    assert payload["citations"][0]["quoted_text"]
    assert payload["key_points"][0]["reference_label"].startswith("Pagina ")
    assert payload["evidence"][0]["page"] == 18
    assert payload["evidence"][0]["quoted_text"]
