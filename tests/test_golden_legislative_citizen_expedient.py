from __future__ import annotations

# ruff: noqa: E501
from datetime import UTC, datetime

from datosenorden.application.legislative_ingestion.expedient import EXPEDIENT_ID
from datosenorden.application.legislative_ingestion.golden_expedient import (
    GOLDEN_QUESTION,
    golden_v2_specification,
    provision_golden_v2,
)
from datosenorden.application.provenance.models import ProvenanceClass
from datosenorden.application.real_expedient.citizen_projection import (
    CitizenDocument,
    CitizenEvidence,
    CitizenKnowledgeCutoff,
    CitizenProjectionContext,
    CitizenQuestionAnswer,
    CitizenTimelineEvent,
    citizen_expedient_projection,
)
from datosenorden.application.real_expedient.models import (
    EpistemicClass,
    ExpedientReferences,
    ExpedientSpecification,
    ExpedientStatus,
    NarrativeStatement,
    ReferenceKind,
    StoredExpedient,
)
from datosenorden.application.real_expedient.ports import ReferenceEligibility
from datosenorden.application.real_expedient.service import (
    ExpedientProvisioningService,
    content_fingerprint,
)


class _Repository:
    def __init__(self) -> None:
        self.current: StoredExpedient | None = None
        self.history: list[StoredExpedient] = []

    def get(self, expedient_id: str) -> StoredExpedient | None:
        return (
            self.current
            if self.current and self.current.specification.expedient_id == expedient_id
            else None
        )

    def get_version(self, expedient_id: str, version: int) -> StoredExpedient | None:
        return next(
            (
                item
                for item in self.history
                if item.specification.expedient_id == expedient_id
                and item.specification.version == version
            ),
            None,
        )

    def insert(self, specification: ExpedientSpecification, fingerprint: str) -> StoredExpedient:
        now = datetime(2026, 8, 20, tzinfo=UTC)
        self.current = StoredExpedient(specification, fingerprint, now, now)
        self.history.append(self.current)
        return self.current

    def append_version(
        self,
        specification: ExpedientSpecification,
        fingerprint: str,
        *,
        expected_current_version: int,
    ) -> StoredExpedient:
        assert (
            self.current is not None
            and self.current.specification.version == expected_current_version
        )
        self.current = StoredExpedient(
            specification, fingerprint, self.current.created_at, datetime(2026, 8, 21, tzinfo=UTC)
        )
        self.history.append(self.current)
        return self.current

    def list_public(self) -> tuple[StoredExpedient, ...]:
        return (self.current,) if self.current else ()


class _Eligibility:
    def classify(self, kind: ReferenceKind, reference_id: str) -> ReferenceEligibility:
        return ReferenceEligibility(ProvenanceClass.REAL, True)


def _v1() -> ExpedientSpecification:
    refs = ExpedientReferences(
        ("claim-official",),
        ("evidence-official",),
        entity_ids=("bulletin",),
        source_ids=("senado", "camara"),
    )
    return ExpedientSpecification(
        EXPEDIENT_ID,
        "Título histórico",
        "Pregunta histórica",
        "Resumen histórico",
        ProvenanceClass.REAL,
        ExpedientStatus.PUBLISHED,
        1,
        refs,
        (
            NarrativeStatement(
                "v1-fact",
                "verified",
                "Hecho histórico.",
                EpistemicClass.FACT,
                refs.claim_ids,
                refs.evidence_ids,
            ),
        ),
    )


