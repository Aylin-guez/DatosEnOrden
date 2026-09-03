"""Deterministic release-time materialization of the approved REAL corpus."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from datosenorden.application.legislative_ingestion.cybersecurity_21663 import (
    provision_cybersecurity_21663,
)
from datosenorden.application.legislative_ingestion.data_protection_21719 import (
    provision_data_protection_21719,
)
from datosenorden.application.legislative_ingestion.escuelas_protegidas import (
    provision_escuelas_protegidas,
)
from datosenorden.application.legislative_ingestion.reconstruccion_nacional import (
    provision_reconstruccion_nacional,
)
from datosenorden.application.provenance.models import ProvenanceClass
from datosenorden.application.real_expedient.control_preventivo_identidad import (
    provision_control_preventivo_identidad,
)
from datosenorden.application.real_expedient.democracia_viva_antofagasta import (
    provision_democracia_viva_antofagasta,
)
from datosenorden.application.real_expedient.eligibility import (
    ProvenanceReferenceEligibility,
)
from datosenorden.application.real_expedient.models import (
    ExpedientStatus,
    ProvisioningResult,
)
from datosenorden.infrastructure.real_expedient.models import RealExpedientRow
from datosenorden.infrastructure.real_expedient.repository import (
    PostgresExpedientRepository,
)

Materializer = Callable[[Session], ProvisioningResult]
EntryMode = Literal["baseline-package", "provisioner"]


class CorpusMaterializationError(RuntimeError):
    """The staging corpus does not satisfy the approved release contract."""


@dataclass(frozen=True)
class ApprovedRealCorpusEntry:
    expedient_id: str
    mode: EntryMode
    provenance_owner: str
    source_manifest: tuple[str, ...]
    materializer: Materializer | None = None


@dataclass(frozen=True)
class CorpusMaterializationResult:
    initial_ids: tuple[str, ...]
    final_ids: tuple[str, ...]
    statuses: tuple[tuple[str, str], ...]
    original_fingerprints: tuple[tuple[str, str], ...]
    original_unchanged: bool


BASELINE_REAL_IDS = (
    "EXP-REAL-CHILECOMPRA-1000813-247-CM26",
    "EXP-REAL-CHILECOMPRA-1002584-197-CM26",
    "EXP-REAL-CHILECOMPRA-1002772-6758-SE26",
    "EXP-REAL-LEGISLATIVE-15975-25",
)

APPROVED_REAL_CORPUS = (
    ApprovedRealCorpusEntry(
        BASELINE_REAL_IDS[0],
        "baseline-package",
        "ChileCompra",
        ("chilecompra-ordenes-compra",),
    ),
    ApprovedRealCorpusEntry(
        BASELINE_REAL_IDS[1],
        "baseline-package",
        "ChileCompra / DIPRES",
        ("chilecompra-ordenes-compra", "dipres-ejecucion-total-programa"),
    ),
    ApprovedRealCorpusEntry(
        BASELINE_REAL_IDS[2],
        "baseline-package",
        "ChileCompra",
        ("chilecompra-ordenes-compra",),
    ),
    ApprovedRealCorpusEntry(
        BASELINE_REAL_IDS[3],
        "baseline-package",
        "Senado / Cámara de Diputadas y Diputados",
        ("senado-legislative-matter", "camara-legislative-matter"),
    ),
    ApprovedRealCorpusEntry(
        "EXP-REAL-ESCUELAS-PROTEGIDAS-18156-04",
        "provisioner",
        "LeyChile / Biblioteca del Congreso Nacional",
        ("leychile-norm", "bcn-law-history"),
        provision_escuelas_protegidas,
    ),
    ApprovedRealCorpusEntry(
        "EXP-REAL-LEGISLATIVE-18216-05",
        "provisioner",
        "Senado / Dirección de Presupuestos",
        ("reconstruccion-nacional",),
        provision_reconstruccion_nacional,
    ),
    ApprovedRealCorpusEntry(
        "EXP-REAL-CYBERSECURITY-14847-06",
        "provisioner",
        "LeyChile / Senado / BCN / Tribunal Constitucional",
        ("cybersecurity-law",),
        provision_cybersecurity_21663,
    ),
    ApprovedRealCorpusEntry(
        "EXP-REAL-DATA-PROTECTION-21719",
        "provisioner",
        "LeyChile / BCN / Tribunal Constitucional",
        ("data-protection-law",),
        provision_data_protection_21719,
    ),
    ApprovedRealCorpusEntry(
        "EXP-REAL-DEMOCRACIA-VIVA-ANTOFAGASTA",
        "provisioner",
        "MINVU / Contraloría / Fiscalía / Poder Judicial",
        ("democracia-viva-antofagasta",),
        provision_democracia_viva_antofagasta,
    ),
    ApprovedRealCorpusEntry(
        "EXP-REAL-CONTROL-PREVENTIVO-IDENTIDAD",
        "provisioner",
        "LeyChile / BCN / Tribunal Constitucional",
        ("control-preventivo-identidad",),
        provision_control_preventivo_identidad,
    ),
)

APPROVED_REAL_IDS = tuple(entry.expedient_id for entry in APPROVED_REAL_CORPUS)


def validate_approved_registry(
    entries: Iterable[ApprovedRealCorpusEntry] = APPROVED_REAL_CORPUS,
) -> tuple[ApprovedRealCorpusEntry, ...]:
    registry = tuple(entries)
    ids = tuple(entry.expedient_id for entry in registry)
    if not registry or len(ids) != len(set(ids)):
        raise CorpusMaterializationError("approved REAL registry contains duplicate IDs")
    if any(not value.startswith("EXP-REAL-") for value in ids):
        raise CorpusMaterializationError("approved REAL registry contains a non-REAL ID")
    for entry in registry:
        if not entry.provenance_owner.strip() or not entry.source_manifest:
            raise CorpusMaterializationError(
                f"approved REAL registry lacks provenance metadata: {entry.expedient_id}"
            )
        if entry.mode == "baseline-package" and entry.materializer is not None:
            raise CorpusMaterializationError(
                f"baseline entry must not execute a materializer: {entry.expedient_id}"
            )
        if entry.mode == "provisioner" and not callable(entry.materializer):
            raise CorpusMaterializationError(
                f"approved materializer is unavailable: {entry.expedient_id}"
            )
    return registry


def materialize_approved_real_corpus(
    session: Session,
    *,
    entries: Iterable[ApprovedRealCorpusEntry] = APPROVED_REAL_CORPUS,
    baseline_ids: tuple[str, ...] = BASELINE_REAL_IDS,
) -> CorpusMaterializationResult:
    registry = validate_approved_registry(entries)
    expected_ids = tuple(entry.expedient_id for entry in registry)
    initial_ids = _current_real_ids(session)
    if initial_ids not in {tuple(sorted(baseline_ids)), tuple(sorted(expected_ids))}:
        raise CorpusMaterializationError(
            "staging database is neither the certified baseline nor the complete approved corpus"
        )
    original_fingerprints = _content_fingerprints(session, baseline_ids)
    statuses: list[tuple[str, str]] = []
    for entry in registry:
        if entry.mode == "baseline-package":
            statuses.append((entry.expedient_id, "preserved"))
            continue
        assert entry.materializer is not None
        try:
            result = entry.materializer(session)
        except Exception as exc:
            raise CorpusMaterializationError(
                f"approved materializer failed: {entry.expedient_id}"
            ) from exc
        actual_id = result.expedient.specification.expedient_id
        if actual_id != entry.expedient_id:
            raise CorpusMaterializationError(
                f"materializer returned unexpected ID for {entry.expedient_id}: {actual_id}"
            )
        statuses.append((entry.expedient_id, "created" if result.created else "preserved"))

    final_ids = assert_approved_corpus_complete(session, entries=registry)
    final_fingerprints = _content_fingerprints(session, baseline_ids)
    original_unchanged = original_fingerprints == final_fingerprints
    if not original_unchanged:
        raise CorpusMaterializationError("materialization changed a certified baseline expedient")
    return CorpusMaterializationResult(
        initial_ids,
        final_ids,
        tuple(statuses),
        original_fingerprints,
        original_unchanged,
    )


def assert_approved_corpus_complete(
    session: Session,
    *,
    entries: Iterable[ApprovedRealCorpusEntry] = APPROVED_REAL_CORPUS,
) -> tuple[str, ...]:
    registry = validate_approved_registry(entries)
    expected_ids = tuple(sorted(entry.expedient_id for entry in registry))
    actual_ids = _current_real_ids(session)
    if actual_ids != expected_ids:
        missing = sorted(set(expected_ids) - set(actual_ids))
        unexpected = sorted(set(actual_ids) - set(expected_ids))
        raise CorpusMaterializationError(
            f"approved REAL corpus is incomplete; missing={missing}, unexpected={unexpected}"
        )

    repository = PostgresExpedientRepository(session)
    for expedient_id in expected_ids:
        stored = repository.get(expedient_id)
        if stored is None:
            raise CorpusMaterializationError(f"approved REAL expedient is absent: {expedient_id}")
        specification = stored.specification
        if (
            specification.provenance_class is not ProvenanceClass.REAL
            or specification.status is not ExpedientStatus.PUBLISHED
        ):
            raise CorpusMaterializationError(
                f"approved expedient is not published REAL: {expedient_id}"
            )
        eligibility = ProvenanceReferenceEligibility(session)
        for kind, reference_ids in specification.references.by_kind().items():
            for reference_id in reference_ids:
                decision = eligibility.classify(kind, reference_id)
                if (
                    decision.provenance_class is not ProvenanceClass.REAL
                    or not decision.public_usable
                ):
                    raise CorpusMaterializationError(
                        "approved expedient has an ineligible reference: "
                        f"{expedient_id}:{kind.value}"
                    )
    return actual_ids


def _current_real_ids(session: Session) -> tuple[str, ...]:
    values = session.scalars(
        select(RealExpedientRow.expedient_id).where(
            RealExpedientRow.provenance_class == ProvenanceClass.REAL.value
        )
    ).all()
    return tuple(sorted(str(value) for value in values))


def _content_fingerprints(
    session: Session, expedient_ids: Iterable[str]
) -> tuple[tuple[str, str], ...]:
    repository = PostgresExpedientRepository(session)
    fingerprints: list[tuple[str, str]] = []
    for expedient_id in sorted(expedient_ids):
        stored = repository.get(expedient_id)
        if stored is None:
            raise CorpusMaterializationError(
                f"certified baseline expedient is absent: {expedient_id}"
            )
        fingerprints.append((expedient_id, stored.content_fingerprint))
    return tuple(fingerprints)
