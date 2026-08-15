from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from datosenorden.application.laboratory.service import get_expedient
from datosenorden.application.provenance import classify_expedient_id
from datosenorden.application.provenance.models import ProvenanceClass
from datosenorden.application.real_expedient import (
    EpistemicClass,
    ExpedientConflictError,
    ExpedientProvisioningService,
    ExpedientReferenceError,
    ExpedientReferences,
    ExpedientSpecification,
    ExpedientStatus,
    NarrativeStatement,
    ReferenceEligibility,
    ReferenceKind,
    StoredExpedient,
    public_expedient_projection,
)


class FakeRepository:
    def __init__(self) -> None:
        self.current: dict[str, StoredExpedient] = {}
        self.history: dict[str, list[StoredExpedient]] = {}

    def get(self, expedient_id: str) -> StoredExpedient | None:
        return self.current.get(expedient_id)

    def insert(
        self, specification: ExpedientSpecification, content_fingerprint: str
    ) -> StoredExpedient:
        now = datetime(2026, 8, 12, tzinfo=UTC)
        stored = StoredExpedient(specification, content_fingerprint, now, now)
        self.current[specification.expedient_id] = stored
        self.history[specification.expedient_id] = [stored]
        return stored

    def append_version(
        self,
        specification: ExpedientSpecification,
        content_fingerprint: str,
        *,
        expected_current_version: int,
    ) -> StoredExpedient:
        previous = self.current[specification.expedient_id]
        assert previous.specification.version == expected_current_version
        stored = StoredExpedient(
            specification,
            content_fingerprint,
            previous.created_at,
            datetime(2026, 8, 13, tzinfo=UTC),
        )
        self.current[specification.expedient_id] = stored
        self.history[specification.expedient_id].append(stored)
        return stored

    def list_public(self) -> tuple[StoredExpedient, ...]:
        return tuple(self.current.values())


class FakeEligibility:
    def __init__(
        self,
        accepted: set[tuple[ReferenceKind, str]],
        overrides: dict[tuple[ReferenceKind, str], ReferenceEligibility] | None = None,
    ) -> None:
        self.accepted = accepted
        self.overrides = overrides or {}

    def classify(self, kind: ReferenceKind, reference_id: str) -> ReferenceEligibility:
        key = (kind, reference_id)
        return self.overrides.get(
            key,
            ReferenceEligibility(ProvenanceClass.REAL, public_usable=key in self.accepted),
        )


def _references() -> ExpedientReferences:
    return ExpedientReferences(
        claim_ids=("claim-real",),
        evidence_ids=("evidence-real",),
        relationship_ids=("relationship-real",),
        entity_ids=("entity-real",),
        document_ids=("document-real",),
        source_ids=("source-real",),
    )


def _accepted(references: ExpedientReferences | None = None) -> set[tuple[ReferenceKind, str]]:
    resolved = references or _references()
    return {(kind, item) for kind, values in resolved.by_kind().items() for item in values}


def _specification(
    *,
    expedient_id: str = "EXP-CONTRACT-TEST",
    provenance_class: ProvenanceClass = ProvenanceClass.REAL,
    status: ExpedientStatus = ExpedientStatus.PUBLISHED,
    version: int = 1,
    summary: str = "Resumen respaldado.",
) -> ExpedientSpecification:
    references = _references()
    return ExpedientSpecification(
        expedient_id=expedient_id,
        title="Expediente contractual de prueba",
        question="¿Qué muestran las referencias existentes?",
        summary=summary,
        provenance_class=provenance_class,
        status=status,
        version=version,
        references=references,
        statements=(
            NarrativeStatement(
                statement_id="statement-1",
                section="what_we_know",
                text="La afirmación está respaldada.",
                epistemic_class=EpistemicClass.FACT,
                claim_ids=("claim-real",),
                evidence_ids=("evidence-real",),
            ),
        ),
    )


def _service() -> tuple[ExpedientProvisioningService, FakeRepository]:
    repository = FakeRepository()
    return ExpedientProvisioningService(repository, FakeEligibility(_accepted())), repository


def test_real_expedient_provisions_reopens_and_is_idempotent() -> None:
    service, repository = _service()
    specification = _specification()

    first = service.create_if_absent(specification)
    repeated = service.create_if_absent(specification)

    assert first.created is True
    assert repeated.created is False
    assert service.get(specification.expedient_id) == first.expedient
    assert len(repository.history[specification.expedient_id]) == 1
    assert first.expedient.specification.version == 1


def test_incompatible_same_id_is_an_explicit_conflict() -> None:
    service, _ = _service()
    service.create_if_absent(_specification())

    with pytest.raises(ExpedientConflictError, match="incompatible content"):
        service.create_if_absent(_specification(summary="Contenido distinto."))


