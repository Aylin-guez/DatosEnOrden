from types import SimpleNamespace

from datosenorden.application.provenance.models import ProvenanceClass
from datosenorden.application.provenance.service import (
    classify_dataset,
    classify_document_id,
    classify_expedient_id,
    combine_derived_classes,
)


def _dataset(name: str, version: str):
    return SimpleNamespace(name=name, version=version)


def test_real_chilecompra_dataset_is_countable() -> None:
    decision = classify_dataset(_dataset("chilecompra-ordenes-compra", "2026-06-18"), SimpleNamespace(name="ChileCompra API Mercado Publico"))
    assert decision.provenance_class is ProvenanceClass.REAL
    assert decision.public_countable is True


def test_demo_test_and_unknown_are_not_real_countable() -> None:
    demo = classify_dataset(_dataset("lobby-meeting-sample", "local-sample-1"), SimpleNamespace(name="DatosEnOrden Lobby Sample"))
    test = classify_dataset(_dataset("local-seed-traceability-flow", "local-seed-1"), SimpleNamespace(name="DatosEnOrden Local Seed"))
    unknown = classify_dataset(_dataset("unseen", "v1"), SimpleNamespace(name="Unseen"))
    assert [demo.provenance_class, test.provenance_class, unknown.provenance_class] == [ProvenanceClass.DEMO, ProvenanceClass.TEST, ProvenanceClass.UNKNOWN]
    assert not any(item.public_countable for item in (demo, test, unknown))


def test_derived_content_fails_closed_for_unknown_or_mixed_inputs() -> None:
    assert combine_derived_classes((ProvenanceClass.REAL, ProvenanceClass.REAL)) is ProvenanceClass.REAL
    assert combine_derived_classes((ProvenanceClass.DEMO, ProvenanceClass.DEMO)) is ProvenanceClass.DEMO
    assert combine_derived_classes((ProvenanceClass.REAL, ProvenanceClass.DEMO)) is ProvenanceClass.UNKNOWN
    assert combine_derived_classes((ProvenanceClass.REAL, ProvenanceClass.UNKNOWN)) is ProvenanceClass.UNKNOWN


def test_document_and_expedient_baselines_are_explicit() -> None:
    assert classify_document_id("senado-docto-9000-mensaje_mocion").provenance_class is ProvenanceClass.REAL
    assert classify_document_id("knowledge-doc-arauco-hospital-demo-2026").provenance_class is ProvenanceClass.DEMO
    assert classify_expedient_id("EXP-001").provenance_class is ProvenanceClass.DEMO