def _context() -> CitizenProjectionContext:
    evidence = CitizenEvidence(
        "evidence-official",
        "Oficio 36701",
        "Senado de la República",
        "https://www.senado.cl/oficio-36701",
        "Corresponde la formación de una Comisión Mixta.",
        "2026-06-09",
    )
    return CitizenProjectionContext(
        evidence=(evidence,),
        timeline=(
            CitizenTimelineEvent("2023-06-01", "PROCEDURAL", "Cuenta del proyecto."),
            CitizenTimelineEvent("2025-03-25", "PROCEDURAL", "Oficio de ley a Cámara Revisora."),
            CitizenTimelineEvent(
                "2026-03-05", "SUBSTANTIVE", "La Cámara introduce modificaciones."
            ),
            CitizenTimelineEvent(
                "2026-04-21", "SUBSTANTIVE", "Informe de Comisión de Seguridad Pública."
            ),
            CitizenTimelineEvent(
                "2026-06-09", "SUBSTANTIVE", "El Senado rechaza cuatro modificaciones."
            ),
            CitizenTimelineEvent(
                "2026-06-09",
                "PROCEDURAL",
                "Se declara formación de Comisión Mixta.",
                "evidence-official",
            ),
            CitizenTimelineEvent(
                "2026-08-05", "ADMINISTRATIVE", "La Cámara designa integrantes para Comisión Mixta."
            ),
        ),
        actors=(
            "Senado",
            "Cámara de Diputadas y Diputados",
            "Comisión de Seguridad Pública",
            "Comisión Mixta",
            "UAF",
            "SII",
            "Servicio Nacional de Aduanas",
            "Jaime Araya Guerrero",
        ),
        documents=(
            CitizenDocument(
                "Mensaje original",
                "Senado de la República",
                "Mensaje",
                "Propuesta original",
                "https://tramitacion.senado.cl/appsenado/index.php?mo=tramitacion&ac=getDocto&iddocto=16514&tipodoc=mensaje_mocion",
                "2023-06-01",
            ),
            CitizenDocument(
                "Oficio 36701",
                "Senado de la República",
                "Oficio",
                "Tercer trámite",
                "https://www.senado.cl/oficio-36701",
                "2026-06-09",
            ),
        ),
        sources=("Senado de la República", "Cámara de Diputadas y Diputados"),
        answers=(
            CitizenQuestionAnswer(
                "¿Por qué este proyecto terminó en Comisión Mixta?",
                "El Senado aprobó la mayor parte de las enmiendas de Cámara, pero rechazó cuatro modificaciones; el oficio 36701 declara expresamente que corresponde formar Comisión Mixta.",
            ),
            CitizenQuestionAnswer(
                "¿El Senado rechazó que la UAF accediera sin autorización judicial?",
                "No puede afirmarse con la evidencia incorporada: la regla bancaria de Cámara no es D3, que pertenece a la Ley N° 18.046.",
            ),
        ),
        knowledge_cutoff=CitizenKnowledgeCutoff(
            "2026-06-09",
            "2026-08-05",
            "Indica hasta dónde llega la evidencia incorporada y verificada; no afirma que no existan actuaciones posteriores.",
        ),
    )


def test_golden_revision_preserves_v1_and_is_idempotent() -> None:
    repository = _Repository()
    service = ExpedientProvisioningService(repository, _Eligibility())
    first_v1 = service.create_if_absent(_v1())
    first = provision_golden_v2(service, first_v1.expedient.specification)
    second = provision_golden_v2(service, first_v1.expedient.specification)
    assert first.created is True and second.created is False
    assert len(repository.history) == 2
    assert repository.get_version(EXPEDIENT_ID, 1) == first_v1.expedient
    assert first.expedient.specification.question == GOLDEN_QUESTION
    assert (
        content_fingerprint(first.expedient.specification) == second.expedient.content_fingerprint
    )


def test_golden_citizen_projection_keeps_epistemic_boundary_and_human_labels() -> None:
    v2 = golden_v2_specification(_v1())
    stored = StoredExpedient(
        v2,
        content_fingerprint(v2),
        datetime(2026, 8, 20, tzinfo=UTC),
        datetime(2026, 8, 20, tzinfo=UTC),
    )
    view = citizen_expedient_projection(stored, _context())
    assert view["question"] == GOLDEN_QUESTION
    assert len(view["facts"]) == 8
    assert len(view["unknowns"]) == 3
    assert len(view["limitations"]) == 1
    assert len(view["open_questions"]) == 1
    assert "D3 pertenece a la Ley N° 18.046" in view["limitations"][0]["statement"]
    assert all(
        "claim-" not in row["statement"] and "evidence-" not in row["statement"]
        for row in view["facts"]
    )
    assert view["chronology"] == sorted(
        view["chronology"], key=lambda row: (row["date"], row["text"])
    )
    assert view["chronology"][5]["evidence"]["can_view_evidence"] is True
    assert "hasta dónde llega" in view["knowledge_cutoff"]["explanation"].lower()


def test_generic_context_hides_empty_non_applicable_sections_without_expedient_switch() -> None:
    v2 = golden_v2_specification(_v1())
    stored = StoredExpedient(
        v2,
        content_fingerprint(v2),
        datetime(2026, 8, 20, tzinfo=UTC),
        datetime(2026, 8, 20, tzinfo=UTC),
    )
    generic = citizen_expedient_projection(stored, CitizenProjectionContext())
    assert "documents" not in generic and "actors" not in generic
    assert "hypotheses" not in generic["sections"]
    assert generic["title"] == "Tramitación del proyecto de Inteligencia Económica"