def test_revision_preserves_history_and_requires_next_version() -> None:
    service, repository = _service()
    service.create_if_absent(_specification())

    revised = service.revise(
        _specification(version=2, summary="Resumen v2 respaldado."),
        expected_current_version=1,
    )

    assert revised.specification.version == 2
    assert [item.specification.version for item in repository.history["EXP-CONTRACT-TEST"]] == [
        1,
        2,
    ]
    assert repository.history["EXP-CONTRACT-TEST"][0].specification.summary == "Resumen respaldado."


@pytest.mark.parametrize(
    ("provenance_class", "public_usable"),
    [
        (ProvenanceClass.DEMO, True),
        (ProvenanceClass.TEST, True),
        (ProvenanceClass.UNKNOWN, True),
        (ProvenanceClass.REAL, False),
    ],
)
def test_real_expedient_fails_closed_for_any_non_real_usable_reference(
    provenance_class: ProvenanceClass,
    public_usable: bool,
) -> None:
    references = _references()
    accepted = _accepted(references)
    evidence_key = (ReferenceKind.EVIDENCE, "evidence-real")
    repository = FakeRepository()
    service = ExpedientProvisioningService(
        repository,
        FakeEligibility(
            accepted,
            {evidence_key: ReferenceEligibility(provenance_class, public_usable)},
        ),
    )

    with pytest.raises(ExpedientReferenceError, match="evidence"):
        service.create_if_absent(_specification())

    assert repository.current == {}


def test_real_expedient_requires_claim_evidence_and_source_references() -> None:
    specification = replace(
        _specification(),
        references=ExpedientReferences(claim_ids=("claim-real",), evidence_ids=("evidence-real",)),
        statements=(),
    )
    service = ExpedientProvisioningService(FakeRepository(), FakeEligibility(set()))

    with pytest.raises(ExpedientReferenceError, match="claim, evidence, and source"):
        service.create_if_absent(specification)


def test_missing_provenance_is_not_accepted_as_real() -> None:
    with pytest.raises(ValueError, match="provenance must be explicit"):
        replace(_specification(), provenance_class=None)  # type: ignore[arg-type]


def test_duplicate_references_are_rejected() -> None:
    with pytest.raises(ValueError, match="non-empty and unique"):
        ExpedientReferences(
            claim_ids=("claim-real", "claim-real"),
            evidence_ids=("evidence-real",),
            source_ids=("source-real",),
        )


def test_factual_narrative_requires_structured_support() -> None:
    with pytest.raises(ValueError, match="require claim or evidence support"):
        NarrativeStatement("statement", "what_we_know", "Afirmación.", EpistemicClass.FACT)


def test_public_projection_is_sanitized_and_resolves_reference_ids() -> None:
    service, _ = _service()
    stored = service.create_if_absent(_specification()).expedient

    projected = public_expedient_projection(stored)

    assert projected["id"] == "EXP-CONTRACT-TEST"
    assert projected["references"]["claims"] == ["claim-real"]  # type: ignore[index]
    assert projected["statements"][0]["evidence_ids"] == ["evidence-real"]  # type: ignore[index]
    assert "content_fingerprint" not in projected
    assert "internal_metadata" not in projected


def test_public_projection_rejects_draft_and_local_paths() -> None:
    service, _ = _service()
    draft = service.create_if_absent(_specification(status=ExpedientStatus.DRAFT)).expedient
    with pytest.raises(ValueError, match="only published"):
        public_expedient_projection(draft)

    public_service, _ = _service()
    unsafe = replace(_specification(), summary=r"C:\Users\operator\internal.txt")
    projected = public_expedient_projection(public_service.create_if_absent(unsafe).expedient)
    assert projected["summary"] == ""


@pytest.mark.parametrize("provenance_class", [ProvenanceClass.TEST, ProvenanceClass.UNKNOWN])
def test_test_and_unknown_expedients_have_no_public_projection(
    provenance_class: ProvenanceClass,
) -> None:
    service, _ = _service()
    stored = service.create_if_absent(_specification(provenance_class=provenance_class)).expedient
    with pytest.raises(ValueError, match="only REAL or DEMO"):
        public_expedient_projection(stored)


def test_public_listing_excludes_non_published_versions() -> None:
    references = _references()
    repository = FakeRepository()
    service = ExpedientProvisioningService(repository, FakeEligibility(_accepted(references)))
    service.create_if_absent(_specification(expedient_id="EXP-PUBLISHED"))
    service.create_if_absent(_specification(expedient_id="EXP-DRAFT", status=ExpedientStatus.DRAFT))

    assert [item.specification.expedient_id for item in service.list_public()] == ["EXP-PUBLISHED"]


def test_exp_001_remains_the_legacy_demo() -> None:
    assert classify_expedient_id("EXP-001").provenance_class is ProvenanceClass.DEMO
    assert get_expedient("EXP-001")["id"] == "EXP-001"  # type: ignore[index]
